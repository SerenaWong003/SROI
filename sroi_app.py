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
            if year_num > 1: current_impact *= (1 - drp_f)
            pv = current_impact / ((1 + (discount_rate/100)) ** year_num)
            item_yearly_pvs.append(pv)
            item_total_pv += pv
            yearly_totals[year_idx] += pv
        
        row_data = {
            "ผู้มีส่วนได้ส่วนเสีย": item['stakeholder'],
            "ผลลัพธ์ (Outcome)": item['outcome_text'],
            "Total PV (TPV)": item_total_pv
        }
        for y_idx, y_pv in enumerate(item_yearly_pvs):
            row_data[f"ปีที่ {y_idx+1} (PV)"] = y_pv
        detailed_list.append(row_data)
        
    total_pv_sum = sum(yearly_totals)
    sroi_ratio = total_pv_sum / total_input if total_input > 0 else 0
    return sroi_ratio, total_pv_sum, detailed_list, yearly_totals

# --- 6. ส่วน Sidebar ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าโครงการ")
    p_name = st.text_input("ชื่อโครงการ", value="โครงการวิจัยพายัพ_2026")
    t_input = st.number_input("งบประมาณรวม (Total Input)", value=100000, min_value=1)
    d_rate = st.number_input("Discount Rate (%)", value=3.5, step=0.1)
    years = st.slider("ระยะเวลาวิเคราะห์ (ปี)", 1, 10, 5)
    st.divider()
    if st.button("🗑️ ล้างข้อมูลทั้งหมด", use_container_width=True):
        reset_system()

# --- 7. การจัดการรายการ ---
if 'num_rows' not in st.session_state: st.session_state.num_rows = 1
def add_row(): st.session_state.num_rows += 1
def remove_row():
    if st.session_state.num_rows > 1: st.session_state.num_rows -= 1

st.subheader("📝 รายละเอียดการวิเคราะห์การเปลี่ยนแปลง (Value Map)")
c_b1, c_b2, _ = st.columns([1, 1, 4])
with c_b1: st.button("➕ เพิ่มรายการ", on_click=add_row, use_container_width=True)
with c_b2: st.button("➖ ลบรายการล่าสุด", on_click=remove_row, use_container_width=True)

outcomes_input = []
for i in range(st.session_state.num_rows):
    with st.expander(f"📍 รายการวิเคราะห์ที่ {i+1}", expanded=True):
        # --- ส่วนที่ 1: ข้อมูลเชิงคุณภาพ (นายหญิงสั่งเพิ่ม) ---
        st.markdown('<div class="section-head">1. ข้อมูลเชิงคุณภาพ (Qualitative Data)</div>', unsafe_allow_html=True)
        q_col1, q_col2 = st.columns(2)
        stk = q_col1.text_input("ผู้มีส่วนได้ส่วนเสีย (Stakeholder)", key=f"stk_{i}")
        inp = q_col2.text_input("ปัจจัยที่ใช้ (Input)", key=f"inp_{i}")
        
        act = q_col1.text_area("กิจกรรม/กระบวนการ (Activity)", height=70, key=f"act_{i}")
        outp = q_col2.text_area("ผลผลิต (Output)", height=70, key=f"outp_{i}")
        
        outc = q_col1.text_area("ผลลัพธ์ (Outcome)", height=70, key=f"outc_{i}")
        ind = q_col2.text_area("ตัวชี้วัด (Indicator)", height=70, key=f"ind_{i}")
        
        prx_desc = q_col1.text_input("คำอธิบายค่าแทนทางการเงิน (Proxy Description)", key=f"prx_d_{i}")
        imp_desc = q_col2.text_input("ผลกระทบ (Impact Description)", key=f"imp_d_{i}")
        
        # --- ส่วนที่ 2: การคำนวณทางการเงิน ---
        st.markdown('<div class="section-head">2. ข้อมูลสำหรับการคำนวณ (Financial Data)</div>', unsafe_allow_html=True)
        f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
        prx_val = f_col1.number_input("ค่าแทนทางการเงิน (Proxy Value - บาท)", value=0, key=f"prx_v_{i}")
        qty = f_col2.number_input("จำนวนหน่วย", value=0, key=f"qty_{i}")
        
        st.markdown("**ปัจจัยปรับลด (%)**")
        p_col1, p_col2, p_col3, p_col4 = st.columns(4)
        dw = p_col1.number_input("Deadweight", 0.0, 100.0, 0.0, key=f"dw_{i}")
        disp = p_col2.number_input("Displacement", 0.0, 100.0, 0.0, key=f"disp_{i}")
        attr = p_col3.number_input("Attribution", 0.0, 100.0, 0.0, key=f"att_{i}")
        drop = p_col4.number_input("Drop-off", 0.0, 100.0, 0.0, key=f"drp_{i}")
        
        outcomes_input.append({
            "stakeholder": stk, "outcome_text": outc, "proxy_val": prx_val, 
            "qty": qty, "dw": dw, "disp": disp, "attr": attr, "drop_off": drop
        })

# --- 8. ประมวลผล ---
if st.button("🚀 คำนวณ SROI", type="primary", use_container_width=True):
    ratio, tpv, details, y_totals = calculate_advanced_sroi(t_input, d_rate, years, outcomes_input)
    st.session_state.res = {"ratio": ratio, "tpv": tpv, "npv": tpv - t_input, "details": details, "y_totals": y_totals, "t_input": t_input, "p_name": p_name}

if 'res' in st.session_state:
    r = st.session_state.res
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SROI Ratio", f"{r['ratio']:.2f}")
    m2.metric("Total PV (TPV)", f"฿{r['tpv']:,.2f}")
    m3.metric("Net PV (NPV)", f"฿{r['npv']:,.2f}")
    m4.metric("Total Input", f"฿{r['t_input']:,.2f}")

    df_final = pd.DataFrame(r['details'])
    summary_data = {"ผู้มีส่วนได้ส่วนเสีย": "TOTAL", "ผลลัพธ์ (Outcome)": "PV PER YEAR", "Total PV (TPV)": r['tpv']}
    for idx, val in enumerate(r['y_totals']): summary_data[f"ปีที่ {idx+1} (PV)"] = val
    df_with_summary = pd.concat([df_final, pd.DataFrame([summary_data])], ignore_index=True)
    st.dataframe(df_with_summary.style.format(subset=["Total PV (TPV)"] + [f"ปีที่ {i+1} (PV)" for i in range(len(r['y_totals']))], precision=2, thousands=","), use_container_width=True)

    c_csv, c_pdf = st.columns(2)
    with c_csv:
        st.download_button("Download CSV", df_with_summary.to_csv(index=False).encode('utf-8-sig'), f"SROI_{r['p_name']}.csv", "text/csv")
    with c_pdf:
        def gen_pdf(data):
            pdf = FPDF()
            if os.path.exists("THSarabunNew.ttf"):
                pdf.add_font("THSarabunNew", "", "THSarabunNew.ttf")
                pdf.add_page(); pdf.set_font("THSarabunNew", size=16)
            else: pdf.add_page(); pdf.set_font("helvetica", size=12)
            pdf.cell(0, 10, txt=f"SROI Analysis Report: {data['p_name']}", align='C', ln=True)
            pdf.cell(0, 10, txt=f"SROI Ratio: {data['ratio']:.2f}", ln=True)
            pdf.cell(0, 10, txt=f"Total PV: {data['tpv']:,.2f} THB", ln=True)
            return bytes(pdf.output())
        st.download_button("Download PDF", gen_pdf(r), f"SROI_{r['p_name']}.pdf", "application/pdf")
