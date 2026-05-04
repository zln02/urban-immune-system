"""KOWAS 주간보고 PDF 자동 다운로더.

질병관리청 감염병포털 게시판(q_bbsSn=1010, q_clsfNo=4)에서
하수기반 감염병 감시 주간 분석보고 PDF를 일괄 다운로드한다.

- 게시판 목록 → 게시글 ID(q_bbsDocNo) 추출
- 상세 페이지 → 첨부파일 ID(q_fileSn, q_fileId) 추출
- ND_fileDownload.do 로 PDF 다운로드 → pipeline/data/kowas/

검증: 2026-04-24 기준 156주차까지 정상 다운로드 확인.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

KDCA_BASE = "https://dportal.kdca.go.kr"
LIST_URL = f"{KDCA_BASE}/pot/bbs/BD_selectBbsList.do"
DETAIL_URL = f"{KDCA_BASE}/pot/bbs/BD_selectBbs.do"
DOWNLOAD_URL = f"{KDCA_BASE}/pot/component/file/ND_fileDownload.do"

# 하수기반 감염병 감시 주간 분석 보고 게시판 식별자
BBS_SN = "1010"
CLSF_NO = "4"

USER_AGENT = "Mozilla/5.0 (compatible; UIS-KOWAS-Crawler/1.0; capstone-research)"

DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "data" / "kowas"


@dataclass(frozen=True)
class KowasReport:
    """KOWAS 주간보고 메타데이터."""

    bbs_doc_no: str       # 게시글 ID
    title: str            # 게시글 제목 (예: "2026년 15주차 ...")
    year: int | None      # 보고 연도
    week: int | None      # 보고 주차

    @property
    def filename(self) -> str:
        if self.year and self.week:
            return f"kowas_{self.year}_w{self.week:02d}.pdf"
        return f"kowas_{self.bbs_doc_no}.pdf"


def _make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=30.0,
        follow_redirects=True,
    )


def list_reports(client: httpx.Client, max_pages: int = 16) -> list[KowasReport]:
    """게시판을 순회해 모든 KOWAS 주간보고 메타데이터를 수집한다.

    페이지당 10건 기본. max_pages * 10 건이 상한 (2026-04 기준 156건 → 16페이지면 충분).
    """
    seen: dict[str, KowasReport] = {}
    title_pattern = re.compile(
        r"q_bbsDocNo=(\d{17})[^>]*>\s*([^<]*?(?:(\d{4})년\s*(\d{1,2})주차[^<]*?))</a"
    )
    fallback_pattern = re.compile(r"q_bbsDocNo=(\d{17})")

    for page in range(1, max_pages + 1):
        params = {
            "q_bbsSn": BBS_SN,
            "q_clsfNo": CLSF_NO,
            "q_currPage": str(page),
        }
        resp = client.get(LIST_URL, params=params)
        resp.raise_for_status()
        html = resp.text

        page_hits = 0
        for m in title_pattern.finditer(html):
            doc_no, title, year, week = m.group(1), m.group(2).strip(), m.group(3), m.group(4)
            if doc_no in seen:
                continue
            seen[doc_no] = KowasReport(
                bbs_doc_no=doc_no,
                title=re.sub(r"\s+", " ", title),
                year=int(year) if year else None,
                week=int(week) if week else None,
            )
            page_hits += 1

        # 제목 패턴 미스 시 fallback (구조 변경 대비)
        if page_hits == 0:
            for m in fallback_pattern.finditer(html):
                doc_no = m.group(1)
                seen.setdefault(
                    doc_no,
                    KowasReport(bbs_doc_no=doc_no, title="(unknown)", year=None, week=None),
                )

        # 페이지 결과 0건이면 끝
        if not re.search(r"q_currPage=" + str(page + 1), html) and page_hits == 0:
            break

        time.sleep(0.5)

    return sorted(seen.values(), key=lambda r: r.bbs_doc_no, reverse=True)


_FILE_LINK_PATTERN = re.compile(
    r"/pot/component/file/ND_fileDownload\.do\?q_fileSn=(\d+)&(?:amp;)?q_fileId=([a-f0-9-]+)"
)


def fetch_pdf_links(client: httpx.Client, report: KowasReport) -> list[tuple[str, str]]:
    """상세 페이지에서 첨부파일(q_fileSn, q_fileId) 페어를 모두 추출."""
    params = {
        "q_bbsSn": BBS_SN,
        "q_bbsDocNo": report.bbs_doc_no,
        "q_clsfNo": CLSF_NO,
    }
    resp = client.get(DETAIL_URL, params=params)
    resp.raise_for_status()
    return _FILE_LINK_PATTERN.findall(resp.text)


def download_pdf(
    client: httpx.Client,
    file_sn: str,
    file_id: str,
    output_path: Path,
    referer: str,
) -> int:
    """단일 PDF를 다운로드해 파일로 저장한다. 저장된 바이트 수 반환."""
    resp = client.get(
        DOWNLOAD_URL,
        params={"q_fileSn": file_sn, "q_fileId": file_id},
        headers={"Referer": referer},
    )
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError(
            f"PDF 매직바이트 검증 실패 fileSn={file_sn} (응답 {len(resp.content)}B)"
        )
    output_path.write_bytes(resp.content)
    return len(resp.content)


def _download_reports(
    reports: list[KowasReport],
    output_dir: Path,
    skip_existing: bool = True,
) -> dict[str, int]:
    """리포트 목록을 실제로 다운로드하는 내부 공통 함수."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stats = {"downloaded": 0, "skipped": 0, "failed": 0}

    with _make_client() as client:
        total = len(reports)
        for i, report in enumerate(reports, 1):
            target = output_dir / report.filename
            if skip_existing and target.exists() and target.stat().st_size > 0:
                stats["skipped"] += 1
                logger.debug("스킵 (이미 존재): %s", target.name)
                continue

            try:
                links = fetch_pdf_links(client, report)
                if not links:
                    logger.warning("첨부파일 없음: %s (%s)", report.title, report.bbs_doc_no)
                    stats["failed"] += 1
                    continue

                # 다중 첨부 시 첫 번째만 (주간보고 본문 PDF) — 부록은 .filename에 _attN 추가
                referer = (
                    f"{DETAIL_URL}?q_bbsSn={BBS_SN}"
                    f"&q_bbsDocNo={report.bbs_doc_no}&q_clsfNo={CLSF_NO}"
                )
                file_sn, file_id = links[0]
                size = download_pdf(client, file_sn, file_id, target, referer)
                stats["downloaded"] += 1
                logger.info(
                    "[%d/%d] 다운로드 완료 %s (%.1fMB)",
                    i, total, target.name, size / 1024 / 1024,
                )

                # 부록 첨부 (있는 경우)
                for j, (sn, fid) in enumerate(links[1:], start=2):
                    att_path = output_dir / f"{target.stem}_att{j}.pdf"
                    if skip_existing and att_path.exists():
                        continue
                    try:
                        download_pdf(client, sn, fid, att_path, referer)
                    except Exception as exc:
                        logger.warning("부록 다운로드 실패 %s: %s", att_path.name, exc)

                time.sleep(1.0)  # 서버 부하 방지 (1초 이상 준수)
            except Exception as exc:
                logger.error("다운로드 실패 %s: %s", report.title, exc)
                stats["failed"] += 1

    return stats


