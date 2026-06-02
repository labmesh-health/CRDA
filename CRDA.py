import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pdfplumber
import io
import re
from collections import Counter

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Customer Rexis Diagnostic Dashboard", layout="wide", initial_sidebar_state="expanded")
st.title("🔬 Customer Rexis Diagnostic & Diagnostic Dashboard")

# --- PROFESSIONAL COLOR PALETTE ---
CORP_BLUE = '#4E79A7'
CORP_RED = '#E15759'
CORP_TEAL = '#76B7B2'
CORP_ORANGE = '#F28E2B'
CORP_GREEN = '#59A14F'
SAFE_PALETTE = px.colors.qualitative.Safe

# ==========================================
# SIDEBAR DATA INGESTION
# ==========================================
st.sidebar.header("📁 Data Ingestion")
uploaded_file = st.sidebar.file_uploader("Upload Customer Service Data", type=["csv", "xlsx", "xls", "pdf"])

@st.cache_data(show_spinner=False)
def load_and_clean_data(file_bytes, file_name):
    file_object = io.BytesIO(file_bytes)
    file_ext = file_name.split('.')[-1].lower()
    
    # 1. READ THE FILE
    try:
        if file_ext == 'csv':
            df = pd.read_csv(file_object)
        elif file_ext in ['xls', 'xlsx']:
            df = pd.read_excel(file_object)
        elif file_ext == 'pdf':
            with pdfplumber.open(file_object) as pdf:
                all_tables = []
                for page in pdf.pages:
                    table = page.extract_table()
                    if table and len(table) > 1:
                        df_page = pd.DataFrame(table[1:], columns=table[0])
                        all_tables.append(df_page)
                if not all_tables:
                    st.error("Could not find structured tabular text data in this PDF.")
                    st.stop()
                df = pd.concat(all_tables, ignore_index=True)
        else:
            st.error("Unsupported file format.")
            st.stop()
    except Exception as e:
        st.error(f"Error reading the file: {str(e)}")
        st.stop()
        
    df.columns = df.columns.str.strip()
    
    # 2. SITE NAME DIFFERENTIATION
    if 'Account Name' in df.columns and 'City' in df.columns:
        df['Site Name'] = df['Account Name'].astype(str) + " (" + df['City'].astype(str) + ")"
    else:
        df['Site Name'] = df.get('Account Name', 'Unknown Site')

    if 'System Down Yes/No' in df.columns:
        df['System Down Yes/No'] = df['System Down Yes/No'].fillna('Not Down').apply(
            lambda x: 'Down' if 'down' in str(x).lower() and 'not' not in str(x).lower() or 'yes' in str(x).lower() else 'Not Down'
        )
    else:
        df['System Down Yes/No'] = 'Unknown'

    # 3. NLP TEXT MINING (Hardware Sub-Domain Categorization)
    if 'Subject' in df.columns:
        df['Subject_Clean'] = df['Subject'].fillna('').astype(str).str.lower()
        
        def categorize_hardware(text):
            if any(word in text for word in ['gripper', 'axis', 'movement', 'rack', 'motor', 'mechanical', 'actuator', 'jam', 'stuck', 'pick up']):
                return 'Kinematic / Robotic'
            elif any(word in text for word in ['pressure', 'wash', 'temperature', 'cooling', 'prime', 'fluid', 'aspiration', 'leak', 'thermistor', 'water']):
                return 'Fluidic / Thermal'
            elif any(word in text for word in ['voltage', 'power', 'room', 'ac', 'ups', 'drop', 'fluctuation', 'board']):
                return 'Environmental / Power'
            elif any(word in text for word in ['rfid', 'noise', 'outlier', 'calibration', 'photometer', 'sensor', 'lld', 'error', 'qc']):
                return 'Analytical / Sensor'
            else:
                return 'General / Unclassified'
                
        df['Hardware Sub-Domain'] = df['Subject_Clean'].apply(categorize_hardware)
        
        # Identify Environmental Flags per site
        df['Env_Flag'] = df['Hardware Sub-Domain'] == 'Environmental / Power'
    else:
        df['Hardware Sub-Domain'] = 'Unknown'
        df['Env_Flag'] = False

    # 4. AUTO-DETECT DATE FORMATS
    date_columns = ['Date/Time Opened', 'Labour Start Date', 'Labour End Date']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')
        
    # 5. MISSING DATA LOGIC
    if 'Labour Start Date' in df.columns and 'Date/Time Opened' in df.columns:
        df['Labour Start Date'] = df['Labour Start Date'].fillna(df['Date/Time Opened'] + pd.Timedelta(hours=2))
    if 'Labour End Date' in df.columns and 'Labour Start Date' in df.columns:
        df['Labour End Date'] = df['Labour End Date'].fillna(df['Labour Start Date'] + pd.Timedelta(hours=4))
    
    # 6. CALCULATE TIMES
    if all(c in df.columns for c in ['Labour Start Date', 'Date/Time Opened', 'Labour End Date']):
        df['Response_Hours'] = (df['Labour Start Date'] - df['Date/Time Opened']).dt.total_seconds() / 3600
        df['Resolution_Hours'] = (df['Labour End Date'] - df['Date/Time Opened']).dt.total_seconds() / 3600
        df['Response_Hours'] = df['Response_Hours'].apply(lambda x: max(x, 0) if pd.notnull(x) else x)
        df['Resolution_Hours'] = df['Resolution_Hours'].apply(lambda x: max(x, 0) if pd.notnull(x) else x)
        
        df['Opened_Date'] = df['Date/Time Opened'].dt.date
        df['Resolved_Date'] = df['Labour End Date'].dt.date
        df['Days_to_Resolve'] = (df['Resolved_Date'] - df['Opened_Date']).apply(lambda x: x.days if pd.notnull(x) else np.nan)
        
        def resolve_category(days):
            if pd.isnull(days): return "Unknown"
            if days == 0: return "Same Day"
            elif days == 1: return "Next Day"
            else: return f"{int(days)} Days Later"
        df['Resolution_Speed'] = df['Days_to_Resolve'].apply(resolve_category)

    if 'Actual Down Time' in df.columns:
        df['Actual Down Time Hours'] = pd.to_timedelta(df['Actual Down Time'].astype(str), errors='coerce').dt.total_seconds() / 3600
        df['Actual Down Time Hours'] = df['Actual Down Time Hours'].fillna(0)

    return df

