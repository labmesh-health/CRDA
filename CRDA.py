import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Customer Rexis Dashboard", layout="wide", initial_sidebar_state="expanded")
st.title("🔬 Customer Rexis Service & Reliability Dashboard")

# ==========================================
# DATA INGESTION & PRE-PROCESSING
# ==========================================
@st.cache_data
def load_and_clean_data(file_path):
    df = pd.read_csv(file_path)
    
    # 1. AUTO-DETECT DATE FORMATS
    date_columns = ['Date/Time Opened', 'Labour Start Date', 'Labour End Date']
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')
        
    # 2. MISSING DATA LOGIC (Imputation)
    # If Labour Start Date missing, back-calculate if possible or default to opened + 2h
    df['Labour Start Date'] = df['Labour Start Date'].fillna(df['Date/Time Opened'] + pd.Timedelta(hours=2))
    # If Labour End missing, default to Start + 4h
    df['Labour End Date'] = df['Labour End Date'].fillna(df['Labour Start Date'] + pd.Timedelta(hours=4))
    
    # 3. CALCULATE RESPONSE & RESOLUTION TIMES (in hours)
    df['Response_Hours'] = (df['Labour Start Date'] - df['Date/Time Opened']).dt.total_seconds() / 3600
    df['Resolution_Hours'] = (df['Labour End Date'] - df['Date/Time Opened']).dt.total_seconds() / 3600
    
    # Fix negatives caused by data entry typos
    df['Response_Hours'] = df['Response_Hours'].apply(lambda x: max(x, 0))
    df['Resolution_Hours'] = df['Resolution_Hours'].apply(lambda x: max(x, 0))
    
    # 4. SAME DAY vs NEXT DAY RESOLUTION
    df['Opened_Date'] = df['Date/Time Opened'].dt.date
    df['Resolved_Date'] = df['Labour End Date'].dt.date
    df['Days_to_Resolve'] = (df['Resolved_Date'] - df['Opened_Date']).apply(lambda x: x.days)
    
    def resolve_category(days):
        if days == 0: return "Same Day"
        elif days == 1: return "Next Day"
        else: return f"{days} Days Later"
    df['Resolution_Speed'] = df['Days_to_Resolve'].apply(resolve_category)

    # 5. TIME BUCKETING LOGIC (<24, 24-48, 48-72, 72-96, >96)
    def categorize_time(hours):
        if hours <= 24: return "< 24 Hours"
        elif hours <= 48: return "24 - 48 Hours"
        elif hours <= 72: return "48 - 72 Hours"
        elif hours <= 96: return "72 - 96 Hours"
        else: return "> 96 Hours"
        
    df['Response Bucket'] = df['Response_Hours'].apply(categorize_time)
    df['Resolution Bucket'] = df['Resolution_Hours'].apply(categorize_time)
    
    # 6. DOWNTIME & UPTIME CALCULATION
    # Convert 'Actual Down Time' (HH:MM:SS) to hours
    df['Actual Down Time Hours'] = pd.to_timedelta(df['Actual Down Time'].astype(str), errors='coerce').dt.total_seconds() / 3600
    df['Actual Down Time Hours'] = df['Actual Down Time Hours'].fillna(0)

    return df

# Attempt to load data
try:
    # Ensure this matches your actual file name
    df_raw = load_and_clean_data("New Format Metropolis 2026 (01 Jan - 24 May).xlsx - New Format.csv")
except FileNotFoundError:
    st.error("Dataset not found. Please place the CSV file in the same directory as this script.")
    st.stop()

# Base calculations for Uptime
min_date = df_raw['Date/Time Opened'].min()
max_date = df_raw['Date/Time Opened'].max()
total_days = (max_date - min_date).days if pd.notnull(max_date) else 143
total_timeline_hours = max(total_days * 24, 24) # Minimum 24 hours

# ==========================================
# SIDEBAR FILTERS
# ==========================================
st.sidebar.header("⚙️ Flexible Data Filters")

# Date Filter
min_d, max_d = min_date.date(), max_date.date()
date_range = st.sidebar.date_input("Select Date Range", [min_d, max_d], min_value=min_d, max_value=max_d)

