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
    .info-card {
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 6px solid;
        height: 100%;
    }
    .info-card.success {
        border-left-color: #59A14F;
        background-color: rgba(89, 161, 79, 0.08);
    }
    .info-card.warning {
        border-left-color: #E15759;
        background-color: rgba(225, 87, 89, 0.08);
    }
    .info-title {
        font-weight: 700;
        font-size: 1.05rem;
        margin-bottom: 8px;
        color: var(--text-color);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .info-metric {
        font-size: 1.8rem;
        font-weight: 900;
        margin-bottom: 5px;
    }
    .success .info-metric { color: #59A14F; }
    .warning .info-metric { color: #E15759; }
    
    .info-desc {
        font-size: 0.95rem;
        line-height: 1.4;
        opacity: 0.85;
    }
    .zone-pill {
        text-align: center; 
        padding: 15px; 
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .zone-pct {
        font-size: 2rem; 
        font-weight: 900; 
        margin: 0;
    }
    .zone-label {
        margin: 0; 
        font-size: 0.9rem; 
        font-weight: 700; 
        text-transform: uppercase;
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
    
    if 'City' in df.columns:
        df['Site Name'] = df['City'].fillna('Unknown Location').astype(str)
    else:
        df['Site Name'] = df.get('Account Name', 'Unknown Site')

    if 'System Down Yes/No' in df.columns:
        df['System Down Yes/No'] = df['System Down Yes/No'].fillna('Not Down').apply(
            lambda x: 'Down' if 'yes' in str(x).lower() or 'down' in str(x).lower() else 'Not Down'
        )
    else:
        df['System Down Yes/No'] = 'Unknown'

    if 'Subject' in df.columns:
        df['Subject_Clean'] = df['Subject'].fillna('').astype(str).str.lower()
        
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
# 4. CONDITIONAL APPLICATION EXECUTION
# ==========================================
if uploaded_file is None:
    st.info("👋 Welcome! Please upload your network service log (CSV, Excel, or PDF) in the sidebar to populate the diagnostic command views.")
else:
    with st.spinner("Extracting and compiling network fleet data..."):
        df_raw = load_and_clean_data(uploaded_file.getvalue(), uploaded_file.name)

    if df_raw.empty:
        st.error("Incompatible dataset structure. Please check internal database keys.")
    else:
        min_date = df_raw['Date/Time Opened'].min()
        max_date = df_raw['Date/Time Opened'].max()
        
        if pd.notnull(min_date) and pd.notnull(max_date):
            total_days = (max_date - min_date).days
            total_timeline_hours = max(total_days * 24, 24)
        else:
            total_timeline_hours = 3432

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

            if not df.empty:
                if 'Site Name' in df.columns and 'Resolution_Speed' in df.columns:
                    site_resolutions = df.groupby('Site Name').agg(
                        Total=('Case Number', 'count'),
                        Same_Day=('Resolution_Speed', lambda x: (x == 'Same Day').sum())
                    )
                    site_resolutions = site_resolutions[site_resolutions['Total'] >= 5]
                    if not site_resolutions.empty:
                        site_resolutions['Pct'] = (site_resolutions['Same_Day'] / site_resolutions['Total']) * 100
                        champion_site = site_resolutions['Pct'].idxmax()
                        champion_site_pct = site_resolutions['Pct'].max()
                    else:
                        champion_site, champion_site_pct = "N/A", 0
                else:
                    champion_site, champion_site_pct = "N/A", 0

                if 'Family/Line: Name' in df.columns:
                    model_down = df.groupby('Family/Line: Name').agg(
                        Total=('Case Number', 'count'),
                        Avg_Down=('Actual Down Time Hours', 'mean')
                    )
                    model_down = model_down[model_down['Total'] >= 5]
                    if not model_down.empty:
                        reliable_model = model_down['Avg_Down'].idxmin()
                        reliable_model_hours = model_down['Avg_Down'].min()
                    else:
                        reliable_model, reliable_model_hours = "N/A", 0
                else:
                    reliable_model, reliable_model_hours = "N/A", 0
                
                non_disruptive_pct = (len(df[df['System Down Yes/No'] == 'Not Down']) / total_cases) * 100 if total_cases > 0 else 0

                max_down_idx = df['Actual Down Time Hours'].idxmax()
                critical_case_number = df.loc[max_down_idx, 'Case Number'] if 'Case Number' in df.columns else "N/A"
                critical_case_hours = df.loc[max_down_idx, 'Actual Down Time Hours']
                critical_case_site = df.loc[max_down_idx, 'Site Name']
                
                df_actionable = df[
                    (df['Actual Down Time Hours'] > 0) & 
                    (~df['Logical Hardware Issue'].isin(['Other Hardware Fault', 'Unknown']))
                ]
                pointed_top_part = df_actionable['Logical Hardware Issue'].mode()[0] if not df_actionable.empty else "N/A"
                
                serial_downtime = df.groupby('Serial No.').agg({'Actual Down Time Hours':'sum', 'Site Name':'first'}).reset_index()
                if not serial_downtime.empty:
                    critical_idx = serial_downtime['Actual Down Time Hours'].idxmax()
                    critical_impact_serial = serial_downtime.loc[critical_idx, 'Serial No.']
                    pointed_serial_hours = serial_downtime.loc[critical_idx, 'Actual Down Time Hours']
                else:
                    critical_impact_serial, pointed_serial_hours = "N/A", 0
            else:
                champion_site, champion_site_pct, reliable_model, reliable_model_hours, non_disruptive_pct = "N/A", 0, "N/A", 0, 0
                critical_case_number, critical_case_hours, critical_case_site, pointed_top_part, critical_impact_serial, pointed_serial_hours = "N/A", 0, "N/A", "N/A", "N/A", 0

            st.markdown("<div class='insight-header'>🌟 Fleet Health & Operational Successes</div>", unsafe_allow_html=True)
            c_good1, c_good2, c_good3 = st.columns(3)
            
            with c_good1:
                st.markdown(f"""
                <div class='info-card success'>
                    <div class='info-title'>🏆 Efficiency Champion Site</div>
                    <div class='info-metric'>{champion_site_pct:.1f}%</div>
                    <div class='info-desc'><strong>{champion_site}</strong> holds the highest Same-Day Fix rate in the network. Analyze their local parts inventory to replicate this success elsewhere.</div>
                </div>
                """, unsafe_allow_html=True)
            with c_good2:
                st.markdown(f"""
                <div class='info-card success'>
                    <div class='info-title'>⚡ Most Resilient Platform</div>
                    <div class='info-metric'>{reliable_model_hours:.1f} hrs</div>
                    <div class='info-desc'>The <strong>{reliable_model}</strong> family demonstrates exceptional reliability, logging the lowest average downtime per incident across the fleet.</div>
                </div>
                """, unsafe_allow_html=True)
            with c_good3:
                st.markdown(f"""
                <div class='info-card success'>
                    <div class='info-title'>🛡️ Non-Disruptive Interventions</div>
                    <div class='info-metric'>{non_disruptive_pct:.1f}%</div>
                    <div class='info-desc'>Of all tickets submitted, a significant majority were resolved <strong>without triggering a system hard-down</strong>, maintaining continuous lab throughput.</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div class='insight-header'>🎯 Strategic Intervention & Focus Areas</div>", unsafe_allow_html=True)
            c_bad1, c_bad2, c_bad3 = st.columns(3)
            
            with c_bad1:
                st.markdown(f"""
                <div class='info-card warning'>
                    <div class='info-title'>🏢 Peak Friction Event</div>
                    <div class='info-metric'>{critical_case_hours:.1f} hrs</div>
                    <div class='info-desc'>Case <strong>{critical_case_number}</strong> at <em>{critical_case_site}</em> represents the single longest network halt. Audit this case to identify logistics or training delays.</div>
                </div>
                """, unsafe_allow_html=True)
            with c_bad2:
                st.markdown(f"""
                <div class='info-card warning'>
                    <div class='info-title'>⚙️ Primary Hardware Stressor</div>
                    <div class='info-metric'>{pointed_top_part}</div>
                    <div class='info-desc'>Logical mining isolates this component group as the leading cause of hardware-related downtime. Proactive PM replacements are highly recommended.</div>
                </div>
                """, unsafe_allow_html=True)
            with c_bad3:
                st.markdown(f"""
                <div class='info-card warning'>
                    <div class='info-title'>🍋 Highest-Risk Asset</div>
                    <div class='info-metric'>SN: {critical_impact_serial}</div>
                    <div class='info-desc'>This specific machine has accumulated <strong>{pointed_serial_hours:.1f} total hours</strong> of downtime. Field fixes are treating symptoms; factory overhaul or depot repair is advised.</div>
                </div>
                """, unsafe_allow_html=True)

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
                            zoom=3.8,  
                            center={"lat": 22.5, "lon": 79.5}, 
                            title="Citywide Breakdown Density Mapping"
                        )
                        fig_map.update_layout(
                            mapbox_style="open-street-map",
                            mapbox_bounds={"west": 68, "east": 98, "south": 6, "north": 36}, 
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
            
            st.markdown("<div class='insight-header'>🫧 Individual Incident Impact Matrix (Zone Segmentation)</div>", unsafe_allow_html=True)
            
            if 'Actual Down Time Hours' in df.columns and 'Resolution_Hours' in df.columns and 'Date/Time Opened' in df.columns and not df.empty:
                plot_df = df.copy()
                
                plot_df['Bubble_Size'] = plot_df['Resolution_Hours'].fillna(1).clip(lower=1)
                
                h_name = 'Case Number' if 'Case Number' in plot_df.columns else None
                c_name = 'Type of Complaint' if 'Type of Complaint' in plot_df.columns else None
                
                h_data = {
                    "Resolution_Hours": ':.1f',
                    "Actual Down Time Hours": ':.1f',
                    "Bubble_Size": False
                }
                
                if 'Site Name' in plot_df.columns:
                    h_data['Site Name'] = True
                if 'Logical Hardware Issue' in plot_df.columns:
                    h_data['Logical Hardware Issue'] = True
                if 'Date/Time Opened' in plot_df.columns:
                    h_data['Date/Time Opened'] = "|%b %d, %Y"

                fig_bubble = px.scatter(
                    plot_df,
                    x="Date/Time Opened",       
                    y="Actual Down Time Hours", 
                    size="Bubble_Size",         
                    color=c_name,
                    hover_name=h_name,
                    hover_data=h_data,
                    size_max=45, 
                    opacity=0.7, 
                    marginal_y="histogram", 
                    marginal_x="histogram", 
                    color_discrete_sequence=[CORP_ORANGE, CORP_BLUE, CORP_TEAL, '#B0B0B0']
                )

                fig_bubble.add_hrect(y0=0, y1=24, fillcolor="#59A14F", opacity=0.1, layer="below", line_width=0, annotation_text="0-24 Hrs (SLA Met)", annotation_position="top right", annotation_font_color="#59A14F")
                fig_bubble.add_hrect(y0=24, y1=48, fillcolor="#F28E2B", opacity=0.1, layer="below", line_width=0, annotation_text="24-48 Hrs (Elevated)", annotation_position="top right", annotation_font_color="#F28E2B")
                fig_bubble.add_hrect(y0=48, y1=96, fillcolor="#E15759", opacity=0.1, layer="below", line_width=0, annotation_text="48-96 Hrs (Severe)", annotation_position="top right", annotation_font_color="#E15759")
                
                max_downtime = plot_df["Actual Down Time Hours"].max()
                if max_downtime > 96:
                    fig_bubble.add_hrect(y0=96, y1=max_downtime * 1.1, fillcolor="#8B0000", opacity=0.15, layer="below", line_width=0, annotation_text=">96 Hrs (Critical)", annotation_position="top right", annotation_font_color="#8B0000")
                else:
                    fig_bubble.add_hrect(y0=96, y1=120, fillcolor="#8B0000", opacity=0.15, layer="below", line_width=0, annotation_text=">96 Hrs (Critical)", annotation_position="top right", annotation_font_color="#8B0000")

                fig_bubble.update_traces(
                    marker=dict(line=dict(width=1, color='White'))
                )
                
                fig_bubble.update_layout(
                    title="Timeline of Every Service Call: Downtime vs. Resolution Speed",
                    xaxis_title="Incident Timeline (Date Opened)",
                    yaxis_title="Actual Down Time (Hours)",
                    showlegend=True,
                    legend_title_text="Complaint Origin",
                    plot_bgcolor='rgba(248, 249, 250, 1)',
                    height=600,
                    margin=dict(l=20, r=20, t=40, b=180),
                    xaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(200,200,200,0.5)', zeroline=True, zerolinecolor='rgba(150,150,150,0.8)'),
                    yaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(200,200,200,0.5)', zeroline=True, zerolinecolor='rgba(150,150,150,0.8)')
                )

                fig_bubble.add_annotation(
                    text="<b>Insight:</b> Top/Right bar charts display the <b>Volume of incidents</b>. Scatter maps the <b>Downtime Impact vs Timeline</b>.",
                    xref="paper", yref="paper", x=0.5, y=-0.32, showarrow=False,
                    font=dict(size=13, color="#4E79A7"), bgcolor="rgba(242, 142, 43, 0.1)",
                    bordercolor=CORP_ORANGE, borderwidth=1, borderpad=8
                )

                st.plotly_chart(fig_bubble, use_container_width=True, theme="streamlit")
                
                total_plotted = len(plot_df)
                if total_plotted > 0:
                    pct_0_24 = len(plot_df[(plot_df['Actual Down Time Hours'] >= 0) & (plot_df['Actual Down Time Hours'] <= 24)]) / total_plotted * 100
                    pct_24_48 = len(plot_df[(plot_df['Actual Down Time Hours'] > 24) & (plot_df['Actual Down Time Hours'] <= 48)]) / total_plotted * 100
                    pct_48_96 = len(plot_df[(plot_df['Actual Down Time Hours'] > 48) & (plot_df['Actual Down Time Hours'] <= 96)]) / total_plotted * 100
                    pct_96_plus = len(plot_df[plot_df['Actual Down Time Hours'] > 96]) / total_plotted * 100
                else:
                    pct_0_24 = pct_24_48 = pct_48_96 = pct_96_plus = 0

                cz1, cz2, cz3, cz4 = st.columns(4)
                cz1.markdown(f"<div class='zone-pill' style='background-color: rgba(89, 161, 79, 0.1); border: 1px solid #59A14F;'><h3 class='zone-pct' style='color:#59A14F;'>{pct_0_24:.1f}%</h3><p class='zone-label'>0-24 Hrs (SLA Met)</p></div>", unsafe_allow_html=True)
                cz2.markdown(f"<div class='zone-pill' style='background-color: rgba(242, 142, 43, 0.1); border: 1px solid #F28E2B;'><h3 class='zone-pct' style='color:#F28E2B;'>{pct_24_48:.1f}%</h3><p class='zone-label'>24-48 Hrs (Elevated)</p></div>", unsafe_allow_html=True)
                cz3.markdown(f"<div class='zone-pill' style='background-color: rgba(225, 87, 89, 0.1); border: 1px solid #E15759;'><h3 class='zone-pct' style='color:#E15759;'>{pct_48_96:.1f}%</h3><p class='zone-label'>48-96 Hrs (Severe)</p></div>", unsafe_allow_html=True)
                cz4.markdown(f"<div class='zone-pill' style='background-color: rgba(139, 0, 0, 0.1); border: 1px solid #8B0000;'><h3 class='zone-pct' style='color:#8B0000;'>{pct_96_plus:.1f}%</h3><p class='zone-label'>>96 Hrs (Critical)</p></div>", unsafe_allow_html=True)

            else:
                st.warning("Insufficient data keys to generate the Incident Scatter matrix.")

            st.markdown("---")
            
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
                        
                        top_lemon_sn = rec_summary.iloc[0]['Serial No.']
                        top_lemon_site = rec_summary.iloc[0]['Site Name']
                        top_lemon_repeats = rec_summary.iloc[0]['Repeats']
                        total_lemons = len(rec_summary)
                        
                        st.markdown(f"""
                        <div style='background-color: rgba(242, 142, 43, 0.1); border-left: 4px solid {CORP_ORANGE}; padding: 10px; border-radius: 5px; margin-top: 10px; font-size: 0.9rem;'>
                            <strong>Quick Insights:</strong><br>
                            • <strong>{total_lemons}</strong> unique assets exhibit chronic instability.<br>
                            • Asset <strong>{top_lemon_sn}</strong> at <em>{top_lemon_site}</em> leads with <strong>{top_lemon_repeats}</strong> repeated breakdowns.<br>
                            • <em>Action:</em> Divert from standard break/fix to mandatory root-cause overhaul for these units.
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.success("No chronic recurring anomalies detected inside current filter bounds.")

            with col_out2:
                st.error("🚨 **High-Impact Network Friction Events:** Single isolated emergency tickets that caused massive continuous system downtime (>24 Hours).")
                if 'Actual Down Time Hours' in df.columns and not df.empty:
                    severe_mask = df['Actual Down Time Hours'].fillna(0) >= 24.0
                    severe_df = df[severe_mask].sort_values('Actual Down Time Hours', ascending=False)
                    
                    if not severe_df.empty:
                        st.dataframe(severe_df[['Case Number', 'Serial No.', 'Site Name', 'Actual Down Time Hours']], use_container_width=True)
                        
                        top_severe_case = severe_df.iloc[0]['Case Number']
                        top_severe_hours = severe_df.iloc[0]['Actual Down Time Hours']
                        top_severe_site = severe_df.iloc[0]['Site Name']
                        total_severe = len(severe_df)

                        st.markdown(f"""
                        <div style='background-color: rgba(225, 87, 89, 0.1); border-left: 4px solid {CORP_RED}; padding: 10px; border-radius: 5px; margin-top: 10px; font-size: 0.9rem;'>
                            <strong>Quick Insights:</strong><br>
                            • <strong>{total_severe}</strong> incidents breached the critical 24-hour SLA boundary.<br>
                            • Peak disruption reached <strong>{top_severe_hours:.1f} hrs</strong> for Case <strong>{top_severe_case}</strong> at <em>{top_severe_site}</em>.<br>
                            • <em>Action:</em> Cross-reference these Case IDs against logistics logs to identify part shipping delays.
                        </div>
                        """, unsafe_allow_html=True)
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
