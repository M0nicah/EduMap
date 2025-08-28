import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px

# Page config
st.set_page_config(page_title="EduMap Kenya", page_icon="📚", layout="wide")

# Title and description
st.title("📚 EduMap - Kenyan Schools Analysis")
st.markdown("*A comprehensive dashboard showing which schools in Kenya need more aid*")

# Table of Contents / Navigation
st.markdown("### 📍 Quick Navigation")
st.markdown("""
- [📊 National Overview](#national-overview)
- [🚨 Critical Schools](#critical-schools) 
- [🎯 Priority Analysis](#priority-analysis)
- [🗺️ Geographic Insights](#geographic-insights)
- [📈 Detailed Analysis](#detailed-analysis)
""")
st.divider()

@st.cache_data
def load_data():
    df = pd.read_csv('edumap_final.csv')
    return df

df = load_data()

# Clean data - remove NaN and empty values
df = df.dropna(subset=['Province', 'SchSponsor', 'District'])
df = df[df['Province'].str.strip() != '']
df = df[df['SchSponsor'].str.strip() != '']
df = df[df['District'].str.strip() != '']
df = df[df['Province'] != 'Central']
df = df[df['SchSponsor'] != 'PRIVATE INDIVIDUAL']

# SIDEBAR FILTERS
st.sidebar.header("🔍 Filters")
provinces = st.sidebar.multiselect("Select Provinces", df['Province'].unique(), default=[])
status = st.sidebar.multiselect("School Status", df['Status'].unique(), default=[])
sponsors = st.sidebar.multiselect("School Sponsor Type", df['SchSponsor'].unique(), default=[])
districts = st.sidebar.multiselect("Select Districts", df['District'].unique(), default=[])
critical_only = st.sidebar.checkbox("Critical Schools Only (15+ teachers needed)")
min_students = st.sidebar.slider("Minimum Students", 0, int(df['Total_Students'].max()), 0)

# Clear filters button
if st.sidebar.button("🗑️ Clear All Filters"):
    provinces = []
    status = []
    sponsors = []
    districts = []
    critical_only = False
    min_students = 0
    st.experimental_rerun()

# Show active filters
active_filters = []
if provinces: active_filters.append(f"Provinces: {len(provinces)}")
if status: active_filters.append(f"Status: {len(status)}")
if sponsors: active_filters.append(f"Sponsors: {len(sponsors)}")
if districts: active_filters.append(f"Districts: {len(districts)}")
if critical_only: active_filters.append("Critical Schools Only")
if min_students > 0: active_filters.append(f"Min Students: {min_students}")

if active_filters:
    st.sidebar.info(f"Active filters: {', '.join(active_filters)}")

# Quick buttons
if st.sidebar.button("Public Schools Only"):
    status = ['PUBLIC']

# District comparison in sidebar
st.sidebar.header("⚖️ Compare Districts")
d1 = st.sidebar.selectbox("District 1", [''] + list(df['District'].unique()))
d2 = st.sidebar.selectbox("District 2", [''] + list(df['District'].unique()))

# Apply filters
filtered_df = df.copy()

if provinces:
    filtered_df = filtered_df[filtered_df['Province'].isin(provinces)]
if status:
    filtered_df = filtered_df[filtered_df['Status'].isin(status)]
if min_students > 0:
    filtered_df = filtered_df[filtered_df['Total_Students'] >= min_students]

# Priority score
filtered_df['Priority'] = filtered_df['Extra_Teachers_Required'] + filtered_df['extra_toilets_required'] + filtered_df['extra_classes_required']

# SECTION 1: NATIONAL OVERVIEW
st.markdown('<a name="national-overview"></a>', unsafe_allow_html=True)
st.header("📊 National Overview")
st.markdown("*High-level statistics showing the current state of Kenya's education system*")

col1, col2, col3, col4 = st.columns(4)

total_schools = filtered_df['School_ID'].nunique()
total_students = filtered_df['Total_Students'].sum()
total_teachers = filtered_df['Total_Teachers'].sum()
national_avg_ratio = filtered_df['Students_per_Teacher'].mean()

norm_ratio = 40
teachers_needed = total_students / norm_ratio
extra_teachers = teachers_needed - total_teachers

