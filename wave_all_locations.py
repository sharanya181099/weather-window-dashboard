import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dashboard.scripts.process_weather_windows import compute_monthly_weather_windows


# ---- STEP 1: Define locations and parameters ----
LOCATIONS = {
    #"Dublin Array": (53.25, -5.65),
    "Arklow Bank": (53.0, -5.75),
    "AMETS": (54.25, -10.30),
    #"Saoirse Wave Farm": (52.75, -10)
}

wave_threshold = 1.5  # meters
duration = 6  # hours
data_dir = "data/processed"  # directory containing 10 years of *_with_valid_time.nc files

# ---- STEP 2: Calculate monthly accessibility for all locations ----
all_results = []

for name, (lat, lon) in LOCATIONS.items():
    df = compute_monthly_weather_windows(lat, lon, wave_threshold, wind_threshold=None, duration_hours=duration, data_dir=data_dir)
    df['Location'] = name
    all_results.append(df)

# ---- STEP 3: Combine and clean results ----
result_df = pd.concat(all_results)
result_df.rename(columns={'percent_access': 'accessibility_percent'}, inplace=True)

# Convert month number to name
result_df['month_name'] = result_df['month'].apply(lambda x: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][x-1])
result_df['month_name'] = pd.Categorical(result_df['month_name'], categories=[
    'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], ordered=True)

# Group in case of duplicate months across files
grouped_df = result_df.groupby(['Location', 'month_name'], as_index=False)['accessibility_percent'].mean()

# ---- STEP 4: Plotting ----
plt.figure(figsize=(12, 6))
sns.set(style="whitegrid")

sns.lineplot(data=grouped_df, x='month_name', y='accessibility_percent', hue='Location', marker='o')

plt.title("Monthly Weather Window Accessibility (Hs < 1.5m and Duartion = 6 hours)")
plt.ylim(0, 100)
plt.ylabel("Accessibility (%)")
plt.xlabel("Month")
plt.legend(title='Location')
plt.tight_layout()
plt.show()