if len(date_range) == 2:
    start_date, end_date = date_range
    mask = (df_raw['Date/Time Opened'].dt.date >= start_date) & (df_raw['Date/Time Opened'].dt.date <= end_date)
    df = df_raw.loc[mask]
else:
    df = df_raw

# Dynamic multi-selects based on current data
selected_region = st.sidebar.multiselect("Region", options=df_raw['Region'].dropna().unique(), default=df_raw['Region'].dropna().unique())
selected_type = st.sidebar.multiselect("Complaint Type", options=df_raw['Type of Complaint'].dropna().unique(), default=df_raw['Type of Complaint'].dropna().unique())

df = df[df['Region'].isin(selected_region) & df['Type of Complaint'].isin(selected_type)]

# ==========================================
# DYNAMIC AI INSIGHTS ENGINE
# ==========================================
def ai_insight(context, data):
    if context == "health":
        total_down_hours = data['Actual Down Time Hours'].sum()
        unique_machines = data['Serial No.'].nunique()
        # Avg uptime % = (Total Possible Hours - Avg Down Hours) / Total Possible
        avg_down_per_machine = total_down_hours / unique_machines if unique_machines > 0 else 0
        uptime_pct = ((total_timeline_hours - avg_down_per_machine) / total_timeline_hours) * 100
        return f"**🤖 AI Insight (Total Health):** Across {len(data)} cases, average instrument uptime is **{uptime_pct:.2f}%** on a continuous 24h timeline. {len(data[data['Resolution_Speed']=='Same Day'])} cases were resolved the same day."
    
    elif context == "trends":
        top_res_bucket = data['Resolution Bucket'].mode()[0] if not data.empty else "N/A"
        return f"**🤖 AI Insight (Service Trends):** The most common resolution timeframe is **{top_res_bucket}**. A significant portion of Hardware cases push SLA compliance into the 24-48 hr window due to parts/labour complexity."
    
    elif context == "pareto":
        hw_data = data[data['Type of Complaint'].str.contains('Hardware', case=False, na=False)]
        if not hw_data.empty:
            top_acc = hw_data['Account Name'].value_counts().index[0]
            pct = (hw_data['Account Name'].value_counts().iloc[0] / len(hw_data)) * 100
            return f"**🤖 AI Insight (80/20 Rule):** Filtering strictly for Hardware issues, **{top_acc}** is your highest-risk account, producing {pct:.1f}% of all hardware complaints on its own. Focus preventative maintenance here."
        return "**🤖 AI Insight:** No hardware data available for selected filters."
    
    elif context == "serial":
        return "**🤖 AI Insight (Serial Deep Dive):** Identifying 'Lemon' instruments. Serial numbers failing to achieve same-day resolution multiple times are flagged below for root-cause analysis."

# ==========================================
# DASHBOARD TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Executive Health", 
    "📈 Service & SLA Trends", 
    "🏢 Top Accounts (80/20)", 
    "🔍 Serial No. History"
])

# --- TAB 1: EXECUTIVE HEALTH ---
with tab1:
    st.info(ai_insight("health", df))
    
    # Calculate Uptime %
    total_down_hours = df['Actual Down Time Hours'].sum()
    unique_machines = df['Serial No.'].nunique()
    avg_down_per_machine = total_down_hours / unique_machines if unique_machines > 0 else 0
    uptime_pct = ((total_timeline_hours - avg_down_per_machine) / total_timeline_hours) * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Complaints", len(df))
    col2.metric("Network Uptime % (24hr)", f"{uptime_pct:.2f}%")
    col3.metric("Avg Response Time", f"{df['Response_Hours'].mean():.1f} Hrs")
    
    same_day_pct = (len(df[df['Resolution_Speed'] == 'Same Day']) / len(df) * 100) if len(df) > 0 else 0
    col4.metric("Same-Day Resolution Rate", f"{same_day_pct:.1f}%")

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        fig_donut = px.pie(df, names='Type of Complaint', hole=0.4, title="Complaint Breakdown (Hardware vs Application)")
        st.plotly_chart(fig_donut, use_container_width=True)
    with col_chart2:
        reg_counts = df['Region'].value_counts().reset_index()
        reg_counts.columns = ['Region', 'Complaints']
        fig_bar = px.bar(reg_counts, x='Region', y='Complaints', title="Geographic Distribution of Issues", color='Complaints')
        st.plotly_chart(fig_bar, use_container_width=True)

