import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime

# --- การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="SROI Calculator Tool", layout="wide")

# ปรับแต่ง CSS เพื่อความสวยงาม
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .info-box { background-color: #e8f4f8; padding: 15px; border-radius: 8px; border-left: 5px solid #2980b9; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 SROI Calculator for University Research")

# --- ส่วนอธิบายศัพท์ ---
with st.expander("ℹ️ คำอธิบายศัพท์เทคนิคในการคำนวณ SROI", expanded=False):
    st.markdown("""
    <div class="info-box">
    <b>1. Deadweight:</b> ผลลัพธ์ที่จะเกิดขึ้นอยู่แล้วแม้ไม่มีโครงการ <br>
    <b>2. Displacement:</b> ผลของโครงการที่ไปทำให้เกิดปัญหาในที่อื่นแทน <br>
    <b>3. Attribution:</b> ผลที่เกิดจากปัจจัยภายนอกหรือหน่วยงานอื่น <br>
    <b>4. Drop-off:</b> อัตราการลดลงของผลประโยชน์หลังจากโครงการสิ้นสุด
    </div>
    """, unsafe_allow_html=True)

# --- Logic การคำนวณ ---
def calculate_sroi(total_input, discount_rate, duration, outcomes):
    total_present_value = 0
    detailed_list = []
    
    for item in outcomes:
        if not item['stakeholder']: continue
        
        # คำนวณ Impact ปีแรก
        initial_impact = (item['proxy'] * item['qty']) * \
                         (1 - item['dw']) * (1 - item['disp']) * (1 - item['attr'])
        
        item_pv_sum = 0
        current_impact = initial_impact
        
        for year in range(1, duration + 1):
            if year > 1:
                current_impact *= (1 - item['drop_off'])
            # PV = Impact / (1 + r)^n
            pv = current_impact / ((1 + (discount_rate/100)) ** year)
            item_pv_sum += pv
        
        total_present_value += item_pv_sum
        detailed_list.append({**item, "item_pv": item_pv_sum})
    
    ratio = total_present_value / total_input if total_input > 0 else 0
    return ratio, total_present_value, detailed_list

# --- ส่วน Sidebar ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าโครงการ")
    project_name = st.text_input("ชื่อโครงการ", value="SROI_Project_2026")
    total_input = st.number_input("งบประมาณโครงการ (บาท)", value=100000, step=1000)
    discount_rate = st.number_input("Discount Rate (%)", value=3.5, step=0.1)
    duration = st.slider("ระยะเวลาที่คำนวณ (ปี)", 1, 10, 5)
    st.divider()
    st.caption("จั่นเจา รายงาน: ตรวจสอบงบประมาณก่อนคำนวณเสมอ
