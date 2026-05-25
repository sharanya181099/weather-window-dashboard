# scripts/process_weather_windows.py

import os
import xarray as xr
import pandas as pd
import numpy as np
from glob import glob
from .utils import extract_time_series_at_location, rolling_weather_window_checker
#from dashboard.scripts.utils import extract_time_series_at_location, rolling_weather_window_checker



def compute_monthly_weather_windows(lat, lon, wave_threshold, wind_threshold, duration_hours, data_dir="data/processed/"):
    """
    Compute average monthly weather window counts across 10 years.

    Parameters:
    - lat, lon: Location
    - wave_threshold: max significant wave height (m)
    - wind_threshold: max wind speed (m/s), or None if not used
    - duration_hours: window duration in hours
    - data_dir: path to NetCDF files with valid_time

    Returns:
    - pandas DataFrame with columns ['month', 'avg_weather_window_count']
    """
    netcdf_files = sorted(glob(os.path.join(data_dir, "*_with_valid_time.nc")))
    monthly_results = []

    for file in netcdf_files:
        ds = xr.open_dataset(file)
        time = ds['valid_time']
        
        # Get time series for location
        swh = extract_time_series_at_location(ds['swh'], lat, lon)
        
        if wind_threshold is not None:
            u10 = extract_time_series_at_location(ds['u10'], lat, lon)
            v10 = extract_time_series_at_location(ds['v10'], lat, lon)
            wind = np.sqrt(u10**2 + v10**2)

            mask = (swh <= wave_threshold) & (wind <= wind_threshold)
        else:
            mask = swh <= wave_threshold

        # Rolling window logic
        # NEW
        rolled = rolling_weather_window_checker(mask, duration_hours)
        valid_windows = rolled >= duration_hours  # Now this is boolean


        df = pd.DataFrame({
            'time': time.values,
            'valid_window': valid_windows.values
        })
        df['month'] = pd.to_datetime(df['time']).dt.month
        monthly_counts = df[df['valid_window']].groupby('month').size()
        

        total_hours_per_month = df.groupby('month').size()  # Total hours per month in data
        monthly_df = pd.DataFrame({
            'month': monthly_counts.index,
            'window_count': monthly_counts.values,
            'total_hours': total_hours_per_month.reindex(monthly_counts.index).values
        })
        monthly_results.append(monthly_df)


    # Combine across years and average
        # Combine across years and compute mean values
    combined_df = pd.concat(monthly_results)
    grouped = combined_df.groupby('month').agg({
        'window_count': 'mean',
        'total_hours': 'mean'
    }).reset_index()
    grouped['percent_access'] = (grouped['window_count'] / grouped['total_hours']) * 100
    grouped.rename(columns={'window_count': 'avg_weather_window_count'}, inplace=True)
    return grouped[['month', 'avg_weather_window_count', 'percent_access']]


def compute_duration_distribution(lat, lon, wave_threshold, wind_threshold, data_dir="data/processed/"):
    """
    Compute frequency of weather window durations across all years.

    Returns:
    - DataFrame with duration (in hours) and count
    """
    netcdf_files = sorted(glob(os.path.join(data_dir, "*_with_valid_time.nc")))
    duration_list = []

    for file in netcdf_files:
        ds = xr.open_dataset(file)
        time = ds['valid_time']

        swh = extract_time_series_at_location(ds['swh'], lat, lon)
        
        if wind_threshold is not None:
            u10 = extract_time_series_at_location(ds['u10'], lat, lon)
            v10 = extract_time_series_at_location(ds['v10'], lat, lon)
            wind = np.sqrt(u10**2 + v10**2)
            mask = (swh <= wave_threshold) & (wind <= wind_threshold)
        else:
            mask = swh <= wave_threshold

        # Convert to 1D numpy array
        mask_vals = mask.values.astype(int)
        
        current_length = 0
        for is_valid in mask_vals:
            if is_valid:
                current_length += 1
            else:
                if current_length > 0:
                    duration_list.append(current_length)
                    current_length = 0
        if current_length > 0:
            duration_list.append(current_length)

    # Count durations
    duration_series = pd.Series(duration_list)
    duration_counts = duration_series.value_counts().sort_index().reset_index()
    duration_counts.columns = ['duration_hours', 'count']
    
    return duration_counts

def compute_wait_times(lat, lon, wave_threshold, wind_threshold, duration_hours, data_dir="data/processed/"):
    from glob import glob
    import xarray as xr
    import numpy as np
    import pandas as pd
    #from scripts.utils import extract_time_series_at_location, rolling_weather_window_checker
    #from dashboard.scripts.utils import extract_time_series_at_location, rolling_weather_window_checker


    netcdf_files = sorted(glob(os.path.join(data_dir, "*_with_valid_time.nc")))
    wait_times = []

    for file in netcdf_files:
        ds = xr.open_dataset(file)
        time = ds['valid_time']
        swh = extract_time_series_at_location(ds['swh'], lat, lon)

        if wind_threshold is not None:
            u10 = extract_time_series_at_location(ds['u10'], lat, lon)
            v10 = extract_time_series_at_location(ds['v10'], lat, lon)
            wind = np.sqrt(u10 ** 2 + v10 ** 2)
            mask = (swh <= wave_threshold) & (wind <= wind_threshold)
        else:
            mask = swh <= wave_threshold

        rolled = rolling_weather_window_checker(mask, duration_hours)
        valid = rolled >= duration_hours

        df = pd.DataFrame({
            'time': time.values,
            'valid': valid.values
        })

        df['time'] = pd.to_datetime(df['time'])
        df = df[df['valid']].reset_index(drop=True)

        for i in range(1, len(df)):
            delta = (df.loc[i, 'time'] - df.loc[i - 1, 'time']).total_seconds() / 3600  # in hours
            if delta > duration_hours:
                wait_times.append({
                    'wait_hours': delta,
                    'month': df.loc[i, 'time'].month
                })

    return pd.DataFrame(wait_times)  # Returns DataFrame with wait_hours and month


def compute_persistence_table(lat, lon, wave_threshold, wind_threshold=None, durations=[3, 6, 12, 24, 48]):
    all_durations = []

    for duration in durations:
        df = compute_monthly_weather_windows(lat, lon, wave_threshold, wind_threshold, duration)
        df['duration_hours'] = duration
        df = df.rename(columns={'percent_access': 'access_percent'})  # rename for clarity
        all_durations.append(df[['month', 'access_percent', 'duration_hours']])

    result_df = pd.concat(all_durations)

    # Pivot: rows = duration, columns = month, values = percent access
    pivot_df = result_df.pivot_table(index='duration_hours', columns='month', values='access_percent', fill_value=0)

    # Sort months numerically
    month_order = list(range(1, 13))
    pivot_df = pivot_df.reindex(columns=month_order, fill_value=0)

    return pivot_df






