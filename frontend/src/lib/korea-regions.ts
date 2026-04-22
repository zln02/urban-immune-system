/**
 * 전국 17개 시도 지도 데이터 (추상화된 SVG geometry).
 *
 * Jeolla 권역 (JB · JN · GJU) 은 프로젝트 Phase 1 의 우선 감시 대상.
 * viewBox: 540 × 700 (portrait)
 *
 * 출처: Claude Design handoff (2026-04-22) — approximate geography
 */

export type RegionCode =
  | "SEL" | "INC" | "GG"  | "GW"
  | "SJ"  | "DJ"  | "CB"  | "CN"
  | "JB"  | "JN"  | "GJU"
  | "GB"  | "DG"  | "GN"  | "US"  | "BS"
  | "JJ";

export interface KoreaRegion {
  code: RegionCode;
  ko: string;
  en: string;
  d: string;
  centroid: { x: number; y: number };
}

export const KOREA_REGIONS: KoreaRegion[] = [
  { code: "SEL", ko: "서울", en: "Seoul",     d: "M 268 198 L 300 192 L 312 210 L 298 228 L 272 224 Z",                       centroid: { x: 290, y: 210 } },
  { code: "INC", ko: "인천", en: "Incheon",   d: "M 222 212 L 262 208 L 268 234 L 248 252 L 220 244 Z",                       centroid: { x: 242, y: 230 } },
  { code: "GG",  ko: "경기", en: "Gyeonggi",  d: "M 240 168 L 320 160 L 352 200 L 338 256 L 288 268 L 238 252 L 220 214 Z",  centroid: { x: 292, y: 218 } },
  { code: "GW",  ko: "강원", en: "Gangwon",   d: "M 322 120 L 470 108 L 490 200 L 440 246 L 356 240 L 330 198 L 320 160 Z",  centroid: { x: 400, y: 178 } },
  { code: "SJ",  ko: "세종", en: "Sejong",    d: "M 276 282 L 304 278 L 312 298 L 292 312 L 272 302 Z",                       centroid: { x: 292, y: 296 } },
  { code: "DJ",  ko: "대전", en: "Daejeon",   d: "M 298 308 L 326 304 L 334 328 L 312 346 L 290 334 Z",                       centroid: { x: 312, y: 324 } },
  { code: "CB",  ko: "충북", en: "Chungbuk",  d: "M 312 260 L 396 250 L 420 298 L 402 342 L 340 344 L 302 312 Z",             centroid: { x: 356, y: 300 } },
  { code: "CN",  ko: "충남", en: "Chungnam",  d: "M 196 256 L 286 264 L 306 312 L 280 356 L 208 360 L 176 316 Z",             centroid: { x: 240, y: 310 } },
  { code: "JB",  ko: "전북", en: "Jeonbuk",   d: "M 188 376 L 296 370 L 330 414 L 308 470 L 232 478 L 180 440 Z",             centroid: { x: 250, y: 420 } },
  { code: "GJU", ko: "광주", en: "Gwangju",   d: "M 212 506 L 250 502 L 262 528 L 238 548 L 212 534 Z",                       centroid: { x: 236, y: 524 } },
  { code: "JN",  ko: "전남", en: "Jeonnam",   d: "M 154 490 L 226 486 L 240 512 L 272 520 L 282 560 L 248 600 L 178 610 L 124 572 L 116 522 Z", centroid: { x: 196, y: 548 } },
  { code: "GB",  ko: "경북", en: "Gyeongbuk", d: "M 400 260 L 490 256 L 510 346 L 484 408 L 416 408 L 390 350 L 402 296 Z",  centroid: { x: 450, y: 332 } },
  { code: "DG",  ko: "대구", en: "Daegu",     d: "M 408 374 L 446 370 L 454 398 L 430 418 L 404 404 Z",                       centroid: { x: 428, y: 392 } },
  { code: "GN",  ko: "경남", en: "Gyeongnam", d: "M 332 430 L 430 430 L 470 468 L 450 518 L 376 526 L 322 490 Z",             centroid: { x: 394, y: 478 } },
  { code: "US",  ko: "울산", en: "Ulsan",     d: "M 466 428 L 498 424 L 510 452 L 486 470 L 462 456 Z",                       centroid: { x: 486, y: 448 } },
  { code: "BS",  ko: "부산", en: "Busan",     d: "M 440 506 L 478 502 L 490 530 L 466 552 L 436 540 Z",                       centroid: { x: 462, y: 524 } },
  { code: "JJ",  ko: "제주", en: "Jeju",      d: "M 190 646 L 268 642 L 282 666 L 260 682 L 196 680 L 180 662 Z",             centroid: { x: 230, y: 662 } },
];

export const REGION_BY_CODE: Record<RegionCode, KoreaRegion> = Object.fromEntries(
  KOREA_REGIONS.map((r) => [r.code, r]),
) as Record<RegionCode, KoreaRegion>;

export const JEOLLA_PRIORITY: readonly RegionCode[] = ["JB", "JN", "GJU"] as const;

export function regionName(code: RegionCode, lang: "ko" | "en"): string {
  const r = REGION_BY_CODE[code];
  return lang === "en" ? r.en : r.ko;
}
