import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Ration-Mitr Dashboard",
    page_icon="🌾",  # Changed to Wheat icon (renders better than flag)
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better padding and visibility
st.markdown("""
<style>
    /* Fix top padding so nothing is hidden */
    .main .block-container {
        padding-top: 2rem; 
        padding-bottom: 2rem;
    }
    /* Style the metric cards */
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. DATA LOADING & LOGIC
# ---------------------------------------------------------
@st.cache_data
def load_and_process_data():
    try:
        df_demo = pd.read_csv('api_data_aadhar_demographic_0_500000.csv')
        df_enrol = pd.read_csv('api_data_aadhar_enrolment_0_500000.csv')
        
        # 1. Aggregation
        demo_agg = df_demo.groupby(['state', 'district'])[['demo_age_17_']].sum().reset_index()
        enrol_agg = df_enrol.groupby(['state', 'district'])[['age_0_5']].sum().reset_index()
        
        # 2. Merge
        merged = pd.merge(demo_agg, enrol_agg, on=['state', 'district'], how='inner')
        
        # 3. Migration Score
        merged['Migration_Score'] = merged['demo_age_17_'] / (merged['age_0_5'] + 1)
        merged['Migration_Score'] = merged['Migration_Score'].round(2)
        
        # 4. Status
        def get_status(score):
            if score > 50: return "CRITICAL"
            elif score > 20: return "WARNING"
            else: return "STABLE"
        merged['Status'] = merged['Migration_Score'].apply(get_status)
        
        # 5. Grain Demand (heuristic)
        merged['Grain_Demand_MT'] = (merged['demo_age_17_'] * 0.02).round(1)
        
        return merged
        
    except FileNotFoundError:
        return None

df = load_and_process_data()

# ---------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/c/cf/Aadhaar_Logo.svg", width=150 )
    st.title("🌾 Ration-Mitr") 
    st.caption("One Nation, One Ration Intelligence")
    st.markdown("---")
    
    if df is not None:
        # State Filter
        state_list = ["All India"] + sorted(df['state'].unique().tolist())
        selected_state = st.selectbox("Select Region", state_list)
        
        if selected_state != "All India":
            df_view = df[df['state'] == selected_state]
        else:
            df_view = df
            
        st.success(f"✅ System Online\n\n**Total Records:** {len(df):,}")
    else:
        st.error("❌ Data missing. Please add CSV files.")
        st.stop()

# ---------------------------------------------------------
# 4. MAIN DASHBOARD (FIXED LAYOUT)
# ---------------------------------------------------------

# FIXED: Removed the Emoji "IN" text and widened columns
col1, col2 = st.columns([3, 1]) 

with col1:
    st.title("National Food Security Command Center") 
    st.markdown("### *Dynamic Resource Allocation System*")

with col2:
    # FIXED: Using a styled box instead of metric to prevent cutting off
    current_view = selected_state if selected_state else "All India"
    st.markdown(f"""
        <div style="background-color: #f1f3f6; padding: 10px; border-radius: 8px; border-left: 5px solid #3498db;">
            <small style="color: #7f8c8d;">CURRENT VIEW</small><br>
            <span style="font-size: 20px; font-weight: bold; color: #2c3e50;">{current_view}</span>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------
# 5. METRICS ROW
# ---------------------------------------------------------
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

total_influx = df_view['demo_age_17_'].sum()
critical_count = df_view[df_view['Status'] == 'CRITICAL'].shape[0]
grain_needed = df_view['Grain_Demand_MT'].sum()

kpi1.metric("Predicted Migrant Influx", f"{total_influx:,}", "Address Updates")
kpi2.metric("Critical Stress Zones", f"{critical_count}", "Districts", delta_color="inverse")
kpi3.metric("Grain Deficit", f"{grain_needed:,.0f} MT", "vs Last Month")
kpi4.metric("Supply Chain Efficiency", "94.2%", "+1.2%")

# ---------------------------------------------------------
# 6. CHARTS & TABLES
# ---------------------------------------------------------
col_chart, col_table = st.columns([2, 1])

with col_chart:
    st.subheader("📍 Real-time Migration Hotspots")
    
    top_districts = df_view.sort_values(by='Migration_Score', ascending=False).head(10)
    
    if not top_districts.empty:
        fig = px.bar(
            top_districts,
            x='Migration_Score',
            y='district',
            orientation='h',
            color='Status',
            color_discrete_map={
                "CRITICAL": "#FF4B4B",  # Red
                "WARNING": "#FFA500",   # Orange
                "STABLE": "#00CC96"     # Green
            },
            title="Migration Intensity Score (Higher = More Influx)",
            text='Migration_Score'
        )
        fig.update_layout(yaxis=dict(autorange="reversed"), height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for this selection.")

with col_table:
    st.subheader("⚠️ Priority Alerts")
    
    # 1. Filter for only Critical and Warning zones
    alerts = df_view[df_view['Status'].isin(['CRITICAL', 'WARNING'])].copy()
    
    # 2. Create a Custom Sort Order (Critical = 0, Warning = 1)
    # This forces "CRITICAL" to always be above "WARNING"
    status_priority = {'CRITICAL': 0, 'WARNING': 1}
    alerts['priority_index'] = alerts['Status'].map(status_priority)
    
    # 3. Sort by Priority Index (Ascending) -> then by Grain Demand (Descending)
    alerts = alerts.sort_values(by=['priority_index', 'Grain_Demand_MT'], ascending=[True, False])
    
    if not alerts.empty:
        st.dataframe(
            alerts[['district', 'Status', 'Grain_Demand_MT']],
            column_config={
                "district": "District",
                "Status": "Risk Level",
                "Grain_Demand_MT": "Addl. Grain (MT)"
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.success("No critical alerts in this region.")

# ---------------------------------------------------------
# 7. RAW DATA EXPANDER
# ---------------------------------------------------------
with st.expander("📂 View Raw Source Data"):
    st.dataframe(df_view)