def download_latest(
    weeks: int = 4,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    skip_existing: bool = True,
) -> list[Path]:
    """최근 N주차 KOWAS 주간보고 PDF를 다운로드한다.

    이미 존재하는 파일은 스킵(idempotent). 스케줄러의 주간 크론 잡에서 호출된다.

    Args:
        weeks: 최근 몇 주차까지 다운로드할지 (기본 4주)
        output_dir: 저장 디렉토리
        skip_existing: 이미 존재하는 파일 건너뛰기

    Returns:
        새로 다운로드된 PDF 경로 목록
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    with _make_client() as client:
        reports = list_reports(client)

    logger.info("KOWAS 게시판에서 %d건 발견, 최근 %d주 대상", len(reports), weeks)
    recent = reports[:weeks]

    stats = _download_reports(recent, output_dir, skip_existing=skip_existing)
    logger.info("최근 %d주 다운로드 완료: %s", weeks, stats)

    downloaded: list[Path] = []
    for report in recent:
        p = output_dir / report.filename
        if p.exists() and p.stat().st_size > 0:
            downloaded.append(p)
    return downloaded


def download_all(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    skip_existing: bool = True,
    limit: int | None = None,
) -> dict[str, int]:
    """전체 KOWAS 주간보고 PDF를 다운로드한다.

    Args:
        output_dir: 저장 디렉토리
        skip_existing: 이미 존재하는 파일 건너뛰기
        limit: 다운로드 최대 건수 (None=전체)

    Returns:
        {"downloaded": N, "skipped": M, "failed": F}
    """
    with _make_client() as client:
        reports = list_reports(client)

    logger.info("KOWAS 게시판에서 %d건 발견", len(reports))

    if limit is not None:
        reports = reports[:limit]

    stats = _download_reports(reports, output_dir, skip_existing=skip_existing)
    logger.info("완료: %s", stats)
    return stats


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="KOWAS 주간보고 PDF 일괄 다운로더")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--weeks", type=int, default=None, help="최근 N주차만 다운로드 (미지정 시 전체)")
    parser.add_argument("--limit", type=int, default=None, help="--all 모드에서 최대 다운로드 건수")
    parser.add_argument("--no-skip", action="store_true", help="기존 파일 무시하고 재다운")
    # --headless / --no-headless: httpx 기반이므로 실제로 브라우저 헤드리스 모드와 무관하지만
    # 미션 CLI 호환성과 향후 Playwright 전환 대비를 위해 플래그로 수용 (현재는 무시)
    parser.add_argument("--headless", dest="headless", action="store_true", default=True,
                        help="헤드리스 모드 (기본값, 현재 httpx 기반이므로 무의미)")
    parser.add_argument("--no-headless", dest="headless", action="store_false",
                        help="헤드리스 OFF (현재 httpx 기반이므로 무의미)")
    args = parser.parse_args()

    if args.weeks is not None:
        paths = download_latest(
            weeks=args.weeks,
            output_dir=args.output,
            skip_existing=not args.no_skip,
        )
        print(f"\n결과: 다운로드 {len(paths)}건")
        for p in paths:
            print(f"  {p.name}  ({p.stat().st_size // 1024}KB)")
    else:
        result = download_all(
            output_dir=args.output,
            skip_existing=not args.no_skip,
            limit=args.limit,
        )
        print(f"\n결과: {result}")
