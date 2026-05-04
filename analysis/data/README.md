# Data Notes

This folder is reserved for real surveillance datasets used in the next stage
of the project.

## Planned Inputs

- OTC purchase trend exports from Naver Shopping Insight API
- Wastewater surveillance bulletins from KOWAS PDFs
- Search trend exports from Naver DataLab API
- Ground-truth case counts from KDCA infectious disease portal

## Suggested Layout

```text
analysis/data/
├── raw/
├── interim/
├── processed/
└── external/
```

## Download Guidance

1. Save original source files under `raw/`.
2. Extract tabular fields from PDF bulletins into `interim/`.
3. Normalize weekly indices into `processed/`.
4. Keep a source log with collection date, URL, and schema notes.

Real data is loaded into TimescaleDB by `pipeline/collectors/`; the Streamlit fallback (`src/app.py`) consumes the same DB via FastAPI.
