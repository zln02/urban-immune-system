"""임상 검증 (실데이터·누수 제거판) — analysis/outputs/clinical_validation_real.{json,png}

기존 backtest_17regions(F1=0.907)의 한계:
  - 타깃이 DB confirmed_cases인데 그 confirmed_cases가 layer_signals와 동일 곡선에서
    합성된 seed라 r≈1.0 공선 → 모델이 사실상 자기 입력을 예측(순환).
이 스크립트는 그 누수를 제거한다:
  - 임상 truth = **외부 독립** WHO FluNet 한국 인플루엔자 양성률(INF_ALL/SPEC_PROCESSED_NB).
  - 선행신호 = 실 네이버 L1(쇼핑인사이트 감기약)·L3(검색), 실 KOWAS L2(하수, 캐시 시계열).
  - 검정 = (A) lead-lag CCF, (B) Granger 증분(순/역), (C) **walk-forward 외표본 예측 skill**
    (확장창 OLS로 h주 후 임상을 예측 → persistence/AR 기준선 대비 MAE 개선율).
    => 동일데이터 in-sample CV가 아니라 미래구간 예측이라 누수 없음.

의존성: httpx, numpy, pandas, scipy, matplotlib (repo .venv 에 존재).
실행: PYTHONPATH=. .venv/bin/python analysis/clinical_validation_real.py
"""
from __future__ import annotations
import os, json, warnings
from pathlib import Path
import httpx, numpy as np, pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
OUT = Path(__file__).resolve().parent / "outputs"
L2_CSV = OUT / "kowas_l2_series.csv"
START, END = "2016-01-01", "2026-06-15"

CID = os.environ.get("NAVER_CLIENT_ID"); CSEC = os.environ.get("NAVER_CLIENT_SECRET")
NAV_H = {"X-Naver-Client-Id": CID, "X-Naver-Client-Secret": CSEC, "Content-Type": "application/json"}


# ── 데이터 ────────────────────────────────────────────────────────────
def fetch_who() -> pd.DataFrame:
    """WHO FluNet 한국 양성률 — 외부 독립 임상 truth."""
    base = "https://xmart-api-public.who.int/FLUMART/VIW_FNT"
    with httpx.Client(timeout=120, follow_redirects=True) as c:
        r = c.get(base, params={
            "$filter": "COUNTRY_CODE eq 'KOR' and ISO_YEAR ge 2016",
            "$select": "ISO_WEEKSTARTDATE,SPEC_PROCESSED_NB,INF_ALL",
            "$orderby": "ISO_WEEKSTARTDATE", "$format": "streaming"})
    w = pd.DataFrame(r.json()["value"])
    w["date"] = pd.to_datetime(w["ISO_WEEKSTARTDATE"]).dt.date
    w["spec"] = pd.to_numeric(w["SPEC_PROCESSED_NB"], errors="coerce")
    w["pos"] = pd.to_numeric(w["INF_ALL"], errors="coerce")
    w["positivity"] = (w["pos"] / w["spec"] * 100).where(w["spec"] > 0)
    return w[["date", "positivity"]].dropna()


def fetch_search() -> pd.DataFrame:
    payload = {"startDate": START, "endDate": END, "timeUnit": "week",
               "keywordGroups": [{"groupName": "flu",
                                  "keywords": ["독감 증상", "인플루엔자", "고열 원인", "몸살 원인", "타미플루"]}]}
    r = httpx.post("https://openapi.naver.com/v1/datalab/search", headers=NAV_H, json=payload, timeout=60)
    d = pd.DataFrame(r.json()["results"][0]["data"])
    d["date"] = pd.to_datetime(d["period"]).dt.date
    return d.rename(columns={"ratio": "L3_search"})[["date", "L3_search"]]


def fetch_shopping() -> pd.DataFrame | None:
    payload = {"startDate": "2017-08-01", "endDate": END, "timeUnit": "week",
               "category": [{"name": "감기약", "param": ["50000167"]}]}
    r = httpx.post("https://openapi.naver.com/v1/datalab/shopping/categories", headers=NAV_H, json=payload, timeout=60)
    js = r.json()
    if "results" not in js or not js["results"]:
        print("  [L1 쇼핑] 응답오류:", str(js)[:200]); return None
    d = pd.DataFrame(js["results"][0]["data"])
    d["date"] = pd.to_datetime(d["period"]).dt.date
    return d.rename(columns={"ratio": "L1_otc"})[["date", "L1_otc"]]


