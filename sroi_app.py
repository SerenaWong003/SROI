import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime

# --- การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="SROI Professional Calculator", layout="wide")

# ปรับแต่ง CSS - เน้นตัวหนังสือสีดำในส่วนคำอธิบาย
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .info-box { 
        background-color: #e8f4f8; 
        padding: 20px; 
        border-radius: 8px; 
        border-left: 5px solid #2980b9; 
        margin-bottom: 20px;
        color: #000000 !important;
    }
    .info-box b, .info-box p { color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 SROI Calculator (Full Financial Edition)")

# --- ส่วนอธิบายศัพท์ (ตัวหนังสือสีดำชัดเจน) ---
with st.expander("ℹ️ คำอธิบายศัพท์เทคนิคและเกณฑ์การปรับมูลค่า (Glossary)", expanded=False):
    st.markdown("""
    <div class="info-box">
    <p><b>1. Deadweight:</b> ผลลัพธ์ที่จะเกิดขึ้นอยู่แล้วแม้ไม่มีโครงการ (เช่น รายได้ที่เพิ่มขึ้นเองตามกลไกตลาด)</p>
    <p><b>2. Displacement:</b> ผลของโครงการที่ไปทำให้เกิดปัญหาในพื้นที่อื่น หรือเป็นการย้ายปัญหาจากจุดหนึ่งไปอีกจุดหนึ่ง</p>
    <p><b>3. Attribution:</b> ผลที่เกิดจากหน่วยงานอื่นหรือปัจจัยภายนอกที่มีส่วนช่วย ไม่ได้มาจากเรา 100%</p>
    <p><b>4. Drop-off:</b> อัตราที่ผลประโยชน์จะลดลงในแต่ละปี หลังจากโครงการเสร็จสิ้นลง</p>
    <p><b>5. Present Value (PV):</b> มูลค่าของเงินในอนาคตที่ถูกทอนกลับมาเป็นมูลค่าในปัจจุบันด้วยอัตราคิดลด (Discount Rate)</p>
    </div>
    """, unsafe_allow_html=True)

# --- Logic การคำนวณขั้นสูง ---
def calculate_advanced_sroi(total_input, discount_rate, duration, outcomes):
    detailed_list = []
    yearly_totals = [0.0] * duration 
    
    for item in outcomes:
        if not item['stakeholder']: continue
        
        # 1. คำนวณ Net Impact ปีแรก
        initial_impact = (item['proxy'] * item['qty']) * \
                         (1 - item['dw']) * (1 - item['disp']) * (1 - item['attr'])
        
        current_impact = initial_impact
        item_yearly_pvs = []
        item_total_pv = 0
        
        for year_idx in range(duration):
            year_num = year_idx + 1
            if year_num > 1:
                current_impact *= (1 - item['drop_off'])
            
            # 2. คำนวณ PV รายปี: PV = Impact / (1 + r)^n
            pv = current_impact / ((1 + (discount_rate/100)) ** year_num)
            
            item_yearly_pvs.append(pv)
            item_total_pv += pv
            yearly_totals[year_idx] += pv
            
        row_data = {
            "Stakeholder/Outcome": item['stakeholder'],
            "Total PV (by Item)": item_total_pv
        }
        for y_idx, y_pv in enumerate(item_yearly_pvs):
            row_data[f"Year {y_idx+1} PV"] = y_pv
            
        detailed_list.append(row_data)
        
    total_pv_all = sum(yearly_totals)
    sroi_ratio = total_pv_all / total_input if total_input > 0 else 0
    return sroi_ratio, total_pv_all, detailed_list, yearly_totals

# --- ส่วน Sidebar ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าโครงการ")
    p_name = st.text_input("ชื่อโครงการ", value="SROI_Analysis_Project")
    t_input = st.number_input("งบประมาณรวม (Total Input)", value=100000, step=1000)
    d_rate = st.number_input("Discount Rate (%)", value=3.5, step=0.1)
    years = st.slider("ระยะเวลาที่ต้องการวิเคราะห์ (ปี)", 1, 10, 5)
    st.divider()
    st.caption("จัดทำโดยสำนักวิจัย มหาวิทยาลัยพายัพ")

# --- การจัดการจำนวนแถ
