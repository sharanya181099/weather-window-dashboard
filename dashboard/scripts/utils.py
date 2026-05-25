# scripts/utils.py

import numpy as np
import xarray as xr

def extract_time_series_at_location(data_array, lat, lon):
    lat = float(lat)
    lon = float(lon)
    # Find nearest grid point indices, then use positional indexing
    # (avoids xarray.sel() which is broken with newer pandas)
    lats = data_array.latitude.values
    lons = data_array.longitude.values
    lat_idx = int(abs(lats - lat).argmin())
    lon_idx = int(abs(lons - lon).argmin())
    return data_array.isel(latitude=lat_idx, longitude=lon_idx)

def rolling_weather_window_checker(mask_array, duration_hours):
    time_dim = 'time'
    for dim in mask_array.dims:
        if 'time' in dim:
            time_dim = dim
            break
    rolled = mask_array.rolling({time_dim: duration_hours}, center=False).sum()
    return rolled


def load_valid_coords(filepath):
    ds = xr.open_dataset(filepath)
    swh = ds['swh'].isel(valid_time=0)
    latitudes = ds['latitude'].values
    longitudes = ds['longitude'].values
    valid_mask = ~np.isnan(swh.values)
    valid_lat, valid_lon = np.meshgrid(latitudes, longitudes, indexing='ij')
    return np.column_stack((valid_lat[valid_mask], valid_lon[valid_mask]))

def find_nearest_valid_point(lat, lon, valid_coords):
    distances = np.sqrt((valid_coords[:, 0] - lat) ** 2 + (valid_coords[:, 1] - lon) ** 2)
    idx = np.argmin(distances)
    return valid_coords[idx][0], valid_coords[idx][1], distances[idx]


