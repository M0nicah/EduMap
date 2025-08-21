import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Page config
st.set_page_config(page_title="EduMap Kenya", page_icon="📚", layout="wide")

st.title("📚 EduMap - Kenyan Schools Analysis")

@st.cache_data
def load_data():
    df = pd.read_csv('EduMap_FINAL.csv')
    # Clean data
    df = df.dropna(subset=['Province', 'SchSponsor', 'District'])
    df = df[df['Province'].str.strip() != '']
    df = df[df['SchSponsor'].str.strip() != '']
    df = df[df['District'].str.strip() != '']
    df = df[df['Province'] != 'Central']
    return df

df = load_data()

# Sidebar filters
st.sidebar.header("🔍 Filters")
provinces = st.sidebar.multiselect("Provinces", df['Province'].unique(), default=[])
status = st.sidebar.multiselect("Status", df['Status'].unique(), default=[])

# Apply filters
filtered_df = df.copy()
if provinces:
    filtered_df = filtered_df[filtered_df['Province'].isin(provinces)]
if status:
    filtered_df = filtered_df[filtered_df['Status'].isin(status)]

# SECTION 1: Overview (Always visible)
st.header("📊 Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🏫 Schools", f"{filtered_df['School_ID'].nunique():,}")
with col2:
    st.metric("👥 Students", f"{filtered_df['Total_Students'].sum():,}")
with col3:
    st.metric("👨‍🏫 Teachers", f"{filtered_df['Total_Teachers'].sum():,}")
with col4:
    ratio = filtered_df['Students_per_Teacher'].mean()
    st.metric("📈 Avg Ratio", f"{ratio:.1f}")

# Critical alert
critical = len(filtered_df[filtered_df['Extra_Teachers_Required'] > 15])
if critical > 0:
    st.error(f"🚨 {critical} schools need 15+ teachers!")

st.divider()

# SECTION 2: School Analysis (Expandable)
with st.expander("🏫 School Analysis - Click to expand"):
    filtered_df['Priority'] = filtered_df['Extra_Teachers_Required'] + filtered_df['extra_toilets_required']
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top Priority Schools")
        priority = filtered_df.nlargest(8, 'Priority')[['Name_of_Sc', 'District', 'Priority']]
        st.dataframe(priority, use_container_width=True)
    
    with col2:
        st.subheader("Private vs Public")
        status_count = filtered_df['Status'].value_counts()
        fig, ax = plt.subplots()
        ax.pie(status_count.values, labels=status_count.index, autopct='%1.1f%%', colors=['#ff6b6b', '#4ecdc4'])
        st.pyplot(fig)

# SECTION 3: Resource Shortages (Expandable)
with st.expander("🚨 Resource Shortages - Click to expand"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Teacher Shortage")
        teacher_shortage = filtered_df.nlargest(8, 'Extra_Teachers_Required')[['Name_of_Sc', 'Extra_Teachers_Required']]
        st.dataframe(teacher_shortage, use_container_width=True)
    
    with col2:
        st.subheader("Toilet Shortage")
        toilet_shortage = filtered_df.nlargest(8, 'extra_toilets_required')[['Name_of_Sc', 'extra_toilets_required']]
        st.dataframe(toilet_shortage, use_container_width=True)
    
    with col3:
        st.subheader("Classroom Shortage")
        class_shortage = filtered_df.nlargest(8, 'extra_classes_required')[['Name_of_Sc', 'extra_classes_required']]
        st.dataframe(class_shortage, use_container_width=True)

# SECTION 4: Geographic Analysis (Expandable)
with st.expander("📍 Geographic Analysis - Click to expand"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Schools by Province")
        province_count = filtered_df['Province'].value_counts()
        st.bar_chart(province_count, color='#ff6b6b')
    
    with col2:
        st.subheader("Top Districts by Students")
        district_students = filtered_df.groupby('District')['Total_Students'].sum().nlargest(10)
        st.bar_chart(district_students, color='#4ecdc4')
    
    st.subheader("Priority by Province")
    province_priority = filtered_df.groupby('Province')['Priority'].mean()
    st.bar_chart(province_priority, color='#ffa500')

# SECTION 5: Resource Planning (Expandable)
with st.expander("📈 Resource Planning - Click to expand"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("School Size Distribution")
        fig, ax = plt.subplots()
        ax.hist(filtered_df['Total_Students'], bins=15, color='#4ecdc4', alpha=0.7)
        ax.set_xlabel('Students')
        ax.set_ylabel('Schools')
        st.pyplot(fig)
    
    with col2:
        st.subheader("Resource Needs by District")
        resource_by_district = filtered_df.groupby('District').agg({
            'Extra_Teachers_Required': 'sum',
            'extra_toilets_required': 'sum'
        }).nlargest(8, 'Extra_Teachers_Required')
        st.bar_chart(resource_by_district, color=['#ff6b6b', '#4ecdc4'])

# SECTION 6: District Comparison (Expandable)
with st.expander("⚖️ District Comparison - Click to expand"):
    col1, col2 = st.columns(2)
    with col1:
        d1 = st.selectbox("District 1", [''] + list(filtered_df['District'].unique()))
    with col2:
        d2 = st.selectbox("District 2", [''] + list(filtered_df['District'].unique()))
    
    if d1 and d2 and d1 != d2:
        col1, col2 = st.columns(2)
        with col1:
            d1_data = filtered_df[filtered_df['District'] == d1]
            st.metric(f"{d1} Schools", len(d1_data))
            st.metric(f"{d1} Students", d1_data['Total_Students'].sum())
            st.metric(f"{d1} Teacher Shortage", int(d1_data['Extra_Teachers_Required'].sum()))
        with col2:
            d2_data = filtered_df[filtered_df['District'] == d2]
            st.metric(f"{d2} Schools", len(d2_data))
            st.metric(f"{d2} Students", d2_data['Total_Students'].sum())
            st.metric(f"{d2} Teacher Shortage", int(d2_data['Extra_Teachers_Required'].sum()))

# SECTION 7: Sponsor Analysis (Expandable)
with st.expander("🏛️ Sponsor Analysis - Click to expand"):
    st.subheader("Schools by Sponsor Type")
    sponsor_count = filtered_df['SchSponsor'].value_counts().head(6)
    st.bar_chart(sponsor_count, color='#45b7d1')
    
    st.subheader("Public vs Private by Top Sponsors")
    sponsor_status = filtered_df.groupby(['SchSponsor', 'Status']).size().unstack(fill_value=0)
    top_sponsors = sponsor_status.nlargest(5, 'PUBLIC')
    st.bar_chart(top_sponsors, color=['#ff6b6b', '#4ecdc4'])