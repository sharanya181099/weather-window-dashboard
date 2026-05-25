# dashboard/app.py

import streamlit as st
import pandas as pd
import calendar
import altair as alt  
from scripts.process_weather_windows import (
    compute_monthly_weather_windows,
    compute_wait_times,
    compute_persistence_table 
)




# --------------------------
# Location options
# --------------------------
LOCATIONS = {
    "Dublin Array (Kish & Bray Banks)": (53.25, -5.65),
    "Arklow Bank Wind Park (County Wicklow)": (53.0, -5.75),
    "AMETS (Belmullet, Co. Mayo)" : (54.25, -10.30),
    "Saoirse Wave Farm (WestWave – Co. Clare)": (52.75, -10),
    #"Sceirde Rocks Wind Farm (County Galway)": (53.0, -10.25)
    #"Codling Wind Park (County Wicklow)": (53.05, -5.75),
   
    #"Celtic Sea": (51.0, -7.0),
    #"Irish Sea": (53.5, -4.5),
    #"Northwest Coast": (55.0, -10.0),
}

# --------------------------
# Streamlit UI
# --------------------------
st.markdown("# Weather Window Dashboard")
st.markdown("Use this tool to assess offshore accessibility windows based on wave and wind thresholds.")

st.markdown("---")
st.markdown("### Location Selection")
st.markdown("Choose how you would like to input a location:")


input_method = st.radio("How would you like to select the location?", ["Select from list", "Enter coordinates"])

if input_method == "Select from list":
    location_name = st.selectbox("Select Location", list(LOCATIONS.keys()))
    lat, lon = LOCATIONS[location_name]
    st.info(f"Using predefined location: {location_name} ({lat:.2f}, {lon:.2f})")

else:
    # input_lat = st.number_input("Latitude", min_value=50.0, max_value=56.0, value=53.0, step=0.1)
    # input_lon = st.number_input("Longitude", min_value=-10.5, max_value=-5.0, value=-8.0, step=0.1)
    col1, col2 = st.columns(2)
    with col1:
        input_lat = st.number_input("Latitude", min_value=50.0, max_value=56.0, value=53.0, step=0.1)
    with col2:
        input_lon = st.number_input("Longitude", min_value=-10.5, max_value=-5.0, value=-8.0, step=0.1)


    from scripts.utils import find_nearest_valid_point, load_valid_coords
    valid_coords = load_valid_coords("data/processed/era5_2015_with_valid_time.nc")
    nearest_lat, nearest_lon, distance_deg = find_nearest_valid_point(input_lat, input_lon, valid_coords)

    if distance_deg > 1.5:
        st.error("Entered coordinates are too far from Irish waters. Please choose a location closer to the coast.")
        st.stop()
    elif (input_lat != nearest_lat or input_lon != nearest_lon):
        st.warning(f"Showing results for nearest valid ocean point: ({nearest_lat:.2f}, {nearest_lon:.2f})")

    lat, lon = nearest_lat, nearest_lon

    



# # Wave threshold
# wave_threshold = st.selectbox("Select Wave Height Threshold (m)", [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0])


# # Wind threshold (optional)
# use_wind = st.checkbox("Include Wind Speed Constraint")
# wind_threshold = None
# if use_wind:
#     wind_threshold = st.selectbox("Select Wind Speed Threshold (m/s)", [6, 7, 8, 9, 10, 11, 12, 13, 14, 15])

# --------------------------
# Vessel Type Selection
# --------------------------
st.markdown("---")
st.markdown("### Vessel Type & Operational Limits")


vessel_options = {
    "Crew Transfer Vessel (CTV)": {"wave": 1.5, "wind": 10},
    "Service Operation Vessel (SOV)": {"wave": 2.5, "wind": 15},
    "Jack-Up Barge": {"wave": 1.65, "wind": 16},
    "Cable Laying Vessel": {"wave": 3.5, "wind": 15},
    "AHTS (Anchor Handler)": {"wave": 2.0, "wind": 20},
    "Custom (set manually)": {"wave": None, "wind": None}
}

vessel_type = st.selectbox("Vessel Type", list(vessel_options.keys()))