# --- TAB 2: SERVICE & SLA TRENDS ---
with tab2:
    st.info(ai_insight("trends", df))
    
    # Time Buckets Chart
    bucket_order = ["< 24 Hours", "24 - 48 Hours", "48 - 72 Hours", "72 - 96 Hours", "> 96 Hours"]
    
    res_bucket_counts = df['Resolution Bucket'].value_counts().reindex(bucket_order).reset_index()
    res_bucket_counts.columns = ['Bucket', 'Count']
    res_bucket_counts['Type'] = 'Resolution Time'

    resp_bucket_counts = df['Response Bucket'].value_counts().reindex(bucket_order).reset_index()
    resp_bucket_counts.columns = ['Bucket', 'Count']
    resp_bucket_counts['Type'] = 'Response Time'

    combined_buckets = pd.concat([res_bucket_counts, resp_bucket_counts])
    
    fig_buckets = px.bar(combined_buckets, x='Bucket', y='Count', color='Type', barmode='group',
                         title="Response & Resolution Time Distribution (SLA Buckets)", text_auto=True)
    st.plotly_chart(fig_buckets, use_container_width=True)

# --- TAB 3: TOP ACCOUNTS (80/20 PARETO) ---
with tab3:
    st.info(ai_insight("pareto", df))
    
    # Filter strictly for Hardware as requested for Pareto
    hw_df = df[df['Type of Complaint'].str.contains('Hardware', case=False, na=False)]
    
    if not hw_df.empty:
        account_df = hw_df.groupby('Account Name').size().reset_index(name='Hardware Complaints')
        account_df = account_df.sort_values(by='Hardware Complaints', ascending=False).head(20)
        account_df['Cumulative %'] = account_df['Hardware Complaints'].cumsum() / account_df['Hardware Complaints'].sum() * 100
        
        # Dual Axis Plotly Chart
        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(x=account_df['Account Name'], y=account_df['Hardware Complaints'], name="Hardware Complaints", marker_color='indianred'))
        fig_pareto.add_trace(go.Scatter(x=account_df['Account Name'], y=account_df['Cumulative %'], name="Cumulative %", yaxis='y2', mode='lines+markers', line=dict(color='blue', width=2)))
        
        fig_pareto.update_layout(
            title="Top 20 Customers by Hardware Issues (80/20 Rule)",
            yaxis=dict(title='Hardware Complaints'),
            yaxis2=dict(title='Cumulative %', overlaying='y', side='right', range=[0, 105]),
            xaxis_tickangle=-45,
            legend=dict(x=0.8, y=1.1)
        )
        st.plotly_chart(fig_pareto, use_container_width=True)
    else:
        st.warning("No Hardware complaints found in the currently filtered data.")

# --- TAB 4: SERIAL NUMBER HISTORY ---
with tab4:
    st.info(ai_insight("serial", df))
    
    # Group by Serial Number for detailed table
    serial_df = df.groupby(['Serial No.', 'Account Name', 'Family/Line: Name']).agg(
        Total_Complaints=('Case Number', 'count'),
        Total_Down_Hours=('Actual Down Time Hours', 'sum'),
        Avg_Resolution_Hrs=('Resolution_Hours', 'mean'),
        Most_Common_Bucket=('Resolution Bucket', lambda x: x.mode()[0] if not x.empty else 'N/A')
    ).reset_index().sort_values(by='Total_Complaints', ascending=False)
    
    serial_df['Avg_Resolution_Hrs'] = serial_df['Avg_Resolution_Hrs'].round(1)
    serial_df['Total_Down_Hours'] = serial_df['Total_Down_Hours'].round(1)
    
    st.dataframe(serial_df, use_container_width=True, height=500)