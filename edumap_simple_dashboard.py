import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Basic page setup
st.set_page_config(
    page_title="Kenya Schools Dashboard - Simple Version", 
    page_icon="🏫",
    layout="wide"
)

st.title("🏫 Kenya Schools Dashboard - Simple Analysis")
st.write("This dashboard shows which schools in Kenya need the most help with teachers, classrooms, and toilets.")

# Load the data
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('EduMap_FINAL.csv')
        # Clean up missing data
        df = df.fillna(0)
        return df
    except:
        st.error("Could not load the data file. Make sure EduMap_FINAL.csv is in the same folder.")
        return None

# Get the data
data = load_data()
if data is None:
    st.stop()

st.success(f"✅ Loaded data for {len(data):,} schools")

# Sidebar filters - keep it simple
st.sidebar.header("📊 Filter Schools")
st.sidebar.write("Choose which schools to look at:")

# Simple province filter
if 'Province' in data.columns:
    provinces = ['All'] + list(data['Province'].unique())
    selected_province = st.sidebar.selectbox("Pick a Province:", provinces)
    
    if selected_province != 'All':
        data = data[data['Province'] == selected_province]
        st.info(f"Showing schools in {selected_province} province only")

st.sidebar.write(f"Total schools shown: {len(data):,}")

# Main tabs - simple names
tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "👨‍🏫 Teachers", "🏛️ Classrooms", "🚻 Toilets"])

with tab1:
    st.header("📈 Basic Numbers")
    st.write("Here are the main numbers about Kenya's schools:")
    
    # Simple metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_schools = len(data)
        st.metric("Total Schools", f"{total_schools:,}")
    
    with col2:
        if 'Total_Students' in data.columns:
            total_students = int(data['Total_Students'].sum())
            st.metric("Total Students", f"{total_students:,}")
    
    with col3:
        if 'Total_Teachers' in data.columns:
            total_teachers = int(data['Total_Teachers'].sum())
            st.metric("Total Teachers", f"{total_teachers:,}")
    
    with col4:
        if 'Total_Students' in data.columns and 'Total_Teachers' in data.columns:
            avg_ratio = data['Total_Students'].sum() / data['Total_Teachers'].sum()
            st.metric("Students per Teacher", f"{avg_ratio:.1f}")
    
    st.write("---")
    
    # Simple pie chart of school types
    st.subheader("Types of Schools")
    if 'Status' in data.columns:
        # Count each type
        public_count = len(data[data['Status'] == 'PUBLIC'])
        private_count = len(data[data['Status'] == 'PRIVATE'])
        other_count = len(data) - public_count - private_count
        
        # Make a simple pie chart
        labels = ['Public', 'Private', 'Other']
        sizes = [public_count, private_count, other_count]
        colors = ['lightblue', 'lightcoral', 'lightgray']
        
        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%')
        ax.set_title('Types of Schools in Kenya')
        st.pyplot(fig)
        
        st.write(f"Most schools ({public_count:,}) are public schools run by the government.")

