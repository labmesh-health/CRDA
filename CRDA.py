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
    page_title="Roche cobas Fleet Diagnostic Command Dashboard", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Inject Custom SaaS-style CSS supporting dynamic light/dark theme inheritance
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
    .bullet-point {
        margin-bottom: 12px;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔬 Roche cobas® Service Network & Fleet Diagnostic Command Center")

# Executive Palette Definitions
CORP_BLUE = '#4E79A7'
CORP_RED = '#E15759'
CORP_TEAL = '#76B7B2'
CORP_ORANGE = '#F28E2B'
SAFE_PALETTE = px.colors.qualitative.Safe

# ==========================================
# 2. DYNAMIC GEOCODING DIRECTORY
# ==========================================
@st.cache_data(show_spinner=False)
def geocode_cities(city_list):
    import requests
    directory = {
        'BANGALORE': {'lat': 12.9716, 'lon': 77.5946},
        'BENGALURU': {'lat': 12.9716, 'lon': 77.5946},
        'MUMBAI': {'lat': 19.0760, 'lon': 72.8777},
        'DELHI': {'lat': 28.7041, 'lon': 77.1025},
        'NEW DELHI': {'lat': 28.6139, 'lon': 77.2090},
        'CHENNAI': {'lat': 13.0827, 'lon': 80.2707},
        'HYDERABAD': {'lat': 17.3850, 'lon': 78.4867},
        'KOLKATA': {'lat': 22.5726, 'lon': 88.3639},
        'PUNE': {'lat': 18.5204, 'lon': 73.8567},
        'AHMEDABAD': {'lat': 23.0225, 'lon': 72.5714},
        'JAIPUR': {'lat': 26.9124, 'lon': 75.7873},
        'COIMBATORE': {'lat': 11.0168, 'lon': 76.9558},
        'KOCHI': {'lat': 9.9312, 'lon': 76.2673},
        'THANE': {'lat': 19.2183, 'lon': 72.9781},
        'NAGPUR': {'lat': 21.1458, 'lon': 79.0882},
        'INDORE': {'lat': 22.7196, 'lon': 75.8577},
        'BHOPAL': {'lat': 23.2599, 'lon': 77.4126},
        'PATNA': {'lat': 25.5941, 'lon': 85.1376},
        'VADODARA': {'lat': 22.3072, 'lon': 73.1812},
        'GHAZIABAD': {'lat': 28.6692, 'lon': 77.4538},
        'LUDHIANA': {'lat': 30.9010, 'lon': 75.8573},
        'AGRA': {'lat': 27.1767, 'lon': 78.0081},
        'NASHIK': {'lat': 19.9975, 'lon': 73.7898},
        'FARIDABAD': {'lat': 28.4089, 'lon': 77.3178},
        'MEERUT': {'lat': 28.9845, 'lon': 77.7064},
        'RAJKOT': {'lat': 22.3039, 'lon': 70.8022},
        'SURAT': {'lat': 21.1702, 'lon': 72.8311},
        'VISAKHAPATNAM': {'lat': 17.6868, 'lon': 83.2185},
        'VIJAYAWADA': {'lat': 16.5062, 'lon': 80.6480},
        'GUNTUR': {'lat': 16.3067, 'lon': 80.4365},
        'NELLORE': {'lat': 14.4426, 'lon': 79.9865},
        'GUWAHATI': {'lat': 26.1445, 'lon': 91.7362},
        'MYSORE': {'lat': 12.2958, 'lon': 76.6394},
        'MANGALORE': {'lat': 12.9141, 'lon': 74.8560},
        'HUBLI': {'lat': 15.3647, 'lon': 75.1240},
        'BELGAUM': {'lat': 15.8497, 'lon': 74.4977},
        'TRIVANDRUM': {'lat': 8.5241, 'lon': 76.9366},
        'CALICUT': {'lat': 11.2588, 'lon': 75.7804},
        'RANCHI': {'lat': 23.3441, 'lon': 85.3096},
        'JAMSHEDPUR': {'lat': 22.8046, 'lon': 86.2029},
        'DHANBAD': {'lat': 23.7957, 'lon': 86.4304},
        'RAIPUR': {'lat': 21.2514, 'lon': 81.6296},
        'BILASPUR': {'lat': 22.0790, 'lon': 82.1391},
        'DEHRADUN': {'lat': 30.3165, 'lon': 78.0322},
        'HARIDWAR': {'lat': 29.9457, 'lon': 78.1642},
        'ROORKEE': {'lat': 29.8543, 'lon': 77.8880},
        'SHIMLA': {'lat': 31.1048, 'lon': 77.1734},
        'SRINAGAR': {'lat': 34.0837, 'lon': 74.7973},
        'JAMMU': {'lat': 32.7266, 'lon': 74.8570},
        'AMRITSAR': {'lat': 31.6340, 'lon': 74.8723},
        'JALANDHAR': {'lat': 31.3260, 'lon': 75.5762},
        'WARANGAL': {'lat': 17.9689, 'lon': 79.5941},
        'AURANGABAD': {'lat': 19.8762, 'lon': 75.3433},
        'SOLAPUR': {'lat': 17.6599, 'lon': 75.9064},
        'KOLHAPUR': {'lat': 16.7050, 'lon': 74.2433},
        'JODHPUR': {'lat': 26.2389, 'lon': 73.0243},
        'UDAIPUR': {'lat': 24.5854, 'lon': 73.7125},
        'KOTA': {'lat': 25.2138, 'lon': 75.8648},
        'GWALIOR': {'lat': 26.2183, 'lon': 78.1828},
        'JABALPUR': {'lat': 23.1815, 'lon': 79.9864},
        'TRICHY': {'lat': 10.7905, 'lon': 78.7047},
        'SALEM': {'lat': 11.6643, 'lon': 78.1460},
        'MADURAI': {'lat': 9.9252, 'lon': 78.1198},
        'VARANASI': {'lat': 25.3176, 'lon': 82.9739},
        'KANPUR': {'lat': 26.4499, 'lon': 80.3319},
    }
    
    coordinates = {}
    for city in city_list:
        if pd.isna(city) or not str(city).strip():
            continue
        clean_name = str(city).strip().upper()
        if clean_name in directory:
            coordinates[city] = directory[clean_name]
            continue
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1"
            headers = {'User-Agent': 'RocheCobasFleetDashboard/1.0'}
            res = requests.get(url, headers=headers, timeout=3).json()
            if res:
                coordinates[city] = {
                    'lat': float(res[0]['lat']),
                    'lon': float(res[0]['lon'])
                }
        except:
            pass
    return coordinates

# ==========================================
# 3. SIDEBAR INGESTION VALIDATION BOUNDARY
# ==========================================
st.sidebar.header("📁 Data Ingestion")
uploaded_file = st.sidebar.file_uploader("Upload Network Service Log", type=["csv", "xlsx", "xls", "pdf"])

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

    # ===================================================
    # 4. DIRECT LOGICAL KEYWORD MAPPING MATRIX (NO NLP)
    # ===================================================
    if 'Subject' in df.columns:
        df['Subject_Clean'] = df['Subject'].fillna('').astype(str).str.lower()
        
        # Mapping Technical Sub-Domains
        def categorize_hardware(text):
            if any(w in text for w in ['gripper', 'axis', 'movement', 'rack', 'motor', 'actuator', 'l2 line', 'feeder', 'cup pick up', '18-05-01']): 
                return 'Kinematic / Robotic'
            if any(w in text for w in ['pressure', 'temperature', 'cooling', 'leak', 'water', 'wash', 'prime', 'flush', 'cc1', 'cc2', 'thermistor', 'fluidic']): 
                return 'Fluidic / Thermal'
            if any(w in text for w in ['voltage', 'power', 'ups', 'board', 'ac', 'noise', 'leakage', 'fluctuation', 'electrical', 'fuse', '072-000006']): 
                return 'Environmental / Power'
            if any(w in text for w in ['rfid', 'calibration', 'sensor', 'error', 'lld', 'qc', 'outlier', 'photometer', 'voltage']): 
                return 'Analytical / Sensor'
            return 'General Hardware'
            
        df['Hardware Sub-Domain'] = df['Subject_Clean'].apply(categorize_hardware)
        df['Env_Flag'] = df['Hardware Sub-Domain'] == 'Environmental / Power'
        
        # Pure Logical Keyword Rule Bucket for APPLICATION-specific issues
        def logical_application_bucket(text):
            if any(w in text for w in ['qc', 'outlier', 'eqa', 'iqc', 'control variation', 'variation']): 
                return 'Quality Control (QC) Issue'
            if any(w in text for w in ['cal ', 'calibration', 'calib', 'not calibrated', 'cal checked']): 
                return 'Calibration Failure'
            if any(w in text for w in ['rfid', 'registration', 'lot data', 'reagent lot', 'transponder']): 
                return 'RFID Reagent Registration Error'
            if any(w in text for w in ['short', 'insufficient', 'sample short', 'clot', 'short error', 'reagent short']): 
                return 'Sample / Reagent Shortage or Clot'
            if any(w in text for w in ['mismatch', 'lot variation', 'sensitivity variation', 'assay channel']): 
                return 'Lot Sensitivity Mismatch'
            return 'Other Application Issue'
        df['Logical Application Issue'] = df['Subject_Clean'].apply(logical_application_bucket)

        # Pure Logical Keyword Rule Bucket for HARDWARE-specific issues
        def logical_hardware_bucket(text):
            if any(w in text for w in ['gripper', 'cup pick', 'pickup', '18-05-01', '300-000028', 'waste mechanism', 'magazine']): 
                return 'Gripper & Cup Pickup Fault'
            if any(w in text for w in ['axis', 'motor', 'stepper', 'actuator', 'movement', 'stuck', 'jam', 'hook', 'binding', 'mechanical', 'l2- line']): 
                return 'Mechanical Axis & Motor Jam'
            if any(w in text for w in ['probe', 'pipeter', 'aspiration', 'sucking', 'leak', 'wash', 'prime', 'flush', 'cc1', 'cc2', 'fluidic', '011-0002', 'pipetter', 'line resistance']): 
                return 'Fluidic Circuit & Probe Aspiration Fault'
            if any(w in text for w in ['temp', 'cooling', 'thermistor', 'rotor temp', '113-000010', 'thermal', 'range']): 
                return 'Thermal Control & Thermistor Failure'
            if any(w in text for w in ['power', 'voltage', 'ups', 'board', 'fuse', '072-000006', 'supply', 'surge', 'electrical', 'fluctuation', 'start']): 
                return 'Power Supply & Electronic Board Failure'
            if any(w in text for w in ['sensor', 'detector', 'rack detector', '611-000007', 'optics', 'photometer', 'blinded', 'optical', 'voltage']): 
                return 'Sensor & Optical Module Error'
            return 'Other Hardware Fault'
        df['Logical Hardware Issue'] = df['Subject_Clean'].apply(logical_hardware_bucket)
    else:
        df['Hardware Sub-Domain'] = 'Unknown'
        df['Env_Flag'] = False
        df['Logical Application Issue'] = 'Unknown'
        df['Logical Hardware Issue'] = 'Unknown'

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
    else:
        df['Actual Down Time Hours'] = 0

    return df


# ==========================================
# 5. CONDITIONAL APPLICATION EXECUTION
# ==========================================
if uploaded_file is None:
    st.info("👋 Welcome! Please upload your network service log (CSV, Excel, or PDF) in the sidebar to populate the diagnostic command views.")
else:
    with st.spinner("Extracting and compiling network fleet data..."):
        df_raw = load_and_clean_data(uploaded_file.getvalue(), uploaded_file.name)

    if df_raw.empty:
        st.error("Incompatible dataset structure. Please check internal database keys.")
    else:
        # Secure Baseline Time Parameters
        min_date = df_raw['Date/Time Opened'].min()
        max_date = df_raw['Date/Time Opened'].max()
        
        if pd.notnull(min_date) and pd.notnull(max_date):
            total_days = (max_date - min_date).days
            total_timeline_hours = max(total_days * 24, 24)
        else:
            total_timeline_hours = 3432

        # Sidebar Input Layout
        st.sidebar.header("⚙️ Command Controls")
        min_d = min_date.date() if pd.notnull(min_date) else pd.to_datetime('2026-01-01').date()
        max_d = max_date.date() if pd.notnull(max_date) else pd.to_datetime('2026-12-31').date()

        date_range = st.sidebar.date_input("Operational Window", [min_d, max_d], min_value=min_d, max_value=max_d)

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
        recurring_days = st.sidebar.slider("Lemon Vulnerability Window (Days)", 7, 90, 30, 1)

        df = df_filtered

        # Structural Layout Tab Definitions
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 1. Strategic Command Center", 
            "🏭 2. Fleet & Site Reliability Matrix", 
            "🔍 3. Root Cause Analytics (RCA)",
            "🚨 4. Operational Risk & Outliers"
        ])

        # ==========================================
        # TAB 1: EXECUTIVE COMMAND CENTER
        # ==========================================
        with tab1:
            total_cases = len(df)
            total_downtime = df['Actual Down Time Hours'].sum()
            unique_machines = max(df['Serial No.'].nunique(), 1) if 'Serial No.' in df.columns else 1
            
            avg_downtime_per_machine = total_downtime / unique_machines
            uptime_pct = ((total_timeline_hours - avg_downtime_per_machine) / total_timeline_hours) * 100
            uptime_pct = min(max(uptime_pct, 0.0), 100.0)
            
            same_day_pct = 0
            if 'Resolution_Speed' in df.columns and total_cases > 0:
                same_day_cases = len(df[df['Resolution_Speed'] == 'Same Day'])
                same_day_pct = (same_day_cases / total_cases) * 100
                
            avg_downtime_per_case = df['Actual Down Time Hours'].mean() if total_cases > 0 else 0

            # Render HTML Metric Pillows
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

            # --- TARGETED AND EXPANDED DIRECT ROW/CASE ID CALCULATIONS ---
            if not df.empty:
                max_down_idx = df['Actual Down Time Hours'].idxmax()
                critical_case_number = df.loc[max_down_idx, 'Case Number'] if 'Case Number' in df.columns else "N/A"
                critical_case_hours = df.loc[max_down_idx, 'Actual Down Time Hours']
                critical_case_site = df.loc[max_down_idx, 'Site Name']
                critical_case_model = df.loc[max_down_idx, 'Family/Line: Name'] if 'Family/Line: Name' in df.columns else "N/A"
                critical_case_hardware_issue = df.loc[max_down_idx, 'Logical Hardware Issue']
                
                df_actionable = df[
                    (df['Actual Down Time Hours'] > 0) & 
                    (~df['Logical Hardware Issue'].isin(['Other Hardware Fault', 'Unknown'])) & 
                    (~df['Logical Application Issue'].isin(['Other Application Issue', 'Unknown']))
                ]
                
                if not df_actionable.empty:
                    pointed_top_part = df_actionable['Logical Hardware Issue'].mode()[0]
                    pointed_top_app = df_actionable['Logical Application Issue'].mode()[0]
                else:
                    pointed_top_part, pointed_top_app = "Gripper & Cup Pickup Fault", "Quality Control (QC) Issue"
                    
                model_downtime = df.groupby('Family/Line: Name')['Actual Down Time Hours'].sum()
                leading_friction_model = model_downtime.idxmax() if not model_downtime.empty else "N/A"
                
                serial_downtime = df.groupby('Serial No.').agg({'Actual Down Time Hours':'sum', 'Site Name':'first'}).reset_index()
                if not serial_downtime.empty:
                    critical_idx = serial_downtime['Actual Down Time Hours'].idxmax()
                    critical_impact_serial = serial_downtime.loc[critical_idx, 'Serial No.']
                    pointed_serial_site = serial_downtime.loc[critical_idx, 'Site Name']
                    pointed_serial_hours = serial_downtime.loc[critical_idx, 'Actual Down Time Hours']
                else:
                    critical_impact_serial, pointed_serial_site, pointed_serial_hours = "N/A", "N/A", 0
                    
                if 'City' in df.columns:
                    top_city_series = df['City'].dropna().mode()
                    pointed_top_city = top_city_series[0] if not top_city_series.empty else "N/A"
                else:
                    pointed_top_city = "N/A"
            else:
                critical_case_number, critical_case_hours, critical_case_site, critical_case_model, critical_case_hardware_issue = "N/A", 0, "N/A", "N/A", "N/A"
                pointed_top_part, pointed_top_app, leading_friction_model, critical_impact_serial, pointed_serial_site, pointed_serial_hours, pointed_top_city = "N/A", "N/A", "N/A", "N/A", "N/A", 0, "N/A"

            severe_outliers_count = len(df[df['Actual Down Time Hours'].fillna(0) >= 24.0])
            env_stress_count = len(df[df['Env_Flag'] == True])
            
            lemon_assets_count = 0
            if 'Serial No.' in df.columns and 'Date/Time Opened' in df.columns and not df.empty:
                ds_check = df.sort_values(['Serial No.', 'Date/Time Opened'])
                ds_check['Days_Diff'] = ds_check.groupby('Serial No.')['Date/Time Opened'].diff().dt.days
                lemon_assets_count = len(ds_check[ds_check['Days_Diff'] <= recurring_days]['Serial No.'].unique())

            # --- STRATEGIC COMMAND CENTER INSIGHTS PANEL ---
            st.markdown("<div class='insight-header'>🏛️ Strategic Command Briefing (Pointed Roche Fleet Metrics)</div>", unsafe_allow_html=True)
            
            exp_brief = st.expander("👁️ Review High-Impact Operational Diagnostics & Case Audits", expanded=True)
            with exp_brief:
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.markdown(f"""
                    <div class='bullet-point'><strong>🏢 Most Critical Network Friction Event:</strong> Case ID <strong>{critical_case_number}</strong> recorded at <em>{critical_case_site}</em> represents the single largest individual disruption across the network. This case involved a <strong>{critical_case_model}</strong> platform that suffered <strong>{critical_case_hours:.1f} hours</strong> of continuous operational halt driven by <em>{critical_case_hardware_issue}</em>. Use this specific Case ID to audit maintenance backlogs in your enterprise records.</div>
                    <div class='bullet-point'><strong>⚙️ Actionable Mechanical Problem Group:</strong> Logical rule extraction maps the leading hardware disruption block directly to <strong>{pointed_top_part}</strong> issues. Geographically, the highest frequency of total fleet breakthroughs is concentrated in <strong>{pointed_top_city}</strong>, as illuminated by the breakdown density map. Engineering re-routing and field operations must immediately prioritize these key hubs.</div>
                    <div class='bullet-point'><strong>🚨 Primary Fleet Friction Platform:</strong> The <strong>{leading_friction_model}</strong> system line is the leading driver of cumulative fleet downtime. Routine support queues are cleared quickly, but overall fleet availability is heavily dictated by this specific architecture.</div>
                    """, unsafe_allow_html=True)
                with col_b2:
                    st.markdown(f"""
                    <div class='bullet-point'><strong>🍋 Single Highest-Risk Unit (Lemon Detector):</strong> Serial Number <strong>{critical_impact_serial}</strong> located at <em>{pointed_serial_site}</em> has caused a massive network gap of <strong>{pointed_serial_hours:.1f} hours</strong>. Successive dispatches to this asset indicate that field activities are addressing immediate symptoms rather than permanent root causes. This unit requires an immediate factory overhaul.</div>
                    <div class='bullet-point'><strong>🧪 Dominant Application Bottleneck:</strong> Outside of physical mechanics, <strong>{pointed_top_app}</strong> generates the primary tracking noise. Restoring electrode baseline priming pressures and utilizing deep-clean fluidic flushes will clear up these sweeping assay channel discrepancies.</div>
                    <div class='bullet-point'><strong>📉 Serious MTTR SLA Violations:</strong> A total of <strong>{severe_outliers_count} high-impact incidents</strong> extended past the critical 24-hour downtime mark, while <strong>{lemon_assets_count} instruments</strong> experienced repeat breakdowns inside the rolling {recurring_days}-day limit. This indicates significant operational drag that directly threatens patient turnaround times (TAT).</div>
                    """, unsafe_allow_html=True)

            # Core Visual Layout Matrix with PAN-LOCKED map-based bubble chart
            col_g1, col_g2, col_g3 = st.columns([1.5, 1.1, 1.4])
            
            with col_g1:
                if 'City' in df.columns and not df.empty:
                    city_counts = df['City'].value_counts().reset_index()
                    city_counts.columns = ['City', 'Breakdowns']
                    
                    unique_cities_tuple = tuple(city_counts['City'].dropna().unique())
                    city_coords = geocode_cities(unique_cities_tuple)
                    
                    city_counts['lat'] = city_counts['City'].map(lambda x: city_coords.get(x, {}).get('lat', None))
                    city_counts['lon'] = city_counts['City'].map(lambda x: city_coords.get(x, {}).get('lon', None))
                    city_counts = city_counts.dropna(subset=['lat', 'lon'])
                    
                    if not city_counts.empty:
                        fig_map = px.scatter_mapbox(
                            city_counts,
                            lat='lat',
                            lon='lon',
                            size='Breakdowns',
                            hover_name='City',
                            hover_data=['Breakdowns'],
                            color_discrete_sequence=[CORP_BLUE],
                            zoom=3.8,  # ZOOM INCREASED
                            center={"lat": 22.5, "lon": 79.5}, # CENTERED ON INDIA
                            title="Citywide Breakdown Density Mapping"
                        )
                        fig_map.update_layout(
                            mapbox_style="open-street-map",
                            mapbox_bounds={"west": 68, "east": 98, "south": 6, "north": 36}, # LOCKED BOUNDARIES FOR INDIA
                            margin=dict(l=5, r=5, t=40, b=5)
                        )
                        st.plotly_chart(fig_map, use_container_width=True, theme="streamlit")
                    else:
                        st.warning("City coordinates not resolved for geographic bubble map loading.")
                elif 'Region' in df.columns and not df.empty:
                    reg_df = df['Region'].value_counts().reset_index()
                    reg_df.columns = ['Region', 'Cases']
                    fig_bar = px.bar(reg_df, x='Region', y='Cases', title="Geographic Case Volume Load", text_auto=True, color_discrete_sequence=[CORP_BLUE])
                    fig_bar.update_traces(textposition='outside')
                    st.plotly_chart(fig_bar, use_container_width=True, theme="streamlit")

            with col_g2:
                if 'Type of Complaint' in df.columns and not df.empty:
                    fig_donut = px.pie(df, names='Type of Complaint', hole=0.5, title="Administrative Case Distribution", color_discrete_sequence=[CORP_TEAL, CORP_ORANGE, CORP_BLUE])
                    fig_donut.update_traces(textinfo='percent+label', textposition='inside')
                    fig_donut.update_layout(margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(fig_donut, use_container_width=True, theme="streamlit")
                
            with col_g3:
                if 'Opened_Date' in df.columns and 'System Down Yes/No' in df.columns and not df.empty:
                    daily_df = df.groupby('Opened_Date').agg(
                        Total=('Case Number', 'count'), 
                        Down=('System Down Yes/No', lambda x: (x == 'Down').sum())
                    ).reset_index()
                    
                    fig_trend = go.Figure()
                    fig_trend.add_trace(go.Scatter(x=daily_df['Opened_Date'], y=daily_df['Total'], mode='lines+markers', name='Total Openings', line=dict(color=CORP_BLUE, width=2)))
                    fig_trend.add_trace(go.Scatter(x=daily_df['Opened_Date'], y=daily_df['Down'], mode='lines+markers', name='System Down Halts', line=dict(color=CORP_RED, width=2)))
                    fig_trend.update_layout(title="Temporal Operational Load vs. Critical Failures", xaxis_title="Timeline Calendar", yaxis_title="Ticket Volumetrics", margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(fig_trend, use_container_width=True, theme="streamlit")

            # --- SYSTEMIC CORRECTIVE ACTION (CAPA) PLAYBOOK ---
            st.markdown("<div class='insight-header'>📋 Actionable Implementation Playbook (Prescriptive CAPA Engine)</div>", unsafe_allow_html=True)
            col_capa1, col_capa2, col_capa3 = st.columns(3)
            
            with col_capa1:
                st.info(f"""
                **⚡ IMMEDIATE ESCALATION (0 - 30 Days)**
                * **Root Cause Incident Audit:** Audit Case ID **{critical_case_number}** directly to determine if on-site spare part availability or technician delay escalated MTTR boundaries.
                * **Component Targeted Swaps:** Force proactive parts replacement of all **{pointed_top_part}** units showing signs of cyclical wear.
                """)
            with col_capa2:
                st.warning("""
                **🛠️ TACTICAL STABILIZATION (30 - 60 Days)**
                * **Tolerance Auditing Checkpoints:** Introduce strict verification checks for Z-axis assemblies and gripper mechanisms during routine service visits.
                * **Environmental Auditing Mandate:** Require customer facility validation (line conditioners, dedicated UPS logging, HVAC stability) before authorizing replacement parts.
                """)
            with col_capa3:
                st.success(f"""
                **🔮 STRATEGIC ASSURANCE (60 - 90 Days)**
                * **Predictive Lifecycle Strategy:** Move from reactive troubleshooting to proactive replacement based on tracked runs for key components.
                * **Automated Asset Escalation:** Automatically flag units like Serial Number **{critical_impact_serial}** in the dispatch system to ensure subsequent faults route immediately to Tier 2 specialist engineers.
                """)

        # ==========================================
        # TAB 2: FLEET & SITE RELIABILITY MATRIX
        # ==========================================
        with tab2:
            st.info("**🔬 Fleet Integrity Analytics:** Macroscopic Pareto distributions of analyzer systems matched against individualized site operational vulnerabilities.")
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if 'Family/Line: Name' in df.columns and not df.empty:
                    fam_counts = df.groupby('Family/Line: Name').size().reset_index(name='Complaints').sort_values('Complaints', ascending=False).head(10)
                    fam_counts['Cum%'] = fam_counts['Complaints'].cumsum() / fam_counts['Complaints'].sum() * 100
                    
                    fig_fam = go.Figure()
                    fig_fam.add_trace(go.Bar(x=fam_counts['Family/Line: Name'], y=fam_counts['Complaints'], marker_color=CORP_BLUE, name="Incident Count", text=fam_counts['Complaints'], textposition='auto'))
                    fig_fam.add_trace(go.Scatter(x=fam_counts['Family/Line: Name'], y=fam_counts['Cum%'], yaxis='y2', line=dict(color=CORP_RED, width=2.5), name="Cumulative Share %", mode='lines+markers+text', text=fam_counts['Cum%'].round(1).astype(str)+'%', textposition='top center'))
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
                fig_city = px.bar(city_df.sort_values('Total', ascending=False).head(40), x='City', y='Total', color='Family/Line: Name', title="Citywise Instrument Breakdowns (Stacked Fleet Model)", text_auto=True, color_discrete_sequence=SAFE_PALETTE)
                fig_city.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_city, use_container_width=True, theme="streamlit")

        # ==========================================
        # TAB 3: ROOT CAUSE ANALYTICS (RCA)
        # ==========================================
        with tab3:
            st.info("**🤖 Logical Keyword Mapping Matrix:** Subjects broken down systematically using rigorous technical rule sets, mapping top application metrics alongside mechanical hardware failure counts.")
            
            col_app_chart, col_hw_chart = st.columns(2)
            
            with col_app_chart:
                if 'Logical Application Issue' in df.columns and not df.empty:
                    app_filter = df[df['Logical Application Issue'] != 'Other Application Issue']
                    app_problems = app_filter['Logical Application Issue'].value_counts().reset_index().head(10)
                    app_problems.columns = ['Application Problem Area', 'Incident Count']
                    
                    fig_app = px.bar(app_problems, x='Incident Count', y='Application Problem Area', orientation='h',
                                     title="Application / Reagent Module: Top Occurring Issues", text_auto=True,
                                     color_discrete_sequence=[CORP_TEAL])
                    fig_app.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(fig_app, use_container_width=True, theme="streamlit")
                    
            with col_hw_chart:
                if 'Logical Hardware Issue' in df.columns and not df.empty:
                    hw_filter = df[df['Logical Hardware Issue'] != 'Other Hardware Fault']
                    hw_problems = hw_filter['Logical Hardware Issue'].value_counts().reset_index().head(10)
                    hw_problems.columns = ['Hardware Mechanical Domain', 'Incident Count']
                    
                    fig_hw = px.bar(hw_problems, x='Incident Count', y='Hardware Mechanical Domain', orientation='h',
                                    title="Hardware Systems: Top Occurring Functional Failures", text_auto=True,
                                    color_discrete_sequence=[CORP_BLUE])
                    fig_hw.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(fig_hw, use_container_width=True, theme="streamlit")

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
            
            if all(c in df.columns for c in ['Serial No.', 'Site Name', 'Family/Line: Name', 'Actual Down Time Hours']) and not df.empty:
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

                    st.dataframe(matrix_df.style.apply(highlight_row, axis=1).format({'Uptime %': "{:.2f}%", 'Down_Hours': "{:.1f}"}), use_container_width=True, height=450)
                else:
                    st.warning("No data points trace back cleanly to match parameters.")
            else:
                st.warning("Missing database keys required to compile the fleet tracking matrix layout.")
