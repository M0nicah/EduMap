import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

# Page config
st.set_page_config(page_title="EduMap Kenya - Key Insights", page_icon="📚", layout="wide")

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

# Sidebar navigation
st.sidebar.title("📚 EduMap Kenya - Key Insights")
page = st.sidebar.radio("Navigate to:", [
    "🎯 Top Priority Regions", 
    "📊 Biggest Resource Gaps", 
    "🏫 Most Crowded Schools", 
    "🏛️ Sponsor Influence", 
    "🚨 Most Urgent School"
])

# Filters (common to all pages)
st.sidebar.header("🔍 Filters")
provinces = st.sidebar.multiselect("Provinces", df['Province'].unique(), default=[])
status = st.sidebar.multiselect("Status", df['Status'].unique(), default=[])

# Apply filters
filtered_df = df.copy()
if provinces:
    filtered_df = filtered_df[filtered_df['Province'].isin(provinces)]
if status:
    filtered_df = filtered_df[filtered_df['Status'].isin(status)]

# Calculate priority score
filtered_df['Priority_Score'] = filtered_df['Extra_Teachers_Required'] + filtered_df['extra_toilets_required'] + filtered_df['extra_classes_required']

# PAGE 1: TOP PRIORITY REGIONS
if page == "🎯 Top Priority Regions":
    st.title("🎯 Top Priority Regions")
    st.markdown("*Regions that need immediate government attention and resource allocation*")
    
    # Regional priority analysis
    regional_analysis = filtered_df.groupby(['Province', 'District']).agg({
        'Priority_Score': 'sum',
        'Extra_Teachers_Required': 'sum',
        'extra_toilets_required': 'sum',
        'extra_classes_required': 'sum',
        'School_ID': 'count',
        'Total_Students': 'sum'
    }).reset_index()
    
    # Top priority provinces
    st.subheader("🗺️ Most Critical Provinces")
    province_priority = regional_analysis.groupby('Province')['Priority_Score'].sum().sort_values(ascending=False)
    
    col1, col2 = st.columns(2)
    with col1:
        st.bar_chart(province_priority.head(6), color='#ff6b6b')
    
    with col2:
        # Critical metrics
        top_province = province_priority.index[0]
        top_score = province_priority.iloc[0]
        
        st.error(f"🚨 **{top_province}** Province is the most critical with {top_score:.0f} total priority points")
        
        # Province breakdown
        top_province_data = regional_analysis[regional_analysis['Province'] == top_province].sort_values('Priority_Score', ascending=False).head(3)
        
        st.subheader(f"Top 3 Districts in {top_province}")
        for _, district in top_province_data.iterrows():
            st.metric(
                label=f"{district['District']}",
                value=f"{district['Priority_Score']:.0f} points",
                help=f"{district['School_ID']} schools, {district['Total_Students']:,} students"
            )
    
    # District-level heatmap
    st.subheader("🗺️ District Priority Heatmap")
    top_districts = regional_analysis.nlargest(15, 'Priority_Score')
    
    fig_treemap = px.treemap(
        top_districts,
        path=['Province', 'District'], 
        values='Priority_Score',
        color='Extra_Teachers_Required',
        color_continuous_scale='Reds',
        title='Priority Districts (Size = Total Priority, Color = Teacher Need)'
    )
    fig_treemap.update_layout(height=500)
    st.plotly_chart(fig_treemap, use_container_width=True)
    
    # Actionable insights
    st.info("""
    💡 **Policy Recommendations:**
    - Deploy emergency teacher teams to red districts first
    - Establish mobile resource units for remote high-priority areas
    - Create regional education hubs in top provinces
    - Prioritize infrastructure development in these regions
    """)

