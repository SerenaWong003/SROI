import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime

# --- การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="SROI Calculator Tool", layout="wide")

# ปรับแต่งสไตล์ด้วย CSS - กำหนดสีตัวอักษรใน info-box ให้เป็นสีดำ
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .info-box { 
        background-color: #e8f4f8; 
        padding: 15px; 
        border-radius: 8px; 
        border-left: 5px solid #2980b9; 
        margin-bottom: 20px;
        color: #000000; /* กำหนดเป็นสีดำ */
    }
    .info-text {
        color: #000000 !important; /* บังคับให้เป็นสีดำ */
        font-weight: 400;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 SROI Calculator for University Research")

# --- ส่วนอธิบายศัพท์ (ปรับเป็นตัวหนังสือสีดำ) ---
with st.expander("ℹ️ คำอธิบายศัพท์เทคนิคในการคำนวณ SROI (Glossary)", expanded=False):
    st.markdown("""
    <div class="info-box">
    <p class="info-text"><b>1. Deadweight (ผลลัพธ์ส่วนเกิน):</b> มูลค่าของผลลัพธ์ที่เกิดขึ้นอยู่แล้วแม้จะไม่มีโครงการนี้เกิดขึ้นก็ตาม</p>
    <p class="info-text"><b>2. Displacement (การแทนที่):</b> ผลของโครงการที่ไปทำให้เกิดปัญหาในพื้นที่อื่น หรือเป็นการย้ายปัญหาจากจุดหนึ่งไปอีกจุดหนึ่ง</p>
    <p class="info-text"><b>3. Attribution (การรับรองสิทธิ์):</b> สัดส่วนของผลลัพธ์ที่เกิดจากหน่วยงานอื่นหรือปัจจัยภายนอกที่ไม่ใช่โครงการของเรา</p>
    <p class="info-text"><b>4. Drop-off (การลดลงของผลประโยชน์):</b> อัตราการลดลงของมูลค่าผลลัพธ์ในแต่ละปี หลังจากที่โครงการสิ้นสุดลง</p>
    </div>
    """, unsafe_allow_html=True)

# --- Logic การคำนวณ ---
def calculate_sroi(total_input, discount_rate, duration, outcomes):
    total_present_value = 0
    detailed_list = []
    
    for item in outcomes:
        if not item['stakeholder']: continue
        
        # สูตรปีแรก: (Proxy * Qty) * (1-DW) * (1-Disp) * (1-Attr)
        initial_impact = (item['proxy'] * item['qty']) * \
                         (1 - item['dw']) * (1 - item['disp']) * (1 - item['attr'])
        
        item_pv_sum = 0
        current_impact = initial_impact
        
        for year in range(1, duration + 1):
            if year > 1:
                current_impact *= (1 - item['drop_off'])
            # PV = Impact / (1 + r)^year
            pv = current_impact / ((1 + (discount_rate/100)) ** year)
            item_pv_sum += pv
        
        total_present_value += item_pv_sum
        detailed_list.append({**item, "item_pv": item_pv_sum})
    
    ratio = total_present_value / total_input if total_input > 0 else 0
    return ratio, total_present_value, detailed_list

# --- ส่วน Sidebar: ตั้งค่าโครงการ ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าโครงการ")
    p_name = st.text_input("ชื่อโครงการ", value="SROI_Project_2026")
    t_input = st.number_input("งบประมาณโครงการ (บาท)", value=100000, step=1000)
    d_rate = st.number_input("Discount Rate (%)", value=3.5, step=0.1)
    years = st.slider("ระยะเวลาที่คำนวณ (ปี)", 1, 10, 5)
    st.divider()
    # แก้ไขปัญหาเครื่องหมายคำพูดโดยใช้บรรทัดเดียวและลบ caption ภาษาไทยที่ยาวเกินไป
    st.caption("ระบบวิเคราะห์ความเสี่ยงโดย จั่นเจา")

# --- ส่วนจัดการรายการผู้มีส่วนได้เสีย ---
if 'num_rows' not in st.session_state:
    st.session_state.num_rows = 1

def add_row():
    if st.session_state.num_rows < 10: st.session_state.num_rows += 1
def remove_row():
    if st.session_state.num_rows > 1: st.session_state.num_rows -= 1

st.subheader("📝 รายละเอียดผู้มีส่วนได้เสีย (สูงสุด 10 รายการ)")
c_btn1, c_btn2, _ = st.columns([1, 1, 4])
with c_btn1:
    st.button("➕ เพิ่มรายการ", on_click=add_row, use_container_width=True)
with c_btn2:
    st.button("➖ ลบรายการ", on_click=remove_row, use_container_width=True)

outcomes_input = []
for i in range(st.session_state.num_rows):
    with st.expander(f"รายการที่ {i+1}", expanded=True):
        r1_c1, r1_c2, r1_c3 = st.columns([2, 1, 1])
        with r1_c1: 
            stk_name = st.text_input("ชื่อผู้มีส่วนได้เสีย/ผลลัพธ์", key=f"stk_{i}")
        with r1_c2: 
            proxy_val = st.number_input("Proxy (บาท)", value=0, key=f"prx_{i}")
        with r1_c3: 
            quantity = st.number_input("จำนวนหน่วย", value=0, key=f"q_{i}")
        
        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
        with r2_c1: dw_val = st.slider("Deadweight", 0.0, 1.0, 0.0, key=f"dw_{i}")
        with r2_c2: disp_val = st.slider("Displacement", 0.0, 1.0, 0.0, key=f"disp_{i}")
        with r2_c3: attr_val = st.slider("Attribution", 0.0, 1.0, 0.0, key=f"attr_{i}")
        with r2_c4: drop_val = st.slider("Drop-off", 0.0, 1.0, 0.0, key=f"drp_{i}")
        
        outcomes_input.append({
            "stakeholder": stk_name, "proxy": proxy_val, "qty": quantity, 
            "dw": dw_val, "disp": disp_val, "attr": attr_val, "drop_off": drop_val
        })

# --- ส่วนการประมวลผล ---
if st.button("🚀 คำนวณ SROI", type="primary", use_container_width=True):
    res_ratio, res_pv, res_details = calculate_sroi(t_input, d_rate, years, outcomes_input)
    st.session_state.calc_results = {
        "ratio": res_ratio, 
        "total_pv": res_pv, 
        "details": res_details, 
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }

# --- แสดงผลและปุ่มส่งออก ---
if 'calc_results' in st.session_state:
    res = st.session_state.calc_results
    st.divider()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("SROI Ratio", f"{res['ratio']:.2f}")
    m2.metric("Total PV", f"฿{res['total_pv']:,.2f}")
    m3.metric("Net Present Value", f"฿{(res['total_pv'] - t_input):,.2f}")

    df_out = pd.DataFrame(res['details'])
    st.dataframe(df_out, use_container_width=True)

    st.subheader("📥 ดาวน์โหลดรายงาน")
    e_col1, e_col2 = st.columns(2)
    with e_col1:
        csv_data = df_out.to_csv(index=False).encode('utf-8-sig')
        st.download_button("Download CSV (Excel)", csv_data, f"SROI_{p_name}.csv", "text/csv")
    
    with e_col2:
        def generate_pdf_file(data):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="SROI Analysis Report", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Project: {p_name}", ln=True)
            pdf.cell(200, 10, txt=f"SROI Ratio: {data['ratio']:.2f}", ln=True)
            pdf.cell(200, 10, txt=f"Investment: {t_input:,.2f} THB", ln=True)
            pdf.cell(200, 10, txt=f"Total PV: {data['total_pv']:,.2f} THB", ln=True)
            pdf.ln(5)
            pdf.cell(200, 10, txt="Details Summary:", ln=True)
            pdf.set_font("Arial", size=10)
            for d in data['details']:
                safe_name = "".join([c if ord(c) < 128 else "?" for c in d['stakeholder']])
                pdf.cell(200, 8, txt=f"- {safe_name}: PV = {d['item_pv']:,.2f} THB", ln=True)
            return pdf.output(dest='S').encode('latin-1')
        
        try:
            pdf_bytes = generate_pdf_file(res)
            st.download_button("Download PDF", pdf_bytes, f"SROI_{p_name}.pdf", "application/pdf")
        except:
            st.warning("หมายเหตุ: PDF ปัจจุบันรองรับเฉพาะภาษาอังกฤษครับ")