if uploaded_file is None:
    st.info("👋 Welcome! Please upload your service log (CSV, Excel, or PDF) in the sidebar.")
    st.stop()

with st.spinner("Extracting and processing data..."):
    file_bytes = uploaded_file.getvalue()
    df_raw = load_and_clean_data(file_bytes, uploaded_file.name)

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

selected_region = st.sidebar.multiselect("Region", options=df_raw['Region'].dropna().unique(), default=df_raw['Region'].dropna().unique())
selected_type = st.sidebar.multiselect("Complaint Type", options=df_raw['Type of Complaint'].dropna().unique(), default=df_raw['Type of Complaint'].dropna().unique())

df = df[df['Region'].isin(selected_region) & df['Type of Complaint'].isin(selected_type)]

st.sidebar.markdown("---")
st.sidebar.header("🔄 Recurring Issues Logic")
recurring_days = st.sidebar.slider("Flag breakdowns recurring within (Days):", min_value=7, max_value=90, value=30, step=1)

# ==========================================
# CAPA GENERATOR (Automated AI Insights)
# ==========================================
def generate_capa(data):
    if data.empty or 'Hardware Sub-Domain' not in data.columns:
        return "Not enough data to generate CAPA."
    
    hw_only = data[data['Type of Complaint'].str.contains('Hardware', case=False, na=False)]
    if hw_only.empty:
        return "**🤖 Diagnostic Insight:** No hardware failures detected in current filter. System stable."
    
    top_domain = hw_only['Hardware Sub-Domain'].mode()[0]
    
    capa_text = f"**🚨 Primary Failure Domain Detected: {top_domain}**\n\n"
    if top_domain == 'Kinematic / Robotic':
        capa_text += "➤ **Immediate (Reactive):** Inspect and replace degraded grippers, Z-axis steppers, and rack transfer motors on targeted units.\n"
        capa_text += "➤ **30-Day (Protocol):** Enhance mechanical tolerance checkpoints during PM visits.\n"
        capa_text += "➤ **90-Day (Proactive):** Institute proactive replacement schedule for robotic components exceeding 15 million cycles."
    elif top_domain == 'Fluidic / Thermal':
        capa_text += "➤ **Immediate (Reactive):** Flush fluidic circuits, verify probe aspiration pressure, and replace faulty thermistors.\n"
        capa_text += "➤ **30-Day (Protocol):** Integrate targeted thermal limit tests and wash-station alignments into PM routines.\n"
        capa_text += "➤ **90-Day (Proactive):** Audit water quality and ambient lab temperatures correlating with cooling system stress."
    elif top_domain == 'Environmental / Power':
        capa_text += "➤ **Immediate (Reactive):** Deploy line-conditioners to sites with recurring ADC noise and voltage drops.\n"
        capa_text += "➤ **30-Day (Protocol):** Execute Environmental Hardening audits (AC stability, vacuum pressure) at Top 20 sites.\n"
        capa_text += "➤ **90-Day (Proactive):** Require lab UPS logs prior to replacing internal instrument power boards."
    else:
        capa_text += "➤ **Immediate (Reactive):** Recalibrate affected sensors and clear optical pathways.\n"
        capa_text += "➤ **30-Day (Protocol):** Monitor RFID and LLD (Liquid Level Detection) module failure rates.\n"
        capa_text += "➤ **90-Day (Proactive):** Update firmware to reduce false-positive analytical flags."
        
    return capa_text

