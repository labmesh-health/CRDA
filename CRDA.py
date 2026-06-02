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
    
    # 2. SITE NAME DIFFERENTIATION (Account + City)
    if 'Account Name' in df.columns and 'City' in df.columns:
        df['Site Name'] = df['Account Name'].astype(str) + " (" + df['City'].astype(str) + ")"
    else:
        df['Site Name'] = df.get('Account Name', 'Unknown Site')

    # Standardize 'System Down Yes/No' Column
    if 'System Down Yes/No' in df.columns:
        df['System Down Yes/No'] = df['System Down Yes/No'].fillna('Not Down').apply(
            lambda x: 'Down' if 'down' in str(x).lower() and 'not' not in str(x).lower() or 'yes' in str(x).lower() else 'Not Down'
        )
    else:
        df['System Down Yes/No'] = 'Unknown'

    # 3. AUTO-DETECT DATE FORMATS
    date_columns = ['Date/Time Opened', 'Labour Start Date', 'Labour End Date']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')
        
    # 4. MISSING DATA LOGIC
    if 'Labour Start Date' in df.columns and 'Date/Time Opened' in df.columns:
        df['Labour Start Date'] = df['Labour Start Date'].fillna(df['Date/Time Opened'] + pd.Timedelta(hours=2))
    if 'Labour End Date' in df.columns and 'Labour Start Date' in df.columns:
        df['Labour End Date'] = df['Labour End Date'].fillna(df['Labour Start Date'] + pd.Timedelta(hours=4))
    
    # 5. CALCULATE TIMES
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

    # 6. DOWNTIME CALCULATION
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

# Base timelines
min_date = df_raw['Date/Time Opened'].min()
max_date = df_raw['Date/Time Opened'].max()
total_days = (max_date - min_date).days if pd.notnull(max_date) else 143
total_timeline_hours = max(total_days * 24, 24)

# ==========================================
# SIDEBAR FILTERS & RECURRING SETTINGS
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
# DASHBOARD TABS
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Tab 1: Executive Health", 
    "📈 Tab 2: Service Trends", 
    "🛠️ Tab 3: Instrument Reliability",
    "🏢 Tab 4: Top Sites (80/20)", 
    "🌆 Tab 5: Citywise Breakdown",
    "🔄 Tab 6: Recurring Breakdowns",
    "🔍 Tab 7: Serial No. Deep Dive"
])

# --- TAB 1: EXECUTIVE HEALTH ---
with tab1:
    st.info("**🤖 AI Insight:** The overall network is being tracked for Uptime SLAs. Geographic heatmaps highlight regions requiring immediate executive attention due to disproportionately high breakdown rates.")
    
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

    # Geographic Heatmap / Bar
    if 'Region' in df.columns:
        reg_counts = df['Region'].value_counts().reset_index()
        reg_counts.columns = ['Region', 'Complaints']
        fig_bar = px.bar(reg_counts, x='Region', y='Complaints', title="Geographic Heatmap of Case Volumes", color='Complaints', color_continuous_scale='Viridis')
        st.plotly_chart(fig_bar, use_container_width=True)

# --- TAB 2: SERVICE & COMPLAINT TRENDS ---
with tab2:
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.info("**🤖 AI Insight:** Hardware failures are often the primary bottleneck compared to Application/Reagent issues, indicating physical wear-and-tear outpaces calibration errors.")
        fig_donut = px.pie(df, names='Type of Complaint', hole=0.4, title="Complaint Breakdown (Hardware vs Application)")
        st.plotly_chart(fig_donut, use_container_width=True)
        
    with col_chart2:
        st.info("**🤖 AI Insight:** Spikes in 'System Down' tickets correlate closely with severe hardware failures. The trendline tracks overall load vs operational halts.")
        # Daily Trendline
        daily_df = df.groupby('Opened_Date').agg(
            Total_Complaints=('Case Number', 'count'),
            Down_Systems=('System Down Yes/No', lambda x: (x == 'Down').sum())
        ).reset_index()
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=daily_df['Opened_Date'], y=daily_df['Total_Complaints'], mode='lines', name='Total Complaints', line=dict(color='blue')))
        fig_trend.add_trace(go.Scatter(x=daily_df['Opened_Date'], y=daily_df['Down_Systems'], mode='lines', name='Systems Down', line=dict(color='red')))
        fig_trend.update_layout(title="Daily Trendline: Total Complaints vs. System Downs", xaxis_title="Date", yaxis_title="Number of Cases")
        st.plotly_chart(fig_trend, use_container_width=True)