with tab2:
    st.header("👨‍🏫 Teacher Problems")
    st.write("This shows which schools don't have enough teachers.")
    
    if 'Extra_Teachers_Required' in data.columns and 'Students_per_Teacher' in data.columns:
        # Count schools with teacher problems
        schools_need_teachers = 0
        total_extra_teachers_needed = 0
        
        # Go through each school and count problems
        for i in range(len(data)):
            extra_needed = data.iloc[i]['Extra_Teachers_Required']
            if extra_needed > 0:
                schools_need_teachers = schools_need_teachers + 1
                total_extra_teachers_needed = total_extra_teachers_needed + extra_needed
        
        # Show the results
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("### 🔍 The Problem")
            st.write(f"**Schools that need more teachers:** {schools_need_teachers:,}")
            st.write(f"**Total schools:** {len(data):,}")
            percentage = (schools_need_teachers / len(data)) * 100
            st.write(f"**Percentage with problems:** {percentage:.1f}%")
            st.write(f"**Extra teachers needed:** {int(total_extra_teachers_needed):,}")
            
            if percentage > 50:
                st.error("⚠️ More than half the schools need more teachers!")
            else:
                st.warning("Some schools need more teachers")
        
        with col2:
            st.write("### 📊 Simple Chart")
            good_schools = len(data) - schools_need_teachers
            
            # Make a bar chart
            fig, ax = plt.subplots()
            bars = ax.bar(['Schools with Enough Teachers', 'Schools Need More Teachers'], 
                         [good_schools, schools_need_teachers], 
                         color=['green', 'red'])
            ax.set_title('Teacher Problems in Schools')
            ax.set_ylabel('Number of Schools')
            
            # Add numbers on top of bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 50,
                       f'{int(height):,}', ha='center', va='bottom')
            
            st.pyplot(fig)
        
        st.write("---")
        
        # Show worst schools - simple way
        st.subheader("🚨 Schools That Need Help Most")
        st.write("These are the 10 schools that need the most extra teachers:")
        
        # Find schools with most teacher shortage
        worst_schools = []
        for i in range(len(data)):
            school_name = data.iloc[i]['Name_of_Sc']
            province = data.iloc[i]['Province'] if 'Province' in data.columns else 'Unknown'
            extra_needed = data.iloc[i]['Extra_Teachers_Required']
            ratio = data.iloc[i]['Students_per_Teacher']
            
            if extra_needed > 0:
                worst_schools.append([school_name, province, int(extra_needed), round(ratio, 1)])
        
        # Sort by extra teachers needed (highest first)
        worst_schools.sort(key=lambda x: x[2], reverse=True)
        
        # Show top 10
        st.write("**Top 10 schools that need the most teachers:**")
        for i in range(min(10, len(worst_schools))):
            school = worst_schools[i]
            st.write(f"{i+1}. **{school[0]}** (in {school[1]}) - needs {school[2]} more teachers, has {school[3]} students per teacher")
        
        st.info("💡 The government should send teachers to these schools first!")

with tab3:
    st.header("🏛️ Classroom Problems") 
    st.write("This shows which schools don't have enough classrooms for their students.")
    
    if 'extra_classes_required' in data.columns:
        # Count classroom problems the simple way
        schools_need_classrooms = 0
        total_classrooms_needed = 0
        
        for i in range(len(data)):
            extra_classes = data.iloc[i]['extra_classes_required']
            if extra_classes > 0:
                schools_need_classrooms = schools_need_classrooms + 1
                total_classrooms_needed = total_classrooms_needed + extra_classes
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("### 📚 Classroom Shortage")
            st.write(f"**Schools needing more classrooms:** {schools_need_classrooms:,}")
            st.write(f"**Total extra classrooms needed:** {int(total_classrooms_needed):,}")
            percentage = (schools_need_classrooms / len(data)) * 100
            st.write(f"**Percentage of schools:** {percentage:.1f}%")
            
            if percentage > 30:
                st.warning("⚠️ Many schools are overcrowded!")
            else:
                st.success("✅ Most schools have enough classrooms")
        
        with col2:
            # Simple bar chart
            good_classrooms = len(data) - schools_need_classrooms
            
            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.bar(['Enough Classrooms', 'Need More Classrooms'], 
                         [good_classrooms, schools_need_classrooms],
                         color=['blue', 'orange'])
            ax.set_title('Classroom Problems in Schools')
            ax.set_ylabel('Number of Schools')
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 30,
                       f'{int(height):,}', ha='center', va='bottom')
            
            st.pyplot(fig)
        
        # Show which provinces have most classroom problems
        if 'Province' in data.columns:
            st.write("### 🗺️ Which Provinces Need More Classrooms?")
            
            province_problems = {}
            
            # Count problems by province
            for i in range(len(data)):
                province = data.iloc[i]['Province']
                extra_classes = data.iloc[i]['extra_classes_required']
                
                if province not in province_problems:
                    province_problems[province] = 0
                
                if extra_classes > 0:
                    province_problems[province] = province_problems[province] + extra_classes
            
            # Sort provinces by most classrooms needed
            sorted_provinces = []
            for province, classrooms_needed in province_problems.items():
                sorted_provinces.append([province, int(classrooms_needed)])
            
            sorted_provinces.sort(key=lambda x: x[1], reverse=True)
            
            # Show results
            st.write("**Provinces that need the most extra classrooms:**")
            for i, (province, classrooms) in enumerate(sorted_provinces[:5]):
                if classrooms > 0:
                    st.write(f"{i+1}. **{province}**: {classrooms:,} extra classrooms needed")

