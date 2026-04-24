export type RegionCode =
  | "SL" | "BS" | "DG" | "IC" | "GJ" | "DJ" | "US" | "SJ"
  | "GG" | "GW" | "CB" | "CN" | "JB" | "JN" | "GB" | "GN" | "JJ";

interface Region {
  code: RegionCode;
  name: { ko: string; en: string };
}

export const KOREA_REGIONS: Region[] = [
  { code: "SL", name: { ko: "서울특별시",    en: "Seoul" } },
  { code: "GG", name: { ko: "경기도",         en: "Gyeonggi" } },
  { code: "IC", name: { ko: "인천광역시",    en: "Incheon" } },
  { code: "GW", name: { ko: "강원특별자치도", en: "Gangwon" } },
  { code: "CB", name: { ko: "충청북도",      en: "Chungbuk" } },
  { code: "CN", name: { ko: "충청남도",      en: "Chungnam" } },
  { code: "DJ", name: { ko: "대전광역시",    en: "Daejeon" } },
  { code: "SJ", name: { ko: "세종특별자치시", en: "Sejong" } },
  { code: "JB", name: { ko: "전라북도", en: "Jeonbuk" } },
  { code: "JN", name: { ko: "전라남도",      en: "Jeonnam" } },
  { code: "GJ", name: { ko: "광주광역시",    en: "Gwangju" } },
  { code: "GB", name: { ko: "경상북도",      en: "Gyeongbuk" } },
  { code: "GN", name: { ko: "경상남도",      en: "Gyeongnam" } },
  { code: "DG", name: { ko: "대구광역시",    en: "Daegu" } },
  { code: "US", name: { ko: "울산광역시",    en: "Ulsan" } },
  { code: "BS", name: { ko: "부산광역시",    en: "Busan" } },
  { code: "JJ", name: { ko: "제주특별자치도", en: "Jeju" } },
];

export function regionName(code: RegionCode, lang: "ko" | "en"): string {
  return KOREA_REGIONS.find((r) => r.code === code)?.name[lang] ?? code;
}