# ==========================================
# DASHBOARD TABS
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Tab 1: Exec Health", 
    "🎯 Tab 2: CAPA & Impact vs Frequency", 
    "🛠️ Tab 3: Instrument Reliability",
    "🏢 Tab 4: Top Sites (Env Flags)", 
    "🌆 Tab 5: Citywise",
    "🔄 Tab 6: Recurring Breakdowns",
    "🔍 Tab 7: Serial Matrix",
    "🚨 Tab 8: Severe Outliers"
])

# --- TAB 1: EXECUTIVE HEALTH ---
with tab1:
    total_down_hours = df['Actual Down Time Hours'].sum() if 'Actual Down Time Hours' in df.columns else 0
    unique_machines = df['Serial No.'].nunique()
    avg_down_per_machine = total_down_hours / unique_machines if unique_machines > 0 else 0
    uptime_pct = ((total_timeline_hours - avg_down_per_machine) / total_timeline_hours) * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Cases Opened", len(df))
    col2.metric("Average Uptime %", f"{uptime_pct:.2f}%")
    if 'Resolution_Speed' in df.columns:
        same_day_pct = (len(df[df['Resolution_Speed'] == 'Same Day']) / len(df) * 100) if len(df) > 0 else 0
        col3.metric("SLA (Same-Day) Compliance %", f"{same_day_pct:.1f}%")

    if 'Region' in df.columns:
        reg_counts = df['Region'].value_counts().reset_index()
        reg_counts.columns = ['Region', 'Complaints']
        fig_bar = px.bar(reg_counts, x='Region', y='Complaints', title="Geographic Case Volumes", text_auto=True, color_discrete_sequence=[CORP_BLUE])
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True, theme="streamlit")

# --- TAB 2: CAPA & IMPACT VS FREQUENCY ---
with tab2:
    st.info(generate_capa(df))
    
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        # IMPACT VS FREQUENCY BUBBLE CHART
        if 'Hardware Sub-Domain' in df.columns:
            bubble_df = df.groupby('Hardware Sub-Domain').agg(
                Frequency=('Case Number', 'count'),
                Avg_Downtime=('Actual Down Time Hours', 'mean'),
                Total_Downtime=('Actual Down Time Hours', 'sum')
            ).reset_index()
            
            fig_bubble = px.scatter(bubble_df, x='Frequency', y='Avg_Downtime', size='Total_Downtime', color='Hardware Sub-Domain',
                                    title="Impact vs. Frequency (The Diagnostic Quadrant)",
                                    labels={"Frequency": "Total Number of Breakdowns", "Avg_Downtime": "Avg Downtime per Incident (Hours)"},
                                    size_max=60, color_discrete_sequence=SAFE_PALETTE)
            st.plotly_chart(fig_bubble, use_container_width=True, theme="streamlit")
            
    with col_chart2:
        hw_only = df[df['Type of Complaint'].str.contains('Hardware', case=False, na=False)]
        if not hw_only.empty:
            fig_hw_donut = px.pie(hw_only, names='Hardware Sub-Domain', hole=0.4, title="Root Cause Breakdown (Hardware Only)", color_discrete_sequence=SAFE_PALETTE)
            fig_hw_donut.update_traces(textinfo='label+percent')
            st.plotly_chart(fig_hw_donut, use_container_width=True, theme="streamlit")

