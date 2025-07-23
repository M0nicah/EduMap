import streamlit as st
import pandas as pd
import plotly.express as px

# Load the dataset
df = pd.read_csv("kenya_primary_schools_updated.csv")

# --- Data Preprocessing ---
df = df[df["TotalEnrol"].notna() & (df["TotalEnrol"] > 0)].copy()
teacher_columns = [
    "GO_KTSC_M", "authorityM", "PTA_BOG_M", "OthersM",
    "GOK_TSC_F", "authorityF", "PTA_BOG_F", "OthersF"
]
df[teacher_columns] = df[teacher_columns].fillna(0)
df["Male_Teachers"] = df["GO_KTSC_M"] + df["authorityM"] + df["PTA_BOG_M"] + df["OthersM"]
df["Female_Teachers"] = df["GOK_TSC_F"] + df["authorityF"] + df["PTA_BOG_F"] + df["OthersF"]
df["Total_Teachers_Recalc"] = df["Male_Teachers"] + df["Female_Teachers"]
df["Teachers_Required"] = (df["TotalEnrol"] / 40).round().astype(int)
df["Teacher_Shortage"] = (df["Teachers_Required"] - df["Total_Teachers_Recalc"]).clip(lower=0)
df["Gender_Enrol_Gap"] = df["TotalGirls"] - df["TotalBoys"]
df["No_Classrooms"] = df["No_Classrm"].fillna(0).astype(int)
df["Toilet_Deficit"] = df["TotalToile"].apply(lambda x: 1 if pd.isna(x) or x <= 0 else 0)

# --- Streamlit Layout ---
st.set_page_config(page_title="EduMap Dashboard", layout="wide")
st.title("EduMap: Kenyan Primary School Education Dashboard")

# --- Sidebar: Filters and Info ---
st.sidebar.header("Filters")
province = st.sidebar.selectbox("Select Province", options=["All"] + sorted(df["Province"].unique()))

if province != "All":
    district_options = sorted(df[df["Province"] == province]["District"].unique())
else:
    district_options = sorted(df["District"].unique())

district = st.sidebar.selectbox("Select District", options=["All"] + district_options)

st.sidebar.markdown("---")
st.sidebar.header("🧭 Dashboard Key & Insight Guide")
st.sidebar.markdown("""
- **Total Enrollment**: Pupils currently in school.
- **Total Teachers**: Combined teaching staff.
- **Teacher Shortage**: Difference from 40:1 ratio.
- **Average Student-Teacher Ratio**: Shows teacher burden.
- **Top 10 Districts by Shortage**: Prioritize these areas.
- **Map Key**:
    - 🟥 High shortage (40+)
    - 🟧 Moderate shortage (20–39)
    - 🟨 Low shortage (1–19)
    - 🟩 No shortage
""")

# --- Filtering the Dataset ---
filtered_df = df.copy()
if province != "All":
    filtered_df = filtered_df[filtered_df["Province"] == province]
if district != "All":
    filtered_df = filtered_df[filtered_df["District"] == district]

# --- KPIs ---
kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Total Enrollment", int(filtered_df["TotalEnrol"].sum()))
kpi2.metric("Total Teachers", int(filtered_df["Total_Teachers_Recalc"].sum()))
kpi3.metric("Total Teacher Shortage", int(filtered_df["Teacher_Shortage"].sum()))

# --- Visuals ---
st.subheader("Student-Teacher Ratio by District")
st.markdown("This chart shows the average number of students assigned to one teacher in each district. A higher ratio suggests potential overload on teaching staff, which can negatively impact the quality of education delivered. Use this insight to identify regions where more teaching resources are required.")
ratio_chart = filtered_df.groupby("District")["PupilTeach"].mean().reset_index()
st.plotly_chart(px.bar(ratio_chart, x="District", y="PupilTeach", title="Average Student-Teacher Ratio"))

st.subheader("Teacher Shortage by District")
st.markdown("This chart highlights districts with the highest total teacher shortages, helping prioritize recruitment or resource allocation efforts. It can guide policymakers on where to focus teacher deployment or training programs to improve the pupil-teacher balance.")
shortage_chart = filtered_df.groupby("District")["Teacher_Shortage"].sum().reset_index()
st.plotly_chart(px.bar(shortage_chart.sort_values("Teacher_Shortage", ascending=False).head(10),
                      x="District", y="Teacher_Shortage", title="Top 10 Districts by Teacher Shortage"))

# --- Map Tabs for Clarity ---
tabs = st.tabs(["Teacher Shortage Map", "Infrastructure Map"])

# Map Data Prep
map_data = filtered_df[["Latitude", "Longitude", "Name_of_Sc", "Teacher_Shortage", "Total_Teachers_Recalc", "No_Classrooms", "TotalToile"]].dropna()

# Teacher Shortage Map
with tabs[0]:
    st.subheader("Teacher Shortage Map")
    st.markdown("Schools are mapped by their geographic location and color-coded based on the severity of teacher shortage.")
    map_data["Shortage_Level"] = pd.cut(
        map_data["Teacher_Shortage"],
        bins=[-1, 0, 19, 39, float("inf")],
        labels=["🟩 No Shortage", "🟨 Low", "🟧 Moderate", "🟥 High"]
    )
    fig_shortage = px.scatter_mapbox(
        map_data,
        lat="Latitude",
        lon="Longitude",
        hover_name="Name_of_Sc",
        hover_data={
            "Teacher_Shortage": True,
            "Total_Teachers_Recalc": True
        },
        color="Shortage_Level",
        zoom=5,
        height=600,
        mapbox_style="carto-positron"
    )
    st.plotly_chart(fig_shortage, use_container_width=True)

# Infrastructure Map
with tabs[1]:
    st.subheader("Infrastructure Needs Map")
    st.markdown("This map displays classroom and toilet availability to identify schools with critical infrastructure deficits.")
    infra_color = map_data["No_Classrooms"] + map_data["TotalToile"]
    fig_infra = px.scatter_mapbox(
        map_data,
        lat="Latitude",
        lon="Longitude",
        hover_name="Name_of_Sc",
        hover_data={
            "No_Classrooms": True,
            "TotalToile": True
        },
        color=infra_color,
        color_continuous_scale="YlOrRd",
        zoom=5,
        height=600,
        mapbox_style="carto-positron"
    )
    st.plotly_chart(fig_infra, use_container_width=True)
