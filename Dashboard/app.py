import os
from datetime import datetime

import streamlit as st

from data_loader import (load_raw, classes, year_columns, flow_wide,
                          window_wide, DATA_PATH, TOTAL, ALL_COUNTRIES, COUNTRIES,
                          MAIN_CROP_PERIODS, MID_CROP_PERIODS)
from charts import monthly_comparison, cumulative_forecast
from table_html import seasonal_table_html

st.set_page_config(page_title="Cocoa Pod Counts: Ghana & Ivory Coast", layout="wide")

CSS = """
<style>
.stApp { background-color: #ffffff; }
.block-container { max-width: 1500px; padding-top: 2.5rem; }

.pod-header h1 {
    color: #1e3a5f;
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 0.02em;
    margin: 0;
}
.pod-header p {
    color: #898781;
    font-size: 13px;
    margin: 4px 0 0;
}

div[data-testid="stSelectbox"] label p {
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #898781 !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    border-radius: 8px;
}

.section-label {
    font-size: 13px;
    font-weight: 700;
    color: #898781;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 16px 0 8px;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

df = load_raw()
COUNTRY_OPTIONS = COUNTRIES + [ALL_COUNTRIES]
CLASS_OPTIONS = classes(df)

PANEL_H = 300


def _latest_period_label():
    df_wide = flow_wide(df, ALL_COUNTRIES, TOTAL)
    year_cols = [y for y in year_columns(df_wide) if y != "LTA"]
    current_year = year_cols[-1]
    s = df_wide[current_year]
    idx = s.last_valid_index()
    if idx is None:
        return current_year
    return f"{df_wide.loc[idx, 'Period']} {current_year}"


updated_str = datetime.fromtimestamp(os.path.getmtime(DATA_PATH)).strftime("%d %b %Y, %H:%M")
st.markdown(
    f'<div class="pod-header"><h1>Cocoa Pod Counts — Ghana &amp; Ivory Coast</h1>'
    f'<p>Data last updated {updated_str} &nbsp;&middot;&nbsp; '
    f'Latest survey through {_latest_period_label()}</p></div>',
    unsafe_allow_html=True,
)
st.write("")

col_country, col_class, _ = st.columns([1, 2, 2])
with col_country:
    country = st.selectbox("Country", COUNTRY_OPTIONS, key="pod_slicer_country")
with col_class:
    class_ = st.selectbox("Class", CLASS_OPTIONS, index=CLASS_OPTIONS.index(TOTAL), key="pod_slicer_class")

df_wide = flow_wide(df, country, class_)
year_cols = year_columns(df_wide)
main_wide = window_wide(df_wide, MAIN_CROP_PERIODS)
mid_wide = window_wide(df_wide, MID_CROP_PERIODS)
ctx = f"{country} · {class_}"

st.markdown(f"#### {class_} Pod Counts &middot; {country}", unsafe_allow_html=True)

row1 = st.columns([1, 1])
with row1[0]:
    st.plotly_chart(monthly_comparison(df_wide, year_cols, title=f"{ctx} — Monthly Counts", height=PANEL_H),
                     use_container_width=True)
with row1[1]:
    # 22/23 dropped from this specific view by request.
    cum_year_cols = [y for y in year_cols if y != "22/23"]
    st.plotly_chart(
        cumulative_forecast(df_wide, cum_year_cols, title=f"{ctx} — Cumulative Counts", height=PANEL_H),
        use_container_width=True,
    )

row2 = st.columns([1, 1])
with row2[0]:
    st.plotly_chart(
        cumulative_forecast(main_wide, year_cols, title=f"{ctx} — Main Crop Cumulative", height=PANEL_H),
        use_container_width=True,
    )
with row2[1]:
    st.plotly_chart(
        cumulative_forecast(mid_wide, year_cols, title=f"{ctx} — Mid Crop Cumulative", height=PANEL_H),
        use_container_width=True,
    )

st.markdown(
    seasonal_table_html(df_wide, year_cols, title=f"{class_} Pod Counts — {country}", unit="", kind="flow"),
    unsafe_allow_html=True,
)
st.markdown(
    seasonal_table_html(main_wide, year_cols, title=f"{class_} — Main Crop ({country})",
                         unit="", kind="flow", summary_label="Total"),
    unsafe_allow_html=True,
)
st.markdown(
    seasonal_table_html(mid_wide, year_cols, title=f"{class_} — Mid Crop ({country})",
                         unit="", kind="flow", summary_label="Total"),
    unsafe_allow_html=True,
)