# --- TAB 3: INSTRUMENT RELIABILITY ---
with tab3:
    col_chart3, col_chart4 = st.columns(2)
    with col_chart3:
        fam_counts = df.groupby('Family/Line: Name').size().reset_index(name='Complaints').sort_values(by='Complaints', ascending=False).head(10)
        fam_counts['Cumulative %'] = fam_counts['Complaints'].cumsum() / fam_counts['Complaints'].sum() * 100
        
        fig_fam_pareto = go.Figure()
        fig_fam_pareto.add_trace(go.Bar(x=fam_counts['Family/Line: Name'], y=fam_counts['Complaints'], name="Complaints", marker_color=CORP_BLUE, text=fam_counts['Complaints'], textposition='auto'))
        fig_fam_pareto.add_trace(go.Scatter(x=fam_counts['Family/Line: Name'], y=fam_counts['Cumulative %'], name="Cumulative %", yaxis='y2', mode='lines+markers+text', text=fam_counts['Cumulative %'].round(1).astype(str)+'%', textposition='top center', line=dict(color=CORP_RED, width=2.5)))
        fig_fam_pareto.update_layout(title="Top Problematic Product Families", yaxis2=dict(overlaying='y', side='right', range=[0, 115]), xaxis_tickangle=-45)
        st.plotly_chart(fig_fam_pareto, use_container_width=True, theme="streamlit")
        
    with col_chart4:
        down_ratio = df.groupby(['Family/Line: Name', 'System Down Yes/No']).size().reset_index(name='Count')
        top_fams = fam_counts['Family/Line: Name'].tolist()
        down_ratio = down_ratio[down_ratio['Family/Line: Name'].isin(top_fams)]
        
        fig_down = px.bar(down_ratio, x='Family/Line: Name', y='Count', color='System Down Yes/No', barmode='stack', text_auto=True, title="System Down Ratio by Product Line", color_discrete_map={'Down': CORP_RED, 'Not Down': CORP_TEAL})
        st.plotly_chart(fig_down, use_container_width=True, theme="streamlit")

# --- TAB 4: TOP SITES (ENV FLAGS) ---
with tab4:
    st.info("**🤖 AI Insight:** Sites marked with ⚠️ indicate known 'Environmental/Power' issues (Voltage drops, temp limits). Hardening these labs will prevent future hardware failures.")
    hw_df = df[df['Type of Complaint'].str.contains('Hardware', case=False, na=False)]
    if not hw_df.empty:
        # Calculate Env Flags per site
        env_sites = hw_df[hw_df['Env_Flag'] == True]['Site Name'].unique()
        
        account_df = hw_df.groupby('Site Name').size().reset_index(name='Hardware Complaints')
        account_df = account_df.sort_values(by='Hardware Complaints', ascending=False).head(20)
        
        # Add warning icon to Site Name if env flag exists
        account_df['Site Display'] = account_df['Site Name'].apply(lambda x: f"⚠️ {x}" if x in env_sites else x)
        account_df['Cumulative %'] = account_df['Hardware Complaints'].cumsum() / account_df['Hardware Complaints'].sum() * 100
        
        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(x=account_df['Site Display'], y=account_df['Hardware Complaints'], name="Hardware Complaints", marker_color=CORP_BLUE, text=account_df['Hardware Complaints'], textposition='auto'))
        fig_pareto.add_trace(go.Scatter(x=account_df['Site Display'], y=account_df['Cumulative %'], name="Cumulative %", yaxis='y2', mode='lines+markers+text', text=account_df['Cumulative %'].round(1).astype(str)+'%', textposition='top center', line=dict(color=CORP_RED, width=2.5)))
        fig_pareto.update_layout(title="Top 20 Sites by Hardware Issues (⚠️ = Environmental Risk)", yaxis2=dict(overlaying='y', side='right', range=[0, 115]), xaxis_tickangle=-45)
        st.plotly_chart(fig_pareto, use_container_width=True, theme="streamlit")

