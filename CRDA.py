import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pdfplumber
import io

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Customer Rexis Dashboard", layout="wide", initial_sidebar_state="expanded")
st.title("🔬 Customer Rexis Service & Reliability Dashboard")

# ==========================================
# SIDEBAR DATA INGESTION
# ==========================================
st.sidebar.header("📁 Data Ingestion")
# Allow CSV, Excel, and PDF formats
uploaded_file = st.sidebar.file_uploader("Upload Customer Service Data", type=["csv", "xlsx", "xls", "pdf"])

# Data Processing Engine
@st.cache_data(show_spinner=False)
def load_and_clean_data(file_bytes, file_name):
    # Convert bytes back to a file-like object for pandas/pdfplumber
    file_object = io.BytesIO(file_bytes)
    file_ext = file_name.split('.')[-1].lower()
    
    # 1. READ THE FILE BASED ON EXTENSION
    try:
        if file_ext == 'csv':
            df = pd.read_csv(file_object)
        elif file_ext in ['xls', 'xlsx']:
            df = pd.read_excel(file_object)
        elif file_ext == 'pdf':
            # Extract tabular data from PDF using pdfplumber
            with pdfplumber.open(file_object) as pdf:
                all_tables = []
                for page in pdf.pages:
                    table = page.extract_table()
                    if table and len(table) > 1:
                        # Convert each page's table to a dataframe (Row 0 is header)
                        df_page = pd.DataFrame(table[1:], columns=table[0])
                        all_tables.append(df_page)
                
                if not all_tables:
                    st.error("Could not find structured tabular text data in this PDF. It may be a scanned image requiring OCR.")
                    st.stop()
                    
                # Combine all tables from all pages
                df = pd.concat(all_tables, ignore_index=True)
        else:
            st.error("Unsupported file format.")
            st.stop()
            
    except Exception as e:
        st.error(f"Error reading the file: {str(e)}")
        st.stop()
        
    # Clean up column names (strip whitespace)
    df.columns = df.columns.str.strip()
        
    # 2. AUTO-DETECT DATE FORMATS
    date_columns = ['Date/Time Opened', 'Labour Start Date', 'Labour End Date']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')
        
    # 3. MISSING DATA LOGIC (Imputation)
    if 'Labour Start Date' in df.columns and 'Date/Time Opened' in df.columns:
        df['Labour Start Date'] = df['Labour Start Date'].fillna(df['Date/Time Opened'] + pd.Timedelta(hours=2))
    if 'Labour End Date' in df.columns and 'Labour Start Date' in df.columns:
        df['Labour End Date'] = df['Labour End Date'].fillna(df['Labour Start Date'] + pd.Timedelta(hours=4))
    
    # 4. CALCULATE RESPONSE & RESOLUTION TIMES (in hours)
    if all(c in df.columns for c in ['Labour Start Date', 'Date/Time Opened', 'Labour End Date']):
        df['Response_Hours'] = (df['Labour Start Date'] - df['Date/Time Opened']).dt.total_seconds() / 3600
        df['Resolution_Hours'] = (df['Labour End Date'] - df['Date/Time Opened']).dt.total_seconds() / 3600
        
        # Fix negatives caused by data entry typos
        df['Response_Hours'] = df['Response_Hours'].apply(lambda x: max(x, 0) if pd.notnull(x) else x)
        df['Resolution_Hours'] = df['Resolution_Hours'].apply(lambda x: max(x, 0) if pd.notnull(x) else x)
        
        # SAME DAY vs NEXT DAY RESOLUTION
        df['Opened_Date'] = df['Date/Time Opened'].dt.date
        df['Resolved_Date'] = df['Labour End Date'].dt.date
        df['Days_to_Resolve'] = (df['Resolved_Date'] - df['Opened_Date']).apply(lambda x: x.days if pd.notnull(x) else np.nan)
        
        def resolve_category(days):
            if pd.isnull(days): return "Unknown"
            if days == 0: return "Same Day"
            elif days == 1: return "Next Day"
            else: return f"{int(days)} Days Later"
        df['Resolution_Speed'] = df['Days_to_Resolve'].apply(resolve_category)

        # TIME BUCKETING LOGIC (<24, 24-48, 48-72, 72-96, >96)
        def categorize_time(hours):
            if pd.isnull(hours): return "Unknown"
            if hours <= 24: return "< 24 Hours"
            elif hours <= 48: return "24 - 48 Hours"
            elif hours <= 72: return "48 - 72 Hours"
            elif hours <= 96: return "72 - 96 Hours"
            else: return "> 96 Hours"
            
        df['Response Bucket'] = df['Response_Hours'].apply(categorize_time)
        df['Resolution Bucket'] = df['Resolution_Hours'].apply(categorize_time)
    
    # 5. DOWNTIME & UPTIME CALCULATION
    if 'Actual Down Time' in df.columns:
        df['Actual Down Time Hours'] = pd.to_timedelta(df['Actual Down Time'].astype(str), errors='coerce').dt.total_seconds() / 3600
        df['Actual Down Time Hours'] = df['Actual Down Time Hours'].fillna(0)

    return df