with col1:
    st.metric("🏫 Total Schools", f"{total_schools:,}", help="Total number of schools in dataset")
with col2:
    st.metric("👥 Total Students", f"{total_students:,}", help="Total student enrollment")
with col3:
    st.metric("👨‍🏫 Total Teachers", f"{total_teachers:,}", help="Total number of teachers")
with col4:
    st.metric("📈 Avg Student-Teacher Ratio", f"{national_avg_ratio:.1f}", help="Average students per teacher (target: 40:1)")

# Key insights box
col1, col2 = st.columns(2)
with col1:
    st.metric("⚠️ Extra Teachers Needed", f"{extra_teachers:,.0f}", help="Additional teachers needed to reach 40:1 ratio")
with col2:
    if national_avg_ratio > 40:
        st.warning(f"📈 Current ratio ({national_avg_ratio:.1f}:1) exceeds Kenya's target of 40:1")
    else:
        st.success(f"✅ Current ratio ({national_avg_ratio:.1f}:1) meets Kenya's target")

st.divider()



# SECTION 2: GEOGRAPHIC INSIGHTS
st.markdown('<a name="geographic-insights"></a>', unsafe_allow_html=True)
st.header("🗺️ Geographic Distribution & Insights")
st.markdown("*Understanding regional patterns and geographic distribution of schools*")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Public vs Private Distribution")
    private_vs_public = filtered_df.groupby('Status')['School_ID'].count().reset_index()
    private_vs_public.columns = ['Status','Number_of_Schools']
    
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(private_vs_public['Number_of_Schools'],
           labels=private_vs_public['Status'],
           autopct='%1.1f%%',
           colors=['#ff6b6b', '#4ecdc4'])
    ax.set_title('School Type Distribution')
    st.pyplot(fig)
    
    # Insight box
    public_pct = (private_vs_public[private_vs_public['Status'] == 'PUBLIC']['Number_of_Schools'].iloc[0] / 
                  private_vs_public['Number_of_Schools'].sum() * 100)
    st.info(f"📊 {public_pct:.1f}% of schools are public, serving the majority of students")

with col2:
    st.subheader("Top Areas by Student Population")
    top_locations = filtered_df.groupby('Location')['Total_Students'].sum().nlargest(10).reset_index()
    top_locations.columns = ['Location','Student_Population']
    st.bar_chart(top_locations.set_index('Location'), color="#4ecdc4")
    st.caption("💡 These locations have the highest total student enrollment")

st.divider()


# District comparison results
if d1 and d2 and d1 != d2:
    st.subheader(f"⚖️ District Comparison: {d1} vs {d2}")
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
    
    st.caption("💡 Compare two districts to see which needs more resources")


# RESOURCE GAP ANALYSIS
st.header("📈 Resource Gap Analysis")

# Teacher shortage heatmap by district
st.subheader("🗺️ Teacher Shortage Heatmap by District")
st.markdown("*Visual representation of which districts need immediate teacher deployment*")

# Prepare data for heatmap
district_shortage = filtered_df.groupby('District').agg({
    'Extra_Teachers_Required': 'sum',
    'Total_Students': 'sum',
    'Total_Teachers': 'sum',
    'School_ID': 'count'
}).reset_index()

# Calculate shortage intensity (teachers needed per 100 students)
district_shortage['Shortage_Intensity'] = (district_shortage['Extra_Teachers_Required'] / district_shortage['Total_Students']) * 100
district_shortage['Avg_Student_Teacher_Ratio'] = district_shortage['Total_Students'] / district_shortage['Total_Teachers']

# Create heatmap using plotly
fig_heatmap = px.treemap(district_shortage.nlargest(15, 'Extra_Teachers_Required'),
                        path=['District'], 
                        values='Extra_Teachers_Required',
                        color='Shortage_Intensity',
                        color_continuous_scale='Reds',
                        title='Teacher Shortage by District (Size = Total Need, Color = Intensity)')

fig_heatmap.update_layout(height=500, font_size=12)
st.plotly_chart(fig_heatmap, use_container_width=True)

