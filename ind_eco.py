import streamlit as st
import json
import plotly.express as px
import pandas as pd
import matplotlib.pyplot as plt
from pandas.api.types import CategoricalDtype
import datetime as dt
from plotly.subplots import make_subplots
import plotly.graph_objects as go


st.set_page_config(layout="wide", page_title="India CPI Inflation Tracker")
st.title("India CPI Inflation Tracker")
st.markdown(
    "Explore Consumer Price Index (CPI) inflation across Indian states and union territories, "
    "sourced from MoSPI's eSankhyiki portal. Pick a series, month, and item group in the sidebar "
    "-- the map, state ranking, and time series below all update together."
)
st.markdown(
    """
    <style>
    .mapboxgl-canvas-container.mapboxgl-interactive,
    .maplibregl-canvas-container.maplibregl-interactive {
        cursor: default !important;
    }
    div[data-baseweb="select"] > div {
        cursor: pointer !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_data
def load_geojson(path):
    print("loading json file...")
    with open(path) as f:
        return json.load(f)

    
@st.cache_data
def load_df(df_path):
    print("loading data...")
    return pd.read_parquet(df_path)

data = load_geojson("India_LGD_states.geojson")
df_all =  load_df("cpi_data.parquet")

# State names differ slightly between series (naming conventions and, for
# base 2012, pre-2020 UT boundaries), so each series gets its own mapping
# onto the geojson's "properties.state_name" values.
STATE_MAPPING_BY_BASE_YEAR = {
    2024: {
        "Andaman And Nicobar Islands": "A & N Islands",
        "Jammu And Kashmir": "Jammu & Kashmir",
        "NCT of Delhi": "Delhi",
        "The Dadra And Nagar Haveli And Daman And Diu": "DNHDD",
    },
    2012: {
        "Andaman & Nicobar Islands": "A & N Islands",
        # Dadra & Nagar Haveli and Daman & Diu were separate UTs pre-2020 and
        # have no matching feature in the current geojson (merged into
        # DNHDD), so they're left unmapped and simply won't render on the map.
    },
}

SERIES_OPTIONS = {
    "2025-present, base 2024 = 100 (Current series)": 2024,
    "2013-2025, base 2012 = 100 (Historical series)": 2012,
}


with open("India_LGD_states.geojson") as f:
    india_geojson = json.load(f)

# Every state/UT the geojson can render -- used so states with no CPI value
# for a given month (a real MoSPI data gap, not a pipeline bug) still show
# up on the map greyed out instead of silently vanishing.
ALL_MAP_STATES = sorted({feat["properties"]["state_name"] for feat in india_geojson["features"]})



#------------------------------------Plot CPI inflation rate state wise------------------------------------

series_label = st.sidebar.selectbox("Select CPI series", list(SERIES_OPTIONS.keys()))
st.sidebar.caption(
    "**Current series**: MoSPI's ongoing series, updated monthly (Jan 2025 onward, base 2024 = 100). "
    "**Historical series**: MoSPI's earlier methodology (Jan 2013-Dec 2025, base 2012 = 100); frozen, "
    "since MoSPI stopped publishing it once the current series took over. Index levels aren't "
    "comparable across the two -- each uses its own base period."
)
base_year = SERIES_OPTIONS[series_label]

df = df_all[df_all["base_year"] == base_year].copy()
df["state"] = df["state"].replace(STATE_MAPPING_BY_BASE_YEAR[base_year])
df["Month-Year"] = df["month"].astype("str") + "-" + df["year"].astype("str")
df["date"] = pd.to_datetime(df["Month-Year"], format= '%B-%Y')
df.sort_values(by=["state","division", "date"], inplace=True)


# Inflation (YoY) needs a same-month value from 12 months earlier, so it's
# null for every state/division in a series' first year (and MoSPI has its
# own occasional total gaps, e.g. April 2020) -- the map and bar chart both
# color by inflation, so picking one of these months would show no data at
# all. Drop them from the picker rather than let users land on a blank map.
months_with_data = set(
    df.loc[(df["sector"] == "Combined") & df["inflation"].notna(), "Month-Year"]
)
options = (
    df[df["Month-Year"].isin(months_with_data)][["date", "Month-Year"]]
    .drop_duplicates()
    .sort_values("date", ascending=False)["Month-Year"]
    .tolist()
)
labels = "Select month-year"
selected = st.sidebar.selectbox(labels, options)
st.sidebar.caption("The month the map and state-ranking chart show a snapshot of (the time series always shows full history).")

item = st.sidebar.selectbox("Select item group", df["division"].unique().tolist())
st.sidebar.caption(
    "The consumption category to filter all three charts by -- e.g. 'Food and beverages' or 'Housing'. "
    "'CPI (General)' (current series) / 'General' (historical series) is the headline all-items index."
)

df_map = df[(df["date"] == dt.datetime.strptime(selected, "%B-%Y")) & (df["division"] == item) & (df["sector"] == "Combined")]



config = {"scrollZoom": False}

# States with no value this month (either MoSPI never published one -- e.g.
# Arunachal Pradesh's Combined-sector CPI in the historical series -- or the
# state has no matching geojson feature at all, like Ladakh in the old
# series) get their own grey layer instead of just disappearing from the map.
df_map_have = df_map.dropna(subset=["inflation"])
no_data_states = sorted(set(ALL_MAP_STATES) - set(df_map_have["state"]))

fig = go.Figure()

fig.add_trace(go.Choroplethmap(
    geojson=india_geojson,
    locations=df_map_have["state"],
    featureidkey="properties.state_name",
    z=df_map_have["inflation"],
    coloraxis="coloraxis",
    marker_line_width=0.5,
    hovertemplate="<b>%{location}</b><br>%{z:.2f}%<extra></extra>",
    showlegend=False,
))

if no_data_states:
    fig.add_trace(go.Choroplethmap(
        geojson=india_geojson,
        locations=no_data_states,
        featureidkey="properties.state_name",
        z=[0] * len(no_data_states),
        showscale=False,
        colorscale=[[0, "#d3d3d3"], [1, "#d3d3d3"]],
        marker_line_width=0.5,
        hovertemplate="<b>%{location}</b><br>No data<extra></extra>",
        name="No data",
        showlegend=True,
    ))

fig.update_layout(
    coloraxis=dict(colorscale="Viridis"),
    legend=dict(x=0.02, y=0.055, xanchor="left", yanchor="bottom", bgcolor="rgba(255,255,255,0.7)", font=dict(size=12)),
)

fig.update_coloraxes(
    colorbar=dict(
        ticks = "outside",
        title=dict(text="Inflation<br>(% YoY)", side="top", font=dict(size=15)),
        tickfont=dict(size=13),
        ticksuffix="%",
        thickness=14,
        len=0.5,
        x=0.95,               # nudge it inward
    )
)

fig.update_layout(
        title=dict(                                    # dict goes HERE, in layout
        text=f"State-wise CPI-General {selected}",
        subtitle=dict(text="Year-on-year change across Indian states and UTs", font=dict(size=13)),
        font=dict(size=18),
        x=.0075,
        y=0.990,
        xanchor="left",
    ),
    font=dict(color="black", size=15),
    paper_bgcolor="white",
    map_style="white-bg",
    width=720,
    height=540,
    map_zoom=2.95,
    map_center={"lat": 22, "lon": 82},   # India centroid lat-long
    margin={"r":0,"t":30,"l":0,"b":25}
)

fig.add_annotation(
    text=f"Source: MoSPI, CPI series (base {base_year} = 100)",
    xref="paper", yref="paper",
    x=0.015, y=0.000, xanchor="left", yanchor="top",
    showarrow=False, font=dict(size=11, color="grey"),
)




#------------------------------------Plot for top 5 states CPI inflation rate----------------------------------------------

df_bar_filtered = df[(df["date"] == dt.datetime.strptime(selected, "%B-%Y")) & (df["division"] == item) ]
df_bar_filtered_states = df_bar_filtered[(df_bar_filtered["state"] != "All India") & (df_bar_filtered["sector"] == "Combined") ].copy()
df_bar_filtered_states = df_bar_filtered_states.sort_values(by=["inflation"], ascending=False)
top5_states = df_bar_filtered_states.head(5)["state"].tolist()
df_bar = df_bar_filtered[df_bar_filtered["state"].isin(top5_states)]


config_bar = {"scrollZoom": False}


fig_bar = px.bar(df_bar, x = "state", y = "inflation",color="sector", barmode="group", category_orders={'state':top5_states}, color_discrete_map={
    "Rural": "#E0D9D9",      # soft warm gray
    "Urban": "#B6B6B6",      # deeper warm gray-brown
    "Combined": "#C97B3D",   # muted burnt orange

    })


fig_bar.update_layout(width=720, height=540)
fig_bar.update_layout(bargap=0.55, bargroupgap=0.0)
fig_bar.update_layout(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(size=15),
    legend=dict(font=dict(size=14)),
    xaxis=dict(showgrid=False, title_font=dict(size=16), tickfont=dict(size=14)),
    yaxis=dict(showgrid=False, ticks="outside", showline = True, title_font=dict(size=16), tickfont=dict(size=14)),
)


#------------------------------------Plot for top 5 states CPI inflation rate----------------------------------------------





filter = (df["division"] == item) & (df["state"] == "All India") & (df["sector"] == "Combined")
df_ts = df[filter].copy()
df_ts_clean = df_ts.dropna(subset=["inflation"])

fig_dual = make_subplots(specs=[[{"secondary_y": True}]])

fig_dual.add_trace(
    go.Scatter(x=df_ts_clean["date"], y=df_ts_clean["inflation"], name="Inflation (% YoY)", line=dict(color="red", width=3.5)),
    secondary_y=False,
)

fig_dual.add_trace(
    go.Scatter(x=df_ts_clean["date"], y=df_ts_clean["index"], name="CPI Level", line=dict(color="blue", width=3.5)),
    secondary_y=True,
)

# With decades of monthly history (the old series especially), a tick for
# every month is unreadable -- space ticks out as the series gets longer.
n_months = df_ts_clean["date"].nunique()
if n_months > 96:
    ts_dtick = "M24"
elif n_months > 48:
    ts_dtick = "M12"
elif n_months > 24:
    ts_dtick = "M6"
else:
    ts_dtick = "M1"

fig_dual.update_xaxes(title_text="Month-Year", dtick=ts_dtick, tickformat="%b-%Y", tickangle=0)
fig_dual.update_yaxes(title_text="CPI Inflation-%YoY", secondary_y=False)
fig_dual.update_yaxes(title_text="CPI Level", secondary_y=True)

fig_dual.update_layout(plot_bgcolor="#FFFFFF",
                       paper_bgcolor="#FFFFFF",
                       width=1400,
                       height = 480,
                       font=dict(size=15),
                       legend=dict(font=dict(size=14)),
                       margin=dict(b=70))
fig_dual.update_xaxes(ticks = "outside", showline=True, linecolor = "Black", title_font=dict(size=16), tickfont=dict(size=14))
fig_dual.update_yaxes(ticks="outside", showline=True, linecolor="black", title_font=dict(size=16), tickfont=dict(size=14), secondary_y=False)
fig_dual.update_yaxes(ticks="outside", showline=True, linecolor="black", title_font=dict(size=16), tickfont=dict(size=14), secondary_y=True)







col1,col2 = st.columns(2, vertical_alignment= "bottom")

with col1:
    st.plotly_chart(fig,config=config,theme=None, use_container_width=False)

with col2:
    st.plotly_chart(fig_bar, config= config_bar,theme=None, use_container_width=False)

st.plotly_chart(fig_dual, theme=None, use_container_width=False)


