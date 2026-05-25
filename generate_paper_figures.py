"""
generate_paper_figures.py

Generates publication-quality figures for the RENEW 2026 weather window paper.

Run from your project root (where data/processed/ lives):
    python generate_paper_figures.py

Required packages:
    pip install xarray pandas numpy matplotlib seaborn netcdf4 cartopy

Outputs (both PNG and PDF):
    paper_figures/fig1_sitemap.{png,pdf}
    paper_figures/fig2_wave_only.{png,pdf}
    paper_figures/fig3_joint_distribution.{png,pdf}
    paper_figures/fig4_threshold_curve.{png,pdf}
    paper_figures/fig5_wait_times.{png,pdf}

Note: Cartopy will download Natural Earth shapefiles on first run
(takes a few seconds, only happens once).
"""

import os
import glob
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# -----------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------

DATA_DIR = "data/processed"
OUT_DIR = "paper_figures"

SITES = {
    "AMETS":  (54.25, -10.25),
    "Arklow": (52.75,  -5.75),
}

HS_NOMINAL = 1.5
WIND_NOMINAL = 10.0
DURATION = 6
HS_WAIT = 2.0
WIND_WAIT = 12.0

# Style: seaborn whitegrid (matches dissertation aesthetic)
sns.set_theme(style="whitegrid", context="paper", font="serif", font_scale=1.15)
mpl.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.dpi": 100,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "pdf.fonttype": 42,
    "axes.linewidth": 0.8,
    "grid.linewidth": 0.5,
    "grid.color": "0.85",
})

COLOR = {"AMETS": "#1f77b4", "Arklow": "#d62728"}
MARKER = {"AMETS": "o", "Arklow": "s"}

# Sizes (inches)
COL_W = 3.4
FULL_W = 7.0

# -----------------------------------------------------------------------
# DATA LOADING
# -----------------------------------------------------------------------

def load_time_series():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.nc")))
    if not files:
        raise FileNotFoundError(f"No NetCDF files found in {DATA_DIR}")
    print(f"Loading {len(files)} years of ERA5...")
    ds = xr.concat([xr.open_dataset(f) for f in files], dim="valid_time").sortby("valid_time")
    series = {}
    for name, (lat, lon) in SITES.items():
        swh = ds["swh"].sel(latitude=lat, longitude=lon).to_series()
        u10 = ds["u10"].sel(latitude=lat, longitude=lon).to_series()
        v10 = ds["v10"].sel(latitude=lat, longitude=lon).to_series()
        wind = np.sqrt(u10**2 + v10**2)
        df = pd.DataFrame({"Hs": swh, "wind": wind}).dropna()
        series[name] = df
        print(f"  {name}: {len(df)} hours, mean Hs = {df['Hs'].mean():.2f} m")
    return series

# -----------------------------------------------------------------------
# CORE COMPUTATIONS
# -----------------------------------------------------------------------

def monthly_acc(df, hs_thr, wind_thr, duration):
    mask = (df["Hs"] <= hs_thr) & (df["wind"] <= wind_thr)
    rolling = mask.astype(int).rolling(window=duration).sum()
    accessible = (rolling == duration).astype(int)
    out = pd.DataFrame({"acc": accessible}, index=df.index)
    out["month"] = out.index.month
    return out.groupby("month")["acc"].mean() * 100

def seasonal_curve(df, wind_thr, duration, season):
    sm = [12, 1, 2] if season == "winter" else [6, 7, 8]
    sub = df[df.index.month.isin(sm)]
    hs_v = np.arange(0.5, 3.05, 0.05)
    accs = []
    for hs in hs_v:
        mask = (sub["Hs"] <= hs) & (sub["wind"] <= wind_thr)
        rolling = mask.astype(int).rolling(window=duration).sum()
        accs.append((rolling == duration).astype(int).mean() * 100)
    return hs_v, np.array(accs)

