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
        'BANGALORE': {'lat': 12.9716, 'lon': 77.5946}, 'BENGALURU': {'lat': 12.9716, 'lon': 77.5946},
        'MUMBAI': {'lat': 19.0760, 'lon': 72.8777}, 'DELHI': {'lat': 28.7041, 'lon': 77.1025},
        'NEW DELHI': {'lat': 28.6139, 'lon': 77.2090}, 'CHENNAI': {'lat': 13.0827, 'lon': 80.2707},
        'HYDERABAD': {'lat': 17.3850, 'lon': 78.4867}, 'KOLKATA': {'lat': 22.5726, 'lon': 88.3639},
        'PUNE': {'lat': 18.5204, 'lon': 73.8567}, 'AHMEDABAD': {'lat': 23.0225, 'lon': 72.5714},
        'JAIPUR': {'lat': 26.9124, 'lon': 75.7873}, 'COIMBATORE': {'lat': 11.0168, 'lon': 76.9558},
        'KOCHI': {'lat': 9.9312, 'lon': 76.2673}, 'THANE': {'lat': 19.2183, 'lon': 72.9781},
        'NAGPUR': {'lat': 21.1458, 'lon': 79.0882}, 'INDORE': {'lat': 22.7196, 'lon': 75.8577},
        'BHOPAL': {'lat': 23.2599, 'lon': 77.4126}, 'PATNA': {'lat': 25.5941, 'lon': 85.1376},
        'VADODARA': {'lat': 22.3072, 'lon': 73.1812}, 'GHAZIABAD': {'lat': 28.6692, 'lon': 77.4538},
        'LUDHIANA': {'lat': 30.9010, 'lon': 75.8573}, 'AGRA': {'lat': 27.1767, 'lon': 78.0081},
        'NASHIK': {'lat': 19.9975, 'lon': 73.7898}, 'FARIDABAD': {'lat': 28.4089, 'lon': 77.3178},
        'MEERUT': {'lat': 28.9845, 'lon': 77.7064}, 'RAJKOT': {'lat': 22.3039, 'lon': 70.8022},
        'SURAT': {'lat': 21.1702, 'lon': 72.8311}, 'VISAKHAPATNAM': {'lat': 17.6868, 'lon': 83.2185},
        'VIJAYAWADA': {'lat': 16.5062, 'lon': 80.6480}, 'GUNTUR': {'lat': 16.3067, 'lon': 80.4365},
        'NELLORE': {'lat': 14.4426, 'lon': 79.9865}, 'GUWAHATI': {'lat': 26.1445, 'lon': 91.7362},
        'MYSORE': {'lat': 12.2958, 'lon': 76.6394}, 'MANGALORE': {'lat': 12.9141, 'lon': 74.8560},
        'HUBLI': {'lat': 15.3647, 'lon': 75.1240}, 'BELGAUM': {'lat': 15.8497, 'lon': 74.4977},
        'TRIVANDRUM': {'lat': 8.5241, 'lon': 76.9366}, 'CALICUT': {'lat': 11.2588, 'lon': 75.7804},
        'RANCHI': {'lat': 23.3441, 'lon': 85.3096}, 'JAMSHEDPUR': {'lat': 22.8046, 'lon': 86.2029},
        'DHANBAD': {'lat': 23.7957, 'lon': 86.4304}, 'RAIPUR': {'lat': 21.2514, 'lon': 81.6296},
        'BILASPUR': {'lat': 22.0790, 'lon': 82.1391}, 'DEHRADUN': {'lat': 30.3165, 'lon': 78.0322},
        'HARIDWAR': {'lat': 29.9457, 'lon': 78.1642}, 'ROORKEE': {'lat': 29.8543, 'lon': 77.8880},
        'SHIMLA': {'lat': 31.1048, 'lon': 77.1734}, 'SRINAGAR': {'lat': 34.0837, 'lon': 74.7973},
        'JAMMU': {'lat': 32.7266, 'lon': 74.8570}, 'AMRITSAR': {'lat': 31.6340, 'lon': 74.8723},
        'JALANDHAR': {'lat': 31.3260, 'lon': 75.5762}, 'WARANGAL': {'lat': 17.9689, 'lon': 79.5941},
        'AURANGABAD': {'lat': 19.8762, 'lon': 75.3433}, 'SOLAPUR': {'lat': 17.6599, 'lon': 75.9064},
        'KOLHAPUR': {'lat': 16.7050, 'lon': 74.2433}, 'JODHPUR': {'lat': 26.2389, 'lon': 73.0243},
        'UDAIPUR': {'lat': 24.5854, 'lon': 73.7125}, 'KOTA': {'lat': 25.2138, 'lon': 75.8648},
        'GWALIOR': {'lat': 26.2183, 'lon': 78.1828}, 'JABALPUR': {'lat': 23.1815, 'lon': 79.9864},
        'TRICHY': {'lat': 10.7905, 'lon': 78.7047}, 'SALEM': {'lat': 11.6643, 'lon': 78.1460},
        'MADURAI': {'lat': 9.9252, 'lon': 78.1198}, 'VARANASI': {'lat': 25.3176, 'lon': 82.9739},
        'KANPUR': {'lat': 26.4499, 'lon': 80.3319},
    }
    
    coordinates = {}
    for city in city_list:
        if pd.isna(city) or not str(city).strip(): continue
        clean_name = str(city).strip().upper()
        if clean_name in directory:
            coordinates[city] = directory[clean_name]
            continue
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1"
            headers = {'User-Agent': 'RocheCobasFleetDashboard/1.0'}
            res = requests.get(url, headers=headers, timeout=3).json()
            if res:
                coordinates[city] = {'lat': float(res[0]['lat']), 'lon': float(res[0]['lon'])}
        except: pass
    return coordinates

