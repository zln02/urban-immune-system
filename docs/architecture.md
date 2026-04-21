# Architecture Overview

## Purpose

Urban Immune System is a presentation-first Streamlit dashboard (`src/`) that demonstrates how
multi-layer surveillance signals can be fused into an infectious disease early
warning workflow.

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

- `src/` (Streamlit dashboard, modularized)
  - `src/app.py` — entry point with 5-tab routing
  - `src/tabs/` — risk_map / timeseries / correlation / validation / report
  - `src/map/` — Folium-based Seoul 25-gu risk map
  - `src/components/` — shared UI (header, sidebar, footer, cards)
  - `src/styles.py` — inline CSS
- `analysis/data/`
  - placeholder for future real datasets + P0 performance reproducibility notebooks
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