# Heatmap insights
col1, col2 = st.columns(2)
with col1:
    most_critical = district_shortage.loc[district_shortage['Extra_Teachers_Required'].idxmax()]
    st.error(f"🚨 **{most_critical['District']}** needs the most teachers: {most_critical['Extra_Teachers_Required']:.0f} teachers")

with col2:
    highest_intensity = district_shortage.loc[district_shortage['Shortage_Intensity'].idxmax()]
    st.warning(f"⚠️ **{highest_intensity['District']}** has highest shortage intensity: {highest_intensity['Shortage_Intensity']:.1f} teachers needed per 100 students")

st.info("""
📊 **Heatmap Guide:**
- **Size of blocks:** Total number of teachers needed in each district
- **Color intensity:** Teachers needed per 100 students (shortage severity)
- **Red districts:** Require immediate intervention
- **Use for:** Prioritizing teacher deployment and resource allocation
""")

# Resource needs by district
st.subheader("Resource Needs by Top Districts")
resource_by_district = filtered_df.groupby('District').agg({
    'Extra_Teachers_Required': 'sum',
    'extra_toilets_required': 'sum', 
    'extra_classes_required': 'sum'
}).nlargest(10, 'Extra_Teachers_Required')

resource_by_district.columns = ['Teachers', 'Toilets', 'Classrooms']
st.bar_chart(resource_by_district, color=['#ff6b6b', '#4ecdc4', '#45b7d1'])

st.info("""
📊 **Resource Needs by District Guide:**
- **Purpose:** Shows the top 10 districts with highest combined resource shortages
- **Chart Components:**
  - **Red bars:** Teacher shortages - immediate staffing needs
  - **Teal bars:** Toilet shortages - sanitation infrastructure needs  
  - **Blue bars:** Classroom shortages - physical infrastructure needs
- **Key Insights:**
  - Districts with tall red bars need urgent teacher deployment
  - Districts with tall teal bars need sanitation infrastructure projects
  - Districts with tall blue bars need classroom construction programs
- **Action Planning:** Use this to allocate budgets and resources by district priority
- **Strategic Value:** Enables district-level resource planning and intervention targeting
""")

# District insights
col1, col2 = st.columns(2)
with col1:
    top_teacher_district = resource_by_district.index[0]
    top_teacher_need = resource_by_district['Teachers'].iloc[0]
    st.caption(f"🚨 **{top_teacher_district}** district has the highest teacher shortage ({top_teacher_need:.0f} teachers needed)")

with col2:
    top_toilet_district = resource_by_district['Toilets'].idxmax()
    top_toilet_need = resource_by_district.loc[top_toilet_district, 'Toilets']
    st.caption(f"🚽 **{top_toilet_district}** district has the highest toilet shortage ({top_toilet_need:.0f} toilets needed)")

st.divider()

# SECTION 5: DETAILED ANALYSIS
st.markdown('<a name="detailed-analysis"></a>', unsafe_allow_html=True)
st.header("📈 Detailed Resource Analysis")
st.markdown("*Deep dive into specific resource shortages and school characteristics*")

# Resource shortage analysis
st.subheader("🔍 Resource Shortage Breakdown")
tab1, tab2, tab3 = st.tabs(["👨‍🏫 Teachers", "🚽 Toilets", "🏫 Classrooms"])

with tab1:
    st.markdown("*Schools with the highest teacher shortages*")
    teacher_shortage = filtered_df.nlargest(10, 'Extra_Teachers_Required')[['Name_of_Sc', 'District', 'Extra_Teachers_Required']]
    st.dataframe(teacher_shortage, use_container_width=True)
    
    avg_shortage = filtered_df['Extra_Teachers_Required'].mean()
    st.info(f"📊 Average teacher shortage per school: {avg_shortage:.1f} teachers")

with tab2:
    st.markdown("*Schools with the highest toilet shortages*")
    toilet_shortage = filtered_df.nlargest(10, 'extra_toilets_required')[['Name_of_Sc', 'District', 'extra_toilets_required']]
    st.dataframe(toilet_shortage, use_container_width=True)
    
    schools_needing_toilets = len(filtered_df[filtered_df['extra_toilets_required'] > 0])
    st.warning(f"🚽 {schools_needing_toilets} schools need additional toilets")

