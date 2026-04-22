import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <header className="mb-12 border-b border-border pb-8">
        <div className="mb-3 text-sm font-medium uppercase tracking-wider text-muted-foreground">
          B2G Surveillance Platform · 2026
        </div>
        <h1 className="text-4xl font-bold tracking-tight">🦠 Urban Immune System</h1>
        <p className="mt-3 text-lg text-muted-foreground">
          3-Layer 비의료 신호 교차검증으로 감염병을 1~3주 선행 감지하는 AI 조기경보 서비스
        </p>
      </header>

      <section className="mb-12 grid gap-6 md:grid-cols-3">
        <LayerCard title="💊 약국 OTC" hint="~2주 선행" desc="네이버 쇼핑인사이트" />
        <LayerCard title="🚰 하수 바이오마커" hint="~3주 선행" desc="환경부 KOWAS" />
        <LayerCard title="🔍 검색 트렌드" hint="~1주 선행" desc="네이버 데이터랩" />
      </section>

      <section className="mb-12 rounded-lg border border-border bg-muted/40 p-6">
        <h2 className="mb-4 text-xl font-semibold">개발 현황</h2>
        <ul className="space-y-2 text-sm">
          <li>✅ 실측 재현 가능 성능 — F1 0.643 · MCC 0.442 · AUPRC 0.885 (seed=42)</li>
          <li>✅ Conservative 대시보드 — 전국 17개 시도 · 전라 권역 L4 경보 시나리오</li>
          <li>✅ KRDS v1.1.0 + Okabe-Ito CUD 2-Tier 디자인 토큰 시스템</li>
          <li>🟡 SSE 실시간 경보 · MapLibre 교체 · ECharts 5 전환 예정</li>
          <li>🟡 Innovative (Brutalist) 변형 · JWT 인증 · PDF 다운로드 실구현</li>
        </ul>
        <div className="mt-6 flex gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            감시 대시보드 열기 →
          </Link>
          <Link
            href="http://localhost:3000/dashboard"
            className="inline-flex items-center gap-2 rounded-md border border-border px-4 py-2 text-sm font-medium"
          >
            EN Preview
          </Link>
        </div>
      </section>

      <footer className="text-sm text-muted-foreground">
        <p>
          내부 데모 대시보드는{" "}
          <Link href="http://34.64.124.90:8501" className="font-medium underline">
            Streamlit (포트 8501)
          </Link>{" "}
          에서 확인 가능합니다.
        </p>
        <p className="mt-2 opacity-70">
          Powered by 2026 AI 아이디어 공모전 대상 수상 연구 · © 2026 Urban Immune System
        </p>
      </footer>
    </main>
  );
}

function LayerCard({ title, hint, desc }: { title: string; hint: string; desc: string }) {
  return (
    <article className="rounded-lg border border-border bg-background p-5">
      <div className="text-lg font-semibold">{title}</div>
      <div className="mt-1 text-sm font-medium text-primary">{hint}</div>
      <div className="mt-2 text-sm text-muted-foreground">{desc}</div>
    </article>
  );
}
