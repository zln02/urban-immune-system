export type Lang = "ko" | "en";

export interface Translations {
  brand: string;
  nav_dashboard: string;
  nav_districts: string;
  nav_reports: string;
  nav_alerts: string;
  nav_audit: string;
  header_sync: string;
  header_status: string;
  user: string;
  role: string;
  trigger: string;
  kpi_alerts: string;
  kpi_at_risk: string;
  kpi_lead: string;
  kpi_confidence: string;
  map_title: string;
  map_sub: string;
  layer_pharmacy: string;
  layer_pharmacy_sub: string;
  layer_sewage: string;
  layer_sewage_sub: string;
  layer_search: string;
  layer_search_sub: string;
  trend_title: string;
  trend_sub: string;
  granger: string;
  footer: string;
  ai_report_title: string;
  ai_report_generate: string;
  ai_report_generating: string;
  ai_report_watermark: string;
  alert_table_title: string;
}

export const DICT: Record<Lang, Translations> = {
  ko: {
    brand: "도시 면역 시스템",
    nav_dashboard: "대시보드",
    nav_districts: "지역 현황",
    nav_reports: "리포트",
    nav_alerts: "경보",
    nav_audit: "감사",
    header_sync: "최종 업데이트",
    header_status: "전국 감시 현황",
    user: "박진영",
    role: "PM · ML Lead",
    trigger: "3계층 중 2개 이상이 임계값 초과 시 경보 발령",
    kpi_alerts: "활성 경보",
    kpi_at_risk: "위험 지역",
    kpi_lead: "선행 탐지",
    kpi_confidence: "모델 신뢰도",
    map_title: "전국 위험도 지도",
    map_sub: "17개 시도 실시간 감시",
    layer_pharmacy: "L1 약국 OTC",
    layer_pharmacy_sub: "Naver 쇼핑인사이트",
    layer_sewage: "L2 하수 바이오마커",
    layer_sewage_sub: "KOWAS 바이러스 농도",
    layer_search: "L3 검색 트렌드",
    layer_search_sub: "Naver DataLab",
    trend_title: "신호 시계열",
    trend_sub: "최근 60일 · 3계층 통합",
    granger: "그랜저 인과성 검증",
    footer: "© 2026 Urban Immune System · KDCA 시범사업",
    ai_report_title: "AI 경보 리포트",
    ai_report_generate: "리포트 생성",
    ai_report_generating: "Claude 분석 중…",
    ai_report_watermark: "AI 생성 · 인간 검토 필요",
    alert_table_title: "경보 이력",
  },
  en: {
    brand: "Urban Immune System",
    nav_dashboard: "Dashboard",
    nav_districts: "Districts",
    nav_reports: "Reports",
    nav_alerts: "Alerts",
    nav_audit: "Audit",
    header_sync: "Last update",
    header_status: "National surveillance",
    user: "Jinyoung Park",
    role: "PM · ML Lead",
    trigger: "Alert triggered when ≥ 2 of 3 layers exceed threshold",
    kpi_alerts: "Active alerts",
    kpi_at_risk: "At-risk regions",
    kpi_lead: "Lead detection",
    kpi_confidence: "Model confidence",
    map_title: "National risk map",
    map_sub: "17 provinces real-time",
    layer_pharmacy: "L1 Pharmacy OTC",
    layer_pharmacy_sub: "Naver Shopping Insight",
    layer_sewage: "L2 Wastewater",
    layer_sewage_sub: "KOWAS viral concentration",
    layer_search: "L3 Search trends",
    layer_search_sub: "Naver DataLab",
    trend_title: "Signal time series",
    trend_sub: "Last 60 days · 3-layer integrated",
    granger: "Granger causality test",
    footer: "© 2026 Urban Immune System · KDCA Pilot",
    ai_report_title: "AI Alert Report",
    ai_report_generate: "Generate report",
    ai_report_generating: "Claude analyzing…",
    ai_report_watermark: "AI generated · Human review required",
    alert_table_title: "Alert history",
  },
};