with tab3:
    st.markdown("*Schools with the highest classroom shortages*")
    classroom_shortage = filtered_df.nlargest(10, 'extra_classes_required')[['Name_of_Sc', 'District', 'extra_classes_required']]
    st.dataframe(classroom_shortage, use_container_width=True)
    
    schools_needing_classes = len(filtered_df[filtered_df['extra_classes_required'] > 0])
    st.warning(f"🏫 {schools_needing_classes} schools need additional classrooms")

# SECTION 3: PRIORITY ANALYSIS  
st.markdown('<a name="priority-analysis"></a>', unsafe_allow_html=True)
st.header("🎯 Priority Analysis")
st.markdown("*Understanding which province need the most help*")

# Province priority overview
st.subheader("🗺️ Priority Levels by Province")
province_avg = filtered_df.groupby('Province')['Priority'].mean().sort_values(ascending=False)
st.bar_chart(province_avg, color='#ff6b6b')
st.caption("💡 Higher bars indicate provinces with greater resource needs")

# Key insight box
if len(province_avg) > 0:
    highest_province = province_avg.index[0]
    highest_score = province_avg.iloc[0]
    st.info(f"📍 **{highest_province}** province has the highest average priority score ({highest_score:.1f})")

st.divider()
 
# School size analysis
st.subheader("📊 School Size Distribution Analysis")
col1, col2 = st.columns(2)

with col1:
    fig, ax = plt.subplots()
    ax.hist(filtered_df['Total_Students'], bins=15, color='#4ecdc4', alpha=0.7)
    ax.set_xlabel('Number of Students')
    ax.set_ylabel('Number of Schools')
    ax.set_title('Distribution of School Sizes')
    # Add average line
    avg_size = filtered_df['Total_Students'].mean()
    ax.axvline(avg_size, color='red', linestyle='--', label=f'Average: {avg_size:.0f}')
    ax.legend()
    st.pyplot(fig)

with col2:
    # School size insights
    small_schools = len(filtered_df[filtered_df['Total_Students'] < 300])
    large_schools = len(filtered_df[filtered_df['Total_Students'] > 800])
    
    st.metric("Small Schools (<300 students)", small_schools)
    st.metric("Large Schools (>800 students)", large_schools)
    st.metric("Average School Size", f"{avg_size:.0f} students")
    
    if large_schools > 0:
        st.info(f"📈 {large_schools} schools are significantly larger than average and may be overcrowded")

st.divider()



# GEOGRAPHIC DISTRIBUTION
st.header("🗺️ Geographic Distribution")

col1, col2 = st.columns(2)

with col1:
    # Provincial distribution
    province_summary = filtered_df.groupby(['Province', 'Status']).size().unstack(fill_value=0)
    st.subheader("Schools by Province")
    st.bar_chart(province_summary, color=['#ff6b6b', '#4ecdc4'])

with col2:
    # Overcrowded locations analysis
    st.subheader("Location Analysis")
    st.markdown("*Understanding resource distribution across different locations*")
    
    location_data = filtered_df.groupby('Location').agg({
        'Total_Students': 'sum',
        'Total_Teachers': 'sum', 
        'School_ID': 'count'
    }).reset_index()
    
    # Top locations by student population
    top_student_locations = location_data.nlargest(10, 'Total_Students')
    st.bar_chart(top_student_locations.set_index('Location')['Total_Students'], color='#ff9999')
    
   
    
    # Additional insights
    max_students_location = location_data.loc[location_data['Total_Students'].idxmax()]
    min_ratio_location = location_data.loc[(location_data['Total_Students']/location_data['Total_Teachers']).idxmax()]
    
    st.caption(f"💡 **{max_students_location['Location']}** has the highest student population ({max_students_location['Total_Students']:,} students)")
    if min_ratio_location['Location'] != max_students_location['Location']:
        ratio = min_ratio_location['Total_Students']/min_ratio_location['Total_Teachers']
        st.caption(f"⚠️ **{min_ratio_location['Location']}** has the highest student-teacher ratio ({ratio:.1f}:1)")

st.divider()

# SCHOOL SPONSOR ANALYSIS
st.header("🏛️ School Sponsor Analysis")

col1, col2 = st.columns(2)

