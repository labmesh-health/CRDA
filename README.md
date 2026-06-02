# CRDA
# 🔬 Customer Rexis Service & Reliability Dashboard

This project is a dynamic, Python-based Streamlit dashboard designed to analyze and visualize field service data for Customer Rexis (Metropolis Healthcare network). 

It automatically processes service records to provide real-time AI-driven insights, calculates complex SLAs (Response and Resolution times), tracks instrument uptime on a 24-hour timeline, and highlights chronic hardware failures using the 80/20 Pareto principle.

## ✨ Key Features
* **Automated Data Cleaning**: Automatically handles missing dates, detects varying date formats, and computes SLA metrics.
* **Uptime Engine**: Calculates true instrument uptime % across a 24-hour continuous timeline.
* **SLA Bucketing**: Dynamically buckets response and resolution times (<24h, 24-48h, 48-72h, etc.) to track service speed.
* **80/20 Pareto Analysis**: Identifies the high-risk customer sites that generate the majority of hardware-related complaints.
* **Serial Number Tracking**: Deep dive into individual instrument (Serial No.) reliability to flag "lemon" machines.
* **Contextual AI Insights**: Every tab generates automated text-based insights based on the real-time filtered data.

## 🛠️ Tech Stack
* **Language**: Python 3.8+
* **Frontend/Framework**: Streamlit
* **Data Processing**: Pandas, NumPy
* **Data Visualization**: Plotly (Express & Graph Objects)

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/customer-rexis-dashboard.git](https://github.com/yourusername/customer-rexis-dashboard.git)
   cd customer-rexis-dashboard