if vessel_type != "Custom (set manually)":
    wave_threshold = vessel_options[vessel_type]["wave"]
    wind_threshold = vessel_options[vessel_type]["wind"]
    use_wind = True
    st.info(f"Significant Wave Height threshold: ≤ {wave_threshold} m | Wind Speed threshold: ≤ {wind_threshold} m/s")
else:
    # wave_threshold = st.selectbox("Select Wave Height Threshold (m)", [0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
    # use_wind = st.checkbox("Include Wind Speed Constraint")
    with st.expander("Manual Threshold Settings", expanded=True):
        wave_threshold = st.selectbox("Significant Wave Height Threshold (m)", [0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
        use_wind = st.checkbox("Include Wind Speed Constraint")
        wind_threshold = (
            st.selectbox("Wind Speed Threshold (m/s)", [5, 8, 10, 12, 15, 20]) if use_wind else None
        )

   


# Duration
duration = st.selectbox("Select Minimum Window Duration (hours)", [3, 6, 9, 12, 18, 24, 36, 48, 72])

# Run Analysis
if st.button("Run Analysis"):
    #st.info(f"Running analysis for {location_name} with wave ≤ {wave_threshold}m"
    # st.info(f"Running analysis for location at ({lat:.2f}, {lon:.2f}) with wave ≤ {wave_threshold}m"

    #         f"{', wind ≤ ' + str(wind_threshold) + ' m/s' if use_wind else ''} "
    #         f"and duration ≥ {duration}h...")
    # st.success("Analysis Complete!")
    st.success(
        f"Location: ({lat:.2f}, {lon:.2f})\n\n"
        f"Wave ≤ {wave_threshold} m"
        + (f" | Wind ≤ {wind_threshold} m/s" if use_wind else "")
        + f" | Duration ≥ {duration}h"
    )

    
    # -----------------------
    # Persistence Table UI
    # -----------------------

    st.subheader("Persistence Table (Monthly Accessibility Percentage)")
    durations_to_test = [3, 6, 12, 24, 48]  # durations in hours
    persistence_df = compute_persistence_table(lat, lon, wave_threshold, wind_threshold, durations=durations_to_test)

    # Rename columns to month names for better display
    month_map = {i: calendar.month_abbr[i] for i in range(1, 13)}
    persistence_df.columns = [month_map[m] for m in persistence_df.columns]

    st.dataframe(persistence_df.style.format("{:.0f}%"), use_container_width=True)


    # Monthly accessibility
    result_df = compute_monthly_weather_windows(
        lat=lat,
        lon=lon,
        wave_threshold=wave_threshold,
        wind_threshold=wind_threshold,
        duration_hours=duration
    )

    
    st.subheader("Monthly Weather Window Count")

    result_df = result_df.rename(columns={
        'avg_weather_window_count': 'count',
        'percent_access': 'accessibility_percent'
    })

    # Add full month names (e.g. January, February)
    result_df['month_name'] = result_df['month'].apply(lambda x: calendar.month_name[x])

    chart = alt.Chart(result_df).mark_bar(color='#4C78A8', cornerRadius=5).encode(
        x=alt.X('month_name:N', title='Month', sort=list(calendar.month_name)[1:]),
        y=alt.Y('count:Q', title='Weather Window Count'),
        tooltip=[
            alt.Tooltip('month_name:N', title='Month'),
            alt.Tooltip('count:Q', title='Window Count'),
            alt.Tooltip('accessibility_percent:Q', title='Access %', format='.1f')
        ]
    ).properties(
        width=700,
        height=400
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).configure_title(
        fontSize=18,
        anchor='start'
    ).configure_view(
        strokeWidth=0
    )

    st.altair_chart(chart, use_container_width=True)

    result_df['accessibility_percent'] = result_df['accessibility_percent'].round(1)
    st.dataframe(result_df.drop(columns=["month"]))

    # --- Monthly Accessibility Line Chart (in addition to bar) ---
    st.subheader("Monthly Accessibility Trend")


    line_chart = alt.Chart(result_df).mark_line(point=True, color='green').encode(
        x=alt.X('month_name:N', title='Month', sort=list(calendar.month_name)[1:]),
        y=alt.Y('accessibility_percent:Q', title='Accessibility (%)'),
        tooltip=['month_name:N', 'accessibility_percent:Q']
    )

    area = alt.Chart(result_df).mark_area(opacity=0.2, color='green').encode(
        x=alt.X('month_name:N', sort=list(calendar.month_name)[1:]),
        y='accessibility_percent:Q'
    )

    st.altair_chart(area + line_chart, use_container_width=True)


    # --- Seasonal Aggregation ---
    season_map = {
        'Winter': ['December', 'January', 'February'],
        'Spring': ['March', 'April', 'May'],
        'Summer': ['June', 'July', 'August'],
        'Autumn': ['September', 'October', 'November']
    }

    # Assign a 'season' column
    def get_season(month):
        for season, months in season_map.items():
            if month in months:
                return season
    result_df['season'] = result_df['month_name'].apply(get_season)

    # Group by season
    season_df = result_df.groupby('season', as_index=False).agg({
        'accessibility_percent': 'mean',
        'count': 'sum'
    })

    st.subheader("Seasonal Weather Window Accessibility")

    season_chart = alt.Chart(season_df).mark_bar(color='#4C78A8',size=40, cornerRadius=5).encode(
        x=alt.X('season:N', title='Season', sort=['Winter', 'Spring', 'Summer', 'Autumn']),
        y=alt.Y('accessibility_percent:Q', title='Mean Accessibility (%)'),
        tooltip=[
            alt.Tooltip('season:N', title='Season'),
            alt.Tooltip('accessibility_percent:Q', title='Mean Access %', format='.1f'),
            alt.Tooltip('count:Q', title='Total Windows')
        ]
    ).properties(
        width=600,
        height=350
    )

    st.altair_chart(season_chart, use_container_width=True)

    


    from scripts.process_weather_windows import compute_wait_times

    wait_df = compute_wait_times(lat, lon, wave_threshold, wind_threshold, duration)
    wait_df['wait_days'] = wait_df['wait_hours'] / 24
    wait_df['month_name'] = wait_df['month'].apply(lambda x: calendar.month_name[x])


    # Convert to days
    st.subheader("Wait Time Between Weather Windows")
    st.write(f"**Mean wait time:** {wait_df['wait_days'].mean():.1f} days")
    st.write(f"**Max wait time:** {wait_df['wait_days'].max():.1f} days")


    # Monthly Average Wait Time Bar Chart
    monthly_wait = wait_df.groupby('month_name', sort=False)['wait_days'].mean().reset_index()
    monthly_wait['wait_days'] = monthly_wait['wait_days'].round(2)

    st.subheader("Average Wait Time Per Month")

    line_chart = alt.Chart(monthly_wait).mark_line(point=True, color='orange').encode(
        x=alt.X('month_name:N', title='Month', sort=list(calendar.month_name)[1:]),
        y=alt.Y('wait_days:Q', title='Average Wait Time (days)'),
        tooltip=['month_name:N', 'wait_days:Q']
    ).properties(
        width=700,
        height=400,
        title=f"Monthly Average Wait Time (Hs ≤ {wave_threshold}m, Duration ≥ {duration}h)"
    )

    st.altair_chart(line_chart, use_container_width=True)

    # Monthly Wait Time Summary Table
    summary_wait = wait_df.groupby('month_name', sort=False).agg(
        avg_wait=('wait_days', 'mean'),
        max_wait=('wait_days', 'max')
    ).reset_index()

    summary_wait['avg_wait'] = summary_wait['avg_wait'].round(2)
    summary_wait['max_wait'] = summary_wait['max_wait'].round(2)

    st.subheader("Monthly Wait Time Summary Table")
    st.dataframe(summary_wait.rename(columns={
        'month_name': 'Month',
        'avg_wait': 'Average Wait (days)',
        'max_wait': 'Max Wait (days)'
    }))






    # Duration distribution
    #from scripts.process_weather_windows import compute_duration_distribution

    #duration_df = compute_duration_distribution(
    #    lat=lat,
     #   lon=lon,
     #   wave_threshold=wave_threshold,
      #  wind_threshold=wind_threshold
    #)

   # st.subheader("📊 Weather Window Duration Distribution")
   # st.bar_chart(duration_df.set_index('duration_hours'))
   # st.dataframe(duration_df)