with col1:
    # Sponsor distribution donut chart
    st.subheader("Top 5 Sponsors")
    sponsor_dist = filtered_df.groupby('SchSponsor').size().sort_values(ascending=False).head(5)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    wedges, texts, autotexts = ax.pie(sponsor_dist.values, labels=sponsor_dist.index, 
                                     autopct='%1.1f%%', colors=['#ff6b6b', '#4ecdc4', '#45b7d1', '#ffa500', '#98d8c8'])
    circle = plt.Circle((0,0), 0.4, fc='white')
    ax.add_patch(circle)
    st.pyplot(fig)

with col2:
    # Public vs Private by sponsor
    st.subheader("Public vs Private by Sponsor")
    sponsor_status = filtered_df.groupby(['SchSponsor', 'Status']).size().unstack(fill_value=0)
    top_sponsors = sponsor_status.nlargest(4, 'PUBLIC')
    st.bar_chart(top_sponsors, color=['#ff6b6b', '#4ecdc4'])

st.divider()

# Teacher shortage distribution by sponsor
st.subheader("Teacher Shortage by Sponsor Type")
st.markdown("*Comparing how teacher shortages vary across different school sponsor types*")

# Teacher shortage by sponsor type - simplified view
sponsor_shortage_summary = []
for sponsor in filtered_df['SchSponsor'].value_counts().head(5).index:
    data = filtered_df[filtered_df['SchSponsor'] == sponsor]['Extra_Teachers_Required']
    sponsor_shortage_summary.append({
        'Sponsor': sponsor[:20] + '...' if len(sponsor) > 20 else sponsor,
        'Avg_Shortage': data.mean(),
        'Total_Shortage': data.sum()
    })

sponsor_df = pd.DataFrame(sponsor_shortage_summary)
st.bar_chart(sponsor_df.set_index('Sponsor')['Total_Shortage'], color='#4ecdc4')

st.divider()


# Additional insights based on the data
col1, col2 = st.columns(2)

with col1:
    # Calculate median shortages for each sponsor
    sponsor_medians = {}
    for i, sponsor in enumerate(filtered_df['SchSponsor'].value_counts().head(5).index):
        data = filtered_df[filtered_df['SchSponsor'] == sponsor]['Extra_Teachers_Required']
        sponsor_medians[sponsor] = data.median()
    
    highest_median_sponsor = max(sponsor_medians, key=sponsor_medians.get)
    st.caption(f"📈 **{highest_median_sponsor}** sponsored schools have the highest median teacher shortage ({sponsor_medians[highest_median_sponsor]:.1f} teachers)")

with col2:
    # Find sponsor with most outliers (high variance)
    sponsor_variance = {}
    for sponsor in filtered_df['SchSponsor'].value_counts().head(5).index:
        data = filtered_df[filtered_df['SchSponsor'] == sponsor]['Extra_Teachers_Required']
        sponsor_variance[sponsor] = data.var()
    
    highest_variance_sponsor = max(sponsor_variance, key=sponsor_variance.get)
    st.caption(f"📊 **{highest_variance_sponsor}** sponsored schools show the most variation in teacher needs (indicating mixed resource levels)")


# SECTION 5: CRITICAL SCHOOLS
st.markdown('<a name="critical-schools"></a>', unsafe_allow_html=True)
st.header("🚨 Critical Schools Needing Immediate Attention")
st.markdown("*Schools with the highest resource shortages that require urgent intervention*")

# Critical alert
critical = len(filtered_df[filtered_df['Extra_Teachers_Required'] > 15])
if critical > 0:
    st.error(f"🚨 **URGENT:** {critical} schools need 15+ teachers immediately!")
else:
    st.success("✅ No schools in critical teacher shortage state")


# Most critical schools
st.subheader("🎯 Top 10 Most Critical Schools")
priority = filtered_df.nlargest(10, 'Priority')[['Name_of_Sc', 'District', 'Priority', 'Extra_Teachers_Required', 'extra_toilets_required', 'extra_classes_required']]
st.dataframe(priority, use_container_width=True)
st.caption("💡 These schools have the highest combined resource needs and should be prioritized for aid")

st.divider()

# FOOTER
st.markdown("---")
st.markdown("*📊 Dashboard created to help identify schools most in need of educational resources in Kenya*")