# PAGE 2: BIGGEST RESOURCE GAPS
elif page == "📊 Biggest Resource Gaps":
    st.title("📊 Biggest Resource Gaps by Category")
    st.markdown("*Understanding where Kenya needs to invest the most resources*")
    
    # Resource gap analysis
    total_teacher_gap = filtered_df['Extra_Teachers_Required'].sum()
    total_toilet_gap = filtered_df['extra_toilets_required'].sum()
    total_classroom_gap = filtered_df['extra_classes_required'].sum()
    
    # Overview metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👨‍🏫 Teachers Needed", f"{total_teacher_gap:,.0f}")
    with col2:
        st.metric("🚽 Toilets Needed", f"{total_toilet_gap:,.0f}")
    with col3:
        st.metric("🏫 Classrooms Needed", f"{total_classroom_gap:,.0f}")
    
    # Resource gap by category
    st.subheader("📊 Resource Gaps by Category")
    
    tab1, tab2, tab3 = st.tabs(["👨‍🏫 Teachers", "🚽 Toilets", "🏫 Classrooms"])
    
    with tab1:
        st.markdown("*Districts with highest teacher shortages*")
        teacher_gaps = filtered_df.groupby('District')['Extra_Teachers_Required'].sum().nlargest(10)
        st.bar_chart(teacher_gaps, color='#ff6b6b')
        
        # Insights
        worst_district = teacher_gaps.index[0]
        worst_gap = teacher_gaps.iloc[0]
        st.error(f"🚨 **{worst_district}** needs {worst_gap:.0f} teachers - highest shortage in Kenya")
    
    with tab2:
        st.markdown("*Districts with highest toilet shortages*")
        toilet_gaps = filtered_df.groupby('District')['extra_toilets_required'].sum().nlargest(10)
        st.bar_chart(toilet_gaps, color='#4ecdc4')
        
        # Gender impact
        schools_needing_toilets = len(filtered_df[filtered_df['extra_toilets_required'] > 0])
        st.warning(f"⚠️ {schools_needing_toilets} schools lack adequate toilets - impacting girls' education")
    
    with tab3:
        st.markdown("*Districts with highest classroom shortages*")
        classroom_gaps = filtered_df.groupby('District')['extra_classes_required'].sum().nlargest(10)
        st.bar_chart(classroom_gaps, color='#45b7d1')
        
        overcrowded_schools = len(filtered_df[filtered_df['extra_classes_required'] > 0])
        st.warning(f"📚 {overcrowded_schools} schools are overcrowded and need more classrooms")
    
    # Resource priority matrix
    st.subheader("🎯 Resource Investment Priority Matrix")
    
    # Create priority matrix data
    resource_matrix = filtered_df.groupby('Province').agg({
        'Extra_Teachers_Required': 'sum',
        'extra_toilets_required': 'sum',
        'extra_classes_required': 'sum'
    })
    
    st.bar_chart(resource_matrix, color=['#ff6b6b', '#4ecdc4', '#45b7d1'])
    
    # Cost estimation (rough estimates for policy planning)
    teacher_cost = total_teacher_gap * 30000 * 12  # 30k KES per month per teacher
    toilet_cost = total_toilet_gap * 150000  # 150k KES per toilet block
    classroom_cost = total_classroom_gap * 800000  # 800k KES per classroom
    
    st.info(f"""
    💰 **Estimated Investment Needed (Annual):**
    - Teachers: KES {teacher_cost:,.0f} ({teacher_cost/1000000:.1f}B)
    - Toilets: KES {toilet_cost:,.0f} ({toilet_cost/1000000:.1f}B) 
    - Classrooms: KES {classroom_cost:,.0f} ({classroom_cost/1000000:.1f}B)
    - **Total: KES {(teacher_cost + toilet_cost + classroom_cost):,.0f} ({(teacher_cost + toilet_cost + classroom_cost)/1000000:.1f}B)**
    """)

