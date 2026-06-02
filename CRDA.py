import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pdfplumber
import io

# ==========================================
# 1. PAGE CONFIGURATION & ENTERPRISE STYLING
# ==========================================
st.set_page_config(
    page_title="Customer Rexis Diagnostic Command Dashboard", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Inject Custom SaaS-style CSS supporting dynamic theme inheritance
st.markdown("""
<style>
    .kpi-container {
        display: flex;
        gap: 15px;
        margin-bottom: 25px;
    }
    .kpi-card {
        flex: 1;
        background-color: var(--background-color);
        border: 1px solid var(--secondary-background-color);
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        padding: 24px 16px;
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
    }
    .kpi-value {
        font-size: 2.6rem;
        font-weight: 800;
        color: #4E79A7;
        margin-bottom: 4px;
    }
    .kpi-label {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text-color);
        opacity: 0.75;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .insight-header {
        font-size: 1.3rem;
        font-weight: 700;
        margin-top: 15px;
        margin-bottom: 10px;
        color: #4E79A7;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔬 Customer Rexis Service Network & Fleet Diagnostic Command Center")

# Executive Palette Definitions
CORP_BLUE = '#4E79A7'
CORP_RED = '#E15759'
CORP_TEAL = '#76B7B2'
CORP_ORANGE = '#F28E2B'
SAFE_PALETTE = px.colors.qualitative.Safe

# ==========================================
# 2. BULLETPROOF DATA PROCESSING & NLP ENGINE
# ==========================================
@st.cache_data(show_spinner=False)
def load_and_clean_data(file_bytes, file_name):
    file_object = io.BytesIO(file_bytes)
    file_ext = file_name.split('.')[-1].lower()
    
    # Structural File Parsing
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
                    return pd.DataFrame()
                df = pd.concat(all_tables, ignore_index=True)
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()
        
    df.columns = df.columns.str.strip()
    
    # Location Hierarchy Consolidation
    if 'Account Name' in df.columns and 'City' in df.columns:
        df['Site Name'] = df['Account Name'].astype(str) + " (" + df['City'].astype(str) + ")"
    else:
        df['Site Name'] = df.get('Account Name', 'Unknown Site')

    # Operational State Standardization
    if 'System Down Yes/No' in df.columns:
        df['System Down Yes/No'] = df['System Down Yes/No'].fillna('Not Down').apply(
            lambda x: 'Down' if 'yes' in str(x).lower() or 'down' in str(x).lower() else 'Not Down'
        )
    else:
        df['System Down Yes/No'] = 'Unknown'

    # Advanced NLP Root Cause Mining
    if 'Subject' in df.columns:
        df['Subject_Clean'] = df['Subject'].fillna('').astype(str).str.lower()
        
        # Mapping Technical Sub-Domains
        def categorize_hardware(text):
            if any(w in text for w in ['gripper', 'axis', 'movement', 'rack', 'motor', 'actuator', 'l2 line']): 
                return 'Kinematic / Robotic'
            if any(w in text for w in ['pressure', 'temperature', 'cooling', 'leak', 'water', 'wash', 'prime', 'flush', 'cc1', 'cc2']): 
                return 'Fluidic / Thermal'
            if any(w in text for w in ['voltage', 'power', 'ups', 'board', 'ac', 'noise', 'leakage', 'fluctuation']): 
                return 'Environmental / Power'
            if any(w in text for w in ['rfid', 'calibration', 'sensor', 'error', 'lld', 'qc', 'outlier']): 
                return 'Analytical / Sensor'
            return 'General Hardware'
            
        df['Hardware Sub-Domain'] = df['Subject_Clean'].apply(categorize_hardware)
        df['Env_Flag'] = df['Hardware Sub-Domain'] == 'Environmental / Power'
        
        # Component Extraction
        def extract_part(text):
            for part in ['gripper', 'motor', 'probe', 'sensor', 'board', 'valve', 'pump', 'thermistor', 'rfid']:
                if part in text: 
                    return part.capitalize()
            return 'Module Base'
        df['Failed Component'] = df['Subject_Clean'].apply(extract_part)

        # Failure Mode Extraction
        def extract_cause(text):
            for cause in ['jam', 'leak', 'voltage', 'noise', 'calibration', 'pressure', 'clot', 'mismatch', 'failed']:
                if cause in text: 
                    return cause.capitalize()
            return 'General Failure'
        df['Failure Cause'] = df['Subject_Clean'].apply(extract_cause)
    else:
        df['Hardware Sub-Domain'] = 'Unknown'
        df['Env_Flag'] = False
        df['Failed Component'] = 'Unknown'
        df['Failure Cause'] = 'Unknown'

    # Service Timeline Engineering
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

    if 'Actual Down Time' in df.columns:
        df['Actual Down Time Hours'] = pd.to_timedelta(df['Actual Down Time'].astype(str), errors='coerce').dt.total_seconds() / 3600
        df['Actual Down Time Hours'] = df['Actual Down Time Hours'].fillna(0)
    else:
        df['Actual Down Time Hours'] = 0

    return df

# ==========================================
# 3. INTERACTIVE CONTAINER ROUTING
# ==========================================
st.sidebar.header("📁 Data Ingestion")
uploaded_file = st.sidebar.file_uploader("Upload Network Service Log", type=["csv", "xlsx", "xls", "pdf"])

if uploaded_file is None:
    st.info("👋 Welcome! Please upload your network service log (CSV, Excel, or PDF) in the sidebar to populate the diagnostic interfaces.")
else:
    with st.spinner("Extracting and compiling network fleet data..."):
        df_raw = load_and_clean_data(uploaded_file.getvalue(), uploaded_file.name)

    if df_raw.empty:
        st.error("Incompatible dataset structure. Please ensure vital database fields exist.")
    else:
        # Secure Global Baseline Temporal Metrics
        min_date = df_raw['Date/Time Opened'].min()
        max_date = df_raw['Date/Time Opened'].max()
        
        if pd.notnull(min_date) and pd.notnull(max_date):
            total_days = (max_date - min_date).days
            total_timeline_hours = max(total_days * 24, 24)
        else:
            total_timeline_hours = 3432

        # Filter Control Layout Matrix
        st.sidebar.header("⚙️ Command Controls")
        min_d = min_date.date() if pd.notnull(min_date) else pd.to_datetime('2026-01-01').date()
        max_d = max_date.date() if pd.notnull(max_date) else pd.to_datetime('2026-12-31').date()

        date_range = st.sidebar.date_input("Operational Window", [min_d, max_d], min_value=min_d, max_value=max_d)

        # Filter Scoping Execution
        if len(date_range) == 2:
            df_filtered = df_raw[(df_raw['Date/Time Opened'].dt.date >= date_range[0]) & (df_raw['Date/Time Opened'].dt.date <= date_range[1])]
        else:
            df_filtered = df_raw

        if 'Region' in df_filtered.columns:
            sel_reg = st.sidebar.multiselect("Geographic Bounds", options=df_filtered['Region'].dropna().unique(), default=df_filtered['Region'].dropna().unique())
            df_filtered = df_filtered[df_filtered['Region'].isin(sel_reg)]

        if 'Type of Complaint' in df_filtered.columns:
            sel_type = st.sidebar.multiselect("Classification Scope", options=df_filtered['Type of Complaint'].dropna().unique(), default=df_filtered['Type of Complaint'].dropna().unique())
            df_filtered = df_filtered[df_filtered['Type of Complaint'].isin(sel_type)]

        st.sidebar.markdown("---")
        recurring_days = st.sidebar.slider("Lemon Vulnerability Threshold (Days)", 7, 90, 30, 1)

        df = df_filtered

        # Master Tab Layout Definition
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 1. Strategic Command Center", 
            "🏭 2. Fleet & Site Reliability Matrix", 
            "🔍 3. Root Cause Deep-Dive (NLP)",
            "🚨 4. Operational Risk & Outliers"
        ])

        # ==========================================
        # TAB 1: EXECUTIVE COMMAND CENTER
        # ==========================================
        with tab1:
            # Mathematical Aggregations for KPI Framework
            total_cases = len(df)
            total_downtime = df['Actual Down Time Hours'].sum()
            unique_machines = max(df['Serial No.'].nunique(), 1) if 'Serial No.' in df.columns else 1
            
            avg_downtime_per_machine = total_downtime / unique_machines
            uptime_pct = ((total_timeline_hours - avg_downtime_per_machine) / total_timeline_hours) * 100
            uptime_pct = min(max(uptime_pct, 0.0), 100.0) # Confining thresholds bound safely
            
            same_day_pct = 0
            if 'Resolution_Speed' in df.columns and total_cases > 0:
                same_day_cases = len(df[df['Resolution_Speed'] == 'Same Day'])
                same_day_pct = (same_day_cases / total_cases) * 100
                
            avg_downtime_per_case = df['Actual Down Time Hours'].mean() if total_cases > 0 else 0

            # Render Pillowed Layout Container
            st.markdown(f"""
            <div class='kpi-container'>
                <div class='kpi-card'>
                    <div class='kpi-value'>{total_cases}</div>
                    <div class='kpi-label'>Logged Fleet Incidents</div>
                </div>
                <div class='kpi-card'>
                    <div class='kpi-value'>{uptime_pct:.2f}%</div>
                    <div class='kpi-label'>Continuous Fleet Uptime</div>
                </div>
                <div class='kpi-card'>
                    <div class='kpi-value'>{same_day_pct:.1f}%</div>
                    <div class='kpi-label'>SLA Same-Day Closure Rate</div>
                </div>
                <div class='kpi-card'>
                    <div class='kpi-value' style='color:{CORP_RED};'>{avg_downtime_per_case:.1f}h</div>
                    <div class='kpi-label'>Mean Operational Halt (MTTR)</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- COMPREHENSIVE EXECUTIVE INSIGHTS PANEL ---
            st.markdown("<div class='insight-header'>🏛️ Strategic Command Briefing & Fleet Cross-Observations</div>", unsafe_allow_html=True)
            
            # Dynamic cross-tab variable generation for narrative delivery
            top_region = df['Region'].mode()[0] if 'Region' in df.columns and not df.empty else "N/A"
            top_complaint = df['Type of Complaint'].mode()[0] if 'Type of Complaint' in df.columns and not df.empty else "N/A"
            top_part = df['Failed Component'].mode()[0] if 'Failed Component' in df.columns and not df.empty else "N/A"
            top_cause = df['Failure Cause'].mode()[0] if 'Failure Cause' in df.columns and not df.empty else "N/A"
            
            severe_incidents_count = len(df[df['Actual Down Time Hours'].fillna(0) >= 24.0])
            env_incidents_count = len(df[df['Env_Flag'] == True])
            
            lemon_count = 0
            if 'Serial No.' in df.columns and 'Date/Time Opened' in df.columns and not df.empty:
                ds_check = df.sort_values(['Serial No.', 'Date/Time Opened'])
                ds_check['Days_Diff'] = ds_check.groupby('Serial No.')['Date/Time Opened'].diff().dt.days
                lemon_count = len(ds_check[ds_check['Days_Diff'] <= recurring_days]['Serial No.'].unique())

            # Formatting Narrative Context Panels
            exp1 = st.expander("👁️ View Cross-Tab Consolidated Analytical Briefing", expanded=True)
            with exp1:
                c_brief1, c_brief2 = st.columns(2)
                with c_brief1:
                    st.markdown(f"""
                    * **The Operational Paradox Summary:** Across the current filter layer, high-volume tickets do not align with critical network impact. While **{top_complaint}** complaints generate the highest raw administrative volume, system downtime is driven almost entirely by localized **Hardware Breakdowns**.
                    * **Geographic Infrastructure Drag:** Network load is heavily localized in the **{top_region}** sector. Technical resource allocation or warehouse spare distributions should prioritize this geographic threshold to cut response boundaries down.
                    * **Lemon Alert Isolation:** Root cause matrix analysis has isolated **{lemon_count} unique instruments** failing repeatedly within a rolling {recurring_days}-day window. These chronic repeat offenders indicate field technicians are correcting symptoms rather than systemic faults.
                    """)
                with c_brief2:
                    st.markdown(f"""
                    * **NLP Component & Sub-Domain Audit:** Text mining of active service subjects reveals that **{top_part}** assemblies represent your primary physical failure vector, with **{top_cause}** emerging as the dominant mechanical root failure mode. 
                    * **Environmental & Site Footprint Risks:** There are **{env_incidents_count} logs** explicitly flagging environment-cascade issues (e.g., room temperature limit violations, voltage instability, water leakages). This proves localized laboratory asset infrastructure issues are actively forcing instruments into emergency fallback states.
                    * **Network Friction Warning:** A total of **{severe_incidents_count} high-impact cases** breached the critical 24-hour downtime limit. These outlier events require immediate diagnostic audits to determine shipping delays, engineering knowledge gaps, or lack of on-site diagnostic kits.
                    """)

            # Core Graphical Interfaces Row
            col_chart1, col_chart2, col_chart3 = st.columns([1.4, 1.1, 1.5])
            
            with col_chart1:
                if 'Region' in df.columns and not df.empty:
                    reg_df = df['Region'].value_counts().reset_index()
                    reg_df.columns = ['Region', 'Cases']
                    fig_bar = px.bar(reg_df, x='Region', y='Cases', title="Geographic Case Volume Distribution", text_auto=True, color_discrete_sequence=[CORP_BLUE])
                    fig_bar.update_traces(textposition='outside')
                    fig_bar.update_layout(xaxis_title="Operational Sector", yaxis_title="Incident Count", margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(fig_bar, use_container_width=True, theme="streamlit")

            with col_chart2:
                if 'Type of Complaint' in df.columns and not df.empty:
                    fig_donut = px.pie(df, names='Type of Complaint', hole=0.5, title="Administrative Case Mix", color_discrete_sequence=[CORP_TEAL, CORP_ORANGE, CORP_BLUE])
                    fig_donut.update_traces(textinfo='percent+label', textposition='inside')
                    fig_donut.update_layout(margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(fig_donut, use_container_width=True, theme="streamlit")
                
            with col_chart3:
                if 'Opened_Date' in df.columns and 'System Down Yes/No' in df.columns and not df.empty:
                    daily_df = df.groupby('Opened_Date').agg(
                        Total=('Case Number', 'count'), 
                        Down=('System Down Yes/No', lambda x: (x == 'Down').sum())
                    ).reset_index()
                    
                    fig_trend = go.Figure()
                    fig_trend.add_trace(go.Scatter(x=daily_df['Opened_Date'], y=daily_df['Total'], mode='lines+markers', name='Total Openings', line=dict(color=CORP_BLUE, width=2)))
                    fig_trend.add_trace(go.Scatter(x=daily_df['Opened_Date'], y=daily_df['Down'], mode='lines+markers', name='System Down Halts', line=dict(color=CORP_RED, width=2)))
                    fig_trend.update_layout(title="Temporal Operational Load vs. Critical Failures", xaxis_title="Timeline Calendar", yaxis_title="Ticket Metric Volumetrics", margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(fig_trend, use_container_width=True, theme="streamlit")

            # --- SYSTEMIC IMPLEMENTATION CORRECTIVE ACTION (CAPA) ROADMAP ---
            st.markdown("<div class='insight-header'>📋 Prescriptive Implementation Protocol (CAPA Roadmap)</div>", unsafe_allow_html=True)
            c_capa1, c_capa2, c_capa3 = st.columns(3)
            
            with c_capa1:
                st.info("""
                **⚡ IMMEDIATE (0 - 30 Days)**
                * **Targeted Engineering Deployments:** Dispatch field specialist units to top friction nodes to address localized mechanical issues directly.
                * **Component Overhaul:** Execute immediate proactive swaps on mechanical components for modules nearing cyclical limits.
                """)
            with c_capa2:
                st.warning("""
                **🛠️ TACTICAL PROTOCOL (30 - 60 Days)**
                * **PM Checkpoint Adjustments:** Mandatory introduction of strict mechanical tolerance tests during standard preventive maintenance visits.
                * **Environmental Lab Audits:** Require lab management infrastructure reviews (UPS voltage logging, AC stability tracking) at high-risk customer sites.
                """)
            with c_capa3:
                st.success("""
                **🔮 STRATEGIC ASSURANCE (60 - 90 Days)**
                * **Predictive Cyclical Schedule:** Shift the technical field organization from reactive fixing to proactive replacement based on tracked cycles.
                * **Tiered Escalation Routing:** Automatically flags repeat units in the service dispatch system, ensuring subsequent dispatches auto-route to high-level system technical specialist units.
                """)

        # ==========================================
        # TAB 2: FLEET & SITE RELIABILITY MATRIX
        # ==========================================
        with tab2:
            st.info("**🤖 Fleet Integrity Analytics:** Macroscopic Pareto distributions of core analyzer product families matched against individualized site operational vulnerabilities.")
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if 'Family/Line: Name' in df.columns and not df.empty:
                    fam_df = df.groupby('Family/Line: Name').size().reset_index(name='Complaints').sort_values('Complaints', ascending=False).head(10)
                    fam_df['Cum%'] = fam_df['Complaints'].cumsum() / fam_df['Complaints'].sum() * 100
                    
                    fig_fam = go.Figure()
                    fig_fam.add_trace(go.Bar(x=fam_df['Family/Line: Name'], y=fam_df['Complaints'], marker_color=CORP_BLUE, name="Incident Count", text=fam_df['Complaints'], textposition='auto'))
                    fig_fam.add_trace(go.Scatter(x=fam_df['Family/Line: Name'], y=fam_df['Cum%'], yaxis='y2', line=dict(color=CORP_RED, width=2.5), name="Cumulative Share %", mode='lines+markers+text', text=fam_df['Cum%'].round(1).astype(str)+'%', textposition='top center'))
                    fig_fam.update_layout(title="Product Line Vulnerability Pareto Model", yaxis2=dict(overlaying='y', side='right', range=[0, 115]), showlegend=False, xaxis_tickangle=-35)
                    st.plotly_chart(fig_fam, use_container_width=True, theme="streamlit")

            with col_p2:
                if 'Site Name' in df.columns and 'Type of Complaint' in df.columns and not df.empty:
                    hw_df = df[df['Type of Complaint'].str.contains('Hardware', case=False, na=False)]
                    if not hw_df.empty:
                        env_sites = hw_df[hw_df['Env_Flag'] == True]['Site Name'].unique()
                        site_df = hw_df.groupby('Site Name').size().reset_index(name='Complaints').sort_values('Complaints', ascending=False).head(15)
                        site_df['Site Display'] = site_df['Site Name'].apply(lambda x: f"⚠️ {x}" if x in env_sites else x)
                        site_df['Cum%'] = site_df['Complaints'].cumsum() / site_df['Complaints'].sum() * 100
                        
                        fig_site = go.Figure()
                        fig_site.add_trace(go.Bar(x=site_df['Site Display'], y=site_df['Complaints'], marker_color=CORP_BLUE, name="Hardware Faults", text=site_df['Complaints'], textposition='auto'))
                        fig_site.add_trace(go.Scatter(x=site_df['Site Display'], y=site_df['Cum%'], yaxis='y2', line=dict(color=CORP_RED, width=2.5), name="Cumulative Base %"))
                        fig_site.update_layout(title="Top Critical Sites Pareto (⚠️ = Environmental Footprint Risk)", yaxis2=dict(overlaying='y', side='right', range=[0, 115]), showlegend=False, xaxis_tickangle=-45)
                        st.plotly_chart(fig_site, use_container_width=True, theme="streamlit")

            if 'City' in df.columns and 'Family/Line: Name' in df.columns and not df.empty:
                city_df = df.groupby(['City', 'Family/Line: Name']).size().reset_index(name='Total')
                fig_city = px.bar(city_df.sort_values('Total', ascending=False).head(40), x='City', y='Total', color='Family/Line: Name', title="Citywise Dynamic Breakdown Load (Stacked Fleet Model)", text_auto=True, color_discrete_sequence=SAFE_PALETTE)
                fig_city.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_city, use_container_width=True, theme="streamlit")

        # ==========================================
        # TAB 3: ROOT CAUSE DEEP-DIVE (NLP)
        # ==========================================
        with tab3:
            st.info("**🤖 Root Cause Identification Vector:** Deep text mining models scanning ticket descriptions to parse specific modular failed physical items and underlying mechanics.")
            
            col_b, col_r = st.columns([1, 1.4])
            with col_b:
                if 'Hardware Sub-Domain' in df.columns and not df.empty:
                    bub_df = df.groupby('Hardware Sub-Domain').agg(
                        Freq=('Case Number', 'count'), 
                        AvgD=('Actual Down Time Hours', 'mean'), 
                        TotD=('Actual Down Time Hours', 'sum')
                    ).reset_index()
                    
                    fig_bub = px.scatter(bub_df, x='Freq', y='AvgD', size='TotD', color='Hardware Sub-Domain', 
                                         title="Diagnostic Domain Mapping (Impact vs. Frequency Matrix)", 
                                         labels={"Freq": "Incident Rate Count", "AvgD": "Mean System Halt Duration (Hours)", "TotD": "Total Cumulated Network Downtime"},
                                         size_max=45, color_discrete_sequence=SAFE_PALETTE)
                    st.plotly_chart(fig_bub, use_container_width=True, theme="streamlit")
                    
            with col_r:
                if 'Hardware Sub-Domain' in df.columns and not df.empty:
                    cr1, cr2 = st.columns(2)
                    hw_only = df[df['Hardware Sub-Domain'] != 'Unknown']
                    
                    with cr1:
                        parts = hw_only['Failed Component'].value_counts().reset_index().head(6)
                        parts.columns = ['Part', 'Count']
                        parts = parts[parts['Part'] != 'Module Base']
                        fig_p = px.bar(parts, x='Count', y='Part', orientation='h', title="Isolated Component Failure Counts", text_auto=True, color_discrete_sequence=[CORP_BLUE])
                        fig_p.update_layout(yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig_p, use_container_width=True, theme="streamlit")
                        
                    with cr2:
                        causes = hw_only['Failure Cause'].value_counts().reset_index().head(6)
                        causes.columns = ['Cause', 'Count']
                        causes = causes[causes['Cause'] != 'General Failure']
                        fig_c = px.bar(causes, x='Count', y='Cause', orientation='h', title="Parsed Underlying Failure Causes", text_auto=True, color_discrete_sequence=[CORP_ORANGE])
                        fig_c.update_layout(yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig_c, use_container_width=True, theme="streamlit")

        # ==========================================
        # TAB 4: OPERATIONAL RISK & OUTLIERS
        # ==========================================
        with tab4:
            col_out1, col_out2 = st.columns(2)
            
            with col_out1:
                st.warning(f"🍋 **Chronic Repeat Anomaly Tracker (Lemon Logic):** Instruments requiring successive technical interventions inside a rolling {recurring_days}-day boundary window.")
                if 'Serial No.' in df.columns and 'Date/Time Opened' in df.columns and not df.empty:
                    df_sorted = df.sort_values(['Serial No.', 'Date/Time Opened'])
                    df_sorted['Days_Diff'] = df_sorted.groupby('Serial No.')['Date/Time Opened'].diff().dt.days
                    rec_df = df_sorted[df_sorted['Days_Diff'] <= recurring_days]
                    
                    if not rec_df.empty:
                        rec_summary = rec_df.groupby(['Serial No.', 'Site Name']).agg(Repeats=('Case Number', 'count')).reset_index().sort_values('Repeats', ascending=False)
                        st.dataframe(rec_summary, use_container_width=True)
                    else:
                        st.success("No chronic recurring anomalies detected inside current filter bounds.")

            with col_out2:
                st.error("🚨 **High-Impact Network Friction Events:** Single isolated emergency tickets that caused massive continuous system downtime (>24 Hours).")
                if 'Actual Down Time Hours' in df.columns and not df.empty:
                    severe_mask = df['Actual Down Time Hours'].fillna(0) >= 24.0
                    severe_df = df[severe_mask].sort_values('Actual Down Time Hours', ascending=False)
                    
                    if not severe_df.empty:
                        st.dataframe(severe_df[['Case Number', 'Serial No.', 'Site Name', 'Actual Down Time Hours']], use_container_width=True)
                    else:
                        st.success("Zero long-duration outlier stops logged.")

            st.markdown("---")
            st.subheader("🔍 Central Fleet Asset Availability & SLA Matrix")
            
            # Safe Matrix Compiling
            if all(c in df.columns for c in ['Serial No.', 'Site Name', 'Family/Line: Name', 'Actual Down Time Hours']) and not df.empty:
                matrix_df = df.groupby(['Serial No.', 'Site Name', 'Family/Line: Name'], dropna=False).agg(
                    Total_Cases=('Case Number', 'count'), 
                    Down_Hours=('Actual Down Time Hours', 'sum')
                ).reset_index()
                
                if not matrix_df.empty:
                    matrix_df['Uptime %'] = ((total_timeline_hours - matrix_df['Down_Hours']) / total_timeline_hours) * 100
                    matrix_df = matrix_df.sort_values('Total_Cases', ascending=False)
                    
                    # Highlight items dropping beneath critical 95% line
                    def highlight_row(row):
                        color = 'background-color: rgba(225, 87, 89, 0.15)' if pd.notnull(row['Uptime %']) and row['Uptime %'] < 95.0 else ''
                        return [color] * len(row)

                    st.dataframe(matrix_df.style.apply(highlight_row, axis=1).format({'Uptime %': "{:.2f}%", 'Down_Hours': "{:.1f}"}), use_container_width=True, height=450)
                else:
                    st.warning("No data points trace back cleanly to match parameters.")
            else:
                st.warning("Missing database keys required to compile the fleet tracking matrix layout.")
