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
    </style>
    """, unsafe_allow_html=True)

# --- 3. ฟังก์ชันสำหรับล้างข้อมูล ---
def reset_system():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.num_rows = 1
    st.rerun()

st.title("📊 SROI Calculator (Annual Forecast Edition)")

# --- 4. Logic การคำนวณ ---
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
            if year_num > 1: current_impact *= (1 - drp_f)
            pv = current_impact / ((1 + (discount_rate/100)) ** year_num)
            item_yearly_pvs.append(pv)
            item_total_pv += pv
            yearly_totals[year_idx] += pv
        
        row_data = {
            "Stakeholder": item['stakeholder'],
            "Outcome": item['outcome_text'],
            "Total PV (TPV)": item_total_pv
        }
        # เพิ่มข้อมูล PV รายปีลงใน Row
        for y_idx, y_pv in enumerate(item_yearly_pvs):
            row_data[f"Year {y_idx+1} PV"] = y_pv
        detailed_list.append(row_data)
        
    total_pv_sum = sum(yearly_totals)
    sroi_ratio = total_pv_sum / total_input if total_input > 0 else 0
    return sroi_ratio, total_pv_sum, detailed_list, yearly_totals

# --- 5. ส่วน Sidebar ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าโครงการ")
    p_name = st.text_input("ชื่อโครงการ", value="SROI_Project_2026")
    t_input = st.number_input("งบประมาณรวม (Total Input)", value=100000, min_value=1)
    d_rate = st.number_input("Discount Rate (%)", value=3.5, step=0.1)
    years = st.slider("ระยะเวลาวิเคราะห์ (ปี)", 1, 10, 5)
    st.divider()
    if st.button("🗑️ ล้างข้อมูลทั้งหมด", use_container_width=True):
        reset_system()
    st.caption("พัฒนาระบบโดย: สำนักวิจัย มหาวิทยาลัยพายัพ")

# --- 6. การกรอกข้อมูล ---
if 'num_rows' not in st.session_state: st.session_state.num_rows = 1
c_b1, c_b2, _ = st.columns([1, 1, 4])
with c_b1: st.button("➕ เพิ่มรายการ", on_click=lambda: st.session_state.update({"num_rows": st.session_state.num_rows + 1}))
with c_b2: st.button("➖ ลบรายการ", on_click=lambda: st.session_state.update({"num_rows": max(1, st.session_state.num_rows - 1)}))

outcomes_input = []
for i in range(st.session_state.num_rows):
    with st.expander(f"📍 รายการที่ {i+1}", expanded=True):
        col1, col2 = st.columns(2)
        stk = col1.text_input("ผู้มีส่วนได้ส่วนเสีย", key=f"stk_{i}")
        outc = col2.text_area("ผลลัพธ์ (Outcome)", height=70, key=f"outc_{i}")
        
        f1, f2 = st.columns(2)
        prx_val = f1.number_input("มูลค่าแทน (Proxy)", value=0, key=f"prx_v_{i}")
        qty = f2.number_input("จำนวน", value=0, key=f"qty_{i}")
        
        p1, p2, p3, p4 = st.columns(4)
        dw = p1.number_input("Deadweight %", 0.0, 100.0, 0.0, key=f"dw_{i}")
        disp = p2.number_input("Displacement %", 0.0, 100.0, 0.0, key=f"disp_{i}")
        attr = p3.number_input("Attribution %", 0.0, 100.0, 0.0, key=f"att_{i}")
        drop = p4.number_input("Drop-off %", 0.0, 100.0, 0.0, key=f"drp_{i}")
        
        outcomes_input.append({
            "stakeholder": stk, "outcome_text": outc, "proxy_val": prx_val, 
            "qty": qty, "dw": dw, "disp": disp, "attr": attr, "drop_off": drop
        })

# --- 7. ประมวลผลและสร้างรายงาน ---
if st.button("🚀 คำนวณและสร้างรายงาน", type="primary", use_container_width=True):
    ratio, tpv, details, y_totals = calculate_advanced_sroi(t_input, d_rate, years, outcomes_input)
    st.session_state.res = {
        "ratio": ratio, "tpv": tpv, "npv": tpv - t_input,
        "details": details, "y_totals": y_totals, "t_input": t_input, "p_name": p_name
    }

if 'res' in st.session_state:
    r = st.session_state.res
    st.divider()
    
    # 1. Metrics (สีดำ พื้นหลังขาว)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SROI Ratio", f"{r['ratio']:.2f}")
    m2.metric("Total PV (TPV)", f"฿{r['tpv']:,.2f}")
    m3.metric("Net PV (NPV)", f"฿{r['npv']:,.2f}")
    m4.metric("Total Input", f"฿{r['t_input']:,.2f}")

    # 2. ตารางข้อมูล (จะถูกใช้ใน CSV ด้วย)
    df_final = pd.DataFrame(r['details'])
    # เพิ่มแถวสรุปผลรวมรายปีที่ท้ายตาราง
    summary_row = {"Stakeholder": "TOTAL ANNUAL PV", "Outcome": "---", "Total PV (TPV)": r['tpv']}
    for idx, val in enumerate(r['y_totals']):
        summary_row[f"Year {idx+1} PV"] = val
    df_with_total = pd.concat([df_final, pd.DataFrame([summary_row])], ignore_index=True)
    
    st.subheader("🗓️ ตารางวิเคราะห์มูลค่าปัจจุบันรายปี")
    st.dataframe(df_with_total.style.format(precision=2, thousands=","), use_container_width=True)

    # 3. ปุ่มดาวน์โหลด
    c1, c2 = st.columns(2)
    with c1:
        # CSV มีครบทุกอย่างตามคำสั่ง
        csv = df_with_total.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Download CSV (Full Annual Data)", csv, f"SROI_Annual_{r['p_name']}.csv", "text/csv")
    
    with c2:
        # PDF รายงานสรุป
        def generate_full_report(data, yearly_data):
            pdf = FPDF()
            font_path = "THSarabunNew.ttf"
            if os.path.exists(font_path):
                pdf.add_font("THSarabunNew", "", font_path)
                pdf.add_page(); pdf.set_font("THSarabunNew", size=18)
            else:
                pdf.add_page(); pdf.set_
