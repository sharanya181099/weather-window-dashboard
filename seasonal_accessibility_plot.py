import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import calendar
from dashboard.scripts.process_weather_windows import compute_monthly_weather_windows

# --- Configuration ---
LOCATIONS = {
    #"Dublin Array": (53.25, -5.65),
    "Arklow Bank": (53.0, -5.75),
    "AMETS": (54.25, -10.30),
    #"Saoirse Wave Farm": (52.75, -10)
}

WAVE_THRESHOLDS = [1.0, 1.5, 2.0, 2.5, 3.0]
DURATION_HOURS = 6
WIND_THRESHOLD = 10
DATA_DIR = "data/processed"

WINTER_MONTHS = {
    12: "December",
    1: "January",
    2: "February"
}

# --- Step 1: Compute accessibility for all thresholds and months ---
all_data = []

for hs in WAVE_THRESHOLDS:
    for name, (lat, lon) in LOCATIONS.items():
        df = compute_monthly_weather_windows(
            lat, lon,
            wave_threshold=hs,
            wind_threshold=WIND_THRESHOLD,
            duration_hours=DURATION_HOURS,
            data_dir=DATA_DIR
        )
        if not df.empty:
            df = df[df['month'].isin(WINTER_MONTHS.keys())]
            df['Location'] = name
            df['Hs'] = f"{hs}m"
            all_data.append(df)

df = pd.concat(all_data)
df.rename(columns={'percent_access': 'accessibility_percent'}, inplace=True)
df['Month'] = df['month'].apply(lambda x: WINTER_MONTHS[x])
df['Hs'] = pd.Categorical(df['Hs'], categories=[f"{v}m" for v in WAVE_THRESHOLDS], ordered=True)

# --- Step 2: Format composite x-axis labels like "1m", "1.5m", etc. per month ---
df['Month_Hs'] = df['Hs']
df['Month'] = pd.Categorical(df['Month'], categories=["December", "January", "February"], ordered=True)

# --- Step 3: Plot grouped bars per month ---
sns.set(style="whitegrid")
fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)

for i, month in enumerate(["December", "January", "February"]):
    ax = axes[i]
    subset = df[df['Month'] == month]
    sns.barplot(
        data=subset,
        x='Hs',
        y='accessibility_percent',
        hue='Location',
        hue_order=LOCATIONS.keys(),
        ci=None,
        ax=ax
    )
    ax.set_title(month, fontsize=12)
    ax.set_xlabel("Wave Height Threshold")
    if i == 0:
        ax.set_ylabel("% Accessibility")
    else:
        ax.set_ylabel("")
    ax.set_ylim(0, 100)
    ax.legend_.remove()

# --- Final Layout ---
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, title="Location", loc='lower center', ncol=7, fontsize=10, title_fontsize=11)
plt.suptitle("Monthly Accessibility in Winter for Various Wave Height Thresholds", fontsize=14, y=1.02)
plt.tight_layout(rect=[0, 0.05, 1, 0.95])
plt.show()
