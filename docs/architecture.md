# Architecture Overview

## Purpose

Urban Immune System fuses three civilian-leading signals (pharmacy OTC,
wastewater biomarkers, search trends) into an infectious disease early
warning workflow targeted at Korean public-health agencies (B2G).

## Layers

1. Layer 1: OTC pharmacy purchase index
2. Layer 2: Wastewater viral concentration
3. Layer 3: Search trend intensity
4. Ground truth: Confirmed infectious disease case counts

## Flow

```text
External data sources
        |
        v
 Ingestion and normalization
        |
        v
 Weekly feature generation
        |
        v
 Signal fusion and risk scoring
        |
        v
 Visualization + AI alert reporting
```

## Components

- `frontend/src/app/dashboard/` (Phase 2 canonical)
  - Next.js 15 App Router dashboard
  - 17-region KoreaMap, real-time KPI cards, Granger/CCF panel
  - SSE-streamed AI alert report + 4-page PDF download
- `src/app.py` (Phase 1, Plan B fallback)
  - Streamlit dashboard kept as deployment fallback
  - simulated data generation utilities used by tests
- `backend/app/` — FastAPI :8001
  - `services/report_pdf.py` ReportLab + matplotlib PDF builder
  - `api/alerts.py` SSE alerts/stream + report-pdf endpoints
- `pipeline/collectors/` — APScheduler weekly cron (otc/wastewater/search/weather)
- `analysis/data/`
  - placeholder for future real datasets
- `.github/workflows/ci.yml`
  - lint and import smoke tests

## Deployment Assumption

The app is designed for a lightweight GCP VM. It avoids heavy ML dependencies
and relies on NumPy, Pandas, Plotly, Folium, and Streamlit only.

## Future Extensions

- Replace simulated signals with weekly production data
- Add district-level historical model calibration
- Generate RAG-backed alert narratives from curated guidance sources
- Export static PDF briefings for public-health decision makers