def load_l2() -> pd.DataFrame | None:
    if not L2_CSV.exists():
        print("  [L2] 캐시 없음 → 제외"); return None
    d = pd.read_csv(L2_CSV)
    d["iso"] = d["year"].astype(int) * 100 + d["week"].astype(int)  # ISO year*100+week 키
    return d.rename(columns={"l2_wastewater": "L2_wastewater"})[["iso", "L2_wastewater"]]


def _iso_key(dates) -> np.ndarray:
    """date 시리즈 → ISO year*100+week (WHO·KOWAS 요일 정렬 불일치 흡수)."""
    iso = pd.to_datetime(pd.Series(list(dates))).dt.isocalendar()
    return (iso["year"].astype(int) * 100 + iso["week"].astype(int)).to_numpy()


# ── 통계 ──────────────────────────────────────────────────────────────
def ccf(x, y, kmin=-4, kmax=8):
    best = (None, -9.0); curve = []
    for k in range(kmin, kmax + 1):
        if k >= 0: a, b = x[:len(x) - k], y[k:]
        else:      a, b = x[-k:], y[:len(y) + k]
        if len(a) > 20 and a.std() > 0 and b.std() > 0:
            rr = float(np.corrcoef(a, b)[0, 1]); curve.append([k, rr])
            if rr > best[1]: best = (k, rr)
    return best, curve


def _ols_rss(X, y):
    b, _, _, _ = np.linalg.lstsq(X, y, rcond=None); res = y - X @ b
    return float(res @ res)


def granger(target, exogs, p=4):
    n = len(target); Y, AR, EX = [], [], []
    for t in range(p, n):
        Y.append(target[t]); AR.append([target[t - 1 - i] for i in range(p)])
        ex = []
        for e in exogs: ex += [e[t - 1 - i] for i in range(p)]
        EX.append(ex)
    Y, AR, EX = np.array(Y), np.array(AR), np.array(EX); one = np.ones((len(Y), 1))
    Xr = np.hstack([one, AR]); Xf = np.hstack([one, AR, EX])
    rss_r, rss_f = _ols_rss(Xr, Y), _ols_rss(Xf, Y)
    q = EX.shape[1]; dfden = len(Y) - Xf.shape[1]
    F = ((rss_r - rss_f) / q) / (rss_f / dfden); pval = float(1 - stats.f.cdf(F, q, dfden))
    tss = ((Y - Y.mean()) ** 2).sum()
    return dict(F=float(F), p=pval, r2_ar=1 - rss_r / tss, r2_full=1 - rss_f / tss)


def walk_forward_skill(y, signals, horizon, p=3, min_train=40):
    """확장창 외표본 예측 skill. 각 t에서 ≤t 데이터로 OLS 적합 → y(t+h) 예측.
    반환: model/persistence/AR 의 MAE 와 skill(=1-MAE_model/MAE_base)."""
    n = len(y); preds = {"model": [], "ar": [], "persist": [], "truth": []}
    feat_lags = list(signals.values())
    for t in range(min_train, n - horizon):
        # 학습표본: tau in [p, t], 타깃 y[tau+h]
        rows_ar, rows_full, ys = [], [], []
        for tau in range(p, t - horizon + 1):
            ar = [y[tau - i] for i in range(p)]
            ex = []
            for sig in feat_lags: ex += [sig[tau - i] for i in range(p)]
            rows_ar.append([1.0] + ar); rows_full.append([1.0] + ar + ex); ys.append(y[tau + horizon])
        if len(ys) < 12: continue
        Xar, Xfull, yt = np.array(rows_ar), np.array(rows_full), np.array(ys)
        bar, _, _, _ = np.linalg.lstsq(Xar, yt, rcond=None)
        bfull, _, _, _ = np.linalg.lstsq(Xfull, yt, rcond=None)
        ar_now = [y[t - i] for i in range(p)]
        ex_now = []
        for sig in feat_lags: ex_now += [sig[t - i] for i in range(p)]
        preds["ar"].append(float(np.array([1.0] + ar_now) @ bar))
        preds["model"].append(float(np.array([1.0] + ar_now + ex_now) @ bfull))
        preds["persist"].append(float(y[t]))            # 기준선: 마지막 관측 유지
        preds["truth"].append(float(y[t + horizon]))
    truth = np.array(preds["truth"])
    if len(truth) < 10:
        return None
    mae = {k: float(np.mean(np.abs(np.array(preds[k]) - truth))) for k in ("model", "ar", "persist")}
    return dict(n_oos=len(truth), mae_model=mae["model"], mae_ar=mae["ar"], mae_persist=mae["persist"],
                skill_vs_persist=1 - mae["model"] / mae["persist"] if mae["persist"] else None,
                skill_vs_ar=1 - mae["model"] / mae["ar"] if mae["ar"] else None)