with tab4:
    st.header("🚻 Toilet Problems")
    st.write("This shows which schools don't have enough toilets for their students.")
    
    if 'extra_toilets_required' in data.columns:
        # Count toilet problems
        schools_need_toilets = 0
        total_toilets_needed = 0
        schools_no_toilets = 0
        
        for i in range(len(data)):
            extra_toilets = data.iloc[i]['extra_toilets_required']
            current_toilets = data.iloc[i]['toilets'] if 'toilets' in data.columns else 1
            
            if extra_toilets > 0:
                schools_need_toilets = schools_need_toilets + 1
                total_toilets_needed = total_toilets_needed + extra_toilets
            
            if current_toilets == 0:
                schools_no_toilets = schools_no_toilets + 1
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🚻 Schools Need More Toilets", f"{schools_need_toilets:,}")
            
        with col2:
            st.metric("🏗️ Total Toilets Needed", f"{int(total_toilets_needed):,}")
            
        with col3:
            st.metric("⚠️ Schools with NO Toilets", f"{schools_no_toilets:,}")
            if schools_no_toilets > 0:
                st.error("Emergency!")
        
        st.write("---")
        
        # Simple analysis
        st.subheader("🔍 What This Means")
        
        percentage_need_toilets = (schools_need_toilets / len(data)) * 100
        
        if percentage_need_toilets > 80:
            st.error(f"😰 **BIG PROBLEM!** {percentage_need_toilets:.1f}% of schools need more toilets!")
        elif percentage_need_toilets > 50:
            st.warning(f"⚠️ **Problem:** {percentage_need_toilets:.1f}% of schools need more toilets")
        else:
            st.success(f"✅ **Good news:** Only {percentage_need_toilets:.1f}% of schools need more toilets")
        
        if schools_no_toilets > 0:
            st.error(f"🚨 **URGENT:** {schools_no_toilets:,} schools have NO toilets at all! Children have nowhere to go to the bathroom at school!")
        
        # Show toilet needs by province - simple way
        if 'Province' in data.columns:
            st.subheader("📍 Which Areas Have the Worst Toilet Problems?")
            
            province_toilet_needs = {}
            
            for i in range(len(data)):
                province = data.iloc[i]['Province']
                extra_toilets = data.iloc[i]['extra_toilets_required']
                
                if province not in province_toilet_needs:
                    province_toilet_needs[province] = 0
                
                province_toilet_needs[province] = province_toilet_needs[province] + extra_toilets
            
            # Sort and show worst provinces
            worst_provinces = []
            for province, toilets_needed in province_toilet_needs.items():
                if toilets_needed > 0:
                    worst_provinces.append([province, int(toilets_needed)])
            
            worst_provinces.sort(key=lambda x: x[1], reverse=True)
            
            st.write("**Provinces that need the most toilets:**")
            for i, (province, toilets) in enumerate(worst_provinces[:5]):
                st.write(f"{i+1}. **{province}**: {toilets:,} extra toilets needed")
        
        # Simple bar chart of toilet problems
        st.subheader("📊 Toilet Problem Chart")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        categories = ['Schools with\nEnough Toilets', 'Schools Need\nMore Toilets']
        values = [len(data) - schools_need_toilets, schools_need_toilets]
        colors = ['green', 'red']
        
        bars = ax.bar(categories, values, color=colors)
        ax.set_title('Toilet Problems in Kenya Schools', fontsize=16)
        ax.set_ylabel('Number of Schools', fontsize=12)
        
        # Add numbers on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 200,
                   f'{int(height):,}', ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        st.pyplot(fig)

# Footer
st.write("---")
st.write("### 💡 Summary - What Should We Do?")
st.info("""
**Most Important Problems:**
1. 🎯 **Teachers First** - Many schools don't have enough teachers
2. 🏛️ **Classrooms** - Some schools are too crowded  
3. 🚻 **Toilets** - Basic facilities that students need

**What to do:**
- Send more teachers to schools that need them most
- Build more classrooms in crowded schools  
- Build toilets in schools that don't have enough

This data helps the government know where to spend money to help children get better education!
""")

st.write("---")
st.caption("📊 Data Source: Kenya School Mapping Project | Dashboard created to help improve education in Kenya 🇰🇪")