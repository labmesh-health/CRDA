import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pdfplumber
import io

# ==========================================
# 1. PAGE CONFIGURATION & CSS
# ==========================================
st.set_page_config(
    page_title="Customer Rexis Diagnostic Dashboard", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Custom CSS for KPI Cards
st.markdown("""
<style>
    .kpi-card {
        background-color: var(--background-color);
        border: 1px solid var(--secondary-background-color);
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
    }
    .kpi-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: #4E79A7;
        margin-bottom: 5px;
    }
    .kpi-label {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-color);
        opacity: 0.8;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔬 Customer Rexis Diagnostic Dashboard")

# Standard Corporate Colors
CORP_BLUE = '#4E79A7'
CORP_RED = '#E15759'
CORP_TEAL = '#76B7B2'
CORP_ORANGE = '#F28E2B'
SAFE_PALETTE = px.colors.qualitative.Safe

# ==========================================
# 2. DATA INGESTION & NLP PROCESSING ENGINE
# ==========================================
@st.cache_data(show_spinner=False)
def load_and_clean_data(file_bytes, file_name):
    file_object = io.BytesIO(file_bytes)
    file_ext = file_name.split('.')[-1].lower()
    
    # Extract data based on file type
    try:
        if file_ext == 'csv':
            file_object.seek(0)
            df = pd.read_csv(file_object)
        elif file_ext in ['xls', 'xlsx']:
            file_object.seek(0)
            df = pd.read_excel(file_object)
        elif file_ext == 'pdf':
            file_object.seek(0)
            with pdfplumber.open(file_object) as pdf:
                all_tables = []
                for page in pdf.pages:
                    table = page.extract_table()
                    if table and len(table) > 1:
                        df_page = pd.DataFrame(table[1:], columns=table[0])
                        all_tables.append(df_page)
                if not all_tables:
                    return pd.DataFrame() # Return empty if no tables
                df = pd.concat(all_tables, ignore_index=True)
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()
        
    df.columns = df.columns.str.strip()
    
    # Clean Site Names
    if 'Account Name' in df.columns and 'City' in df.columns:
        df['Site Name'] = df['Account Name'].astype(str) + " (" + df['City'].astype(str) + ")"
    else:
        df['Site Name'] = df.get('Account Name', 'Unknown Site')

    # Standardize System Down
    if 'System Down Yes/No' in df.columns:
        df['System Down Yes/No'] = df['System Down Yes/No'].fillna('Not Down').apply(
            lambda x: 'Down' if 'yes' in str(x).lower() or 'down' in str(x).lower() else 'Not Down'
        )
    else:
        df['System Down Yes/No'] = 'Unknown'

    # NLP Engine: Extract Parts, Causes, and Domains from Subject
    if 'Subject' in df.columns:
        df['Subject_Clean'] = df['Subject'].fillna('').astype(str).str.lower()
        
        def categorize_hardware(text):
            if any(w in text for w in ['gripper', 'axis', 'movement', 'rack', 'motor']): return 'Kinematic / Robotic'
            if any(w in text for w in ['pressure', 'temperature', 'cooling', 'leak', 'water']): return 'Fluidic / Thermal'
            if any(w in text for w in ['voltage', 'power', 'ups', 'board', 'ac']): return 'Environmental / Power'
            if any(w in text for w in ['rfid', 'calibration', 'sensor', 'error', 'lld']): return 'Analytical / Sensor'
            return 'General Hardware'
            
        df['Hardware Sub-Domain'] = df['Subject_Clean'].apply(categorize_hardware)
        df['Env_Flag'] = df['Hardware Sub-Domain'] == 'Environmental / Power'
        
        def extract_part(text):
            for part in ['gripper', 'motor', 'probe', 'sensor', 'board', 'valve', 'pump', 'thermistor', 'rfid']:
                if part in text: return part.capitalize()
            return 'Module Base'
        df['Failed Component'] = df['Subject_Clean'].apply(extract_part)

        def extract_cause(text):
            for cause in ['jam', 'leak', 'voltage', 'noise', 'calibration', 'pressure', 'clot']:
                if cause in text: return cause.capitalize()
            return 'General Failure'
        df['Failure Cause'] = df['Subject_Clean'].apply(extract_cause)
    else:
        df['Hardware Sub-Domain'] = 'Unknown'
        df['Env_Flag'] = False
        df['Failed Component'] = 'Unknown'
        df['Failure Cause'] = 'Unknown'

    # Calculate Times & SLAs
    for col in ['Date/Time Opened', 'Labour Start Date', 'Labour End Date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')
            
    if 'Labour Start Date' in df.columns and 'Date/Time Opened' in df.columns:
        df['Labour Start Date'] = df['Labour Start Date'].fillna(df['Date/Time Opened'] + pd.Timedelta(hours=2))
    if 'Labour End Date' in df.columns and 'Labour Start Date' in df.columns:
        df['Labour End Date'] = df['Labour End Date'].fillna(df['Labour Start Date'] + pd.Timedelta(hours=4))
    
    if all(c in df.columns for c in ['Labour Start Date', 'Date/Time Opened', 'Labour End Date']):
        df['Resolution_Hours'] = (df['Labour End Date'] - df['Date/Time Opened']).dt.total_seconds() / 3600
        df['Resolution_Hours'] = df['Resolution_Hours'].apply(lambda x: max(x, 0) if pd.notnull(x) else x)
        
        df['Days_to_Resolve'] = (df['Labour End Date'].dt.date - df['Date/Time Opened'].dt.date).apply(lambda x: x.days if pd.notnull(x) else np.nan)
        df['Resolution_Speed'] = df['Days_to_Resolve'].apply(lambda d: "Unknown" if pd.isnull(d) else ("Same Day" if d == 0 else "Next Day" if d == 1 else "Days Later"))

    # Actual Downtime
    if 'Actual Down Time' in df.columns:
        df['Actual Down Time Hours'] = pd.to_timedelta(df['Actual Down Time'].astype(str), errors='coerce').dt.total_seconds() / 3600
        df['Actual Down Time Hours'] = df['Actual Down Time Hours'].fillna(0)
    else:
        df['Actual Down Time Hours'] = 0

    return df

# ==========================================
# 3. APP STARTUP & FILE UPLOAD
# ==========================================
st.sidebar.header("📁 Data Ingestion")
uploaded_file = st.sidebar.file_uploader("Upload Service Log", type=["csv", "xlsx", "xls", "pdf"])

if uploaded_file is None:
    st.info("👋 Welcome! Please upload your service log (CSV, Excel, or PDF) in the sidebar to load the dashboard.")
    st.stop() # App completely halts here until a file is uploaded.

# Process the file once uploaded
with st.spinner("Extracting and processing data..."):
    df_raw = load_and_clean_data(uploaded_file.getvalue(), uploaded_file.name)

if df_raw.empty:
    st.error("Error: Could not extract valid data from the uploaded file. Please ensure it has the correct columns.")
    st.stop()

# ==========================================
# 4. GLOBAL CALCULATIONS & FILTERS
# ==========================================
# Define total_timeline_hours safely
min_date = df_raw['Date/Time Opened'].min()
max_date = df_raw['Date/Time Opened'].max()

if pd.notnull(min_date) and pd.notnull(max_date):
    total_days = (max_date - min_date).days
    total_timeline_hours = max(total_days * 24, 24)
else:
    total_timeline_hours = 3432 # Fallback failsafe

# Sidebar Filters
st.sidebar.header("⚙️ Data Filters")
min_d = min_date.date() if pd.notnull(min_date) else pd.to_datetime('2026-01-01').date()
max_d = max_date.date() if pd.notnull(max_date) else pd.to_datetime('2026-12-31').date()

date_range = st.sidebar.date_input("Date Range", [min_d, max_d], min_value=min_d, max_value=max_d)

if len(date_range) == 2:
    df_filtered = df_raw[(df_raw['Date/Time Opened'].dt.date >= date_range[0]) & (df_raw['Date/Time Opened'].dt.date <= date_range[1])]
else:
    df_filtered = df_raw

if 'Region' in df_filtered.columns:
    sel_reg = st.sidebar.multiselect("Region", options=df_filtered['Region'].dropna().unique(), default=df_filtered['Region'].dropna().unique())
    df_filtered = df_filtered[df_filtered['Region'].isin(sel_reg)]

if 'Type of Complaint' in df_filtered.columns:
    sel_type = st.sidebar.multiselect("Complaint Type", options=df_filtered['Type of Complaint'].dropna().unique(), default=df_filtered['Type of Complaint'].dropna().unique())
    df_filtered = df_filtered[df_filtered['Type of Complaint'].isin(sel_type)]

st.sidebar.markdown("---")
recurring_days = st.sidebar.slider("Flag recurring breakdowns within (Days):", 7, 90, 30, 1)

# Apply final filtered dataset to a clean variable
df = df_filtered

# ==========================================
# 5. DASHBOARD TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 1. Executive Dashboard", 
    "🏭 2. Fleet Reliability", 
    "🔍 3. Root Cause Analytics",
    "🚨 4. Serial Matrix & Outliers"
])

# ------------------------------------------
# TAB 1: EXECUTIVE DASHBOARD
# ------------------------------------------
with tab1:
    st.info("**🤖 Executive Summary:** System health tracking and high-level Service Level Agreement (SLA) compliance.")
    
    # KPI Calculations
    total_cases = len(df)
    total_downtime = df['Actual Down Time Hours'].sum()
    unique_machines = max(df['Serial No.'].nunique(), 1) if 'Serial No.' in df.columns else 1
    
    avg_downtime_per_machine = total_downtime / unique_machines
    uptime_pct = ((total_timeline_hours - avg_downtime_per_machine) / total_timeline_hours) * 100
    
    same_day_pct = 0
    if 'Resolution_Speed' in df.columns and total_cases > 0:
        same_day_cases = len(df[df['Resolution_Speed'] == 'Same Day'])
        same_day_pct = (same_day_cases / total_cases) * 100
        
    avg_downtime_per_case = df['Actual Down Time Hours'].mean() if total_cases > 0 else 0

    # Draw KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f"<div class='kpi-card'><div class='kpi-value'>{total_cases}</div><div class='kpi-label'>Total Support Cases</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='kpi-card'><div class='kpi-value'>{uptime_pct:.2f}%</div><div class='kpi-label'>Network Uptime</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='kpi-card'><div class='kpi-value'>{same_day_pct:.1f}%</div><div class='kpi-label'>Same-Day Fix Rate</div></div>", unsafe_allow_html=True)
    col4.markdown(f"<div class='kpi-card'><div class='kpi-value' style='color:{CORP_RED};'>{avg_downtime_per_case:.1f}h</div><div class='kpi-label'>Avg Downtime / Case</div></div>", unsafe_allow_html=True)

    # Charts Row
    col_chart1, col_chart2, col_chart3 = st.columns([1.5, 1, 1.5])
    
    with col_chart1:
        if 'Region' in df.columns:
            reg_df = df['Region'].value_counts().reset_index()
            reg_df.columns = ['Region', 'Cases']
            fig_bar = px.bar(reg_df, x='Region', y='Cases', title="Geographic Case Load", text_auto=True, color_discrete_sequence=[CORP_BLUE])
            fig_bar.update_traces(textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_chart2:
        if 'Type of Complaint' in df.columns:
            fig_donut = px.pie(df, names='Type of Complaint', hole=0.5, title="Issue Breakdown", color_discrete_sequence=[CORP_TEAL, CORP_ORANGE, CORP_BLUE])
            fig_donut.update_traces(textinfo='percent+label', textposition='inside')
            st.plotly_chart(fig_donut, use_container_width=True)
        
    with col_chart3:
        if 'Opened_Date' in df.columns and 'System Down Yes/No' in df.columns:
            daily_df = df.groupby('Opened_Date').agg(
                Total=('Case Number', 'count'), 
                Down=('System Down Yes/No', lambda x: (x == 'Down').sum())
            ).reset_index()
            
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=daily_df['Opened_Date'], y=daily_df['Total'], mode='lines+markers', name='Total Opened', line=dict(color=CORP_BLUE)))
            fig_trend.add_trace(go.Scatter(x=daily_df['Opened_Date'], y=daily_df['Down'], mode='lines+markers', name='Systems Down', line=dict(color=CORP_RED)))
            fig_trend.update_layout(title="Daily Open Cases vs. System Downs", xaxis_title="Date")
            st.plotly_chart(fig_trend, use_container_width=True)

# ------------------------------------------
# TAB 2: NETWORK & FLEET RELIABILITY
# ------------------------------------------
with tab2:
    st.info("**🤖 Fleet Insights:** Identifies problematic product lines and highest-risk customer sites. ⚠️ indicates environmental risks.")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if 'Family/Line: Name' in df.columns:
            fam_df = df.groupby('Family/Line: Name').size().reset_index(name='Complaints').sort_values('Complaints', ascending=False).head(10)
            fam_df['Cum%'] = fam_df['Complaints'].cumsum() / fam_df['Complaints'].sum() * 100
            
            fig_fam = go.Figure()
            fig_fam.add_trace(go.Bar(x=fam_df['Family/Line: Name'], y=fam_df['Complaints'], marker_color=CORP_BLUE, name="Cases"))
            fig_fam.add_trace(go.Scatter(x=fam_df['Family/Line: Name'], y=fam_df['Cum%'], yaxis='y2', line=dict(color=CORP_RED), name="Cum%"))
            fig_fam.update_layout(title="Top Products (Pareto)", yaxis2=dict(overlaying='y', side='right', range=[0, 115]), showlegend=False)
            st.plotly_chart(fig_fam, use_container_width=True)

    with col_p2:
        if 'Site Name' in df.columns and 'Type of Complaint' in df.columns:
            hw_df = df[df['Type of Complaint'].str.contains('Hardware', case=False, na=False)]
            if not hw_df.empty:
                env_sites = hw_df[hw_df['Env_Flag'] == True]['Site Name'].unique()
                site_df = hw_df.groupby('Site Name').size().reset_index(name='Complaints').sort_values('Complaints', ascending=False).head(15)
                site_df['Site Display'] = site_df['Site Name'].apply(lambda x: f"⚠️ {x}" if x in env_sites else x)
                site_df['Cum%'] = site_df['Complaints'].cumsum() / site_df['Complaints'].sum() * 100
                
                fig_site = go.Figure()
                fig_site.add_trace(go.Bar(x=site_df['Site Display'], y=site_df['Complaints'], marker_color=CORP_BLUE, name="Cases"))
                fig_site.add_trace(go.Scatter(x=site_df['Site Display'], y=site_df['Cum%'], yaxis='y2', line=dict(color=CORP_RED), name="Cum%"))
                fig_site.update_layout(title="Top Sites Hardware Issues (Pareto)", yaxis2=dict(overlaying='y', side='right', range=[0, 115]), showlegend=False)
                st.plotly_chart(fig_site, use_container_width=True)

    if 'City' in df.columns and 'Family/Line: Name' in df.columns:
        city_df = df.groupby(['City', 'Family/Line: Name']).size().reset_index(name='Total')
        fig_city = px.bar(city_df.sort_values('Total', ascending=False).head(40), x='City', y='Total', color='Family/Line: Name', title="Citywise Instrument Breakdowns (Stacked)", color_discrete_sequence=SAFE_PALETTE)
        st.plotly_chart(fig_city, use_container_width=True)

# ------------------------------------------
# TAB 3: ROOT CAUSE ANALYTICS (RCA)
# ------------------------------------------
with tab3:
    st.info("**🤖 Diagnostic NLP Engine:** Text-mining ticket subjects to isolate the exact Component failing and the underlying Cause.")
    
    col_b, col_r = st.columns([1, 1.5])
    with col_b:
        if 'Hardware Sub-Domain' in df.columns:
            bub_df = df.groupby('Hardware Sub-Domain').agg(
                Freq=('Case Number', 'count'), 
                AvgD=('Actual Down Time Hours', 'mean'), 
                TotD=('Actual Down Time Hours', 'sum')
            ).reset_index()
            
            fig_bub = px.scatter(bub_df, x='Freq', y='AvgD', size='TotD', color='Hardware Sub-Domain', title="Impact vs Frequency", size_max=40, color_discrete_sequence=SAFE_PALETTE)
            st.plotly_chart(fig_bub, use_container_width=True)
            
    with col_r:
        if 'Hardware Sub-Domain' in df.columns:
            cr1, cr2 = st.columns(2)
            hw_only = df[df['Hardware Sub-Domain'] != 'Unknown']
            
            with cr1:
                parts = hw_only['Failed Component'].value_counts().reset_index().head(5)
                parts.columns = ['Part', 'Count']
                fig_p = px.bar(parts, x='Count', y='Part', orientation='h', title="Top Failed Parts", color_discrete_sequence=[CORP_BLUE])
                fig_p.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_p, use_container_width=True)
                
            with cr2:
                causes = hw_only['Failure Cause'].value_counts().reset_index().head(5)
                causes.columns = ['Cause', 'Count']
                fig_c = px.bar(causes, x='Count', y='Cause', orientation='h', title="Top Failure Causes", color_discrete_sequence=[CORP_ORANGE])
                fig_c.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_c, use_container_width=True)

# ------------------------------------------
# TAB 4: SERIAL MATRIX & OUTLIERS
# ------------------------------------------
with tab4:
    col_out1, col_out2 = st.columns(2)
    
    with col_out1:
        st.warning(f"🍋 **Lemon Tracker:** Serials breaking repeatedly within {recurring_days} Days.")
        if 'Serial No.' in df.columns and 'Date/Time Opened' in df.columns:
            df_sorted = df.sort_values(['Serial No.', 'Date/Time Opened'])
            df_sorted['Days_Diff'] = df_sorted.groupby('Serial No.')['Date/Time Opened'].diff().dt.days
            rec_df = df_sorted[df_sorted['Days_Diff'] <= recurring_days]
            
            if not rec_df.empty:
                rec_summary = rec_df.groupby(['Serial No.', 'Site Name']).agg(Repeats=('Case Number', 'count')).reset_index().sort_values('Repeats', ascending=False)
                st.dataframe(rec_summary, use_container_width=True)
            else:
                st.success("No recurring issues found.")

    with col_out2:
        st.error("🚨 **Severe Outliers:** Single incidents causing >24h downtime.")
        if 'Actual Down Time Hours' in df.columns:
            severe_mask = df['Actual Down Time Hours'].fillna(0) >= 24.0
            severe_df = df[severe_mask].sort_values('Actual Down Time Hours', ascending=False)
            
            if not severe_df.empty:
                st.dataframe(severe_df[['Case Number', 'Serial No.', 'Site Name', 'Actual Down Time Hours']], use_container_width=True)
            else:
                st.success("No severe outliers found.")

    st.markdown("---")
    st.subheader("🔍 Complete Serial Number Uptime Matrix")
    
    if all(c in df.columns for c in ['Serial No.', 'Site Name', 'Family/Line: Name', 'Actual Down Time Hours']):
        matrix_df = df.groupby(['Serial No.', 'Site Name', 'Family/Line: Name'], dropna=False).agg(
            Total_Cases=('Case Number', 'count'), 
            Down_Hours=('Actual Down Time Hours', 'sum')
        ).reset_index()
        
        if not matrix_df.empty:
            matrix_df['Uptime %'] = ((total_timeline_hours - matrix_df['Down_Hours']) / total_timeline_hours) * 100
            matrix_df = matrix_df.sort_values('Total_Cases', ascending=False)
            
            def highlight_row(row):
                color = 'background-color: rgba(225, 87, 89, 0.15)' if pd.notnull(row['Uptime %']) and row['Uptime %'] < 95.0 else ''
                return [color] * len(row)

            st.dataframe(matrix_df.style.apply(highlight_row, axis=1).format({'Uptime %': "{:.2f}%", 'Down_Hours': "{:.1f}"}), use_container_width=True, height=500)
        else:
            st.warning("No data matches current filters.")
    else:
        st.warning("Missing columns for Serial Matrix.")
