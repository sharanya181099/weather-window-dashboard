# Weather Window Dashboard

Interactive dashboard for assessing offshore weather window accessibility around the Irish coastline, based on ten years (2015–2024) of hourly ERA5 reanalysis data.

This dashboard accompanies the paper:

> Santosh, S. and Ringwood, J. V. (2026). Weather window analysis and threshold sensitivity for Irish offshore renewable energy operations. *Proceedings of RENEW2026*, Lisbon.

## Live demo

A live version of the dashboard is hosted at: *(link to be added after deployment)*

## What it does

The dashboard computes weather window accessibility statistics at any user-defined point on the Irish coastline, using significant wave height and 10-m wind speed thresholds for crew transfer vessels (CTV), service operation vessels (SOV), jack-up barges, cable-laying vessels, and anchor-handling tugs (AHTS).

Outputs include:

- A persistence table showing monthly accessibility for window durations of 3, 6, 12, 24, and 48 hours
- Monthly and seasonal accessibility charts
- Inter-window wait time statistics

## Running locally

```bash
git clone https://github.com/sharanya181099/weather-window-dashboard.git
cd weather-window-dashboard
pip install -r requirements.txt
streamlit run dashboard/app.py
```

## Data

The `data/processed/` folder contains pre-processed ERA5 NetCDF files (2015–2024) covering the Irish maritime domain (50–56°N, 10.5–5°W), with significant wave height (`swh`), and 10-m wind components (`u10`, `v10`). The raw ERA5 data is from the Copernicus Climate Change Service ([Hersbach et al., 2020](https://doi.org/10.1002/qj.3803)).

## Contact

Sharanya Santosh, Centre for Ocean Energy Research, Maynooth University.
