import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pdfplumber
import io

# ==========================================
# PAGE CONFIGURATION & CUSTOM CSS (Pillowed Cards)
# ==========================================
st.set_page_config(page_title="Customer Rexis Diagnostic Dashboard", layout="wide", initial_sidebar_state="expanded")

# Inject Custom CSS for the pillowed/shadowed KPI Cards supporting Dark/Light Mode
st.markdown("""
<style>
    .kpi-card {
        background-color: var(--background-color);
        border: 1px solid var(--secondary-background-color);
        border-radius: 20px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.12), 0 4px 8px rgba(0,0,0,0.06);
        padding: 25px 15px;
        text-align: center;
        margin-bottom: 20px;
        transition: transform 0.3s ease;
    }
    .kpi-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 25px rgba(0,0,0,0.18), 0 5px 10px rgba(0,0,0,0.08);
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
        opacity: 0.7;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔬 Customer Rexis Diagnostic Dashboard")

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

    # 3. ADVANCED NLP TEXT MINING (Sub-Domains, Parts, Causes, Fixes)
    if 'Subject' in df.columns:
        df['Subject_Clean'] = df['Subject'].fillna('').astype(str).str.lower()
        
        # Sub-Domain
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
                return 'General Hardware'
        df['Hardware Sub-Domain'] = df['Subject_Clean'].apply(categorize_hardware)
        df['Env_Flag'] = df['Hardware Sub-Domain'] == 'Environmental / Power'

        # Extracted Part
        def extract_part(text):
            parts = ['gripper', 'motor', 'probe', 'sensor', 'lamp', 'board', 'valve', 'pump', 'rack', 'disk', 'thermistor', 'rfid', 'incubator', 'pipetter']
            found = [p.capitalize() for p in parts if p in text]
            return found[0] if found else 'Module Base'
        df['Failed Component'] = df['Subject_Clean'].apply(extract_part)

        # Extracted Cause
        def extract_cause(text):
            causes = ['jam', 'leak', 'temperature', 'voltage', 'noise', 'calibration', 'outlier', 'malfunction', 'clot', 'pressure', 'crash']
            found = [c.capitalize() for c in causes if c in text]
            return found[0] if found else 'General Failure'
        df['Failure Cause'] = df['Subject_Clean'].apply(extract_cause)

        # Extracted Fix (if Remarks exist, search there too)
        remarks_col = 'Remarks' if 'Remarks' in df.columns else 'Subject'
        df['Remarks_Clean'] = df[remarks_col].fillna('').astype(str).str.lower()
        def extract_fix(row):
            combined_text = row['Subject_Clean'] + " " + row['Remarks_Clean']
            fixes = ['replace', 'clean', 'recalibrate', 'reset', 'update', 'flush', 'adjust', 'align', 'restart']
            found = [f.capitalize() for f in fixes if f in combined_text]
            return found[0] if found else 'Standard PM'
        df['Prescribed Fix'] = df.apply(extract_fix, axis=1)
        
    else:
        df['Hardware Sub-Domain'] = 'Unknown'
        df['Env_Flag'] = False
        df['Failed Component'] = 'Unknown'
        df['Failure Cause'] = 'Unknown'
        df['Prescribed Fix'] = 'Unknown'

    # 4. DATE FORMATS & MISSING DATA
    for col in ['Date/Time Opened', 'Labour Start Date', 'Labour End Date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')
            
    if 'Labour Start Date' in df.columns and 'Date/Time Opened' in df.columns:
        df['Labour Start Date'] = df['Labour Start Date'].fillna(df['Date/Time Opened'] + pd.Timedelta(hours=2))
    if 'Labour End Date' in df.columns and 'Labour Start Date' in df.columns:
        df['Labour End Date'] = df['Labour End Date'].fillna(df['Labour Start Date'] + pd.Timedelta(hours=4))
    
    # 5. TIME & SLA CALCULATION
    if all(c in df.columns for c in ['Labour Start Date', 'Date/Time Opened', 'Labour End Date']):
        df['Response_Hours'] = (df['Labour Start Date'] - df['Date/Time Opened']).dt.total_seconds() / 3600
        df['Resolution_Hours'] = (df['Labour End Date'] - df['Date/Time Opened']).dt.total_seconds() / 3600
        df['Response_Hours'] = df['Response_Hours'].apply(lambda x: max(x, 0) if pd.notnull(x) else x)
        df['Resolution_Hours'] = df['Resolution_Hours'].apply(lambda x: max(x, 0) if pd.notnull(x) else x)
        
        df['Opened_Date'] = df['Date/Time Opened'].dt.date
        df['Resolved_Date'] = df['Labour End Date'].dt.date
        df['Days_to_Resolve'] = (df['Resolved_Date'] - df['Opened_Date']).apply(lambda x: x.days if pd.notnull(x) else np.nan)
        
        df['Resolution_Speed'] = df['Days_to_Resolve'].apply(lambda d: "Unknown" if pd.isnull(d) else ("Same Day" if d == 0 else ("Next Day" if d == 1 else f"{int(d)} Days Later")))
        
        def categorize_time(hours):
            if pd.isnull(hours): return "Unknown"
            if hours <= 24: return "< 24 Hours"
            elif hours <= 48: return "24 - 48 Hours"
            elif hours <= 72: return "48 - 72 Hours"
            elif hours <= 96: return "72 - 96 Hours"
            else: return "> 96 Hours"
            
        df['Resolution Bucket'] = df['Resolution_Hours'].apply(categorize_time)

    if 'Actual Down Time' in df.columns:
        df['Actual Down Time Hours'] = pd.to_timedelta(df['Actual Down Time'].astype(str), errors='coerce').dt.total_seconds() / 3600
        df['Actual Down Time Hours'] = df['Actual Down Time Hours'].fillna(0)

    return df

if uploaded_file is None:
    st.info("👋 Welcome! Please upload your service log (CSV, Excel, or PDF) in the sidebar.")
    st.stop()

with st.spinner("Extracting and processing data..."):
    df_raw = load_and_clean_data(uploaded_file.getvalue(), uploaded_file.name)

min_date = df_raw['Date/Time Opened'].min()
max_date = df_raw['Date/Time Opened'].max()
total_timeline_hours = max(((max_date - min_date).days if pd.notnull(max_date) else 143) * 24, 24)

# ==========================================
# SIDEBAR FILTERS
# ==========================================
st.sidebar.header("⚙️ Flexible Data Filters")
min_d, max_d = min_date.date(), max_date.date()
date_range = st.sidebar.date_input("Select Date Range", [min_d, max_d], min_value=min_d, max_value=max_d)

df = df_raw[(df_raw['Date/Time Opened'].dt.date >= date_range[0]) & (df_raw['Date/Time Opened'].dt.date <= date_range[1])] if len(date_range) == 2 else df_raw

selected_region = st.sidebar.multiselect("Region", options=df_raw['Region'].dropna().unique(), default=df_raw['Region'].dropna().unique())
selected_type = st.sidebar.multiselect("Complaint Type", options=df_raw['Type of Complaint'].dropna().unique(), default=df_raw['Type of Complaint'].dropna().unique())

df = df[df['Region'].isin(selected_region) & df['Type of Complaint'].isin(selected_type)]

st.sidebar.markdown("---")
recurring_days = st.sidebar.slider("Flag recurring breakdowns within (Days):", 7, 90, 30, 1)

# ==========================================
# CONSOLIDATED DASHBOARD TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 1. Executive Dashboard", 
    "🏭 2. Network & Fleet Reliability", 
    "🔍 3. Root Cause Analytics (RCA)",
    "🚨 4. Serial Matrix & Outliers"
])

# --- TAB 1: EXECUTIVE DASHBOARD ---
with tab1:
    st.info("**🤖 Executive Summary:** System health tracking and high-level Service Level Agreement (SLA) compliance.")
    
    # Calculate KPIs safely
    num_unique_machines = max(df['Serial No.'].nunique(), 1) if 'Serial No.' in df.columns else 1
    total_down = df['Actual Down Time Hours'].sum() if 'Actual Down Time Hours' in df.columns else 0
    uptime_pct = ((total_timeline_hours - (total_down / num_unique_machines)) / total_timeline_hours) * 100
    
    same_day_pct = 0
    if 'Resolution_Speed' in df.columns:
        same_day_pct = (len(df[df['Resolution_Speed'] == 'Same Day']) / max(len(df), 1)) * 100
        
    avg_downtime = df['Actual Down Time Hours'].mean() if 'Actual Down Time Hours' in df.columns else 0

    # PILLOWED KPI CARDS (HTML)
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f"<div class='kpi-card'><div class='kpi-value'>{len(df)}</div><div class='kpi-label'>Total Support Cases</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='kpi-card'><div class='kpi-value'>{uptime_pct:.2f}%</div><div class='kpi-label'>Network Uptime (24h)</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='kpi-card'><div class='kpi-value'>{same_day_pct:.1f}%</div><div class='kpi-label'>Same-Day Fix Rate</div></div>", unsafe_allow_html=True)
    col4.markdown(f"<div class='kpi-card'><div class='kpi-value' style='color:{CORP_RED};'>{avg_downtime:.1f}h</div><div class='kpi-label'>Avg Downtime / Case</div></div>", unsafe_allow_html=True)

    col_map, col_donut, col_trend = st.columns([1.5, 1, 1.5])
    
    with col_map:
        if 'Region' in df.columns:
            reg_counts = df['Region'].value_counts().reset_index().rename(columns={'index':'Region', 'Region':'Complaints'})
            fig_bar = px.bar(reg_counts, x='Region', y='Complaints', title="Geographic Case Load", text_auto=True, color_discrete_sequence=[CORP_BLUE])
            fig_bar.update_traces(textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True, theme="streamlit")

    with col_donut:
        if 'Type of Complaint' in df.columns:
            fig_donut = px.pie(df, names='Type of Complaint', hole=0.5, title="Issue Breakdown", color_discrete_sequence=[CORP_TEAL, CORP_ORANGE, CORP_BLUE])
            fig_donut.update_traces(textinfo='percent+label', textposition='inside')
            st.plotly_chart(fig_donut, use_container_width=True, theme="streamlit")
        
    with col_trend:
        if 'Opened_Date' in df.columns and 'System Down Yes/No' in df.columns:
            daily_df = df.groupby('Opened_Date').agg(Total=('Case Number', 'count'), Down=('System Down Yes/No', lambda x: (x == 'Down').sum())).reset_index()
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=daily_df['Opened_Date'], y=daily_df['Total'], mode='lines+markers', name='Total Opened', line=dict(color=CORP_BLUE)))
            fig_trend.add_trace(go.Scatter(x=daily_df['Opened_Date'], y=daily_df['Down'], mode='lines+markers', name='Systems Down', line=dict(color=CORP_RED)))
            fig_trend.update_layout(title="Daily Open Cases vs. System Downs", xaxis_title="Date", margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_trend, use_container_width=True, theme="streamlit")

# --- TAB 2: NETWORK & FLEET RELIABILITY ---
with tab2:
    st.info("**🤖 Fleet Insights:** Identifies problematic product lines, highest-risk customer sites (80/20 rule), and citywide failure density. ⚠️ indicates environmental risks like voltage or temperature drops.")
    
    col_pareto1, col_pareto2 = st.columns(2)
    with col_pareto1:
        if 'Family/Line: Name' in df.columns:
            # Product Family Pareto
            fam_counts = df.groupby('Family/Line: Name').size().reset_index(name='Complaints').sort_values(by='Complaints', ascending=False).head(10)
            fam_counts['Cum%'] = fam_counts['Complaints'].cumsum() / fam_counts['Complaints'].sum() * 100
            fig_fam = go.Figure()
            fig_fam.add_trace(go.Bar(x=fam_counts['Family/Line: Name'], y=fam_counts['Complaints'], name="Complaints", marker_color=CORP_BLUE, text=fam_counts['Complaints'], textposition='auto'))
            fig_fam.add_trace(go.Scatter(x=fam_counts['Family/Line: Name'], y=fam_counts['Cum%'], name="Cumulative %", yaxis='y2', mode='lines+markers+text', text=fam_counts['Cum%'].round(1).astype(str)+'%', textposition='top center', line=dict(color=CORP_RED)))
            fig_fam.update_layout(title="Product Line Breakdown (Pareto)", yaxis2=dict(overlaying='y', side='right', range=[0, 115]))
            st.plotly_chart(fig_fam, use_container_width=True, theme="streamlit")

    with col_pareto2:
        if 'Type of Complaint' in df.columns and 'Site Name' in df.columns:
            # Top Sites Pareto (80/20) with Env Flags
            hw_df = df[df['Type of Complaint'].str.contains('Hardware', case=False, na=False)]
            if not hw_df.empty:
                env_sites = hw_df[hw_df['Env_Flag'] == True]['Site Name'].unique()
                acc_df = hw_df.groupby('Site Name').size().reset_index(name='Complaints').sort_values(by='Complaints', ascending=False).head(15)
                acc_df['Site Display'] = acc_df['Site Name'].apply(lambda x: f"⚠️ {x}" if x in env_sites else x)
                acc_df['Cum%'] = acc_df['Complaints'].cumsum() / acc_df['Complaints'].sum() * 100
                
                fig_site = go.Figure()
                fig_site.add_trace(go.Bar(x=acc_df['Site Display'], y=acc_df['Complaints'], name="Hardware Complaints", marker_color=CORP_BLUE, text=acc_df['Complaints'], textposition='auto'))
                fig_site.add_trace(go.Scatter(x=acc_df['Site Display'], y=acc_df['Cum%'], name="Cum %", yaxis='y2', mode='lines+markers', line=dict(color=CORP_RED)))
                fig_site.update_layout(title="Top 15 Problematic Customer Sites (Hardware)", yaxis2=dict(overlaying='y', side='right', range=[0, 115]), xaxis_tickangle=-45)
                st.plotly_chart(fig_site, use_container_width=True, theme="streamlit")

    if 'City' in df.columns and 'Family/Line: Name' in df.columns:
        # Citywise Stacked
        city_inst = df.groupby(['City', 'Family/Line: Name']).size().reset_index(name='Total')
        fig_city = px.bar(city_inst.sort_values(by='Total', ascending=False).head(40), x='City', y='Total', color='Family/Line: Name', title="Citywise Instrument Breakdowns (Stacked)", text_auto=True, color_discrete_sequence=SAFE_PALETTE)
        st.plotly_chart(fig_city, use_container_width=True, theme="streamlit")

# --- TAB 3: ROOT CAUSE ANALYTICS (RCA) ---
with tab3:
    st.info("**🤖 Diagnostic NLP Engine:** Text-mining ticket subjects to isolate the exact Component failing, the underlying Cause, and the most frequent field Fix.")
    
    col_bubble, col_rca = st.columns([1, 1.5])
    with col_bubble:
        if 'Hardware Sub-Domain' in df.columns:
            bubble_df = df.groupby('Hardware Sub-Domain').agg(Freq=('Case Number', 'count'), Avg_Down=('Actual Down Time Hours', 'mean'), Tot_Down=('Actual Down Time Hours', 'sum')).reset_index()
            fig_bubble = px.scatter(bubble_df, x='Freq', y='Avg_Down', size='Tot_Down', color='Hardware Sub-Domain', title="Impact vs. Frequency Quadrant", labels={"Freq": "Breakdown Count", "Avg_Down": "Avg Downtime (Hrs)"}, size_max=50, color_discrete_sequence=SAFE_PALETTE)
            st.plotly_chart(fig_bubble, use_container_width=True, theme="streamlit")

    with col_rca:
        if 'Hardware Sub-Domain' in df.columns:
            # Top Parts, Causes, Fixes Sub-columns
            hw_filter = df[df['Hardware Sub-Domain'] != 'Unknown']
            r1, r2, r3 = st.columns(3)
            
            # 1. Top Parts
            part_df = hw_filter['Failed Component'].value_counts().reset_index().head(6)
            part_df.columns = ['Part', 'Count']
            part_df = part_df[part_df['Part'] != 'Module Base'] # Hide defaults if others exist
            fig_p = px.bar(part_df, x='Count', y='Part', orientation='h', title="Top Failed Parts", text_auto=True, color_discrete_sequence=[CORP_BLUE])
            fig_p.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=30, b=0))
            r1.plotly_chart(fig_p, use_container_width=True, theme="streamlit")

            # 2. Top Causes
            cause_df = hw_filter['Failure Cause'].value_counts().reset_index().head(6)
            cause_df.columns = ['Cause', 'Count']
            cause_df = cause_df[cause_df['Cause'] != 'General Failure']
            fig_c = px.bar(cause_df, x='Count', y='Cause', orientation='h', title="Top Failure Modes", text_auto=True, color_discrete_sequence=[CORP_ORANGE])
            fig_c.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=30, b=0))
            r2.plotly_chart(fig_c, use_container_width=True, theme="streamlit")

            # 3. Top Fixes
            fix_df = hw_filter['Prescribed Fix'].value_counts().reset_index().head(6)
            fix_df.columns = ['Fix', 'Count']
            fix_df = fix_df[fix_df['Fix'] != 'Standard PM']
            fig_f = px.bar(fix_df, x='Count', y='Fix', orientation='h', title="Top Prescribed Fixes", text_auto=True, color_discrete_sequence=[CORP_TEAL])
            fig_f.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=30, b=0))
            r3.plotly_chart(fig_f, use_container_width=True, theme="streamlit")

# --- TAB 4: SERIAL MATRIX & OUTLIERS ---
with tab4:
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.warning(f"**🍋 Lemon Tracker:** Serial Numbers breaking down repeatedly within **{recurring_days} Days**.")
        if 'Serial No.' in df.columns and 'Date/Time Opened' in df.columns:
            df_sort = df.sort_values(by=['Serial No.', 'Date/Time Opened'])
            df_sort['Days_Since_Last'] = df_sort.groupby('Serial No.')['Date/Time Opened'].diff().dt.days
            recurring = df_sort[df_sort['Days_Since_Last'] <= recurring_days]
            if