# ── 실행 ──────────────────────────────────────────────────────────────
def main():
    print("실데이터 수집 중 (WHO FluNet + Naver L1/L3 + KOWAS L2)...")
    who = fetch_who(); print(f"[WHO 임상]  {len(who)}주  {who['date'].min()} ~ {who['date'].max()}")
    s3 = fetch_search(); print(f"[L3 검색]   {len(s3)}주")
    s1 = fetch_shopping(); l2 = load_l2()

    m = pd.merge(who, s3, on="date", how="inner")
    layers = ["L3_search"]
    if s1 is not None: m = pd.merge(m, s1, on="date", how="inner"); layers = ["L1_otc", "L3_search"]
    m = m.sort_values("date").reset_index(drop=True)

    result = {
        "generated_for": "clinical validation (real data, leakage-free)",
        "clinical_truth": "WHO FluNet Korea influenza positivity (INF_ALL/SPEC_PROCESSED_NB) — EXTERNAL, independent of model inputs",
        "contrast_with": "analysis/outputs/backtest_17regions.json (F1=0.907) uses DB confirmed_cases which is seed-synthetic & collinear with inputs (circular)",
        "layers_validated": layers + (["L2_wastewater"] if l2 is not None else []),
        "blocks": {}, "leadlag": {}, "granger": {}, "forecast_skill": {},
        "caveats": [
            "L1/L3 are national Naver values (no regional resolution) — regional claims not supported by this test.",
            "L2 (KOWAS) only ~65 weeks (1 season since 2025-03) — low power to separate lead vs contemporaneous.",
            "CCF/Granger test temporal precedence, NOT prediction skill. Forecast-skill block is the predictive test.",
        ],
    }

    def block(df, cols, label, key):
        if len(df) < 40:
            print(f"\n[{label}] n={len(df)} (부족, 스킵)"); return
        y = df["positivity"].to_numpy(float)
        print(f"\n{'='*64}\n[{label}] n={len(df)}주  {df['date'].min()} ~ {df['date'].max()}  계층={cols}")
        ll, gg = {}, {}
        for c in cols:
            x = df[c].to_numpy(float)
            (k, r), curve = ccf(x, y)
            g_fwd = granger(y, [x]); g_rev = granger(x, [y])
            verdict = "선행" if (k or 0) > 0 else ("동시" if k == 0 else "후행")
            ll[c] = {"best_lag_weeks": k, "best_r": round(r, 3), "verdict": verdict, "curve": curve}
            gg[c] = {"fwd_F": round(g_fwd["F"], 2), "fwd_p": g_fwd["p"],
                     "fwd_dR2": round(g_fwd["r2_full"] - g_fwd["r2_ar"], 4),
                     "rev_F": round(g_rev["F"], 2), "rev_p": g_rev["p"],
                     "unidirectional": g_fwd["p"] < 0.05 and g_rev["p"] >= 0.05}
            print(f"  {c:13}: CCF r={r:+.3f}@k={k:+d}({verdict}) | Granger 순 p={g_fwd['p']:.3f}"
                  f" 역 p={g_rev['p']:.3f} {'단방향✓' if gg[c]['unidirectional'] else ''}")
        result["leadlag"][key] = ll; result["granger"][key] = gg
        result["blocks"][key] = {"label": label, "n_weeks": len(df),
                                 "start": str(df["date"].min()), "end": str(df["date"].max())}

    block(m, layers, "전체 기간", "all")
    block(m[pd.to_datetime(m.date).dt.year <= 2019].reset_index(drop=True), layers, "COVID 이전 2016–2019(청정)", "pre_covid")

    # L2 블록 (겹치는 기간만)
    if l2 is not None:
        who2 = who.copy(); who2["iso"] = _iso_key(who2["date"])
        m2 = pd.merge(who2, l2, on="iso", how="inner").sort_values("date").reset_index(drop=True)
        block(m2, ["L2_wastewater"], "L2 하수 vs 임상 (KOWAS 겹침)", "l2")

    # ── walk-forward 외표본 예측 skill (핵심: 누수 없는 예측검정) ──
    print(f"\n{'='*64}\n[Walk-forward 외표본 예측 skill]  (신호 결합이 임상 h주후 예측을 개선?)")
    y = m["positivity"].to_numpy(float)
    sig = {c: m[c].to_numpy(float) for c in layers}
    for h in (1, 2, 3, 4):
        sk = walk_forward_skill(y, sig, h)
        if sk:
            result["forecast_skill"][f"h{h}"] = sk
            print(f"  h={h}주: n_oos={sk['n_oos']}  MAE 모델={sk['mae_model']:.2f} vs persist={sk['mae_persist']:.2f}"
                  f" vs AR={sk['mae_ar']:.2f}  | skill vs persist={sk['skill_vs_persist']:+.1%}"
                  f" vs AR={sk['skill_vs_ar']:+.1%}")

    (OUT / "clinical_validation_real.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[저장] {OUT/'clinical_validation_real.json'}")
    make_plot(result, m, layers)
    return result, m, l2, who, layers