# PAGE 3: MOST CROWDED SCHOOLS
elif page == "🏫 Most Crowded Schools":
    st.title("🏫 Most Crowded Schools Analysis")
    st.markdown("*Schools operating beyond capacity with urgent infrastructure needs*")
    
    # Define overcrowding metrics
    filtered_df['Overcrowding_Score'] = (
        filtered_df['Students_per_Teacher'] / 40 +  # Normalized to target ratio
        filtered_df['extra_classes_required'] * 2 +  # Classroom shortage weight
        filtered_df['extra_toilets_required']  # Sanitation shortage
    )
    
    # Most crowded schools
    st.subheader("🚨 Most Severely Overcrowded Schools")
    most_crowded = filtered_df.nlargest(15, 'Overcrowding_Score')[
        ['Name_of_Sc', 'District', 'Province', 'Students_per_Teacher', 'Total_Students', 'Overcrowding_Score']
    ]
    
    st.dataframe(most_crowded, use_container_width=True)
    
    # Crowding analysis by region
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Crowding by Province")
        province_crowding = filtered_df.groupby('Province')['Overcrowding_Score'].mean().sort_values(ascending=False)
        st.bar_chart(province_crowding, color='#ff6b6b')
        
        worst_province = province_crowding.index[0]
        st.error(f"🚨 **{worst_province}** has the most overcrowded schools on average")
    
    with col2:
        st.subheader("👥 Student-Teacher Ratio Distribution")
        
        # Ratio categories
        excellent = len(filtered_df[filtered_df['Students_per_Teacher'] <= 30])
        good = len(filtered_df[(filtered_df['Students_per_Teacher'] > 30) & (filtered_df['Students_per_Teacher'] <= 40)])
        concerning = len(filtered_df[(filtered_df['Students_per_Teacher'] > 40) & (filtered_df['Students_per_Teacher'] <= 60)])
        critical = len(filtered_df[filtered_df['Students_per_Teacher'] > 60])
        
        ratio_data = pd.DataFrame({
            'Category': ['Excellent (≤30:1)', 'Good (31-40:1)', 'Concerning (41-60:1)', 'Critical (>60:1)'],
            'Schools': [excellent, good, concerning, critical]
        }).set_index('Category')
        
        st.bar_chart(ratio_data, color='#4ecdc4')
        
        if critical > 0:
            st.error(f"🚨 {critical} schools have critically high ratios (>60:1)")
        else:
            st.success("✅ No schools with critically high ratios")
    
    # School size vs crowding analysis
    st.subheader("📈 School Size vs Crowding Analysis")
    
    # Create size categories
    filtered_df['Size_Category'] = pd.cut(
        filtered_df['Total_Students'], 
        bins=[0, 200, 500, 800, float('inf')], 
        labels=['Small (<200)', 'Medium (200-499)', 'Large (500-799)', 'Very Large (800+)']
    )
    
    size_crowding = filtered_df.groupby('Size_Category')['Students_per_Teacher'].mean()
    st.bar_chart(size_crowding, color='#45b7d1')
    
    st.info("""
    🎯 **Crowding Insights:**
    - Large schools often have better teacher ratios due to economies of scale
    - Small schools may struggle with teacher allocation
    - Very large schools may face infrastructure challenges
    - Focus infrastructure investments on high-scoring overcrowded schools
    """)

