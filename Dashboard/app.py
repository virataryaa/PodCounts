import os
from datetime import datetime

import pandas as pd
import streamlit as st

from data_loader import (load_raw, classes, year_columns, flow_wide, compare_wide,
                          get_crop_years, window_wide, class_mix, class_month_matrix,
                          long_run_series, country_share_series, monthly_country_mix,
                          DATA_PATH, TOTAL, SETTINGS_LABEL, ALL_COUNTRIES, COUNTRIES,
                          MAIN_CROP_PERIODS, MID_CROP_PERIODS)
from charts import (monthly_comparison, cumulative_forecast, min_max_avg, summary_table,
                     ytd_comparison, compare_series, pie_breakdown, ranking_bar,
                     destination_heatmap, long_run_line, share_line, monthly_mix_bars)
from table_html import seasonal_table_html, summary_table_html, overview_table_html

st.set_page_config(page_title="Cocoa Pod Counts: Ghana & Ivory Coast", layout="wide")

CSS = """
<style>
.stApp { background-color: #ffffff; }
.block-container { max-width: 1400px; padding-top: 2.5rem; }

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
.card-desc {
    font-size: 12px;
    color: #898781;
    margin: -4px 0 10px;
    line-height: 1.4;
}

button[data-baseweb="tab"] p { font-size: 13px !important; font-weight: 600; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

df = load_raw()
COUNTRY_OPTIONS = COUNTRIES + [ALL_COUNTRIES]
CLASS_OPTIONS = classes(df)


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

tab_detail, tab_insights = st.tabs(["Detail", "Insights"])

PANEL_H = 330


def render_single(country, class_):
    df_wide = flow_wide(df, country, class_)
    year_cols = year_columns(df_wide)
    unit = "count"

    st.markdown(f"#### {class_} Pod Counts &middot; {country}", unsafe_allow_html=True)

    cols = st.columns([1, 1])
    with cols[0]:
        st.plotly_chart(monthly_comparison(df_wide, year_cols, title="Monthly Counts", height=PANEL_H),
                         use_container_width=True)
        st.plotly_chart(min_max_avg(df_wide, year_cols, height=PANEL_H), use_container_width=True)
    with cols[1]:
        st.plotly_chart(
            cumulative_forecast(df_wide, year_cols, title="Cumulative Counts (crop year)", height=2 * PANEL_H + 40),
            use_container_width=True,
        )

    bottom_cols = st.columns([1, 3])
    with bottom_cols[0]:
        table, period_label = summary_table(df_wide, year_cols, "flow")
        st.markdown(summary_table_html(table, period_label, unit), unsafe_allow_html=True)
    with bottom_cols[1]:
        table_height = 24 + 18 * len(year_cols)
        st.plotly_chart(ytd_comparison(df_wide, year_cols, kind="flow", height=table_height),
                         use_container_width=True)

    st.markdown(
        seasonal_table_html(df_wide, year_cols, title=f"{class_} Pod Counts — {country}", unit=unit, kind="flow"),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">Main Crop (Apr–Sep) &amp; Mid Crop (Oct–Mar)</div>',
                unsafe_allow_html=True)
    main_wide = window_wide(df_wide, MAIN_CROP_PERIODS)
    mid_wide = window_wide(df_wide, MID_CROP_PERIODS)
    cols = st.columns([1, 1])
    with cols[0]:
        st.plotly_chart(
            cumulative_forecast(main_wide, year_cols, title="Main Crop — Cumulative", height=PANEL_H),
            use_container_width=True,
        )
        st.markdown(
            seasonal_table_html(main_wide, year_cols, title=f"{class_} — Main Crop ({country})",
                                 unit=unit, kind="flow", summary_label="Total"),
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.plotly_chart(
            cumulative_forecast(mid_wide, year_cols, title="Mid Crop — Cumulative", height=PANEL_H),
            use_container_width=True,
        )
        st.markdown(
            seasonal_table_html(mid_wide, year_cols, title=f"{class_} — Mid Crop ({country})",
                                 unit=unit, kind="flow", summary_label="Total"),
            unsafe_allow_html=True,
        )


def render_compare(country, classes_selected):
    ref_wide = flow_wide(df, country, TOTAL)
    year_cols_full = year_columns(ref_wide)
    real_years = [y for y in year_cols_full if y != "LTA"]

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
                     "yoy": yoy, "vs_avg": None, "unit": "count"})
    st.markdown(
        overview_table_html(rows, f"{country} — Total by Class", prev_year or "—", crop_year),
        unsafe_allow_html=True,
    )


with tab_detail:
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


with tab_insights:
    col_country, col_range, _ = st.columns([1, 2, 2])
    with col_country:
        country_ins = st.selectbox("Country", COUNTRY_OPTIONS, key="pod_insights_country")
    crop_years = get_crop_years(df)
    default_start = crop_years[max(0, len(crop_years) - 3)]
    with col_range:
        start_cy, end_cy = st.select_slider(
            "Crop Year Range", options=crop_years, value=(default_start, crop_years[-1]),
            key=f"pod_insights_range_{country_ins}",
        )
    i0, i1 = crop_years.index(start_cy), crop_years.index(end_cy)
    range_years = crop_years[i0:i1 + 1]
    range_caption = start_cy if start_cy == end_cy else f"{start_cy}–{end_cy}"

    mix = class_mix(df, country_ins, range_years)

    with st.expander(f"Class Mix — {country_ins} ({range_caption})", expanded=True):
        if mix:
            labels = [c for c, _ in mix]
            values = [v for _, v in mix]
            st.plotly_chart(pie_breakdown(labels, values, "Share by Class", height=PANEL_H),
                             use_container_width=True)
        else:
            st.info("No data for this Country / Crop Year range.")

    with st.expander(f"Ranked Classes — {country_ins} ({range_caption})", expanded=True):
        if mix:
            st.plotly_chart(ranking_bar(labels, values, "Classes by Count", height=PANEL_H),
                             use_container_width=True)
        else:
            st.info("No data for this Country / Crop Year range.")

    matrix = class_month_matrix(df, country_ins, range_years)
    with st.expander(f"Class × Month — {country_ins} ({range_caption})", expanded=True):
        if not matrix.empty:
            st.plotly_chart(
                destination_heatmap(matrix, f"{country_ins} Pod Counts by Class & Month",
                                     height=max(280, 40 * len(matrix) + 100)),
                use_container_width=True,
            )
        else:
            st.info("No data for this Country / Crop Year range.")

    st.markdown('<div class="section-label">Long-Run History</div>', unsafe_allow_html=True)
    longrun_class = st.selectbox("Class", CLASS_OPTIONS, key=f"pod_insights_longrun_class_{country_ins}")
    series = long_run_series(df, country_ins, longrun_class)
    st.plotly_chart(
        long_run_line(series["Date"], series["NUMBER"],
                      f"{longrun_class} Pod Counts — {country_ins} — Full History", height=PANEL_H),
        use_container_width=True,
    )

    st.markdown('<div class="section-label">Ghana / Ivory Coast Mix</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-desc">IVC count &divide; (GH count + IVC count) &times; 100 for the selected class '
        '&mdash; i.e. what share of the combined Ghana+Ivory Coast pod count comes from Ivory Coast.</div>',
        unsafe_allow_html=True,
    )
    mix_class = st.selectbox("Class", CLASS_OPTIONS, key="pod_insights_mix_class")
    share = country_share_series(df, mix_class)
    share_windowed = [(y, v) for y, v in share if y in range_years]
    st.plotly_chart(
        share_line([y for y, _ in share_windowed], [v for _, v in share_windowed],
                   f"IVC Share of Combined {mix_class} Counts ({range_caption})", height=PANEL_H),
        use_container_width=True,
    )

    monthly_mix = monthly_country_mix(df, mix_class, range_years)
    st.plotly_chart(
        monthly_mix_bars(monthly_mix["Date"], monthly_mix["GH"], monthly_mix["IVC"],
                          monthly_mix["IVCSharePct"],
                          f"Monthly GH vs IVC {mix_class} Counts ({range_caption})", height=PANEL_H,
                          name_a="GH", name_b="IVC", share_name="IVC %"),
        use_container_width=True,
    )
