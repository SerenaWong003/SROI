import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import os

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="SROI Professional Calculator", layout="wide")

# --- 2. ปรับแต่ง CSS - บังคับสีดำบนพื้นหลังขาว ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="metric-container"] {
        background-color: #ffffff !important;
        border: 1px solid #dee2e6;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #000000 !important; font-weight: 600; }
    .info-box { 
        background-color: #ffffff; padding: 20px; border-radius: 8px; 
        border: 1px solid #2980b9; border-left: 10px solid #2980b9;
        margin-bottom: 25px; color: #000000 !important;
    }
    .info-box b, .info-box p { color: #000000 !important; }
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
    <p><b>5. Present Value (PV):</b> มูลค่าปัจจุบันของเงินในอนาคต</p>
    </div>
    """, unsafe_allow_html=True)

# --- 5. Logic การคำนวณ ---
def calculate_advanced_sroi(total_input, discount_rate, duration, outcomes):
    detailed_list = []
    yearly_totals = [0.0] * duration 
    for item in outcomes:
        if not item['stakeholder']: continue
        initial_impact = (item['proxy'] * item['qty']) * (1 - item['dw']) * (1 - item['disp']) * (1 - item['attr'])
        current_impact = initial_impact
        item_yearly_pvs = []
        item_total_pv = 0
        for year_idx in range(duration):
            year_num = year_idx + 1
            if year_num > 1: current_impact *= (1 - item['drop_off'])
            pv = current_impact / ((1 + (discount_rate/100)) ** year_num)
            item_yearly_pvs.append(pv)
            item_total_pv += pv
            yearly_totals[year_idx] += pv
        row_data = {"ผู้มีส่วนได้เสีย/ผลลัพธ์": item['stakeholder'], "Total PV (TPV)": item_total_pv}
        for y_idx, y_pv in enumerate(item_yearly_pvs):
            row_data[f"ปีที่ {y_idx+1} (PV)"] = y_pv
        detailed_list.append(row_data)
    total_pv_all = sum(yearly_totals)
    ratio = total_pv_all / total_input if total_input > 0 else 0
    return ratio, total_pv_all, detailed_list, yearly_totals

# --- 6. ส่วน Sidebar ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าโครงการ")
    p_name = st.text_input("ชื่อโครงการ", value="โครงการวิจัย_2026")
    t_input = st.number_input("งบประมาณรวม (Total Input)", value=100000, min_value=1)
    d_rate = st.number_input("Discount Rate (%)", value=3.5, step=0.1)
    years = st.slider("ระยะเวลาวิเคราะห์ (ปี)", 1, 10, 5)
    st.divider()
    if st.button("🗑️ ล้างข้อมูลทั้งหมด", use_container_width=True):
        reset_system()
    st.caption("พัฒนาระบบโดย : สำนักวิจัย มหาวิทยาลัยพายัพ")

# --- 7. การจัดการข้อมูล ---
if 'num_rows' not in st.session_state: st.session_state.num_rows = 1
def add_row():
    if st.session_state.num_rows < 10: st.session_state.num_rows += 1
def remove_row():
    if st.session_state.num_rows > 1: st.session_state.num_rows -= 1

st.subheader("📝 รายละเอียดข้อมูลผลลัพธ์ คำนวนได้สูงสุด 10 รายการ")
c_b1, c_b2, _ = st.columns([1, 1, 4])
with c_b1: st.button("➕ เพิ่มรายการ", on_click=add_row, use_container_width=True)
with c_b2: st.button("➖ ลบรายการ", on_click=remove_row, use_container_width=True)

outcomes_input = []
for i in range(st.session_state.num_rows):
    with st.expander(f"รายการที่ {i+1}", expanded=True):
        r1_c1, r1_c2, r1_c3 = st.columns([2, 1, 1])
        with r1_c1: stk = st.text_input("ชื่อผลลัพธ์", key=f"stk_{i}")
        with r1_c2: prx = st.number_input("Proxy (บาท)", value=0, key=f"prx_{i}")
        with r1_c3: q = st.number_input("จำนวนหน่วย", value=0, key=f"q_{i}")
        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4) 
        with r2_c1: dw = st.slider("Deadweight", 0.0, 1.0, 0.0, key=f"dw_{i}")
        with r2_c2: disp = st.slider("Displacement", 0.0, 1.0, 0.0, key=f"disp_{i}")
        with r2_c3: att = st.slider("Attribution", 0.0, 1.0, 0.0, key=f"attr_{i}")
        with r2_c4: drp = st.slider("Drop-off", 0.0, 1.0, 0.0, key=f"drp_{i}")
        outcomes_input.append({"stakeholder": stk, "proxy": prx, "qty": q, "dw": dw, "disp": disp, "attr": att, "drop_off": drp})

# --- 8. ประมวลผลและส่งออกรายงาน ---
if st.button("🚀 คำนวณผล SROI", type="primary", use_container_width=True):
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

    df_res = pd.DataFrame(r['details'])
    summary_row = {"ผู้มีส่วนได้เสีย/ผลลัพธ์": "TOTAL PV PER YEAR", "Total PV (TPV)": r['tpv']}
    for idx, val in enumerate(r['y_totals']): summary_row[f"ปีที่ {idx+1} (PV)"] = val
    df_with_summary = pd.concat([df_res, pd.DataFrame([summary_row])], ignore_index=True)
    st.dataframe(df_with_summary.style.format(precision=2, thousands=","), use_container_width=True)

    st.subheader("📥 ดาวน์โหลดรายงาน")
    e_col1, e_col2 = st.columns(2)
    with e_col1:
        csv = df_with_summary.to_csv(index=False).encode('utf-8-sig')
        st.download_button("Download CSV (Excel)", csv, f"SROI_{r['p_name']}.csv", "text/csv")
    with e_col2:
        def generate_pdf(data):
            pdf = FPDF()
            # ปรับเปลี่ยนชื่อไฟล์ฟอนต์ตามคำสั่งนายหญิง
            font_path = "THSarabunNew.ttf"
            font_name = "THSarabunNew"

            if os.path.exists(font_path):
                pdf.add_font(font_name, "", font_path)
                pdf.add_page() # สร้างหน้าหลังโหลดฟอนต์เสร็จ
                pdf.set_font(font_name, size=16)
            else:
                st.error(f"❌ ไม่พบไฟล์ {font_path} ใน GitHub กรุณาอัปโหลดไฟล์ฟอนต์ชื่อนี้ไว้ในโฟลเดอร์เดียวกับโค้ดครับ")
                return None
            
            pdf.cell(0, 10, txt="SROI Analysis Report (รายงานวิจัย)", align='C', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)
            pdf.cell(0, 10, txt=f"ชื่อโครงการ: {data['p_name']}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 10, txt=f"SROI Ratio: {data['ratio']:.2f}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 10, txt=f"Total PV (TPV): {data['tpv']:,.2f} บาท", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 10, txt=f"Net PV (NPV): {data['npv']:,.2f} บาท", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(10)
            pdf.cell(0, 10, txt="รายละเอียดผลลัพธ์:", new_x="LMARGIN", new_y="NEXT")
            
            for d in data['details']:
                stk_name = d.get('ผู้มีส่วนได้เสีย/ผลลัพธ์', 'ไม่ระบุ')
                val_tpv = d.get('Total PV (TPV)', 0)
                pdf.cell(0, 10, txt=f"- {stk_name}: {val_tpv:,.2f} บาท", new_x="LMARGIN", new_y="NEXT")
            
            return bytes(pdf.output())

        pdf_data = generate_pdf(r)
        if pdf_data:
            st.download_button("Download PDF (Report)", pdf_data, f"SROI_Report_{r['p_name']}.pdf", "application/pdf")
