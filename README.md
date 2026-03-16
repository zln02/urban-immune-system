# Urban Immune System

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Prototype-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-Interactive-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge)

Urban Immune System is a Streamlit prototype for an AI-powered infectious
disease early warning dashboard. It visualizes multi-layer surveillance
signals from OTC purchases, wastewater monitoring, and search trends to
support faster public-health response in Seoul.

## Why It Matters

- Detect outbreak signals 1 to 3 weeks earlier than confirmed case counts.
- Combine three surveillance layers into a single operational risk view.
- Present a competition-ready interface with high-impact interactive visuals.

## Demo Highlights

- Seoul district risk map with 25 gu-level markers.
- Seasonal time-series analysis with train/test split and peak windows.
- Cross-correlation analysis showing leading indicators by signal type.
- Cross-validation comparison between single-layer and integrated models.
- AI alert report with layer contribution breakdown and response guidance.

## Project Structure

```text
urban-immune-system/
├── README.md
├── LICENSE
├── .gitignore
├── prototype/
│   ├── app.py
│   ├── requirements.txt
│   ├── assets/
│   └── .streamlit/
│       └── config.toml
├── analysis/
│   ├── data/
│   │   ├── .gitkeep
│   │   └── README.md
│   └── notebooks/
├── docs/
│   └── architecture.md
└── .github/
    └── workflows/
        └── ci.yml
```

## Quick Start

```bash
cd prototype
pip install --no-cache-dir -r requirements.txt
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Then open `http://<YOUR_VM_IP>:8501`.

## Analysis Summary

| Layer | Signal | Lead Time | Narrative |
| --- | --- | --- | --- |
| Layer 1 | OTC purchase index | ~2 weeks | Pharmacy demand reacts early. |
| Layer 2 | Wastewater viral load | ~3 weeks | Environmental signal leads cases. |
| Layer 3 | Search trend | ~1 week | Public concern spikes before diagnosis. |
| Integrated | 3-layer fusion | Stable | Preserves precision while improving recall. |

## Technology Stack

- Streamlit
- Plotly
- Folium
- Pandas
- NumPy
- GitHub Actions

## Data Sources

- Layer 1: Naver Shopping Insight API
- Layer 2: KOWAS wastewater monitoring bulletin PDFs
- Layer 3: Naver DataLab API
- Ground Truth: KDCA infectious disease portal

This prototype uses simulated data for visualization and storytelling. See
[analysis/data/README.md](analysis/data/README.md) for notes on future data
integration.

## Team

Urban Immune System Team

- Product and narrative design for public-health competition demos
- Multi-layer signal fusion for infectious disease early warning
- Rapid prototyping with explainable AI dashboards

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
