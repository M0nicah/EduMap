import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
import warnings
import requests
import json
warnings.filterwarnings('ignore')


# Page configuration
st.set_page_config(
    page_title="EduMap Kenya Comprehensive Dashboard",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Performance optimization - session state management
if 'app_initialized' not in st.session_state:
    st.session_state.app_initialized = True
    # Clear cache on first load to prevent memory buildup
    st.cache_data.clear()

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.2rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .urgent-card {
        background-color: #fff5f5;
        border-left-color: #e53e3e;
    }
    .warning-card {
        background-color: #fffaf0;
        border-left-color: #dd6b20;
    }
    .good-card {
        background-color: #f0fff4;
        border-left-color: #38a169;
    }
    .header-style {
        color: #2d3748;
        border-bottom: 3px solid #4299e1;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    .kpi-container {
        display: flex;
        justify-content: space-around;
        margin: 20px 0;
    }
    .priority-tag {
        background: linear-gradient(90deg, #ff6b6b, #feca57);
        color: white;
        padding: 5px 10px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.8em;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load and process the EduMap dataset"""
    try:
        df = pd.read_csv('EduMap_FINAL.csv')
        # Clean column names
        df.columns = [col.strip() for col in df.columns]
        
        # Clean data types and handle missing values
        text_columns = ['Province', 'District', 'Division', 'Location', 'Costituenc', 
                       'Name_of_Sc', 'School_type', 'Status', 'SchSponsor']
        
        for col in text_columns:
            if col in df.columns:
                # Convert to string and handle NaN values
                df[col] = df[col].astype(str)
                df[col] = df[col].replace(['nan', '', ' ', '-'], 'Unknown')
                df[col] = df[col].fillna('Unknown')
                # Strip whitespace and standardize
                df[col] = df[col].str.strip()
        
        # Fix specific data quality issues
        if 'Status' in df.columns:
            # Clean up Status column aggressively
            df['Status'] = df['Status'].str.upper().str.strip()
            df['Status'] = df['Status'].replace({
                'O PRIMARY SCH."': 'PUBLIC',
                'PRIMARY SCHOOL': 'PUBLIC',
                'UNKNOWN': 'PUBLIC',  # Assume unknown schools are public
                'NAN': 'PUBLIC',
                '': 'PUBLIC',
                ' ': 'PUBLIC',
                '-': 'PUBLIC'
            })
            # Force everything to be either PUBLIC or PRIVATE (assume PUBLIC if unclear)
            df['Status'] = df['Status'].apply(lambda x: 'PRIVATE' if x == 'PRIVATE' else 'PUBLIC')
        
        if 'SchSponsor' in df.columns:
            # Standardize common sponsor names
            df['SchSponsor'] = df['SchSponsor'].str.upper()
            sponsor_mapping = {
                'CENTRAL  GOVERNMENT/DEB': 'CENTRAL GOVERNMENT/DEB',
                'CENTRAL GORVERNMENT/DEB': 'CENTRAL GOVERNMENT/DEB', 
                'CENTRAL GOVERNMET/DEB': 'CENTRAL GOVERNMENT/DEB',
                'LOCAL GORVERNMENT AUTHORITY': 'LOCAL GOVERNMENT AUTHORITY',
                'DEB': 'CENTRAL GOVERNMENT/DEB',
                'CENTRAL GOVERNMENT': 'CENTRAL GOVERNMENT/DEB'
            }
            df['SchSponsor'] = df['SchSponsor'].replace(sponsor_mapping)
            # Clean up very small categories
            sponsor_counts = df['SchSponsor'].value_counts()
            small_sponsors = sponsor_counts[sponsor_counts < 5].index
            df['SchSponsor'] = df['SchSponsor'].apply(lambda x: 'Other' if x in small_sponsors else x)
        
        # Ensure numeric columns are properly typed
        numeric_columns = ['Total_Students', 'Total_Teachers', 'Students_per_Teacher', 
                          'Teachers_Required', 'Extra_Teachers_Required', 'toilets',
                          'expected_toilets', 'extra_toilets_required', 'classes',
                          'expected_classes', 'extra_classes_required']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def calculate_resource_gap_score(df):
    """Calculate composite resource gap score - EDUCATION FOCUSED"""
    df = df.copy()
    
    # Normalize shortage metrics (0-1 scale)
    metrics = []
    weights = {}
    
    # EDUCATION FIRST - Teachers are the priority (60% weight)
    if 'Extra_Teachers_Required' in df.columns:
        df['teacher_shortage_norm'] = (df['Extra_Teachers_Required'] - df['Extra_Teachers_Required'].min()) / (df['Extra_Teachers_Required'].max() - df['Extra_Teachers_Required'].min())
        metrics.append('teacher_shortage_norm')
        weights['teacher_shortage_norm'] = 0.6  # Increased from 0.4 to 0.6
    
    # LEARNING ENVIRONMENT - Classrooms second priority (25% weight)  
    if 'extra_classes_required' in df.columns:
        df['class_shortage_norm'] = (df['extra_classes_required'] - df['extra_classes_required'].min()) / (df['extra_classes_required'].max() - df['extra_classes_required'].min())
        metrics.append('class_shortage_norm')
        weights['class_shortage_norm'] = 0.25  # Reduced from 0.3 to 0.25
    
    # BASIC INFRASTRUCTURE - Toilets supporting need (15% weight)
    if 'extra_toilets_required' in df.columns:
        df['toilet_shortage_norm'] = (df['extra_toilets_required'] - df['extra_toilets_required'].min()) / (df['extra_toilets_required'].max() - df['extra_toilets_required'].min())
        metrics.append('toilet_shortage_norm')
        weights['toilet_shortage_norm'] = 0.15  # Reduced from 0.3 to 0.15
    
    # Calculate weighted composite score
    if metrics:
        df['resource_gap_score'] = 0
        for metric in metrics:
            df['resource_gap_score'] += df[metric].fillna(0) * weights[metric]
    else:
        df['resource_gap_score'] = 0
    
    return df

@st.cache_data
def create_kenya_map_optimized(df, metric_column, title, max_markers=50):
    """Create an optimized map of Kenya - PERFORMANCE OPTIMIZED"""
    # Initialize map centered on Kenya
    kenya_center = [-0.0236, 37.9062]
    m = folium.Map(location=kenya_center, zoom_start=6, tiles='OpenStreetMap')
    
    # OPTIMIZATION: Limit data processing for maps
    if 'Location' in df.columns and metric_column in df.columns:
        # Aggregate and get top locations only (major performance boost)
        location_data = df.groupby('Location').agg({
            metric_column: 'sum',
            'Total_Students': 'sum' if 'Total_Students' in df.columns else 'count',
            'Name_of_Sc': 'count'
        }).reset_index()
        
        # OPTIMIZATION: Only show top N locations with highest need
        top_locations = location_data.nlargest(max_markers, metric_column)
        
        # Pre-calculate quantiles for color coding
        if len(top_locations) > 0:
            q80 = top_locations[metric_column].quantile(0.8)
            q60 = top_locations[metric_column].quantile(0.6)
            
            # Add markers only for top locations
            for idx, row in top_locations.iterrows():
                if pd.notna(row[metric_column]) and row[metric_column] > 0:
                    # Simplified color coding
                    if row[metric_column] > q80:
                        color, icon = 'red', 'exclamation-sign'
                    elif row[metric_column] > q60:
                        color, icon = 'orange', 'warning-sign'
                    else:
                        color, icon = 'green', 'ok-sign'
                    
                    # Use a more spread out positioning
                    lat_offset = np.random.uniform(-3, 3)
                    lon_offset = np.random.uniform(-4, 4)
                    
                    folium.Marker(
                        location=[kenya_center[0] + lat_offset, kenya_center[1] + lon_offset],
                        popup=f"""
                        <b>{row['Location']}</b><br>
                        {metric_column}: {row[metric_column]:.0f}<br>
                        Schools: {row['Name_of_Sc']}<br>
                        Students: {row['Total_Students'] if 'Total_Students' in row else 'N/A'}
                        """,
                        tooltip=f"{row['Location']}: {row[metric_column]:.0f}",
                        icon=folium.Icon(color=color, icon=icon)
                    ).add_to(m)
    
    return m

@st.cache_data
def create_choropleth_chart_optimized(df, group_col, metric_col, title, top_n=15):
    """Create optimized choropleth-style chart - PERFORMANCE OPTIMIZED"""
    if group_col not in df.columns or metric_col not in df.columns:
        return None
    
    # OPTIMIZATION: Efficient aggregation and limit results
    if metric_col == 'Name_of_Sc':  # Special case for school count
        geo_data = df.groupby(group_col).size().reset_index(name='count')
        geo_data = geo_data.nlargest(top_n, 'count')
        y_col = 'count'
    else:
        geo_data = df.groupby(group_col)[metric_col].sum().reset_index()
        geo_data = geo_data.nlargest(top_n, metric_col)
        y_col = metric_col
    
    fig = px.bar(
        geo_data,
        x=group_col,
        y=y_col,
        title=title,
        color=y_col,
        color_continuous_scale='Reds',
        text=y_col
    )
    
    fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
    fig.update_xaxes(tickangle=45)
    fig.update_layout(height=400)  # Reduced height for performance
    
    return fig

# Keep old function for backward compatibility but make it call optimized version
def create_choropleth_chart(df, group_col, metric_col, title):
    return create_choropleth_chart_optimized(df, group_col, metric_col, title)

def create_school_profile_breakdown(df):
    """Create school profile breakdown visualizations"""
    # Note: School type chart removed since dataset only contains Primary Schools
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'Status' in df.columns:
            # Filter out Unknown values for cleaner visualization
            status_df = df[df['Status'].isin(['PUBLIC', 'PRIVATE'])]
            status_counts = status_df['Status'].value_counts()
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Public vs Private Schools",
                color_discrete_map={'PUBLIC': '#2ecc71', 'PRIVATE': '#e74c3c'}
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("**Interpretation:** Green = Public schools (government responsibility), Red = Private schools (may need different aid approaches).")
    
    with col2:
        # Show total schools breakdown by province instead
        if 'Province' in df.columns:
            province_counts = df['Province'].value_counts().head(8)
            fig = px.bar(
                x=province_counts.values,
                y=province_counts.index,
                orientation='h',
                title="Schools by Province (Top 8)",
                color=province_counts.values,
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("**Interpretation:** Shows which provinces have the most schools - helpful for understanding regional education infrastructure.")
    
    # Sponsorship breakdown
    if 'SchSponsor' in df.columns:
        sponsor_counts = df['SchSponsor'].value_counts().head(10)
        fig = px.bar(
            x=sponsor_counts.values,
            y=sponsor_counts.index,
            orientation='h',
            title="Top 10 School Sponsors",
            color=sponsor_counts.values,
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**Interpretation:** Longer bars indicate sponsors managing more schools. These are key partners for aid distribution and policy implementation.")

@st.cache_data
def create_enrollment_staffing_analysis(df):
    """Create enrollment and staffing analysis"""
    col1, col2 = st.columns(2)
    
    with col1:
        if 'Province' in df.columns and 'Total_Students' in df.columns:
            province_students = df.groupby('Province')['Total_Students'].sum().sort_values(ascending=False)
            fig = px.bar(
                x=province_students.index,
                y=province_students.values,
                title="Total Students by Province",
                color=province_students.values,
                color_continuous_scale='Blues'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'Province' in df.columns and 'Total_Teachers' in df.columns:
            province_teachers = df.groupby('Province')['Total_Teachers'].sum().sort_values(ascending=False)
            fig = px.bar(
                x=province_teachers.index,
                y=province_teachers.values,
                title="Total Teachers by Province",
                color=province_teachers.values,
                color_continuous_scale='Greens'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
    
    # Student-teacher ratio analysis
    if 'Students_per_Teacher' in df.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.histogram(
                df,
                x='Students_per_Teacher',
                nbins=50,
                title="Distribution of Student-Teacher Ratios",
                labels={'Students_per_Teacher': 'Students per Teacher', 'count': 'Number of Schools'}
            )
            fig.add_vline(x=40, line_dash="dash", line_color="red", annotation_text="National Standard (40:1)")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("**How to read:** Red line = ideal 40:1 ratio. Schools to the right of the line are overcrowded and need more teachers.")
        
        with col2:
            # Top 10 schools with highest ratios
            highest_ratios = df.nlargest(10, 'Students_per_Teacher')[['Name_of_Sc', 'Students_per_Teacher', 'Province']]
            fig = px.bar(
                highest_ratios,
                x='Students_per_Teacher',
                y='Name_of_Sc',
                orientation='h',
                title="Top 10 Most Overcrowded Schools",
                color='Students_per_Teacher',
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("**Priority list:** These schools have the most severe overcrowding and should receive teachers immediately.")

@st.cache_data
def create_teacher_shortage_analysis(df):
    """Create teacher shortage analysis"""
    if 'Extra_Teachers_Required' not in df.columns:
        st.warning("Teacher shortage data not available in the dataset")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Schools below required teacher count
        schools_below_standard = len(df[df['Extra_Teachers_Required'] > 0])
        total_schools = len(df)
        percentage_below = (schools_below_standard / total_schools) * 100
        
        st.markdown(f"""
        <div class="metric-card urgent-card">
            <h3>📊 Schools Below Teacher Standard</h3>
            <h2>{schools_below_standard:,} ({percentage_below:.1f}%)</h2>
            <p>out of {total_schools:,} total schools</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Total extra teachers required by region
        if 'Province' in df.columns:
            teacher_shortage_by_province = df.groupby('Province')['Extra_Teachers_Required'].sum().sort_values(ascending=False)
            fig = px.bar(
                x=teacher_shortage_by_province.index,
                y=teacher_shortage_by_province.values,
                title="Teacher Shortage by Province",
                color=teacher_shortage_by_province.values,
                color_continuous_scale='Reds'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Distribution of teacher shortages
        shortage_schools = df[df['Extra_Teachers_Required'] > 0]
        if not shortage_schools.empty:
            fig = px.histogram(
                shortage_schools,
                x='Extra_Teachers_Required',
                nbins=30,
                title="Distribution of Teacher Shortages",
                labels={'Extra_Teachers_Required': 'Extra Teachers Needed', 'count': 'Number of Schools'}
            )
            st.plotly_chart(fig, use_container_width=True)

def create_sanitation_analysis(df):
    """Create sanitation adequacy analysis"""
    if 'extra_toilets_required' not in df.columns:
        st.warning("Sanitation data not available in the dataset")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Schools meeting toilet standard
        schools_adequate_toilets = len(df[df['extra_toilets_required'] <= 0])
        total_schools = len(df)
        percentage_adequate = (schools_adequate_toilets / total_schools) * 100
        
        st.markdown(f"""
        <div class="metric-card {'good-card' if percentage_adequate > 50 else 'urgent-card'}">
            <h3>🚻 Schools with Adequate Toilets</h3>
            <h2>{schools_adequate_toilets:,} ({percentage_adequate:.1f}%)</h2>
            <p>Meeting expected standards</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Schools with no toilets
        schools_no_toilets = len(df[df['toilets'] == 0]) if 'toilets' in df.columns else 0
        st.markdown(f"""
        <div class="metric-card urgent-card">
            <h3>⚠️ Schools with No Toilets</h3>
            <h2>{schools_no_toilets:,}</h2>
            <p>Critical intervention needed</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Total extra toilets required
        total_toilets_needed = df['extra_toilets_required'].sum()
        st.markdown(f"""
        <div class="metric-card warning-card">
            <h3>🏗️ Total Toilets Needed</h3>
            <h2>{total_toilets_needed:,.0f}</h2>
            <p>Across all schools</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Toilet shortage by district/province
    if 'District' in df.columns:
        toilet_shortage_by_district = df.groupby('District')['extra_toilets_required'].sum().sort_values(ascending=False).head(15)
        fig = px.bar(
            x=toilet_shortage_by_district.index,
            y=toilet_shortage_by_district.values,
            title="Top 15 Districts by Toilet Shortage",
            color=toilet_shortage_by_district.values,
            color_continuous_scale='Oranges'
        )
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

@st.cache_data
def create_classroom_capacity_analysis(df):
    """Create classroom capacity analysis"""
    if 'extra_classes_required' not in df.columns:
        st.warning("Classroom capacity data not available in the dataset")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Schools meeting classroom standard
        schools_adequate_classes = len(df[df['extra_classes_required'] <= 0])
        total_schools = len(df)
        percentage_adequate = (schools_adequate_classes / total_schools) * 100
        
        st.markdown(f"""
        <div class="metric-card {'good-card' if percentage_adequate > 50 else 'warning-card'}">
            <h3>🏫 Schools with Adequate Classrooms</h3>
            <h2>{schools_adequate_classes:,} ({percentage_adequate:.1f}%)</h2>
            <p>Meeting expected standards</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Total extra classes required by region
        if 'Province' in df.columns:
            class_shortage_by_province = df.groupby('Province')['extra_classes_required'].sum().sort_values(ascending=False)
            fig = px.bar(
                x=class_shortage_by_province.index,
                y=class_shortage_by_province.values,
                title="Classroom Shortage by Province",
                color=class_shortage_by_province.values,
                color_continuous_scale='Purples'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Schools with zero extra capacity vs large shortfalls
        zero_capacity = len(df[df['extra_classes_required'] == 0])
        large_shortfalls = len(df[df['extra_classes_required'] > df['extra_classes_required'].quantile(0.8)])
        
        fig = go.Figure(data=[
            go.Bar(name='Zero Extra Capacity', x=['Schools'], y=[zero_capacity], marker_color='orange'),
            go.Bar(name='Large Shortfalls (Top 20%)', x=['Schools'], y=[large_shortfalls], marker_color='red')
        ])
        
        fig.update_layout(
            barmode='group',
            title='Classroom Capacity Distribution',
            yaxis_title='Number of Schools'
        )
        st.plotly_chart(fig, use_container_width=True)

@st.cache_data
def create_sponsor_status_comparison(df):
    """Create sponsor and status impact comparison"""
    comparison_cols = ['Extra_Teachers_Required', 'extra_toilets_required', 'extra_classes_required']
    available_cols = [col for col in comparison_cols if col in df.columns]
    
    if not available_cols:
        st.warning("Resource shortage data not available for comparison")
        return
    
    # Compare by Status (Public vs Private) - Filter out Unknown
    if 'Status' in df.columns:
        st.subheader("📊 Public vs Private School Resource Gaps")
        
        # Filter out any Unknown or invalid status values
        status_df = df[df['Status'].isin(['PUBLIC', 'PRIVATE'])].copy()
        
        if status_df.empty:
            st.warning("No valid status data for comparison")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            status_comparison = status_df.groupby('Status')[available_cols].mean()
            fig = px.bar(
                status_comparison,
                title="Average Resource Shortfalls: Public vs Private",
                barmode='group',
                color_discrete_sequence=['#3498db', '#e74c3c', '#f39c12']
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Box plot for distribution comparison
            if 'Extra_Teachers_Required' in status_df.columns:
                fig = px.box(
                    status_df,
                    x='Status',
                    y='Extra_Teachers_Required',
                    title="Teacher Shortage Distribution by Status"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Compare by Sponsor
    if 'SchSponsor' in df.columns:
        st.subheader("🏛️ Resource Gaps by Sponsor Type")
        
        # Get top 8 sponsors by school count, excluding Unknown
        sponsor_counts = df[df['SchSponsor'] != 'Unknown']['SchSponsor'].value_counts()
        top_sponsors = sponsor_counts.head(8).index
        sponsor_df = df[df['SchSponsor'].isin(top_sponsors)]
        
        sponsor_comparison = sponsor_df.groupby('SchSponsor')[available_cols].mean()
        
        fig = px.bar(
            sponsor_comparison,
            title="Average Resource Shortfalls by Sponsor Type",
            barmode='group'
        )
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)
        
        # Identify systematically under-resourced sponsors
        st.subheader("⚠️ Sponsors with Highest Resource Gaps")
        if 'Extra_Teachers_Required' in sponsor_comparison.columns:
            worst_sponsors = sponsor_comparison.sort_values('Extra_Teachers_Required', ascending=False)
            st.dataframe(worst_sponsors.round(2), use_container_width=True)

@st.cache_data
def create_comparison_analysis(df, comparison_settings):
    """Create comparison analysis based on user selections"""
    if not comparison_settings or not comparison_settings.get('items'):
        return
    
    st.header(f"🔄 Comparison Analysis: {comparison_settings['title']}")
    st.markdown(f"""
    **Comparing:** {', '.join(comparison_settings['items'])}  
    **Metrics:** {', '.join(comparison_settings.get('metrics', []))}
    
    This side-by-side comparison helps identify which {comparison_settings['title'].lower()} need the most urgent attention 
    and reveals performance patterns across different categories.
    """)
    
    category_col = comparison_settings['category']
    selected_items = comparison_settings['items']
    selected_metrics = comparison_settings.get('metrics', [])
    
    if not selected_metrics:
        st.warning("Please select at least one metric to compare.")
        return
    
    # Filter data to only include selected items
    filtered_df = df[df[category_col].isin(selected_items)].copy()
    
    if filtered_df.empty:
        st.warning("No data found for the selected comparison items.")
        return
    
    # Create metric mapping
    metric_mapping = {
        "Teacher Shortage": "Extra_Teachers_Required",
        "Toilet Shortage": "extra_toilets_required",
        "Classroom Shortage": "extra_classes_required", 
        "Student-Teacher Ratio": "Students_per_Teacher",
        "Total Students": "Total_Students",
        "Total Teachers": "Total_Teachers"
    }
    
    # Prepare comparison data
    comparison_data = []
    for item in selected_items:
        item_data = filtered_df[filtered_df[category_col] == item]
        if not item_data.empty:
            row = {'Category': item, 'Schools': len(item_data)}
            
            for metric in selected_metrics:
                if metric in metric_mapping:
                    col_name = metric_mapping[metric]
                    if col_name in item_data.columns:
                        if metric in ["Teacher Shortage", "Toilet Shortage", "Classroom Shortage"]:
                            # Sum for shortage metrics
                            row[metric] = item_data[col_name].sum()
                        else:
                            # Average for ratio and per-school metrics
                            row[metric] = item_data[col_name].mean()
            
            comparison_data.append(row)
    
    if not comparison_data:
        st.warning("No comparison data could be calculated.")
        return
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Create visualizations
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Multi-metric bar chart
        metrics_to_plot = [m for m in selected_metrics if m in comparison_df.columns]
        
        if len(metrics_to_plot) > 1:
            fig = px.bar(
                comparison_df,
                x='Category',
                y=metrics_to_plot,
                title=f"Multi-Metric Comparison: {comparison_settings['title']}",
                barmode='group'
            )
            fig.update_xaxes(tickangle=45)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        elif len(metrics_to_plot) == 1:
            metric = metrics_to_plot[0]
            fig = px.bar(
                comparison_df,
                x='Category',
                y=metric,
                title=f"{metric} Comparison: {comparison_settings['title']}",
                color=metric,
                color_continuous_scale='Reds' if 'Shortage' in metric else 'Blues'
            )
            fig.update_xaxes(tickangle=45)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Summary table
        st.subheader("📊 Comparison Summary")
        
        # Round numeric columns for display
        display_df = comparison_df.copy()
        for col in display_df.columns:
            if col != 'Category' and display_df[col].dtype in ['float64', 'int64']:
                display_df[col] = display_df[col].round(2)
        
        st.dataframe(display_df, use_container_width=True)
        
        # Highlight top performers
        if len(metrics_to_plot) > 0:
            metric = metrics_to_plot[0]
            if metric in comparison_df.columns:
                if 'Shortage' in metric or metric == 'Student-Teacher Ratio':
                    # For shortage metrics, lowest is best
                    best_performer = comparison_df.loc[comparison_df[metric].idxmin(), 'Category']
                    worst_performer = comparison_df.loc[comparison_df[metric].idxmax(), 'Category']
                    st.success(f"🏆 **Best:** {best_performer}")
                    st.error(f"⚠️ **Needs Attention:** {worst_performer}")
                else:
                    # For positive metrics, highest is best
                    best_performer = comparison_df.loc[comparison_df[metric].idxmax(), 'Category']
                    worst_performer = comparison_df.loc[comparison_df[metric].idxmin(), 'Category']
                    st.success(f"🏆 **Highest:** {best_performer}")
                    st.info(f"📊 **Lowest:** {worst_performer}")
    
    # Detailed breakdown
    if len(selected_metrics) > 1:
        st.subheader("📈 Individual Metric Analysis")
        
        metric_tabs = st.tabs(selected_metrics[:4])  # Limit to 4 tabs for UI clarity
        
        for i, metric in enumerate(selected_metrics[:4]):
            with metric_tabs[i]:
                if metric in comparison_df.columns:
                    # Individual metric chart
                    fig = px.bar(
                        comparison_df,
                        x='Category',
                        y=metric,
                        title=f"{metric} by {comparison_settings['title']}",
                        color=metric,
                        color_continuous_scale='Reds' if 'Shortage' in metric else 'Blues'
                    )
                    fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Add interpretation
                    if 'Shortage' in metric:
                        st.markdown(f"**Interpretation:** Higher values indicate greater need for intervention in {metric.lower()}.")
                    elif metric == 'Student-Teacher Ratio':
                        st.markdown("**Interpretation:** Values above 40 indicate overcrowding (Kenya's standard is 40:1).")
                    else:
                        st.markdown(f"**Interpretation:** Shows the total/average {metric.lower()} across selected {comparison_settings['title'].lower()}.")

@st.cache_data
def create_intervention_priority_list(df):
    """Create high-priority intervention list"""
    st.header("🎯 Educational Intervention Priorities")
    st.markdown("""
    **What this shows:** Schools ranked by educational urgency - prioritizing teacher deployment first, then learning 
    environment improvements. This education-focused list helps direct limited aid to where children need learning support most.
    
    **Education-First Approach:**
    - **🔴 CRITICAL**: Severe teacher shortages preventing basic education
    - **🟡 HIGH**: Overcrowded classes limiting learning quality  
    - **🟠 MEDIUM**: Infrastructure gaps affecting attendance
    - Priority: Deploy teachers → Build classrooms → Improve facilities
    """)
    
    # Calculate composite scores
    df_scored = calculate_resource_gap_score(df)
    
    # Top 20 schools by combined shortfall
    intervention_cols = ['Name_of_Sc', 'Province', 'District', 'resource_gap_score']
    
    if 'Extra_Teachers_Required' in df.columns:
        intervention_cols.append('Extra_Teachers_Required')
    if 'extra_toilets_required' in df.columns:
        intervention_cols.append('extra_toilets_required')
    if 'extra_classes_required' in df.columns:
        intervention_cols.append('extra_classes_required')
    if 'Total_Students' in df.columns:
        intervention_cols.append('Total_Students')
    
    top_priority_schools = df_scored.nlargest(20, 'resource_gap_score')[intervention_cols]
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Top 20 Schools Requiring Immediate Intervention")
        
        # Add priority tags
        def add_priority_tag(row):
            if row['resource_gap_score'] > 0.8:
                return "🔴 CRITICAL"
            elif row['resource_gap_score'] > 0.6:
                return "🟡 HIGH"
            else:
                return "🟠 MEDIUM"
        
        if 'resource_gap_score' in top_priority_schools.columns:
            top_priority_schools['Priority'] = top_priority_schools.apply(add_priority_tag, axis=1)
        
        st.dataframe(
            top_priority_schools.round(3),
            use_container_width=True,
            height=600
        )
    
    with col2:
        st.subheader("Quick Filters")
        
        # Critical shortage filters
        if st.button("🚫 Schools with No Teachers"):
            if 'Total_Teachers' in df.columns:
                no_teachers = df[df['Total_Teachers'] == 0]
                st.write(f"Found {len(no_teachers)} schools with no teachers")
                if not no_teachers.empty:
                    st.dataframe(no_teachers[['Name_of_Sc', 'Province', 'District']].head(10))
        
        if st.button("🚻 Schools with No Toilets"):
            if 'toilets' in df.columns:
                no_toilets = df[df['toilets'] == 0]
                st.write(f"Found {len(no_toilets)} schools with no toilets")
                if not no_toilets.empty:
                    st.dataframe(no_toilets[['Name_of_Sc', 'Province', 'District']].head(10))
        
        if st.button("🏫 Schools with No Spare Classrooms"):
            if 'extra_classes_required' in df.columns:
                no_spare_classes = df[df['extra_classes_required'] > 0]
                st.write(f"Found {len(no_spare_classes)} schools needing more classrooms")
                if not no_spare_classes.empty:
                    st.dataframe(no_spare_classes[['Name_of_Sc', 'Province', 'extra_classes_required']].head(10))

def main():
    """Main dashboard function"""
    st.title("🏫 EduMap Kenya: Educational Resource Dashboard")
    st.markdown("*Identify schools and areas with critical need for aid*")
    
    # Load data
    with st.spinner("Loading EduMap data..."):
        df = load_data()
    
    if df.empty:
        st.error("❌ Unable to load data. Please ensure EduMap_FINAL.csv is in the current directory.")
        st.info("💡 Make sure the file is in the same folder as this dashboard.")
        return
    
    # Show data overview
    st.success(f"✅ Loaded {len(df):,} schools from {df['Province'].nunique()} provinces")
    
    # Show comparison analysis if enabled
    if hasattr(st.session_state, 'comparison_settings') and st.session_state.comparison_settings:
        create_comparison_analysis(df, st.session_state.comparison_settings)
        st.markdown("---")
    
    # Sidebar filters
    st.sidebar.header("🔍 Advanced Filters")
    
    # Geographic filters - Default to ALL, let user choose specific ones
    if 'Province' in df.columns:
        unique_provinces = [x for x in df['Province'].unique() if x != 'Unknown' and pd.notna(x)]
        if unique_provinces:
            selected_provinces = st.sidebar.multiselect(
                "🗺️ Filter by Province (Leave empty for ALL)",
                options=sorted(unique_provinces),
                default=[],  # Default to empty = show all
                help="Select specific provinces to focus on, or leave empty to show all provinces"
            )
            if selected_provinces:  # Only filter if user selected something
                df = df[df['Province'].isin(selected_provinces)]
    
    if 'District' in df.columns:
        unique_districts = [x for x in df['District'].unique() if x != 'Unknown' and pd.notna(x)]
        if unique_districts:
            selected_districts = st.sidebar.multiselect(
                "🏘️ Filter by District (Leave empty for ALL)",
                options=sorted(unique_districts),
                default=[],  # Default to empty = show all
                help="Select specific districts to focus on, or leave empty to show all districts"
            )
            if selected_districts:  # Only filter if user selected something
                df = df[df['District'].isin(selected_districts)]
    
    # School type filters - Default to ALL
    if 'Status' in df.columns:
        unique_status = [x for x in df['Status'].unique() if x != 'Unknown' and pd.notna(x)]
        if unique_status:
            status_filter = st.sidebar.selectbox(
                "🏫 School Status",
                options=["All"] + sorted(unique_status),
                index=0,
                help="Filter by public/private status"
            )
            if status_filter != "All":
                df = df[df['Status'] == status_filter]
    
    # Remove school type filter - only one type exists (Primary School)
    # if 'School_type' in df.columns:
    #     unique_school_types = [x for x in df['School_type'].unique() if x != 'Unknown' and pd.notna(x)]
    #     if len(unique_school_types) > 1:  # Only show filter if multiple types exist
    #         school_type_filter = st.sidebar.multiselect(
    #             "🎓 Filter by School Type (Leave empty for ALL)",
    #             options=sorted(unique_school_types),
    #             default=[],
    #             help="Select specific school types to focus on"
    #         )
    #         if school_type_filter:
    #             df = df[df['School_type'].isin(school_type_filter)]
    
    # Sponsor filters - Default to ALL
    if 'SchSponsor' in df.columns:
        unique_sponsors = [x for x in df['SchSponsor'].unique() if x != 'Unknown' and pd.notna(x)]
        if unique_sponsors and len(unique_sponsors) <= 20:  # Only show if reasonable number
            sponsor_filter = st.sidebar.multiselect(
                "🏛️ Filter by Sponsor (Leave empty for ALL)",
                options=sorted(unique_sponsors),
                default=[],  # Default to empty = show all
                help="Select specific sponsors to analyze"
            )
            if sponsor_filter:  # Only filter if user selected something
                df = df[df['SchSponsor'].isin(sponsor_filter)]
    
    # Resource gap filters - Optional
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📊 Advanced Filters**")
    
    if 'Students_per_Teacher' in df.columns:
        valid_ratios = df['Students_per_Teacher'].dropna()
        if not valid_ratios.empty and valid_ratios.max() > 0:
            min_ratio = max(1, int(valid_ratios.min()))
            max_ratio_val = min(200, int(valid_ratios.max()))
            
            use_ratio_filter = st.sidebar.checkbox("Filter by Student-Teacher Ratio")
            if use_ratio_filter:
                max_ratio = st.sidebar.slider(
                    "Maximum Student-Teacher Ratio",
                    min_value=min_ratio,
                    max_value=max_ratio_val,
                    value=50,  # More reasonable default
                    step=5
                )
                df = df[df['Students_per_Teacher'] <= max_ratio]
    
    # Comparison Analysis Section
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🔄 Comparison Analysis**")
    st.sidebar.markdown("*Compare categories side-by-side*")
    
    # Store comparison settings in session state
    if 'comparison_active' not in st.session_state:
        st.session_state.comparison_active = False
    
    enable_comparison = st.sidebar.checkbox("Enable Comparison Mode", value=st.session_state.comparison_active)
    st.session_state.comparison_active = enable_comparison
    
    comparison_settings = {}
    if enable_comparison:
        # Choose what to compare
        comparison_category = st.sidebar.selectbox(
            "📊 Compare by:",
            options=["Provinces", "Districts", "Sponsors", "Public vs Private"],
            help="Select the category you want to compare"
        )
        
        # Choose specific items to compare
        if comparison_category == "Provinces" and 'Province' in df.columns:
            available_provinces = [x for x in df['Province'].unique() if x != 'Unknown' and pd.notna(x)]
            selected_items = st.sidebar.multiselect(
                "Select Provinces to Compare:",
                options=sorted(available_provinces),
                default=sorted(available_provinces)[:3] if len(available_provinces) >= 3 else available_provinces,
                help="Choose 2-5 provinces for meaningful comparison"
            )
            comparison_settings = {
                'category': 'Province',
                'items': selected_items,
                'title': 'Provinces'
            }
        
        elif comparison_category == "Districts" and 'District' in df.columns:
            available_districts = [x for x in df['District'].unique() if x != 'Unknown' and pd.notna(x)]
            # Show top 15 districts by school count for easier selection
            district_counts = df['District'].value_counts().head(15)
            top_districts = district_counts.index.tolist()
            
            selected_items = st.sidebar.multiselect(
                "Select Districts to Compare:",
                options=top_districts,
                default=top_districts[:4] if len(top_districts) >= 4 else top_districts,
                help="Choose 2-5 districts for meaningful comparison (showing top 15 by school count)"
            )
            comparison_settings = {
                'category': 'District', 
                'items': selected_items,
                'title': 'Districts'
            }
        
        elif comparison_category == "Sponsors" and 'SchSponsor' in df.columns:
            sponsor_counts = df[df['SchSponsor'] != 'Unknown']['SchSponsor'].value_counts()
            top_sponsors = sponsor_counts.head(8).index.tolist()
            
            selected_items = st.sidebar.multiselect(
                "Select Sponsors to Compare:",
                options=top_sponsors,
                default=top_sponsors[:4] if len(top_sponsors) >= 4 else top_sponsors,
                help="Choose 2-5 sponsors for meaningful comparison"
            )
            comparison_settings = {
                'category': 'SchSponsor',
                'items': selected_items, 
                'title': 'Sponsors'
            }
        
        elif comparison_category == "Public vs Private" and 'Status' in df.columns:
            comparison_settings = {
                'category': 'Status',
                'items': ['PUBLIC', 'PRIVATE'],
                'title': 'Public vs Private'
            }
        
        # Choose metrics to compare
        available_metrics = []
        if 'Extra_Teachers_Required' in df.columns:
            available_metrics.append("Teacher Shortage")
        if 'extra_toilets_required' in df.columns:
            available_metrics.append("Toilet Shortage") 
        if 'extra_classes_required' in df.columns:
            available_metrics.append("Classroom Shortage")
        if 'Students_per_Teacher' in df.columns:
            available_metrics.append("Student-Teacher Ratio")
        if 'Total_Students' in df.columns:
            available_metrics.append("Total Students")
        if 'Total_Teachers' in df.columns:
            available_metrics.append("Total Teachers")
        
        selected_metrics = st.sidebar.multiselect(
            "📈 Metrics to Compare:",
            options=available_metrics,
            default=["Teacher Shortage", "Student-Teacher Ratio"] if len(available_metrics) >= 2 else available_metrics,
            help="Choose which metrics to compare across categories"
        )
        
        comparison_settings['metrics'] = selected_metrics
        
        st.sidebar.success(f"🔄 Comparing {len(comparison_settings.get('items', []))} {comparison_settings.get('title', '')} across {len(selected_metrics)} metrics")
    
    # Store comparison settings for use in main dashboard
    if enable_comparison and comparison_settings:
        st.session_state.comparison_settings = comparison_settings
    else:
        st.session_state.comparison_settings = None
    
    # Show filtered results count
    st.sidebar.metric("Filtered Schools", len(df))
    
    # Main content tabs - EDUCATION FOCUSED ORDER
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Overview", "👨‍🏫 Teacher Crisis", "👥 Student-Teacher Ratios", 
        "🏛️ Classroom Capacity", "🏫 School Profiles", "🗺️ Geographic", 
        "🏗️ Infrastructure", "🎯 Priority Interventions"
    ])
    
    with tab1:
        st.header("📊 Kenya's Education Crisis - Executive Overview")
        st.markdown("""
        **The Challenge:** Kenya faces a severe teacher shortage crisis that prevents millions of children from receiving 
        quality education. This dashboard prioritizes teacher deployment as the #1 intervention need.
        
        **Focus:** Educational access first, infrastructure second. Children need teachers to learn.
        """)
        
        # Key metrics overview
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            total_schools = len(df)
            st.markdown(f"""
            <div class="metric-card">
                <h3>🏫 Total Schools</h3>
                <h2>{total_schools:,}</h2>
                <p>In filtered selection</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if 'Total_Students' in df.columns:
                total_students = df['Total_Students'].sum()
                st.markdown(f"""
                <div class="metric-card">
                    <h3>👥 Total Students</h3>
                    <h2>{total_students:,}</h2>
                    <p>Across all schools</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col3:
            if 'Total_Teachers' in df.columns:
                total_teachers = df['Total_Teachers'].sum()
                avg_ratio = total_students / total_teachers if total_teachers > 0 else 0
                ratio_color = "urgent-card" if avg_ratio > 40 else "good-card"
                st.markdown(f"""
                <div class="metric-card {ratio_color}">
                    <h3>👨‍🏫 Avg Ratio</h3>
                    <h2>{avg_ratio:.1f}:1</h2>
                    <p>Student:Teacher</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col4:
            if 'Extra_Teachers_Required' in df.columns:
                teacher_shortage = df['Extra_Teachers_Required'].sum()
                st.markdown(f"""
                <div class="metric-card urgent-card">
                    <h3>⚠️ Teacher Gap</h3>
                    <h2>{teacher_shortage:,.0f}</h2>
                    <p>Additional needed</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col5:
            if 'extra_toilets_required' in df.columns:
                toilet_shortage = df['extra_toilets_required'].sum()
                st.markdown(f"""
                <div class="metric-card warning-card">
                    <h3>🚻 Toilet Gap</h3>
                    <h2>{toilet_shortage:,.0f}</h2>
                    <p>Additional needed</p>
                </div>
                """, unsafe_allow_html=True)
        
        # Resource gap composite scoring
        st.header("🎯 Educational Priority Analysis")
        st.markdown("""
        **What this shows:** A composite scoring system focused on educational needs that combines teacher shortages, 
        classroom capacity, and basic infrastructure into a single "educational priority score" from 0-1. Higher scores 
        indicate schools where children face the greatest barriers to learning.
        
        **How it's calculated:** Teacher shortage (60%) + Classroom shortage (25%) + Basic infrastructure (15%)
        
        **Why teachers matter most:** Without adequate teachers, children cannot receive quality education regardless of facilities.
        """)
        df_scored = calculate_resource_gap_score(df)
        
        if 'resource_gap_score' in df_scored.columns:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Top 15 areas by resource gap
                if 'Costituenc' in df.columns:
                    constituency_gaps = df_scored.groupby('Costituenc')['resource_gap_score'].mean().sort_values(ascending=False).head(15)
                    fig = px.bar(
                        x=constituency_gaps.values,
                        y=constituency_gaps.index,
                        orientation='h',
                        title="Top 15 Constituencies by Resource Gap Score",
                        color=constituency_gaps.values,
                        color_continuous_scale='Reds'
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Gap score distribution
                fig = px.histogram(
                    df_scored,
                    x='resource_gap_score',
                    nbins=30,
                    title="Distribution of Resource Gap Scores"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Only load content if user is viewing this tab
        with st.spinner("Loading teacher analysis..."):
            st.header("👨‍🏫 Teacher Crisis - The Core Educational Challenge")
            st.markdown("""
            **What this shows:** The most critical barrier to education in Kenya - massive teacher shortages that prevent 
        children from receiving quality instruction. This is the PRIMARY focus of educational aid efforts.
        
        **Why teachers matter most:**
        - Without teachers, children cannot learn regardless of facilities
        - Kenya's target: 40 students per teacher maximum
        - Current reality: Many schools have 70+ students per teacher
        """)
            create_teacher_shortage_analysis(df)
    
    with tab3:
        with st.spinner("Loading enrollment analysis..."):
            st.header("👥 Student-Teacher Ratios - Measuring Educational Access")
        st.markdown("""
        **What this shows:** Student-teacher ratios across Kenya compared to the national standard of 40:1. 
        This directly measures whether children can receive adequate individual attention from teachers.
        
        **Critical for learning outcomes:** 
        - Ratios >40:1 mean overcrowded classes and poor learning conditions
        - "Most overcrowded schools" need immediate teacher deployment
        - Provincial analysis shows where to focus teacher recruitment
        """)
        create_enrollment_staffing_analysis(df)
    
    with tab4:
        with st.spinner("Loading classroom analysis..."):
            st.header("🏛️ Classroom Capacity - Learning Environment")
        st.markdown("""
        **What this shows:** Classroom adequacy for proper learning. Even with teachers, children need adequate 
        physical space to learn effectively and separate grade levels appropriately.
        
        **Educational impact:**
        - Insufficient classrooms force multiple grades into one room
        - Overcrowded classes reduce learning effectiveness
        - Strategic classroom construction supports better teacher deployment
        """)
        create_classroom_capacity_analysis(df)
    
    with tab5:
        with st.spinner("Loading school profiles..."):
            st.header("🏫 School Profiles - System Overview")
        st.markdown("""
        **What this shows:** Breakdown of Kenya's schools by ownership (Public/Private) and sponsorship organizations. 
        This reveals which sectors need educational support and potential partners for teacher deployment.
        
        **Why it matters for education:** 
        - Public schools serve most children but may need more teacher support
        - Different sponsors may have different capacities to hire teachers
        - Helps target teacher training and deployment programs
        """)
        create_school_profile_breakdown(df)
    
    with tab6:
        with st.spinner("Loading map visualization..."):
            st.header("🗺️ Geographic Distribution - Where Are the Educational Gaps?")
            st.markdown("""
            **What this shows:** Geographic distribution of educational resources across Kenya. Shows where children 
            have limited access to schools and teachers by region.
            
            **Why geography matters:** Remote areas often have the worst teacher shortages and need targeted programs.
            """)
            
            # School count by Province, District, Division
            create_choropleth_chart(df, 'Province', 'Name_of_Sc', 'School Count by Province')
            
            col1, col2 = st.columns(2)
        
            with col1:
                if 'District' in df.columns:
                    fig = create_choropleth_chart(df, 'District', 'Name_of_Sc', 'Top 15 Districts by School Count')
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if 'Costituenc' in df.columns:
                    fig = create_choropleth_chart(df, 'Costituenc', 'Name_of_Sc', 'Top 15 Constituencies by School Count')
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
        
            # Interactive map
            st.subheader("🗺️ Interactive Kenya Map - Teacher Shortage Hotspots")
            st.markdown("""
            **What this shows:** Interactive map showing where teacher shortages are most severe. 
            Red markers = urgent need for teachers, Orange = moderate need, Green = meeting standards.
            """)
            
            if 'Extra_Teachers_Required' in df.columns:
                # OPTIMIZATION: Use optimized map with limited markers
                with st.spinner("Loading teacher shortage map (top 50 locations)..."):
                    kenya_map = create_kenya_map_optimized(df, 'Extra_Teachers_Required', 'Teacher Shortage by Location', max_markers=50)
                    st_folium(kenya_map, width=1000, height=400)
                st.info("💡 Map shows top 50 locations with highest teacher shortages for optimal performance")
    
    with tab7:
        with st.spinner("Loading infrastructure analysis..."):
            st.header("🏗️ Basic Infrastructure - Supporting Educational Access")
            st.markdown("""
            **What this shows:** Basic infrastructure needs (toilets, water, etc.) that support education. While secondary 
            to teacher needs, adequate facilities help maintain attendance and create conducive learning environments.
            
            **Supporting role for education:**
            - Poor sanitation affects attendance, especially for girls
            - Basic facilities support teacher retention in rural areas  
            - Infrastructure investments should follow teacher deployment priorities
        """)
            create_sanitation_analysis(df)
    
    with tab8:
        with st.spinner("Loading priority interventions..."):
            create_intervention_priority_list(df)
    
    # Additional analysis sections
    st.markdown("---")
    
    # Sponsor and Status Impact
    st.header("🏛️ Sponsor & Status Impact Analysis")
    st.markdown("""
    **What this shows:** Comparison of resource adequacy between different school sponsors (government, religious 
    organizations, private entities) and public vs private schools. This reveals which sponsors may be systematically 
    under-resourcing their schools.
    
    **Policy implications:**
    - Sponsors with consistently high shortages may need additional support or oversight
    - Public vs private gaps indicate equity issues requiring policy intervention
    - This data helps identify potential partners for aid distribution and accountability measures
    """)
    create_sponsor_status_comparison(df)
    
    # Data export section
    st.markdown("---")
    st.header("💾 Data Export & Reports")
    st.markdown("""
    **What this provides:** Download filtered and analyzed data for further use in reports, presentations, 
    or external analysis tools. Each export contains different levels of detail for different stakeholder needs.
    """)
    
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Download Priority Schools"):
            df_scored = calculate_resource_gap_score(df)
            priority_schools = df_scored.nlargest(50, 'resource_gap_score') if 'resource_gap_score' in df_scored.columns else df.head(50)
            csv = priority_schools.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="priority_schools_comprehensive.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("🗺️ Download Geographic Summary"):
            if 'Province' in df.columns:
                geo_summary = df.groupby(['Province', 'District']).agg({
                    'Name_of_Sc': 'count',
                    'Total_Students': 'sum' if 'Total_Students' in df.columns else 'count',
                    'Total_Teachers': 'sum' if 'Total_Teachers' in df.columns else 'count',
                    'Extra_Teachers_Required': 'sum' if 'Extra_Teachers_Required' in df.columns else 'count'
                }).reset_index()
                csv = geo_summary.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="geographic_summary.csv",
                    mime="text/csv"
                )
    
    with col3:
        if st.button("🏫 Download Sponsor Analysis"):
            if 'SchSponsor' in df.columns:
                sponsor_analysis = df.groupby(['SchSponsor', 'Status']).agg({
                    'Name_of_Sc': 'count',
                    'Extra_Teachers_Required': 'mean' if 'Extra_Teachers_Required' in df.columns else 'count',
                    'extra_toilets_required': 'mean' if 'extra_toilets_required' in df.columns else 'count',
                    'Students_per_Teacher': 'mean' if 'Students_per_Teacher' in df.columns else 'count'
                }).reset_index()
                csv = sponsor_analysis.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="sponsor_analysis.csv",
                    mime="text/csv"
                )
    
    with col4:
        if st.button("📈 Download Full Analysis"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="comprehensive_edumap_analysis.csv",
                mime="text/csv"
            )
    
    # Footer
    st.markdown("---")
    st.markdown("**EduMap Kenya Dashboard** | Supporting equitable education through data insights 🇰🇪")

if __name__ == "__main__":
    main()