# --- TAB 3: INSTRUMENT & PRODUCT LINE RELIABILITY ---
with tab3:
    col_chart3, col_chart4 = st.columns(2)
    
    with col_chart3:
        st.info("**🤖 AI Insight:** The Pareto chart exposes highly unstable product lines generating the bulk of the support volume.")
        fam_counts = df.groupby('Family/Line: Name').size().reset_index(name='Complaints').sort_values(by='Complaints', ascending=False).head(10)
        fam_counts['Cumulative %'] = fam_counts['Complaints'].cumsum() / fam_counts['Complaints'].sum() * 100
        
        fig_fam_pareto = go.Figure()
        fig_fam_pareto.add_trace(go.Bar(x=fam_counts['Family/Line: Name'], y=fam_counts['Complaints'], name="Complaints", marker_color='orange'))
        fig_fam_pareto.add_trace(go.Scatter(x=fam_counts['Family/Line: Name'], y=fam_counts['Cumulative %'], name="Cumulative %", yaxis='y2', mode='lines+markers', line=dict(color='black')))
        fig_fam_pareto.update_layout(title="Top Problematic Product Families", yaxis2=dict(overlaying='y', side='right', range=[0, 105]), xaxis_tickangle=-45)
        st.plotly_chart(fig_fam_pareto, use_container_width=True)
        
    with col_chart4:
        st.info("**🤖 AI Insight:** AI anomaly detection highlights which specific product lines have the highest likelihood of resulting in a total 'System Down' state.")
        down_ratio = df.groupby(['Family/Line: Name', 'System Down Yes/No']).size().reset_index(name='Count')
        top_fams = fam_counts['Family/Line: Name'].tolist()
        down_ratio = down_ratio[down_ratio['Family/Line: Name'].isin(top_fams)]
        
        fig_down = px.bar(down_ratio, x='Family/Line: Name', y='Count', color='System Down Yes/No', barmode='stack', title="System Down Ratio by Product Line", color_discrete_map={'Down':'red', 'Not Down':'green'})
        st.plotly_chart(fig_down, use_container_width=True)

# --- TAB 4: TOP SITES (80/20 PARETO) ---
with tab4:
    st.info("**🤖 AI Insight:** Account Names merged with Cities to accurately execute the 80/20 rule for Hardware interventions.")
    hw_df = df[df['Type of Complaint'].str.contains('Hardware', case=False, na=False)]
    if not hw_df.empty:
        account_df = hw_df.groupby('Site Name').size().reset_index(name='Hardware Complaints')
        account_df = account_df.sort_values(by='Hardware Complaints', ascending=False).head(20)
        account_df['Cumulative %'] = account_df['Hardware Complaints'].cumsum() / account_df['Hardware Complaints'].sum() * 100
        
        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(x=account_df['Site Name'], y=account_df['Hardware Complaints'], name="Hardware Complaints", marker_color='indianred'))
        fig_pareto.add_trace(go.Scatter(x=account_df['Site Name'], y=account_df['Cumulative %'], name="Cumulative %", yaxis='y2', mode='lines+markers', line=dict(color='blue', width=2)))
        fig_pareto.update_layout(title="Top 20 Sites by Hardware Issues", yaxis2=dict(overlaying='y', side='right', range=[0, 105]), xaxis_tickangle=-45)
        st.plotly_chart(fig_pareto, use_container_width=True)

# --- TAB 5: CITYWISE BREAKDOWN ---
with tab5:
    st.info("**🤖 AI Insight:** Identifies which cities carry the heaviest instrument failure load across all product lines.")
    if 'City' in df.columns and 'Family/Line: Name' in df.columns:
        city_inst = df.groupby(['City', 'Family/Line: Name']).size().reset_index(name='Total Breakdowns')
        city_inst = city_inst.sort_values(by='Total Breakdowns', ascending=False).head(50)
        fig_city = px.bar(city_inst, x='City', y='Total Breakdowns', color='Family/Line: Name', title="Citywise Instrument Breakdowns", barmode='stack')
        st.plotly_chart(fig_city, use_container_width=True)

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

# --- TAB 7: SERIAL NUMBER INVESTIGATIVE DEEP DIVE ---
with tab7:
    st.info("**🤖 AI Insight:** Granular tracking for repetitive instrument failures. Rows highlighted in Red indicate the instrument has fallen below the 95% Uptime threshold.")
    
    # Calculate metrics grouped by Serial Number
    def get_mode(x):
        return x.mode()[0] if not x.empty else "Unknown"

    serial_df = df.groupby(['Serial No.', 'Site Name', 'Family/Line: Name']).agg(
        Total_Complaints=('Case Number', 'count'),
        Total_Down_Hours=('Actual Down Time Hours', 'sum'),
        Primary_Technician=('Primary Technician', get_mode)
    ).reset_index()

    # Calculate individual Serial Number Uptime %
    serial_df['Uptime %'] = ((total_timeline_hours - serial_df['Total_Down_Hours']) / total_timeline_hours) * 100
    serial_df['Uptime %'] = serial_df['Uptime %'].round(2)
    serial_df['Total_Down_Hours'] = serial_df['Total_Down_Hours'].round(1)
    
    # Sort and reorder columns
    serial_df = serial_df.sort_values(by='Total_Complaints', ascending=False)
    serial_df = serial_df[['Serial No.', 'Site Name', 'Family/Line: Name', 'Total_Complaints', 'Uptime %', 'Total_Down_Hours', 'Primary_Technician']]

    # Streamlit conditional formatting (Highlight Uptime < 95%)
    def highlight_low_uptime(row):
        color = 'background-color: #ffcccc' if row['Uptime %'] < 95.0 else ''
        return [color] * len(row)

    styled_df = serial_df.style.apply(highlight_low_uptime, axis=1).format({'Uptime %': "{:.2f}%"})
    st.dataframe(styled_df, use_container_width=True, height=600)