# PAGE 4: SPONSOR INFLUENCE
elif page == "🏛️ Sponsor Influence":
    st.title("🏛️ Sponsor Influence Analysis")
    st.markdown("*Understanding how different sponsors impact school resource management*")
    
    # Sponsor effectiveness analysis
    sponsor_analysis = filtered_df.groupby('SchSponsor').agg({
        'Students_per_Teacher': 'mean',
        'Extra_Teachers_Required': 'mean',
        'extra_toilets_required': 'mean',
        'extra_classes_required': 'mean',
        'Total_Students': 'sum',
        'School_ID': 'count',
        'Priority_Score': 'mean'
    }).reset_index()
    
    # Filter to sponsors with at least 10 schools for statistical significance
    sponsor_analysis = sponsor_analysis[sponsor_analysis['School_ID'] >= 10].sort_values('School_ID', ascending=False)
    
    st.subheader("📊 Top School Sponsors by Scale")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Sponsor scale
        sponsor_scale = sponsor_analysis.set_index('SchSponsor')['School_ID'].head(8)
        st.bar_chart(sponsor_scale, color='#4ecdc4')
        st.caption("Number of schools managed by each sponsor")
    
    with col2:
        # Student reach
        sponsor_reach = sponsor_analysis.set_index('SchSponsor')['Total_Students'].head(8)
        st.bar_chart(sponsor_reach, color='#45b7d1')
        st.caption("Total students served by each sponsor")
    
    # Sponsor effectiveness comparison
    st.subheader("🎯 Sponsor Resource Management Effectiveness")
    
    # Create effectiveness score (lower is better)
    sponsor_analysis['Effectiveness_Score'] = (
        sponsor_analysis['Students_per_Teacher'] / 40 +  # Ratio to target
        sponsor_analysis['Priority_Score'] / 10  # Normalized priority score
    )
    
    best_sponsors = sponsor_analysis.nsmallest(6, 'Effectiveness_Score')
    worst_sponsors = sponsor_analysis.nlargest(6, 'Effectiveness_Score')
    
    tab1, tab2 = st.tabs(["🏆 Best Performing", "📉 Needs Support"])
    
    with tab1:
        st.markdown("*Sponsors with best resource management (low student-teacher ratios, fewer shortages)*")
        
        for _, sponsor in best_sponsors.iterrows():
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    label=sponsor['SchSponsor'][:25] + ('...' if len(sponsor['SchSponsor']) > 25 else ''),
                    value=f"{sponsor['Students_per_Teacher']:.1f}:1 ratio"
                )
            with col2:
                st.metric("Schools", f"{sponsor['School_ID']}")
            with col3:
                st.metric("Students", f"{sponsor['Total_Students']:,.0f}")
    
    with tab2:
        st.markdown("*Sponsors that may need additional support or oversight*")
        
        for _, sponsor in worst_sponsors.iterrows():
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    label=sponsor['SchSponsor'][:25] + ('...' if len(sponsor['SchSponsor']) > 25 else ''),
                    value=f"{sponsor['Students_per_Teacher']:.1f}:1 ratio"
                )
            with col2:
                st.metric("Avg Teacher Gap", f"{sponsor['Extra_Teachers_Required']:.1f}")
            with col3:
                st.metric("Priority Score", f"{sponsor['Priority_Score']:.1f}")
    
    # Public vs Private comparison
    st.subheader("🏛️ Public vs Private Performance")
    
    public_private = filtered_df.groupby('Status').agg({
        'Students_per_Teacher': 'mean',
        'Extra_Teachers_Required': 'mean',
        'Priority_Score': 'mean',
        'School_ID': 'count'
    })
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Public Schools Avg Ratio", f"{public_private.loc['PUBLIC', 'Students_per_Teacher']:.1f}:1")
        st.metric("Public Teacher Gap", f"{public_private.loc['PUBLIC', 'Extra_Teachers_Required']:.1f}")
        
    with col2:
        st.metric("Private Schools Avg Ratio", f"{public_private.loc['PRIVATE', 'Students_per_Teacher']:.1f}:1")
        st.metric("Private Teacher Gap", f"{public_private.loc['PRIVATE', 'Extra_Teachers_Required']:.1f}")
    
    st.info("""
    💡 **Sponsor Insights:**
    - Partner with high-performing sponsors to scale best practices
    - Provide targeted support to struggling sponsor types
    - Consider sponsor diversity in resource allocation
    - Monitor private vs public performance gaps
    """)