# Halt rendering if no file is uploaded yet
if uploaded_file is None:
    st.info("👋 Welcome! Please upload your service log (CSV, Excel, or PDF) in the sidebar to populate the dashboard metrics.")
    st.stop()

# Load data dynamically once uploaded
with st.spinner("Extracting and processing data..."):
    # Read bytes so it can be hashed by st.cache_data
    file_bytes = uploaded_file.getvalue()
    df_raw = load_and_clean_data(file_bytes, uploaded_file.name)

# Ensure essential columns exist before proceeding to visual logic
essential_cols = ['Date/Time Opened', 'Type of Complaint', 'Region', 'Account Name', 'Serial No.']
missing_cols = [c for c in essential_cols if c not in df_raw.columns]
if missing_cols:
    st.error(f"Uploaded file is missing essential columns required for the dashboard: {', '.join(missing_cols)}")
    st.stop()

# Base timelines calculations for Uptime
min_date = df_raw['Date/Time Opened'].min()
max_date = df_raw['Date/Time Opened'].max()
total_days = (max_date - min_date).days if pd.notnull(max_date) else 143
total_timeline_hours = max(total_days * 24, 24)

# ==========================================
# SIDEBAR FILTERS
# ==========================================
st.sidebar.header("⚙️ Flexible Data Filters")

min_d, max_d = min_date.date(), max_date.date()
date_range = st.sidebar.date_input("Select Date Range", [min_d, max_d], min_value=min_d, max_value=max_d)

if len(date_range) == 2:
    start_date, end_date = date_range
    mask = (df_raw['Date/Time Opened'].dt.date >= start_date) & (df_raw['Date/Time Opened'].dt.date <= end_date)
    df = df_raw.loc[mask]
else:
    df = df_raw

# Dynamic multi-selects
selected_region = st.sidebar.multiselect("Region", options=df_raw['Region'].dropna().unique(), default=df_raw['Region'].dropna().unique())
selected_type = st.sidebar.multiselect("Complaint Type", options=df_raw['Type of Complaint'].dropna().unique(), default=df_raw['Type of Complaint'].dropna().unique())

df = df[df['Region'].isin(selected_region) & df['Type of Complaint'].isin(selected_type)]

# ==========================================
# DYNAMIC AI INSIGHTS ENGINE
# ==========================================
def ai_insight(context, data):
    if data.empty:
        return "**🤖 AI Insight:** No data available for the current selection."
    
    if context == "health":
        total_down_hours = data['Actual Down Time Hours'].sum() if 'Actual Down Time Hours' in data.columns else 0
        unique_machines = data['Serial No.'].nunique()
        avg_down_per_machine = total_down_hours / unique_machines if unique_machines > 0 else 0
        uptime_pct = ((total_timeline_hours - avg_down_per_machine) / total_timeline_hours) * 100
        same_day_count = len(data[data['Resolution_Speed']=='Same Day']) if 'Resolution_Speed' in data.columns else 0
        return f"**🤖 AI Insight (Total Health):** Across {len(data)} cases, average instrument uptime is **{uptime_pct:.2f}%** on a continuous 24h timeline. {same_day_count} cases were resolved the same day."
    
    elif context == "trends":
        if 'Resolution Bucket' in data.columns:
            top_res_bucket = data['Resolution Bucket'].mode()[0] if not data.empty else "N/A"
            return f"**🤖 AI Insight (Service Trends):** The most common resolution timeframe is **{top_res_bucket}**. Hardware interventions heavily dictate the tail end of service timelines."
        return "**🤖 AI Insight:** Time bucketing data not available."
    
    elif context == "pareto":
        hw_data = data[data['Type of Complaint'].str.contains('Hardware', case=False, na=False)]
        if not hw_data.empty:
            top_acc = hw_data['Account Name'].value_counts().index[0]
            pct = (hw_data['Account Name'].value_counts().iloc[0] / len(hw_data)) * 100
            return f"**🤖 AI Insight (80/20 Rule):** Filtering strictly for Hardware issues, **{top_acc}** is your highest-risk account, producing {pct:.1f}% of all hardware complaints on its own."
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
    
    # KPIs Calculation
    total_down_hours = df['Actual Down Time Hours'].sum() if 'Actual Down Time Hours' in df.columns else 0
    unique_machines = df['Serial No.'].nunique()
    avg_down_per_machine = total_down_hours / unique_machines if unique_machines > 0 else 0
    uptime_pct = ((total_timeline_hours - avg_down_per_machine) / total_timeline_hours) * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Complaints", len(df))
    col2.metric("Network Uptime % (24hr)", f"{uptime_pct:.2f}%")
    
    if 'Response_Hours' in df.columns:
        col3.metric("Avg Response Time", f"{df['Response_Hours'].mean():.1f} Hrs")
    else:
        col3.metric("Avg Response Time", "N/A")
        
    if 'Resolution_Speed' in df.columns:
        same_day_pct = (len(df[df['Resolution_Speed'] == 'Same Day']) / len(df) * 100) if len(df) > 0 else 0
        col4.metric("Same-Day Resolution Rate", f"{same_day_pct:.1f}%")
    else:
        col4.metric("Same-Day Resolution Rate", "N/A")

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        fig_donut = px.pie(df, names='Type of Complaint', hole=0.4, title="Complaint Breakdown")
        st.plotly_chart(fig_donut, use_container_width=True)
    with col_chart2:
        reg_counts = df['Region'].value_counts().reset_index()
        reg_counts.columns = ['Region', 'Complaints']
        fig_bar = px.bar(reg_counts, x='Region', y='Complaints', title="Geographic Distribution", color='Complaints')
        st.plotly_chart(fig_bar, use_container_width=True)

