import os
from datetime import datetime

import pandas as pd
import streamlit as st

from data_loader import (load_raw, classes, year_columns, flow_wide, compare_wide,
                          window_wide, DATA_PATH, TOTAL, ALL_COUNTRIES, COUNTRIES,
                          MAIN_CROP_PERIODS, MID_CROP_PERIODS)
from charts import monthly_comparison, cumulative_forecast, compare_series
from table_html import seasonal_table_html, overview_table_html

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

div[data-testid="stSelectbox"] label p,
div[data-testid="stMultiSelect"] label p {
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #898781 !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"],
div[data-testid="stMultiSelect"] div[data-baseweb="select"] {
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


def render_single(country, class_):
    df_wide = flow_wide(df, country, class_)
    year_cols = year_columns(df_wide)
    main_wide = window_wide(df_wide, MAIN_CROP_PERIODS)
    mid_wide = window_wide(df_wide, MID_CROP_PERIODS)

    st.markdown(f"#### {class_} Pod Counts &middot; {country}", unsafe_allow_html=True)

    row1 = st.columns([1, 1])
    with row1[0]:
        st.plotly_chart(monthly_comparison(df_wide, year_cols, title="Monthly Counts", height=PANEL_H),
                         use_container_width=True)
    with row1[1]:
        st.plotly_chart(
            cumulative_forecast(df_wide, year_cols, title="Cumulative Counts", height=PANEL_H),
            use_container_width=True,
        )

    row2 = st.columns([1, 1])
    with row2[0]:
        st.plotly_chart(
            cumulative_forecast(main_wide, year_cols, title="Main Crop — Cumulative", height=PANEL_H),
            use_container_width=True,
        )
    with row2[1]:
        st.plotly_chart(
            cumulative_forecast(mid_wide, year_cols, title="Mid Crop — Cumulative", height=PANEL_H),
            use_container_width=True,
        )

    bottom_cols = st.columns([2, 1, 1])
    with bottom_cols[0]:
        st.markdown(
            seasonal_table_html(df_wide, year_cols, title=f"{class_} Pod Counts — {country}", unit="", kind="flow"),
            unsafe_allow_html=True,
        )
    with bottom_cols[1]:
        st.markdown(
            seasonal_table_html(main_wide, year_cols, title=f"{class_} — Main Crop ({country})",
                                 unit="", kind="flow", summary_label="Total"),
            unsafe_allow_html=True,
        )
    with bottom_cols[2]:
        st.markdown(
            seasonal_table_html(mid_wide, year_cols, title=f"{class_} — Mid Crop ({country})",
                                 unit="", kind="flow", summary_label="Total"),
            unsafe_allow_html=True,
        )


def render_compare(country, classes_selected):
    ref_wide = flow_wide(df, country, TOTAL)
    year_cols_full = year_columns(ref_wide)

    crop_year = st.selectbox("Crop Year", year_cols_full, index=len(year_cols_full) - 1,
                              key=f"pod_compare_crop_year_{country}")
    idx_sel = year_cols_full.index(crop_year)
    prev_year = year_cols_full[idx_sel - 1] if idx_sel > 0 else None

    st.markdown(f"#### {', '.join(classes_selected)} &middot; {country} &middot; {crop_year}",
                unsafe_allow_html=True)

    combined = compare_wide(df, country, classes_selected, crop_year)
    cols = st.columns([1, 1])
    with cols[0]:
        st.plotly_chart(compare_series(combined, classes_selected, f"Monthly Counts — {crop_year}", height=PANEL_H),
                         use_container_width=True)
    with cols[1]:
        st.plotly_chart(
            compare_series(combined, classes_selected, f"Cumulative Counts — {crop_year}",
                            height=PANEL_H, cumulative=True),
            use_container_width=True,
        )

    rows = []
    for c in classes_selected:
        w = flow_wide(df, country, c)
        latest_total = w[crop_year].sum(skipna=True)
        prev_total = w[prev_year].sum(skipna=True) if prev_year else None
        yoy = None
        if prev_total not in (None, 0) and pd.notna(prev_total):
            yoy = (latest_total - prev_total) / prev_total * 100
        rows.append({"name": c, "period": crop_year, "prev": prev_total, "latest": latest_total,
                     "yoy": yoy, "vs_avg": None, "unit": ""})
    st.markdown(
        overview_table_html(rows, f"{country} — Total by Class", prev_year or "—", crop_year),
        unsafe_allow_html=True,
    )


col_country, col_class, _ = st.columns([1, 2, 2])
with col_country:
    country = st.selectbox("Country", COUNTRY_OPTIONS, key="pod_slicer_country")
with col_class:
    class_sel = st.multiselect("Class", CLASS_OPTIONS, default=[TOTAL], key=f"pod_slicer_class_{country}")

if not class_sel:
    st.info("Select at least one class.")
elif len(class_sel) == 1:
    render_single(country, class_sel[0])
else:
    render_compare(country, class_sel)