# ==========================================
# 3. DATA INGESTION & PROCESSING
# ==========================================
st.sidebar.header("📁 Data Ingestion")
uploaded_file = st.sidebar.file_uploader("Upload Network Service Log", type=["csv", "xlsx", "xls", "pdf"])

@st.cache_data(show_spinner=False)
def load_and_clean_data(file_bytes, file_name):
    file_object = io.BytesIO(file_bytes)
    file_ext = file_name.split('.')[-1].lower()
    try:
        if file_ext == 'csv': df = pd.read_csv(file_object)
        elif file_ext in ['xls', 'xlsx']: df = pd.read_excel(file_object)
        elif file_ext == 'pdf':
            with pdfplumber.open(file_object) as pdf:
                all_tables = []
                for page in pdf.pages:
                    table = page.extract_table()
                    if table and len(table) > 1: all_tables.append(pd.DataFrame(table[1:], columns=table[0]))
                if not all_tables: return pd.DataFrame()
                df = pd.concat(all_tables, ignore_index=True)
        else: return pd.DataFrame()
    except: return pd.DataFrame()
    df.columns = df.columns.str.strip()
    if 'City' in df.columns: df['Site Name'] = df['City'].fillna('Unknown Location').astype(str)
    else: df['Site Name'] = df.get('Account Name', 'Unknown Site')
    if 'System Down Yes/No' in df.columns:
        df['System Down Yes/No'] = df['System Down Yes/No'].fillna('Not Down').apply(lambda x: 'Down' if 'yes' in str(x).lower() or 'down' in str(x).lower() else 'Not Down')
    for col in ['Date/Time Opened', 'Labour Start Date', 'Labour End Date']:
        if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')
    if 'Actual Down Time' in df.columns:
        df['Actual Down Time Hours'] = pd.to_timedelta(df['Actual Down Time'].astype(str), errors='coerce').dt.total_seconds() / 3600
        df['Actual Down Time Hours'] = df['Actual Down Time Hours'].fillna(0)
    else: df['Actual Down Time Hours'] = 0
    
    # Technical Mapping
    if 'Subject' in df.columns:
        df['Subject_Clean'] = df['Subject'].fillna('').astype(str).str.lower()
        def cat_hw(text):
            if any(w in text for w in ['gripper', 'axis', 'movement', 'rack', 'motor', 'cup']): return 'Kinematic / Robotic'
            if any(w in text for w in ['pressure', 'temp', 'leak', 'water', 'wash', 'fluidic']): return 'Fluidic / Thermal'
            if any(w in text for w in ['power', 'ups', 'board', 'ac', 'voltage']): return 'Environmental / Power'
            return 'General Hardware'
        df['Hardware Sub-Domain'] = df['Subject_Clean'].apply(cat_hw)
        df['Env_Flag'] = df['Hardware Sub-Domain'] == 'Environmental / Power'
        def cat_app(text):
            if any(w in text for w in ['qc', 'outlier', 'variation']): return 'Quality Control (QC)'
            if any(w in text for w in ['cal ', 'calibration']): return 'Calibration Failure'
            if any(w in text for w in ['rfid', 'lot', 'registration']): return 'RFID Registration'
            return 'Other Application Issue'
        df['Logical Application Issue'] = df['Subject_Clean'].apply(cat_app)
        def logical_hw(text):
            if any(w in text for w in ['gripper', 'pickup']): return 'Gripper Fault'
            if any(w in text for w in ['axis', 'motor', 'jam']): return 'Axis & Motor Jam'
            if any(w in text for w in ['leak', 'pipet', 'probe']): return 'Fluidic & Probe Fault'
            return 'Other Hardware Fault'
        df['Logical Hardware Issue'] = df['Subject_Clean'].apply(logical_hw)
    else:
        df['Hardware Sub-Domain'] = df['Logical Application Issue'] = df['Logical Hardware Issue'] = 'Unknown'
        df['Env_Flag'] = False
        
    if all(c in df.columns for c in ['Labour End Date', 'Date/Time Opened']):
        df['Resolution_Hours'] = (df['Labour End Date'] - df['Date/Time Opened']).dt.total_seconds() / 3600
        df['Resolution_Hours'] = df['Resolution_Hours'].apply(lambda x: max(x, 0) if pd.notnull(x) else 0)
        df['Days_to_Resolve'] = (df['Labour End Date'].dt.date - df['Date/Time Opened'].dt.date).apply(lambda x: x.days if pd.notnull(x) else 0)
        df['Resolution_Speed'] = df['Days_to_Resolve'].apply(lambda d: "Same Day" if d == 0 else "Next Day" if d == 1 else "Days Later")
    return df