# --- TAB 2: SERVICE & SLA TRENDS ---
with tab2:
    st.info(ai_insight("trends", df))
    
    if 'Resolution Bucket' in df.columns and 'Response Bucket' in df.columns:
        bucket_order = ["< 24 Hours", "24 - 48 Hours", "48 - 72 Hours", "72 - 96 Hours", "> 96 Hours"]
        
        res_bucket_counts = df['Resolution Bucket'].value_counts().reindex(bucket_order).reset_index()
        res_bucket_counts.columns = ['Bucket', 'Count']
        res_bucket_counts['Type'] = 'Resolution Time'

        resp_bucket_counts = df['Response Bucket'].value_counts().reindex(bucket_order).reset_index()
        resp_bucket_counts.columns = ['Bucket', 'Count']
        resp_bucket_counts['Type'] = 'Response Time'

        combined_buckets = pd.concat([res_bucket_counts, resp_bucket_counts])
        fig_buckets = px.bar(combined_buckets, x='Bucket', y='Count', color='Type', barmode='group', title="SLA Buckets", text_auto=True)
        st.plotly_chart(fig_buckets, use_container_width=True)
    else:
        st.warning("Insufficient data to calculate SLA buckets.")

# --- TAB 3: TOP ACCOUNTS (80/20 PARETO) ---
with tab3:
    st.info(ai_insight("pareto", df))
    hw_df = df[df['Type of Complaint'].str.contains('Hardware', case=False, na=False)]
    
    if not hw_df.empty:
        account_df = hw_df.groupby('Account Name').size().reset_index(name='Hardware Complaints')
        account_df = account_df.sort_values(by='Hardware Complaints', ascending=False).head(20)
        account_df['Cumulative %'] = account_df['Hardware Complaints'].cumsum() / account_df['Hardware Complaints'].sum() * 100
        
        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(x=account_df['Account Name'], y=account_df['Hardware Complaints'], name="Hardware Complaints", marker_color='indianred'))
        fig_pareto.add_trace(go.Scatter(x=account_df['Account Name'], y=account_df['Cumulative %'], name="Cumulative %", yaxis='y2', mode='lines+markers', line=dict(color='blue', width=2)))
        
        fig_pareto.update_layout(
            title="Top 20 Customers by Hardware Issues (80/20 Rule)",
            yaxis=dict(title='Hardware Complaints'),
            yaxis2=dict(title='Cumulative %', overlaying='y', side='right', range=[0, 105]),
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig_pareto, use_container_width=True)
    else:
        st.warning("No Hardware complaints found in the currently filtered data.")

# --- TAB 4: SERIAL NUMBER HISTORY ---
with tab4:
    st.info(ai_insight("serial", df))
    
    # Try to identify Family/Line Name column safely
    fam_col = 'Family/Line: Name' if 'Family/Line: Name' in df.columns else None
    groupby_cols = ['Serial No.', 'Account Name']
    if fam_col:
        groupby_cols.append(fam_col)
        
    agg_dict = {'Date/Time Opened': 'count'} # Always have count
    if 'Actual Down Time Hours' in df.columns:
        agg_dict['Actual Down Time Hours'] = 'sum'
    if 'Resolution_Hours' in df.columns:
        agg_dict['Resolution_Hours'] = 'mean'
    if 'Resolution Bucket' in df.columns:
        agg_dict['Resolution Bucket'] = lambda x: x.mode()[0] if not x.empty else 'N/A'

    serial_df = df.groupby(groupby_cols).agg(agg_dict).reset_index()
    
    # Rename columns gracefully based on what exists
    rename_dict = {'Date/Time Opened': 'Total_Complaints', 'Actual Down Time Hours': 'Total_Down_Hours', 'Resolution_Hours': 'Avg_Resolution_Hrs', 'Resolution Bucket': 'Most_Common_Bucket'}
    serial_df.rename(columns=rename_dict, inplace=True)
    serial_df = serial_df.sort_values(by='Total_Complaints', ascending=False)
    
    if 'Avg_Resolution_Hrs' in serial_df.columns:
        serial_df['Avg_Resolution_Hrs'] = serial_df['Avg_Resolution_Hrs'].round(1)
    if 'Total_Down_Hours' in serial_df.columns:
        serial_df['Total_Down_Hours'] = serial_df['Total_Down_Hours'].round(1)
    
    st.dataframe(serial_df, use_container_width=True, height=500)
