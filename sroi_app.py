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

# --- ส่วนอธิบายศัพท์ (ที่นายหญิงต้องการ) ---
with st.expander("ℹ️ คำอธิบายศัพท์เทคนิคในการคำนวณ SROI", expanded=False):
    st.markdown("""
    <div class="info-box">
    <b>1. Deadweight (ผลลัพธ์ส่วนเกิน):</b> มูลค่าของผลลัพธ์ที่คาดว่าจะเกิดขึ้นอยู่แล้ว แม้จะไม่มีโครงการนี้ก็ตาม (เช่น แนวโน้มรายได้ที่เพิ่มขึ้นตามปกติของชุมชน) <br><br>
    <b>2. Displacement (การแทนที่):</b> ผลของโครงการที่ไปทำให้เกิดปัญหาในที่อื่น หรือเป็นการย้ายปัญหาจากจุดหนึ่งไปอีกจุดหนึ่ง <br><br>
    <b>3. Attribution (การรับรองสิทธิ์):</b> สัดส่วนของผลลัพธ์ที่เกิดขึ้นจากปัจจัยภายนอก หรือหน่วยงานอื่นที่มีส่วนร่วมสนับสนุนโครงการ <br><br>
    <b>4. Drop-off (การลดลงของผลประโยชน์):</b> อัตราการลดลงของมูลค่าผลลัพธ์ในแต่ละปี หลังจากที่โครงการสิ้นสุดลง
    </div>
    """, unsafe_allow_html=True)

# --- Logic การคำนวณ ---
def calculate_sroi(total_input, discount_rate, duration, outcomes):
    total_present_value = 0
    detailed_list = []
    
    for item in outcomes:
        if not item['stakeholder']: continue
        
        # Net Impact ปีแรก: (Proxy * Qty) * (1-DW) * (1-Disp) * (1-Attr)
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
    project_name = st.text_input("ชื่อโครงการ", value="SROI_Project_2024")
    total_input = st.number_input("งบประมาณโครงการ (บาท)", value=100000, step=1000)
    discount_rate = st.number_input("Discount Rate (%)", value=3.5, step=0.1)
    duration = st.slider("ระยะเวลาที่ต้องการคำนวณ (ปี)", 1, 10, 5)
    st.divider()
    st.caption("จั่นเจา รายงาน: ตรวจ
