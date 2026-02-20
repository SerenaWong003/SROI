import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import os

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="SROI Professional Calculator", layout="wide")

# --- 2. ปรับแต่ง CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="metric-container"] {
        background-color: #ffffff !important;
        border: 1px solid #dee2e6;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
    }
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #000000 !important; font-weight: 600; }
    .info-box { 
        background-color: #ffffff; padding: 20px; border-radius: 8px; 
        border: 1px solid #2980b9; border-left: 10px solid #2980b9;
        margin-bottom: 25px; color: #000000 !important;
    }
    .section-head {
        background-color: #e8f4f8; padding: 10px; border-radius: 5px;
        font-weight: bold; color: #2c3e50; margin-bottom: 15px;
        border-left: 5px solid #3498db;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ฟังก์ชันสำหรับล้างข้อมูล ---
def reset_system():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.num_rows = 1
    st.rerun()

st.title("📊 SROI Calculator for University Research")

# --- 4. ส่วนอธิบายศัพท์ ---
with st.expander("ℹ️ คำอธิบายศัพท์เทคนิคในการคำนวณ SROI", expanded=False):
    st.markdown("""
    <div class="info-box">
    <p><b>1. Deadweight:</b> ผลลัพธ์ที่จะเกิดขึ้นอยู่แล้วแม้ไม่มีโครงการ</p>
    <p><b>2. Displacement:</b> การย้ายปัญหาจากจุดหนึ่งไปอีกจุดหนึ่ง</p>
    <p><b>3. Attribution:</b> ผลที่เกิดจากปัจจัยภายนอกที่ไม่ใช่โครงการเรา 100%</p>
    <p><b>4. Drop-off:</b> อัตราที่ผลประโยชน์ลดลงในแต่ละปีหลังโครงการสิ้นสุด</p>
    </div>
    """, unsafe_allow_html=True)

# --- 5. Logic การคำนวณ ---
def calculate_advanced_sroi(total_input, discount_rate, duration, outcomes):
    detailed_list = []
    yearly_totals = [0.0] * duration 
    for item in outcomes:
        if not item['outcome_text']: continue
        dw_f = item['dw'] / 100
        disp_f = item['disp'] / 100
        att_f = item['attr'] / 100
        drp_f = item['drop_off'] / 100
        
        initial_impact = (item['proxy_val'] * item['qty']) * (1 - dw_f) * (1 - disp_f) * (1 - att_f)
        current_impact = initial_impact
        item_total_pv = 0
        item_yearly_pvs = []
        for year_idx in range(duration):
            year_num = year_idx + 1
            if year_
