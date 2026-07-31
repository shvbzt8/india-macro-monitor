import streamlit as st
import json
import plotly.express as px
import pandas as pd
import matplotlib.pyplot as plt
from pandas.api.types import CategoricalDtype
import datetime as dt
from plotly.subplots import make_subplots
import plotly.graph_objects as go


st.set_page_config(layout="wide")
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
    return pd.read_excel(df_path)

data = load_geojson("India_LGD_states.geojson")
df =  load_df("cpi_6.xlsx")

state_mapping = {
    "Andaman And Nicobar Islands": "A & N Islands",
    "Jammu And Kashmir": "Jammu & Kashmir",
    "NCT of Delhi": "Delhi",
    "The Dadra And Nagar Haveli And Daman And Diu": "DNHDD",
}


with open("India_LGD_states.geojson") as f:
    india_geojson = json.load(f)



#------------------------------------Plot CPI inflation rate state wise------------------------------------

df["state"] = df["state"].replace(state_mapping)
df["Month-Year"] = df["month"].astype("str") + "-" + df["year"].astype("str")
df["date"] = pd.to_datetime(df["Month-Year"], format= '%B-%Y')
df.sort_values(by=["state","division", "date"], inplace=True)


options = df.loc[df["date"] >= "2026-01-01 00:00:00", "Month-Year"].unique()
labels = "Select month-year"
selected = st.sidebar.selectbox(labels, options)
item = st.sidebar.selectbox("Select item group", df["division"].unique().tolist())

df_map = df[(df["date"] == dt.datetime.strptime(selected, "%B-%Y")) & (df["division"] == item) & (df["sector"] == "Combined")]
st.write(selected)


config = {"scrollZoom": False}

fig = px.choropleth_map(df_map, geojson= india_geojson, 
                        locations= "state", 
                        featureidkey= "properties.state_name",
                        color= "inflation",
                        color_continuous_scale='Viridis',
                        title=f'State-wise CPI-General {selected}'
                           )
fig.update_traces(
    hovertemplate="<b>%{location}</b><br>%{z:.2f}%<extra></extra>"
)

fig.update_coloraxes(
    colorbar=dict(
        ticks = "outside",
        title=dict(text="Inflation<br>(% YoY)", side="top"),
        ticksuffix="%",       
        thickness=14,
        len=0.5,              
        x=0.95,               # nudge it inward
    )
)

fig.update_layout(
        title=dict(                                    # dict goes HERE, in layout
        subtitle=dict(text="Year-on-year change across Indian states and UTs"),
        x=.0075,
        y=0.990,
        xanchor="left",
    ),
    font=dict(color="black"),
    paper_bgcolor="white",
    map_style="white-bg",
    width=600,
    height=500, 
    map_zoom=2.95,
    map_center={"lat": 22, "lon": 82},   # India centroid lat-long
    margin={"r":0,"t":30,"l":0,"b":25}
)

fig.add_annotation(
    text="Source: MoSPI, CPI series (base 2024 = 100)",
    xref="paper", yref="paper",
    x=0.015, y=0.000, xanchor="left", yanchor="top",
    showarrow=False, font=dict(size=10, color="grey"),
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


fig_bar.update_layout(width=630, height=430)
fig_bar.update_layout(bargap=0.55, bargroupgap=0.0)
fig_bar.update_layout(
    plot_bgcolor="white",
    paper_bgcolor="white",
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=False, ticks="outside", showline = True)
)


#------------------------------------Plot for top 5 states CPI inflation rate----------------------------------------------





filter = (df["division"] == item) & (df["state"] == "All India") & (df["sector"] == "Combined")
df_ts = df[filter].copy()
df_ts_clean = df_ts.dropna(subset=["inflation"])

fig_dual = make_subplots(specs=[[{"secondary_y": True}]])

fig_dual.add_trace(
    go.Scatter(x=df_ts_clean["date"], y=df_ts_clean["inflation"], name="Inflation (% YoY)", line=dict(color="tab:red" if False else "red")),
    secondary_y=False,
)

fig_dual.add_trace(
    go.Scatter(x=df_ts_clean["date"], y=df_ts_clean["index"], name="CPI Level", line=dict(color="blue")),
    secondary_y=True,
)

fig_dual.update_xaxes(title_text="Month-Year", dtick="M1", tickformat="%b-%Y")
fig_dual.update_yaxes(title_text="CPI Inflation-%YoY", secondary_y=False)
fig_dual.update_yaxes(title_text="CPI Level", secondary_y=True)

fig_dual.update_layout(plot_bgcolor="#FFFFFF", 
                       paper_bgcolor="#FFFFFF",
                       width=750,
                       height = 400)
fig_dual.update_xaxes(ticks = "outside", showline=True, linecolor = "Black")
fig_dual.update_yaxes(ticks="outside", showline=True, linecolor="black", secondary_y=False)
fig_dual.update_yaxes(ticks="outside", showline=True, linecolor="black", secondary_y=True)







col1,col2 = st.columns(2, vertical_alignment= "bottom")

with col1:
    st.plotly_chart(fig,config=config,theme=None, use_container_width=False)

with col2:
    st.plotly_chart(fig_bar, config= config_bar,theme=None, use_container_width=False)

st.plotly_chart(fig_dual, theme=None, use_container_width=False)