# PAGE 5: MOST URGENT SCHOOL
elif page == "🚨 Most Urgent School":
    st.title("🚨 School Needing Aid ASAP")
    st.markdown("*The single school that requires immediate emergency intervention*")
    
    # Find the most urgent school using comprehensive scoring
    filtered_df['Urgency_Score'] = (
        filtered_df['Students_per_Teacher'] / 10 +  # High weight on overcrowding
        filtered_df['Extra_Teachers_Required'] * 2 +  # Teacher shortage
        filtered_df['extra_toilets_required'] * 1.5 +  # Sanitation crisis
        filtered_df['extra_classes_required'] * 1.5  # Infrastructure shortage
    )
    
    most_urgent = filtered_df.loc[filtered_df['Urgency_Score'].idxmax()]
    
    # Emergency alert
    st.error("🚨 EMERGENCY INTERVENTION REQUIRED")
    
    # School details
    st.subheader(f"📍 {most_urgent['Name_of_Sc']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏫 School Information")
        st.metric("Location", f"{most_urgent['District']}, {most_urgent['Province']}")
        st.metric("School Type", most_urgent['Status'])
        st.metric("Sponsor", most_urgent['SchSponsor'])
        st.metric("Total Students", f"{most_urgent['Total_Students']:,}")
        st.metric("Total Teachers", f"{most_urgent['Total_Teachers']:,}")
    
    with col2:
        st.markdown("### 🚨 Critical Issues")
        st.error(f"Student-Teacher Ratio: {most_urgent['Students_per_Teacher']:.1f}:1")
        st.error(f"Teachers Needed: {most_urgent['Extra_Teachers_Required']:.0f}")
        st.error(f"Toilets Needed: {most_urgent['extra_toilets_required']:.0f}")
        st.error(f"Classrooms Needed: {most_urgent['extra_classes_required']:.0f}")
        st.error(f"Urgency Score: {most_urgent['Urgency_Score']:.1f}")
    
    # Emergency action plan
    st.subheader("⚡ Immediate Action Plan")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📅 Week 1")
        st.markdown("""
        - Deploy emergency teaching staff
        - Provide temporary classroom solutions
        - Assess infrastructure needs
        - Coordinate with local authorities
        """)
    
    with col2:
        st.markdown("### 📅 Month 1")
        st.markdown("""
        - Install temporary toilet facilities
        - Set up mobile classrooms
        - Recruit permanent teachers
        - Establish supply chain for materials
        """)
    
    with col3:
        st.markdown("### 📅 Month 3")
        st.markdown("""
        - Complete infrastructure upgrades
        - Finalize permanent staff placement
        - Implement monitoring system
        - Document lessons learned
        """)
    
    # Comparison with other urgent schools
    st.subheader("📊 Context: Top 5 Most Urgent Schools")
    
    top_urgent = filtered_df.nlargest(5, 'Urgency_Score')[
        ['Name_of_Sc', 'District', 'Province', 'Students_per_Teacher', 'Extra_Teachers_Required', 'Urgency_Score']
    ]
    
    st.dataframe(top_urgent, use_container_width=True)
    
    # Resource requirements
    immediate_teachers = top_urgent['Extra_Teachers_Required'].sum()
    immediate_cost = immediate_teachers * 30000 * 12  # Annual cost
    
    st.warning(f"""
    💰 **Emergency Resource Requirements:**
    - Teachers needed for top 5 schools: {immediate_teachers:.0f}
    - Estimated annual cost: KES {immediate_cost:,.0f}
    - Recommended: Establish emergency response fund for such cases
    """)
    
    # Contact information placeholder
    st.info("""
    📞 **Emergency Contacts:**
    - Ministry of Education Emergency Line: [Contact Details]
    - Regional Education Office: [Contact Details]  
    - Local Government: [Contact Details]
    - NGO Partners: [Contact Details]
    """)

# Footer
st.markdown("---")
st.markdown("*📊 EduMap Kenya - Providing actionable insights for education policymakers*")