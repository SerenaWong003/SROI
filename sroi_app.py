import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import os

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="SROI Professional Calculator", layout="wide")

# --- 2. ปรับแต่ง CSS - บังคับสีดำบนพื้นหลังขาวสำหรับส่วนสรุปผล ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    
    /* ปรับแต่งส่วน Metric ให้พื้นหลังขาว ตัวหนังสือดำ */
    [data-testid="metric-container"] {
        background-color: #ffffff !important;
        border: 1px solid #dee2e6;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
    }
    [data-testid="stMetricValue"] {
        color: #000000 !important;
        font-weight: bold;
        font-size: 2.2rem !important;
    }
    [data-testid="stMetricLabel"] {
        color: #000000 !important;
        font-weight: 600;
        font-size: 1.1rem !important;
    }

    /* ปรับแต่งส่วนคำอธิบาย Glossary ให้ตัวหนังสือดำชัดเจนบนพื้นขาว */
    .info-box { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 8px; 
        border: 1px solid #2980b9; 
        border-left: 10px solid #2980b9;
        margin-bottom: 25px;
        color: #000000 !important;
    }
    .info-box b, .info-box p { color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ฟังก์ชันสำหรับล้างข้อมูลทั้งหมด ---
def reset_system():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.num_rows = 1
    st.rerun()

st.title("📊 SROI Calculator for University Research")

# --- 4. ส่วนอธิบายศัพท์ (Glossary) ---
with st.expander("ℹ️ คำอธิบายศัพท์เทคนิคในการคำนวณ SROI", expanded=False):
    st.markdown("""
    <div class="info-box">
    <p><b>1. Deadweight (ผลลัพธ์ส่วนเกิน):</b> มูลค่าของผลลัพธ์ที่เกิดขึ้นอยู่แล้วแม้ไม่มีโครงการ</p>
    <p><b>2. Displacement (การแทนที่):</b> การย้ายปัญหาจากจุดหนึ่งไปอีกจุดหนึ่ง หรือทำให้เกิดปัญหาที่อื่นแทน</p>
    <p><b>3. Attribution (การรับรองสิทธิ์):</b> ผลที่เกิดจากปัจจัยภายนอก หรือหน่วยงานอื่นที่มีส่วนช่วย ไม่ใช่เรา 100%</p>
    <p><b>4. Drop-off (การลดลงของผลประโยชน์):</b> อัตราที่ผลประโยชน์ลดลงในแต่ละปี หลังจากโครงการเสร็จสิ้นลง</p>
    <p><b>5. Present Value (PV):</b> มูลค่าของเงินในอนาคตที่ทอนกลับมาเป็นมูลค่าปัจจุบันด้วยอัตราคิดลด</p>
    </div>
    """, unsafe_allow_html=True)

# --- 5. Logic การคำนวณรายปี ---
def calculate_advanced_sroi(total_input, discount_rate, duration, outcomes):
    detailed_list = []
    yearly_totals = [0.0] * duration 
    
    for item in outcomes:
        if not item['stakeholder']: continue
        
        # ทอนค่า % กลับเป็นทศนิยม (0.0 - 1.0)
        dw_f = item['dw'] / 100
        disp_f = item['disp'] / 100
        att_f = item['attr'] / 100
        drp_f = item['drop_off'] / 100
        
        # คำนวณ Impact ปีแรก
        initial_impact = (item['proxy'] * item['qty']) * \
                         (1 - dw_f) * (1 - disp_f) * (1 - att_f)
        
        current_impact = initial_impact
        item_yearly_pvs = []
        item_total_pv = 0
        
        for year_idx in range(duration):
            year_num = year_idx + 1
            if year_num > 1:
                current_impact *= (1 - drp_f)
            
            # สูตร PV = Impact / (1 + r)^n
            pv = current_impact / ((1 + (discount_rate/100)) ** year_num)
            item_yearly_pvs.append(pv)
            item_total_pv += pv
            yearly_totals[year_idx] += pv
            
        row_data = {"ผู้มีส่วนได้เสีย/ผลลัพธ์": item['stakeholder'], "Total PV (TPV)": item_total_pv}
        for y_idx, y_pv in enumerate(item_yearly_pvs):
            row_data[f"ปีที่ {y_idx+1} (PV)"] = y_pv
        detailed_list.append(row_data)
        
    total_pv_all = sum(yearly_totals)
    sroi_ratio = total_pv_all / total_input if total_input > 0 else 0
    return sroi_ratio, total_pv_all, detailed_list, yearly_totals

# --- 6. ส่วน Sidebar ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าโครงการ")
    p_name = st.text_input("ชื่อโครงการ", value="โครงการวิจัยพายัพ_2026")
    t_input = st.number_input("งบประมาณรวม (Total Input)", value=100000, min_value=1, step=1000)
    d_rate = st.number_input("Discount Rate (%)", value=3.5, step=0.1)
    years = st.slider("ระยะเวลาวิเคราะห์ (ปี)", 1, 10, 5)
    st.divider()
    if st.button("🗑️ ล้างข้อมูลทั้งหมด", use_container_width=True):
        reset_system()
    st.caption("พัฒนาระบบโดย : สำนักวิจัย มหาวิทยาลัยพายัพ")