def _z(a):
    a = np.asarray(a, float); return (a - np.nanmean(a)) / (np.nanstd(a) + 1e-9)


def make_plot(result, m, layers):
    """선행성 시각화: (1) 임상 vs 신호 표준화 시계열, (2) 계층별 CCF 곡선, (3) walk-forward MAE."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(18, 5.2))
    COL = {"L1_otc": "#e8590c", "L3_search": "#1c7ed6", "L2_wastewater": "#2f9e44", "clinical": "#212529"}

    # (1) 표준화 시계열 — 임상 vs L1 (선행 강조)
    dts = pd.to_datetime(m["date"])
    ax[0].plot(dts, _z(m["positivity"]), color=COL["clinical"], lw=2.2, label="Clinical (WHO FluNet positivity)")
    for c in layers:
        ax[0].plot(dts, _z(m[c]), color=COL.get(c, "#888"), lw=1.3, alpha=0.85, label=c)
    ax[0].set_title("Real signals vs independent clinical truth (z-score)", fontsize=11)
    ax[0].legend(fontsize=8, loc="upper left"); ax[0].grid(alpha=0.25)

    # (2) CCF 곡선 (전체기간 + 청정기 L1)
    src = result["leadlag"].get("pre_covid") or result["leadlag"].get("all", {})
    for c, d in src.items():
        curve = np.array(d["curve"]);
        if len(curve):
            ax[1].plot(curve[:, 0], curve[:, 1], "-o", ms=3, color=COL.get(c, "#888"), label=c)
            k = d["best_lag_weeks"]; ax[1].scatter([k], [d["best_r"]], s=90, color=COL.get(c, "#888"),
                                                   zorder=5, edgecolor="k", linewidth=0.7)
    # L2 (별도 블록)
    if "l2" in result["leadlag"]:
        d = result["leadlag"]["l2"]["L2_wastewater"]; curve = np.array(d["curve"])
        if len(curve): ax[1].plot(curve[:, 0], curve[:, 1], "-o", ms=3, color=COL["L2_wastewater"], label="L2_wastewater")
    ax[1].axvline(0, color="k", lw=0.8, ls="--"); ax[1].axhline(0, color="#aaa", lw=0.6)
    ax[1].set_xlabel("lag k (weeks); k>0 = signal LEADS clinical"); ax[1].set_ylabel("cross-correlation r")
    ax[1].set_title("Lead-lag CCF — L1 OTC leads +6~7wk (unidirectional)", fontsize=11)
    ax[1].legend(fontsize=8); ax[1].grid(alpha=0.25)

    # (3) walk-forward 외표본 MAE
    fs = result["forecast_skill"]
    if fs:
        hs = sorted(fs.keys()); x = np.arange(len(hs)); w = 0.26
        ax[2].bar(x - w, [fs[h]["mae_model"] for h in hs], w, label="model (AR+signals)", color="#e8590c")
        ax[2].bar(x, [fs[h]["mae_ar"] for h in hs], w, label="AR-only baseline", color="#868e96")
        ax[2].bar(x + w, [fs[h]["mae_persist"] for h in hs], w, label="persistence", color="#adb5bd")
        ax[2].set_xticks(x); ax[2].set_xticklabels([h.replace("h", "+") + "wk" for h in hs])
        ax[2].set_ylabel("out-of-sample MAE (lower=better)")
        ax[2].set_title("Walk-forward forecast skill — signals do NOT beat persistence", fontsize=11)
        ax[2].legend(fontsize=8); ax[2].grid(alpha=0.25, axis="y")

    fig.suptitle("Clinical validation (REAL data, leakage-free) — WHO FluNet truth | "
                 "L1 pharmacy OTC is the only validated leading indicator", fontsize=12, y=1.02)
    fig.tight_layout()
    png = OUT / "clinical_validation_real.png"
    fig.savefig(png, dpi=130, bbox_inches="tight")
    print(f"[저장] {png}")
    # 대시보드 공개경로에도 복사(존재 시)
    pub = Path("/home/ubuntu/urban-immune-system/frontend/public/data")
    if pub.exists():
        fig.savefig(pub / "clinical_validation_real.png", dpi=130, bbox_inches="tight")
        print(f"[저장] {pub/'clinical_validation_real.png'}")
    plt.close(fig)


if __name__ == "__main__":
    main()
