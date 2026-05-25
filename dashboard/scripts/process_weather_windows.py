# scripts/process_weather_windows.py

import os
import xarray as xr
import pandas as pd
import numpy as np
import streamlit as st
from glob import glob
from .utils import extract_time_series_at_location, rolling_weather_window_checker


# -----------------------------------------------------------------------------
# Cached I/O layer
# -----------------------------------------------------------------------------
# The expensive part of every compute call is opening 10 NetCDF files and
# extracting time series at a location. We cache that extraction once per
# (lat, lon, data_dir) tuple, so every subsequent analysis at the same point
# (any threshold, any duration) is essentially free.

@st.cache_data(show_spinner=False)
def _load_location_series(lat, lon, data_dir="data/processed/"):
    """
    Load all 10 years of (time, swh, u10, v10) at a single (lat, lon).
    Result is cached by (lat, lon, data_dir).
    """
    netcdf_files = sorted(glob(os.path.join(data_dir, "*_with_valid_time.nc")))

    times = []
    swh_list = []
    u10_list = []
    v10_list = []

    for file in netcdf_files:
        ds = xr.open_dataset(file)
        times.append(ds['valid_time'].values)
        swh_list.append(extract_time_series_at_location(ds['swh'], lat, lon).values)
        u10_list.append(extract_time_series_at_location(ds['u10'], lat, lon).values)
        v10_list.append(extract_time_series_at_location(ds['v10'], lat, lon).values)
        ds.close()

    df = pd.DataFrame({
        'time': np.concatenate(times),
        'swh': np.concatenate(swh_list),
        'u10': np.concatenate(u10_list),
        'v10': np.concatenate(v10_list),
    })
    df['time'] = pd.to_datetime(df['time'])
    df['wind'] = np.sqrt(df['u10']**2 + df['v10']**2)
    df['year'] = df['time'].dt.year
    df['month'] = df['time'].dt.month
    return df


def _build_mask(df, wave_threshold, wind_threshold):
    """Boolean Series indicating hours that satisfy the thresholds."""
    mask = df['swh'] <= wave_threshold
    if wind_threshold is not None:
        mask = mask & (df['wind'] <= wind_threshold)
    return mask


def _rolling_valid(mask_series, duration_hours):
    """
    For each hour t, True if hours [t-duration+1, t] are all admissible.
    Pure pandas implementation — fast and avoids xarray's rolling overhead.
    """
    return mask_series.rolling(window=duration_hours, min_periods=duration_hours).sum() >= duration_hours


# -----------------------------------------------------------------------------
# Public API (unchanged signatures so app.py needs no changes)
# -----------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def compute_monthly_weather_windows(lat, lon, wave_threshold, wind_threshold, duration_hours, data_dir="data/processed/"):
    """
    Compute average monthly weather window counts across all years.
    Returns DataFrame with ['month', 'avg_weather_window_count', 'percent_access'].
    """
    df = _load_location_series(lat, lon, data_dir).copy()
    mask = _build_mask(df, wave_threshold, wind_threshold)
    df['valid_window'] = _rolling_valid(mask, duration_hours)

    # Per-year per-month counts, then average across years
    yearly = df.groupby(['year', 'month']).agg(
        window_count=('valid_window', 'sum'),
        total_hours=('valid_window', 'size')
    ).reset_index()

    grouped = yearly.groupby('month').agg(
        window_count=('window_count', 'mean'),
        total_hours=('total_hours', 'mean')
    ).reset_index()

    grouped['percent_access'] = (grouped['window_count'] / grouped['total_hours']) * 100
    grouped = grouped.rename(columns={'window_count': 'avg_weather_window_count'})
    return grouped[['month', 'avg_weather_window_count', 'percent_access']]


@st.cache_data(show_spinner=False)
def compute_wait_times(lat, lon, wave_threshold, wind_threshold, duration_hours, data_dir="data/processed/"):
    """
    Compute wait times between consecutive valid weather windows.
    Returns DataFrame with ['wait_hours', 'month'].
    """
    df = _load_location_series(lat, lon, data_dir).copy()
    mask = _build_mask(df, wave_threshold, wind_threshold)
    df['valid'] = _rolling_valid(mask, duration_hours)

    valid_df = df[df['valid']].reset_index(drop=True)
    if len(valid_df) < 2:
        return pd.DataFrame(columns=['wait_hours', 'month'])

    deltas = valid_df['time'].diff().dt.total_seconds() / 3600
    wait_mask = deltas > duration_hours
    out = pd.DataFrame({
        'wait_hours': deltas[wait_mask].values,
        'month': valid_df.loc[wait_mask, 'time'].dt.month.values,
    })
    return out


@st.cache_data(show_spinner=False)
def compute_persistence_table(lat, lon, wave_threshold, wind_threshold=None, durations=(3, 6, 12, 24, 48)):
    """
    Persistence table: rows = duration_hours, columns = month, values = % accessibility.
    """
    rows = []
    for duration in durations:
        monthly = compute_monthly_weather_windows(lat, lon, wave_threshold, wind_threshold, duration)
        monthly = monthly.rename(columns={'percent_access': 'access_percent'})
        monthly['duration_hours'] = duration
        rows.append(monthly[['month', 'access_percent', 'duration_hours']])

    result_df = pd.concat(rows)
    pivot_df = result_df.pivot_table(
        index='duration_hours', columns='month', values='access_percent', fill_value=0
    )
    pivot_df = pivot_df.reindex(columns=list(range(1, 13)), fill_value=0)
    return pivot_df


@st.cache_data(show_spinner=False)
def compute_duration_distribution(lat, lon, wave_threshold, wind_threshold=None, data_dir="data/processed/"):
    """
    Frequency of weather window durations across all years.
    Returns DataFrame with ['duration_hours', 'count'].
    """
    df = _load_location_series(lat, lon, data_dir).copy()
    mask = _build_mask(df, wave_threshold, wind_threshold).values.astype(int)

    durations = []
    current = 0
    for v in mask:
        if v:
            current += 1
        else:
            if current > 0:
                durations.append(current)
                current = 0
    if current > 0:
        durations.append(current)

    series = pd.Series(durations)
    counts = series.value_counts().sort_index().reset_index()
    counts.columns = ['duration_hours', 'count']
    return counts
