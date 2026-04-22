/**
 * 최소 i18n — 대시보드 하드코딩 문구.
 * 본격 i18n 은 next-intl 로 /[locale]/ 라우팅 전환 시 교체.
 */

export type Lang = "ko" | "en";

export interface Dict {
  brand: string;
  brand_sub: string;
  nav_dashboard: string;
  nav_districts: string;
  nav_reports: string;
  nav_alerts: string;
  nav_audit: string;
  nav_settings: string;
  header_status: string;
  header_sync: string;
  role: string;
  user: string;

  alert_title: string;
  alert_sub: string;
  alert_action_report: string;
  alert_action_ack: string;

  layer_pharmacy: string;
  layer_pharmacy_sub: string;
  layer_sewage: string;
  layer_sewage_sub: string;
  layer_search: string;
  layer_search_sub: string;

  map_title: string;
  map_sub: string;

  trend_title: string;
  trend_sub: string;
  trend_train: string;
  trend_test: string;
  trend_forecast: string;

  ai_title: string;
  ai_sub: string;
  ai_watermark: string;
  ai_finding: string;
  ai_action: string;

  kpi_alerts: string;
  kpi_at_risk: string;
  kpi_lead: string;
  kpi_confidence: string;

  granger: string;
  ci95: string;
  trigger: string;

  footer: string;
}

export const DICT: Record<Lang, Dict> = {
  ko: {
    brand: "Urban Immune System",
    brand_sub: "도시 면역 시스템",
    nav_dashboard: "대시보드",
    nav_districts: "시도 상세",
    nav_reports: "AI 리포트",
    nav_alerts: "경보",
    nav_audit: "감사 로그",
    nav_settings: "설정",
    header_status: "실시간 · 마지막 수집",
    header_sync: "KDCA 동기화",
    role: "질병관리청 · 감염병감시지원단",
    user: "박진영",
    alert_title: "긴급 경보 발령",
    alert_sub: "3-Layer 신호 동시 상승",
    alert_action_report: "리포트 열기",
    alert_action_ack: "확인",
    layer_pharmacy: "약국 OTC",
    layer_pharmacy_sub: "L1 · 2주 선행",
    layer_sewage: "하수 바이오마커",
    layer_sewage_sub: "L2 · 3주 선행",
    layer_search: "검색 트렌드",
    layer_search_sub: "L3 · 1주 선행",
    map_title: "전국 17개 시도 위험도",
    map_sub: "choropleth · 전라 권역 최우선 모니터링 · 클릭하여 상세 이동",
    trend_title: "3-Layer 교차검증 시계열",
    trend_sub: "60일 관측 + 21일 예측 (95% CI)",
    trend_train: "학습",
    trend_test: "검증",
    trend_forecast: "예측 구간",
    ai_title: "AI 경보 리포트",
    ai_sub: "RAG 기반 · 인간 검토 필요",
    ai_watermark: "AI 생성",
    ai_finding: "주요 발견",
    ai_action: "PDF 다운로드",
    kpi_alerts: "활성 경보",
    kpi_at_risk: "위험 지역",
    kpi_lead: "평균 선행 시간",
    kpi_confidence: "예측 신뢰도",
    granger: "Granger 인과",
    ci95: "95% CI",
    trigger: "발동 조건: 3-Layer 중 2개 이상 + 임계값 초과",
    footer: "Powered by 2026 AI 아이디어 공모전 수상 연구",
  },
  en: {
    brand: "Urban Immune System",
    brand_sub: "KDCA Surveillance Platform",
    nav_dashboard: "Dashboard",
    nav_districts: "Regions",
    nav_reports: "AI Reports",
    nav_alerts: "Alerts",
    nav_audit: "Audit Log",
    nav_settings: "Settings",
    header_status: "Live · Last sync",
    header_sync: "KDCA sync",
    role: "KDCA · Surveillance Division",
    user: "J. Park",
    alert_title: "Urgent alert issued",
    alert_sub: "3-Layer signals crossed",
    alert_action_report: "Open report",
    alert_action_ack: "Acknowledge",
    layer_pharmacy: "Pharmacy OTC",
    layer_pharmacy_sub: "L1 · 2-wk lead",
    layer_sewage: "Sewage biomarker",
    layer_sewage_sub: "L2 · 3-wk lead",
    layer_search: "Search trends",
    layer_search_sub: "L3 · 1-wk lead",
    map_title: "Nationwide · 17 provinces",
    map_sub: "Choropleth · Jeolla region priority · click for detail",
    trend_title: "3-Layer cross-validation",
    trend_sub: "60-day obs. + 21-day forecast (95% CI)",
    trend_train: "Train",
    trend_test: "Test",
    trend_forecast: "Forecast band",
    ai_title: "AI Alert Report",
    ai_sub: "RAG-based · human review required",
    ai_watermark: "AI-generated",
    ai_finding: "Key findings",
    ai_action: "Download PDF",
    kpi_alerts: "Active alerts",
    kpi_at_risk: "At-risk regions",
    kpi_lead: "Mean lead time",
    kpi_confidence: "Forecast confidence",
    granger: "Granger causality",
    ci95: "95% CI",
    trigger: "Trigger: ≥2 of 3 layers cross threshold",
    footer: "Powered by 2026 AI Idea Competition award-winning research",
  },
};
