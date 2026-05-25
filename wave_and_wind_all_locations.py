import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import calendar
from dashboard.scripts.process_weather_windows import compute_monthly_weather_windows

# ---- STEP 1: Define locations and thresholds ----
LOCATIONS = {
    #"Dublin Array": (53.25, -5.65),
    "Arklow Bank": (53.0, -5.75),
    "AMETS": (54.25, -10.30),
    #"Saoirse Wave Farm": (52.75, -10)
}

wave_threshold = 1.5  # meters
wind_threshold = 6  # m/s
duration = 6  # hours
data_dir = "data/processed"  # directory containing 10 years of *_with_valid_time.nc

# ---- STEP 2: Compute weather window accessibility ----
all_results = []

for name, (lat, lon) in LOCATIONS.items():
    df = compute_monthly_weather_windows(
        lat, lon,
        wave_threshold=wave_threshold,
        wind_threshold=wind_threshold,
        duration_hours=duration,
        data_dir=data_dir
    )
    if not df.empty:
        df['Location'] = name
        all_results.append(df)

# ---- STEP 3: Combine, label, and average results ----
result_df = pd.concat(all_results)
result_df.rename(columns={'percent_access': 'accessibility_percent'}, inplace=True)

# Month names
result_df['month_name'] = result_df['month'].apply(lambda x: calendar.month_abbr[x])
result_df['month_name'] = pd.Categorical(result_df['month_name'], categories=calendar.month_abbr[1:], ordered=True)

# Group by month and location (mean across years)
grouped_df = result_df.groupby(['Location', 'month_name'], as_index=False)['accessibility_percent'].mean()

# ---- STEP 4: Plot ----
plt.figure(figsize=(12, 6))
sns.set(style="whitegrid")

sns.lineplot(data=grouped_df, x='month_name', y='accessibility_percent', hue='Location', marker='o')

plt.title("Monthly Weather Window Accessibility (Hs < 1.5m & Wind Speed < 10 m/s & Duartion = 6 hours)")
plt.ylim(0, 100)
plt.ylabel("Accessibility (%)")
plt.xlabel("Month")
plt.legend(title='Location')
plt.tight_layout()
plt.show()