def monthly_wait(df, hs_thr, wind_thr, duration):
    mask = (df["Hs"] <= hs_thr) & (df["wind"] <= wind_thr)
    rolling = mask.astype(int).rolling(window=duration).sum()
    is_w = (rolling == duration).astype(int)
    starts = df.index[(is_w == 1) & (is_w.shift(1, fill_value=0) == 0)]
    ends = df.index[(is_w == 1) & (is_w.shift(-1, fill_value=0) == 0)]
    waits = []
    for i in range(len(ends) - 1):
        if i + 1 < len(starts):
            wait_h = (starts[i+1] - ends[i]).total_seconds() / 3600
            waits.append((ends[i].month, wait_h / 24))
    df_w = pd.DataFrame(waits, columns=["month", "wait_days"])
    return df_w.groupby("month")["wait_days"].mean()

# -----------------------------------------------------------------------
# FIGURES
# -----------------------------------------------------------------------

def fig1_sitemap():
    """Site map with Cartopy basemap of Ireland."""
    fig = plt.figure(figsize=(COL_W * 1.5, COL_W * 1.1))
    proj = ccrs.PlateCarree()
    ax = plt.axes(projection=proj)
    ax.set_extent([-12, -5, 51, 56], crs=proj)

    ax.add_feature(cfeature.LAND.with_scale("50m"),
                   facecolor="#f0e8d8", edgecolor="none")
    ax.add_feature(cfeature.OCEAN.with_scale("50m"),
                   facecolor="#dde8f0", edgecolor="none")
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"),
                   edgecolor="#444444", linewidth=0.6)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"),
                   edgecolor="#888888", linewidth=0.4, linestyle=":")

    gl = ax.gridlines(draw_labels=True, linewidth=0.4,
                      color="gray", alpha=0.5, linestyle=":")
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {"size": 9}
    gl.ylabel_style = {"size": 9}

    for name, (lat, lon) in SITES.items():
        ax.scatter(lon, lat, c=COLOR[name], marker=MARKER[name], s=130,
                   edgecolors="black", linewidth=1.2, zorder=10, transform=proj)
        offset = (8, 6) if name == "AMETS" else (8, -3)
        ax.annotate(name, (lon, lat), xytext=offset, textcoords="offset points",
                    fontsize=11, fontweight="bold", color="black",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))

    plt.savefig(os.path.join(OUT_DIR, "fig1_sitemap.png"))
    plt.savefig(os.path.join(OUT_DIR, "fig1_sitemap.pdf"))
    plt.close()
    print("  fig1_sitemap.png/pdf")


def fig2_wave_only(series):
    """Monthly accessibility, wave-only constraint."""
    months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    fig, ax = plt.subplots(figsize=(COL_W * 1.5, COL_W * 0.9))
    for name, df in series.items():
        m = monthly_acc(df, HS_NOMINAL, 999, DURATION)
        ax.plot(range(1, 13), m.values, marker=MARKER[name], color=COLOR[name],
                label=name, lw=1.8, ms=7,
                markeredgecolor="black", markeredgewidth=0.6)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(months)
    ax.set_xlabel("Month")
    ax.set_ylabel("Accessibility (%)")
    ax.set_ylim(0, 100)
    ax.legend(loc="lower center", frameon=True, fancybox=False, edgecolor="0.7")
    plt.savefig(os.path.join(OUT_DIR, "fig2_wave_only.png"))
    plt.savefig(os.path.join(OUT_DIR, "fig2_wave_only.pdf"))
    plt.close()
    print("  fig2_wave_only.png/pdf")