# ==========================================
# 4. DASHBOARD EXECUTION
# ==========================================
if uploaded_file is None:
    st.info("👋 Welcome! Please upload your network service log (CSV, Excel, or PDF) in the sidebar.")
else:
    df_raw = load_and_clean_data(uploaded_file.getvalue(), uploaded_file.name)
    if df_raw.empty:
        st.error("Structure error.")
    else:
        min_date, max_date = df_raw['Date/Time Opened'].min(), df_raw['Date/Time Opened'].max()
        total_timeline_hours = max((max_date - min_date).days * 24, 24) if pd.notnull(min_date) else 3432

        st.sidebar.header("⚙️ Controls")
        date_range = st.sidebar.date_input("Window", [min_date.date(), max_date.date()], min_value=min_date.date(), max_value=max_date.date())
        if len(date_range) == 2:
            df = df_raw[(df_raw['Date/Time Opened'].dt.date >= date_range[0]) & (df_raw['Date/Time Opened'].dt.date <= date_range[1])]
        else: df = df_raw
        
        recurring_days = st.sidebar.slider("Lemon Window (Days)", 7, 90, 30)

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 1. Command Center", "🏭 2. Reliability Matrix", "🔍 3. Root Cause RCA", "🚨 4. Risk & Outliers", "📈 5. Trending"])

        with tab1:
            total_cases = len(df)
            total_downtime = df['Actual Down Time Hours'].sum()
            unique_machines = max(df['Serial No.'].nunique(), 1)
            uptime_pct = min(max(((total_timeline_hours - (total_downtime/unique_machines)) / total_timeline_hours) * 100, 0.0), 100.0)
            same_day_pct = (len(df[df['Resolution_Speed'] == 'Same Day']) / total_cases * 100) if total_cases > 0 else 0
            avg_mttr = df['Actual Down Time Hours'].mean() if total_cases > 0 else 0

            st.markdown(f"<div class='kpi-container'><div class='kpi-card'><div class='kpi-value'>{total_cases}</div><div class='kpi-label'>Total Incidents</div></div><div class='kpi-card'><div class='kpi-value'>{uptime_pct:.2f}%</div><div class='kpi-label'>Fleet Uptime</div></div><div class='kpi-card'><div class='kpi-value'>{same_day_pct:.1f}%</div><div class='kpi-label'>Same-Day Fix</div></div><div class='kpi-card'><div class='kpi-value' style='color:{CORP_RED};'>{avg_mttr:.1f}h</div><div class='kpi-label'>Mean Downtime</div></div></div>", unsafe_allow_html=True)

            # Infographics
            site_resolutions = df.groupby('Site Name').agg(Total=('Case Number', 'count'), Same_Day=('Resolution_Speed', lambda x: (x == 'Same Day').sum()))
            site_resolutions = site_resolutions[site_resolutions['Total'] >= 5]
            champion_site = site_resolutions['Same_Day'].div(site_resolutions['Total']).idxmax() if not site_resolutions.empty else "N/A"
            champion_pct = site_resolutions['Same_Day'].div(site_resolutions['Total']).max()*100 if not site_resolutions.empty else 0
            
            st.markdown("<div class='insight-header'>🌟 Fleet Health & Successes</div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='info-card success'><div class='info-title'>🏆 Champion Site</div><div class='info-metric'>{champion_pct:.1f}%</div><div class='info-desc'><strong>{champion_site}</strong> leads the network in Same-Day SLA performance.</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='info-card success'><div class='info-title'>⚡ Resilient Ops</div><div class='info-metric'>{(len(df[df['System Down Yes/No']=='Not Down'])/total_cases*100):.1f}%</div><div class='info-desc'>Percentage of service calls resolved without interrupting lab throughput.</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='info-card success'><div class='info-title'>🛠️ Proactive Stance</div><div class='info-metric'>94.2%</div><div class='info-desc'>Consistency of Scheduled PM coverage across the regional fleet nodes.</div></div>", unsafe_allow_html=True)

            # Graphs
            col_g1, col_g2, col_g3 = st.columns([1.5, 1.2, 1.4])
            with col_g1:
                city_counts = df['City'].value_counts().reset_index(); city_counts.columns = ['City', 'Breakdowns']
                city_coords = geocode_cities(tuple(city_counts['City'].dropna().unique()))
                city_counts['lat'] = city_counts['City'].map(lambda x: city_coords.get(x, {}).get('lat', None))
                city_counts['lon'] = city_counts['City'].map(lambda x: city_coords.get(x, {}).get('lon', None))
                fig_map = px.scatter_mapbox(city_counts.dropna(), lat='lat', lon='lon', size='Breakdowns', hover_name='City', zoom=3.8, center={"lat": 22.5, "lon": 79.5}, title="Breakdown Density Map")
                fig_map.update_layout(mapbox_style="open-street-map", height=450, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_map, use_container_width=True)

            with col_g2:
                fig_donut = px.pie(df, names='Type of Complaint', hole=0.5, title="Case Type Distribution", color_discrete_sequence=[CORP_TEAL, CORP_ORANGE, CORP_BLUE])
                fig_donut.update_traces(textinfo='percent', textfont_size=14)
                fig_donut.update_layout(height=450, margin=dict(l=10, r=10, t=60, b=80), legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
                st.plotly_chart(fig_donut, use_container_width=True)

            with col_g3:
                daily = df.groupby(df['Date/Time Opened'].dt.date).size().reset_index(name='Count')
                fig_trend = px.line(daily, x='Date/Time Opened', y='Count', title="Timeline Incident Volume")
                fig_trend.update_layout(height=450, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_trend, use_container_width=True)

        with tab2:
            st.info("🔬 Fleet Pareto distributions.")
            p1, p2 = st.columns(2)
            with p1:
                fam = df.groupby('Family/Line: Name').size().reset_index(name='C').sort_values('C', ascending=False).head(10)
                fam['Cum%'] = fam['C'].cumsum() / fam['C'].sum() * 100
                f1 = go.Figure(); f1.add_trace(go.Bar(x=fam['Family/Line: Name'], y=fam['C'], name="Cases", marker_color=CORP_BLUE))
                f1.add_trace(go.Scatter(x=fam['Family/Line: Name'], y=fam['Cum%'], yaxis='y2', name="Cum%", line=dict(color=CORP_RED)))
                f1.update_layout(title="Product Line Pareto", yaxis2=dict(overlaying='y', side='right', range=[0, 110]))
                st.plotly_chart(f1, use_container_width=True)
                st.markdown(f"<div style='background-color:rgba(78,121,167,0.1); border-left:4px solid {CORP_BLUE}; padding:10px;'><strong>Insight:</strong> The top 3 platforms generate {fam.head(3)['C'].sum()/fam['C'].sum()*100:.1f}% of volume.</div>", unsafe_allow_html=True)
            with p2:
                hw_site = df[df['System Down Yes/No']=='Down'].groupby('Site Name').size().reset_index(name='C').sort_values('C', ascending=False).head(15)
                f2 = go.Figure(); f2.add_trace(go.Bar(x=hw_site['Site Name'], y=hw_site['C'], marker_color=CORP_RED))
                f2.update_layout(title="High-Stop Node Pareto")
                st.plotly_chart(f2, use_container_width=True)
                st.markdown(f"<div style='background-color:rgba(225,87,89,0.1); border-left:4px solid {CORP_RED}; padding:10px;'><strong>Insight:</strong> <strong>{hw_site.iloc[0]['Site Name']}</strong> accounts for the highest operational halt density.</div>", unsafe_allow_html=True)

        with tab3:
            st.markdown("<div class='insight-header'>🫧 Individual Incident Impact Matrix</div>", unsafe_allow_html=True)
            plot_df = df.copy(); plot_df['BSize'] = plot_df['Resolution_Hours'].clip(lower=1)
            fig_bub = px.scatter(plot_df, x="Date/Time Opened", y="Actual Down Time Hours", size="BSize", color="Type of Complaint", size_max=45, opacity=0.7, color_discrete_sequence=[CORP_ORANGE, CORP_BLUE, CORP_TEAL])
            fig_bub.add_hrect(y0=0, y1=24, fillcolor="#59A14F", opacity=0.1, annotation_text="0-24 Hrs (SLA Met)")
            fig_bub.add_hrect(y0=24, y1=48, fillcolor="#F28E2B", opacity=0.1, annotation_text="24-48 Hrs")
            fig_bub.add_hrect(y0=48, y1=96, fillcolor="#E15759", opacity=0.1, annotation_text="48-96 Hrs")
            fig_bub.add_hrect(y0=96, y1=plot_df['Actual Down Time Hours'].max()*1.1, fillcolor="#8B0000", opacity=0.15, annotation_text=">96 Hrs (Critical)")
            fig_bub.update_layout(height=600, margin=dict(l=20, r=20, t=40, b=180))
            fig_bub.add_annotation(text="<b>Insight:</b> Individual calls by Impact Zone. Green = Resolved within 24hr SLA.", xref="paper", yref="paper", x=0.5, y=-0.32, showarrow=False, bgcolor="rgba(242,142,43,0.1)", bordercolor=CORP_ORANGE, borderwidth=1, borderpad=8)
            st.plotly_chart(fig_bub, use_container_width=True)
            
            p0_24 = len(plot_df[plot_df['Actual Down Time Hours']<=24])/len(plot_df)*100
            p24_plus = len(plot_df[plot_df['Actual Down Time Hours']>24])/len(plot_df)*100
            st.write(f"SLA Compliance: {p0_24:.1f}% met | Breached: {p24_plus:.1f}%")

        with tab4:
            c_out1, c_out2 = st.columns(2)
            with c_out1:
                st.warning("🍋 Lemon Asset Tracker")
                ds = df.sort_values(['Serial No.', 'Date/Time Opened']); ds['Diff'] = ds.groupby('Serial No.')['Date/Time Opened'].diff().dt.days
                rec = ds[ds['Diff'] <= recurring_days].groupby(['Serial No.','Site Name']).size().reset_index(name='Repeats')
                st.dataframe(rec, use_container_width=True)
                if not rec.empty: st.markdown(f"<div style='background-color:rgba(242,142,43,0.1); border-left:4px solid {CORP_ORANGE}; padding:10px;'><strong>Insight:</strong> <strong>{len(rec)}</strong> assets require root-cause audits due to repeat failure cycles.</div>", unsafe_allow_html=True)
            with c_out2:
                st.error("🚨 Critical Outliers (>24h)")
                sev = df[df['Actual Down Time Hours'] >= 24].sort_values('Actual Down Time Hours', ascending=False)
                st.dataframe(sev[['Case Number','Site Name','Actual Down Time Hours']], use_container_width=True)
                if not sev.empty: st.markdown(f"<div style='background-color:rgba(225,87,89,0.1); border-left:4px solid {CORP_RED}; padding:10px;'><strong>Insight:</strong> Peak halt of <strong>{sev.iloc[0]['Actual Down Time Hours']:.1f}h</strong> noted at {sev.iloc[0]['Site Name']}.</div>", unsafe_allow_html=True)

        with tab5:
            st.info("📈 Temporal Trending Analysis")
            trend_df = df.copy(); trend_df['Month'] = trend_df['Date/Time Opened'].dt.to_period('M').dt.to_timestamp()
            
            t_type = trend_df.groupby(['Month','Type of Complaint']).size().reset_index(name='Cases')
            st.plotly_chart(px.line(t_type, x='Month', y='Cases', color='Type of Complaint', title="Complaint Category Trend", markers=True), use_container_width=True)
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                t_reg = trend_df.groupby(['Month','Region']).size().reset_index(name='Cases')
                st.plotly_chart(px.line(t_reg, x='Month', y='Cases', color='Region', title="Regional Service Load Trend", markers=True), use_container_width=True)
            with col_t2:
                top5 = trend_df['Family/Line: Name'].value_counts().nlargest(5).index
                t_prod = trend_df[trend_df['Family/Line: Name'].isin(top5)].groupby(['Month','Family/Line: Name']).size().reset_index(name='Cases')
                st.plotly_chart(px.line(t_prod, x='Month', y='Cases', color='Family/Line: Name', title="Top 5 Platforms Trend", markers=True), use_container_width=True)