# --- TAB 5: CITYWISE BREAKDOWN ---
with tab5:
    if 'City' in df.columns and 'Family/Line: Name' in df.columns:
        city_inst = df.groupby(['City', 'Family/Line: Name']).size().reset_index(name='Total Breakdowns')
        city_inst = city_inst.sort_values(by='Total Breakdowns', ascending=False).head(50)
        fig_city = px.bar(city_inst, x='City', y='Total Breakdowns', color='Family/Line: Name', title="Citywise Instrument Breakdowns", text_auto=True, barmode='stack', color_discrete_sequence=SAFE_PALETTE)
        st.plotly_chart(fig_city, use_container_width=True, theme="streamlit")

# --- TAB 6: RECURRING BREAKDOWNS ---
with tab6:
    st.info(f"**🤖 AI Insight:** The 'Lemon' machine tracker. Flagging instruments requiring service again within **{recurring_days} days**.")
    df_sorted = df.sort_values(by=['Serial No.', 'Date/Time Opened'])
    df_sorted['Days_Since_Last_Issue'] = df_sorted.groupby('Serial No.')['Date/Time Opened'].diff().dt.days
    recurring_df = df_sorted[df_sorted['Days_Since_Last_Issue'] <= recurring_days]
    
    if not recurring_df.empty:
        recurring_summary = recurring_df.groupby(['Serial No.', 'Family/Line: Name', 'Site Name']).agg(
            Recurring_Incidents=('Case Number', 'count'),
            Avg_Days_Between_Failures=('Days_Since_Last_Issue', 'mean')
        ).reset_index().sort_values(by='Recurring_Incidents', ascending=False)
        recurring_summary['Avg_Days_Between_Failures'] = recurring_summary['Avg_Days_Between_Failures'].round(1)
        st.dataframe(recurring_summary, use_container_width=True)

# --- TAB 7: SERIAL NUMBER INVESTIGATIVE MATRIX ---
with tab7:
    def get_mode(x):
        return x.mode()[0] if not x.empty else "Unknown"

    serial_df = df.groupby(['Serial No.', 'Site Name', 'Family/Line: Name']).agg(
        Total_Complaints=('Case Number', 'count'),
        Total_Down_Hours=('Actual Down Time Hours', 'sum'),
        Primary_Technician=('Primary Technician', get_mode)
    ).reset_index()

    serial_df['Uptime %'] = ((total_timeline_hours - serial_df['Total_Down_Hours']) / total_timeline_hours) * 100
    serial_df['Uptime %'] = serial_df['Uptime %'].round(2)
    serial_df['Total_Down_Hours'] = serial_df['Total_Down_Hours'].round(1)
    
    serial_df = serial_df.sort_values(by='Total_Complaints', ascending=False)
    serial_df = serial_df[['Serial No.', 'Site Name', 'Family/Line: Name', 'Total_Complaints', 'Uptime %', 'Total_Down_Hours', 'Primary_Technician']]

    def highlight_low_uptime(row):
        color = 'background-color: rgba(225, 87, 89, 0.2)' if row['Uptime %'] < 95.0 else ''
        return [color] * len(row)

    styled_df = serial_df.style.apply(highlight_low_uptime, axis=1).format({'Uptime %': "{:.2f}%"})
    st.dataframe(styled_df, use_container_width=True, height=600)

# --- TAB 8: SEVERE OUTLIERS (>24 Hours) ---
with tab8:
    st.info("**🚨 The Network Friction List:** Below are isolated incidents that resulted in excessive operational downtime (>24 Hours). These specific tickets warrant deep-dive Root Cause Analysis (RCA).")
    
    severe_df = df[df['Actual Down Time Hours'] >= 24.0]
    
    if not severe_df.empty:
        severe_disp = severe_df[['Case Number', 'Site Name', 'Serial No.', 'Family/Line: Name', 'Hardware Sub-Domain', 'Actual Down Time', 'Actual Down Time Hours', 'Subject']].copy()
        severe_disp = severe_disp.sort_values(by='Actual Down Time Hours', ascending=False)
        
        severe_disp['Actual Down Time Hours'] = severe_disp['Actual Down Time Hours'].round(1)
        st.dataframe(severe_disp, use_container_width=True, height=600)
    else:
        st.success("Excellent! No individual breakdowns exceeded 24 hours of continuous downtime based on current filters.")