def fig3_joint_distribution(series):
    """Joint Hs/wind distribution at both sites."""
    fig, axes = plt.subplots(1, 2, figsize=(FULL_W, COL_W * 1.0))
    for idx, (name, df) in enumerate(series.items()):
        ax = axes[idx]
        hs_max = df["Hs"].quantile(0.99)
        wind_max = df["wind"].quantile(0.99)
        h = ax.hist2d(df["Hs"], df["wind"], bins=[60, 60],
                      range=[[0, hs_max], [0, wind_max]],
                      cmap="Blues", cmin=1)
        ax.axvline(HS_NOMINAL, color="#d62728", ls="--", lw=1.5, alpha=0.85)
        ax.axhline(WIND_NOMINAL, color="#ff7f0e", ls="--", lw=1.5, alpha=0.85)
        ax.text(HS_NOMINAL + 0.05, wind_max * 0.93, r"$H_s = 1.5$ m",
                color="#d62728", fontsize=9, va="top",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
        ax.text(hs_max * 0.95, WIND_NOMINAL + 0.5, r"$U = 10$ m/s",
                color="#cc6600", fontsize=9, ha="right",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
        ax.set_xlabel(r"Significant wave height $H_s$ (m)")
        ax.set_ylabel("Wind speed (m/s)")
        ax.set_title(f"({chr(97+idx)}) {name}", loc="left", fontsize=11)
        ax.set_xlim(0, hs_max)
        ax.set_ylim(0, wind_max)
        cbar = plt.colorbar(h[3], ax=ax, fraction=0.046, pad=0.02)
        cbar.set_label("Hours", fontsize=10)
        cbar.ax.tick_params(labelsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fig3_joint_distribution.png"))
    plt.savefig(os.path.join(OUT_DIR, "fig3_joint_distribution.pdf"))
    plt.close()
    print("  fig3_joint_distribution.png/pdf")


def fig4_threshold_curve(series):
    """Accessibility vs Hs threshold, winter and summer."""
    fig, axes = plt.subplots(1, 2, figsize=(FULL_W, COL_W * 1.0), sharey=True)
    for idx, (season, label) in enumerate([
        ("winter", "(a) Winter (DJF)"),
        ("summer", "(b) Summer (JJA)")
    ]):
        ax = axes[idx]
        for name, df in series.items():
            hs_v, accs = seasonal_curve(df, WIND_NOMINAL, DURATION, season)
            ax.plot(hs_v, accs, color=COLOR[name], lw=2.0, label=name)
            i15 = np.argmin(np.abs(hs_v - HS_NOMINAL))
            ax.scatter(HS_NOMINAL, accs[i15], color=COLOR[name], s=60,
                       zorder=5, edgecolors="black", linewidth=1.0)
        ax.axvline(HS_NOMINAL, color="0.5", ls="--", lw=1.0, alpha=0.7)
        ax.text(HS_NOMINAL, 95, "Nominal CTV", fontsize=9, color="0.3",
                ha="center", va="top",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9))
        ax.set_xlabel(r"Wave height threshold $H_s$ (m)")
        if idx == 0:
            ax.set_ylabel("Accessibility (%)")
        ax.set_title(label, loc="left")
        ax.set_xlim(0.5, 3.0)
        ax.set_ylim(0, 100)
        ax.legend(loc="center right", frameon=True, fancybox=False, edgecolor="0.7",
                  bbox_to_anchor=(0.99, 0.32))
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fig4_threshold_curve.png"))
    plt.savefig(os.path.join(OUT_DIR, "fig4_threshold_curve.pdf"))
    plt.close()
    print("  fig4_threshold_curve.png/pdf")


def fig5_wait_times(series):
    """Monthly average wait times, log y-axis."""
    months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    fig, ax = plt.subplots(figsize=(COL_W * 1.5, COL_W * 0.9))
    for name, df in series.items():
        w = monthly_wait(df, HS_WAIT, WIND_WAIT, DURATION)
        ax.plot(w.index, w.values, marker=MARKER[name], color=COLOR[name],
                label=name, lw=1.8, ms=7,
                markeredgecolor="black", markeredgewidth=0.6)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(months)
    ax.set_xlabel("Month")
    ax.set_ylabel("Wait time (days)")
    ax.set_yscale("log")
    ax.set_yticks([0.5, 1, 2, 5, 10, 20])
    ax.set_yticklabels(["0.5", "1", "2", "5", "10", "20"])
    ax.set_ylim(0.4, 25)
    ax.legend(loc="upper center", frameon=True, fancybox=False, edgecolor="0.7", ncol=2)
    plt.savefig(os.path.join(OUT_DIR, "fig5_wait_times.png"))
    plt.savefig(os.path.join(OUT_DIR, "fig5_wait_times.pdf"))
    plt.close()
    print("  fig5_wait_times.png/pdf")


# -----------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    series = load_time_series()
    print("\nGenerating figures:")
    fig1_sitemap()
    fig2_wave_only(series)
    fig3_joint_distribution(series)
    fig4_threshold_curve(series)
    fig5_wait_times(series)
    print(f"\nDone. Figures saved to {OUT_DIR}/")