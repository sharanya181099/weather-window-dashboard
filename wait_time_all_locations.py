import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import calendar
from dashboard.scripts.process_weather_windows import compute_wait_times

# --- Configuration ---
LOCATIONS = {
   # "Dublin Array": (53.25, -5.65),
    "Arklow Bank": (53.0, -5.75),
    "AMETS": (54.25, -10.30),
    #"Saoirse Wave Farm": (52.75, -10)
}

WAVE_THRESHOLD = 2  # adjust as needed
DURATION_HOURS = 6
WIND_THRESHOLD = 12.0
DATA_DIR = "data/processed"

# --- Step 1: Calculate wait times per location ---
all_wait_data = []

for name, (lat, lon) in LOCATIONS.items():
    df = compute_wait_times(
        lat, lon,
        wave_threshold=WAVE_THRESHOLD,
        wind_threshold=WIND_THRESHOLD,
        duration_hours=DURATION_HOURS,
        data_dir=DATA_DIR
    )
    if not df.empty:
        df['Location'] = name
        all_wait_data.append(df)

# Combine and prepare data
wait_df = pd.concat(all_wait_data)
wait_df['wait_time_days'] = wait_df['wait_hours'] / 24
wait_df['month_name'] = wait_df['month'].apply(lambda x: calendar.month_name[x])
wait_df['month_name'] = pd.Categorical(wait_df['month_name'], categories=calendar.month_name[1:], ordered=True)

# Average wait time per month per location
grouped_df = wait_df.groupby(['Location', 'month_name'], as_index=False)['wait_time_days'].mean()


# --- Step 2: Plot ---
sns.set(style="whitegrid")
plt.figure(figsize=(14, 6))

sns.lineplot(
    data=grouped_df,
    x='month_name',
    y='wait_time_days',
    hue='Location',
    marker='o'
)

plt.title(f"Monthly Average Wait Time (Hs ≤ {WAVE_THRESHOLD} m & Wind ≤ {WIND_THRESHOLD} m/s & Duration = 6 hours)")
plt.xlabel("Month")
plt.ylabel("Average Wait Time (days)")
plt.xticks(rotation=45)
plt.ylim(0, grouped_df['wait_time_days'].max() + 1)
plt.tight_layout()
plt.legend(title="Location")
plt.show()
