import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime

# --- 1. การตั้งค่าหน้าจอ (Page Config) ---
st.set_page_config(page_title="SROI Professional Calculator", layout="wide")

# --- 2. ปรับแต่ง CSS (เน้นตัวหนังสือสีดำในส่วนคำอธิบาย) ---
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
        color: #000000 !important; /* บังคับตัวหนังสือสีดำ */
    }
    .info-box b, .info-box p { color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 SROI Calculator (Full Financial Edition)")

# --- 3. ส่วนอธิบายศัพท์ (ตัวหนังสือสีดำชัดเจน) ---
with st.expander("ℹ️ คำอธิบายศัพท์เทคนิคและเกณฑ์การปรับมูลค่า (Glossary)", expanded=False):
    st.markdown("""
    <div class="info-box">
    <p><b>1. Deadweight:</b> ผลลัพธ์ที่จะเกิดขึ้นอยู่แล้วแม้ไม่มีโครงการ (เช่น รายได้ที่เพิ่มขึ้นเองตามกลไกตลาด)</p>
    <p><b>2. Displacement:</b> ผลของโครงการที่ไปทำให้เกิดปัญหาในพื้นที่อื่น หรือเป็นการย้ายปัญหาจากจุดหนึ่งไปอีกจุดหนึ่ง</p>
    <p><b>3. Attribution:</b> ผลที่เกิดจากหน่วยงานอื่นหรือปัจจัยภายนอกที่มีส่วนช่วย ไม่ได้มาจากโครงการเรา 100%</p>
    <p><b>4. Drop-off:</b> อัตราที่ผลประโยชน์จะลดลงในแต่ละปี หลังจากโครงการเสร็จสิ้นลง</p>
    <p><b>5. Present Value (PV):</b> มูลค่าของเงินในอนาคตที่ถูกทอนกลับมาเป็นมูลค่าในปัจจุบันด้วยอัตราคิดลด</p>
    </div>
    """, unsafe_allow_html=True)

# --- 4. Logic การคำนวณขั้นสูง ---
def calculate_advanced_sroi(total_input, discount_rate, duration, outcomes):
    detailed_list = []
    yearly_totals = [0.0] * duration 
    
    for item in outcomes:
        if not item['stakeholder']: continue
        
        # คำนวณ Net Impact ปีแรก
        initial_impact = (item['proxy'] * item['qty']) * \
                         (1 - item['dw']) * (1 - item['disp']) * (1 - item['attr'])
        
        current_impact = initial_impact
        item_yearly_pvs = []
        item_total_pv = 0
        
        for year_idx in range(duration):
            year_num = year_idx + 1
            if year_num > 1:
                current_impact *= (1 - item['drop_off'])
            
            # สูตร PV = Impact / (1 + r)^n
            pv = current_impact / ((1 + (discount_rate/100)) ** year_num)
            
            item_yearly_pvs.append(pv)
            item_total_pv += pv
            yearly_totals[year_idx] += pv
            
        row_data = {
            "Stakeholder/Outcome": item['stakeholder'],
            "Total PV (by Item)": item_total_pv
        }
        for y_idx, y_pv in enumerate(item_yearly_pvs):
            row_data[f"Y{y_idx+1} PV"] = y_pv
            
        detailed_list.append(row_data)
        
    total_pv_all = sum(yearly_totals)
    sroi_ratio = total_pv_all / total_input if total_input > 0 else 0
    return sroi_ratio, total_pv_all, detailed_list, yearly_totals

# --- 5. ส่วน Sidebar (การตั้งค่าโครงการ) ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าโครงการ")
    p_name = st.text_input("ชื่อโครงการ", value="SROI_Project_2026")
    t_input = st.number_input("งบประมาณรวม (Total Input)", value=100000, step=1000)
    d_rate = st.number_input("Discount Rate (%)", value=3.5, step=0.1)
    years = st.slider("ระยะเวลาที่ต้องการวิเคราะห์ (ปี)", 1, 10, 5)
    st.divider()
    st.caption("ระบบโดย: จั่นเจา")

# --- 6. การจัดการจำนวนแถวข้อมูล ---
if 'num_rows' not in st.session_state:
    st.session_state.num_rows = 1

def add_row():
    if st.session_state.num_rows < 10: st.session_state.num_rows += 1
def remove_row():
    if st.session_state.num_rows > 1: st.session_state.num_rows -= 1

st.subheader("📝 รายละเอียดข้อมูลผู้มีส่วนได้เสีย")
col_b1, col_b2, _ = st.columns([1, 1, 4])
with col_b1:
    st.button("➕ เพิ่มแถว", on_click=add_row, use_container_width=True)
with col_b2:
    st.button("➖ ลบแถว", on_click=remove_row, use_container_width=True)

outcomes_input = []
for i in range(st.session_state.num_rows):
    with st.expander(f"รายการที่ {i+1}", expanded=True):
        r1_c1, r1_c2, r1_c3 = st.columns([2, 1, 1])
        with r1_c1: stk = st.text_input("ชื่อผู้มีส่วนได้เสีย / ผลลัพธ์", key=f"stk_{i}")
        with r1_c2: prx = st.number_input("Financial Proxy", value=0, key=f"prx_{i}")
        with r1_c3: q = st.number_input("จำนวน (Quantity)", value=0, key=f"q_{i}")
        
        # ตรวจสอบจุดนี้: ใส่ () เรียบร้อยแล้วเพื่อป้องกัน TypeError
        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4) 
        with r2_c1: dw = st.slider("Deadweight", 0.0, 1.0, 0.0, key=f"dw_{i}")
        with r2_c2: disp = st.slider("Displacement", 0.0, 1.0, 0.0, key=f"disp_{i}")
        with r2_c3: att = st.slider("Attribution", 0.0, 1.0, 0.0, key=f"attr_{i}")
        with r2_c4: drp = st.slider("Drop-off", 0.0, 1.0, 0.0, key=f"drp_{i}")
        
        outcomes_input.append({"stakeholder": stk, "proxy": prx, "qty": q, "dw": dw, "disp": disp, "attr": att, "drop_off": drp})

# --- 7. ประมวลผลและแสดงผลลัพธ์ ---
if st.button("🚀 คำนวณและประมวลผล SROI", type="primary", use_container_width=True):
    ratio, tpv, details_list, y_totals = calculate_advanced_sroi(t_input, d_rate, years, outcomes_input)
    st.session_state.sroi_results = {
        "ratio": ratio, "tpv": tpv, "npv": tpv - t_input,
        "details": details_list, "yearly_totals": y_totals,
        "total_input": t_input, "project_name": p_name
    }

if 'sroi_results' in st.session_state:
    res = st.session_state.sroi_results
    st.divider()
    
    st.subheader("📈 สรุปผลตัวชี้วัดทางการเงิน (Financial Indicators)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SROI Ratio", f"{res['ratio']:.2f}")
    m2.metric("Total PV (TPV)", f"฿{res['tpv']:,.2f}")
    m3.metric("Net PV (NPV)", f"฿{res['npv']:,.2f}")
    m4.metric("Total Input", f"฿{res['total_input']:,.2f}")

    st.subheader("🗓️ ตารางมูลค่าปัจจุบันรายปี (Present Value of Each Year)")
    df_final = pd.DataFrame(res['details'])
    
    # เพิ่มแถวสรุปผลรวมรายปี (TOTAL PV PER YEAR)
    summary_row = {"Stakeholder/Outcome": "TOTAL PV PER YEAR", "Total PV (by Item)": res['tpv']}
    for idx, val in enumerate(res['yearly_totals']):
        summary_row[f"Y{idx+1} PV"] = val
    
    df_with_summary = pd.concat([df_final, pd.DataFrame([summary_row])], ignore_index=True)
    st.dataframe(df_with_summary.style.format(precision=2, thousands=","), use_container_width=True)

    # --- 8. ส่วนการ Export ---
    st.subheader("📥 ดาวน์โหลดผลลัพธ์")
    e1, e2 = st.columns(2)
    with e1:
        # Export CSV (utf-8-sig เพื่อรองรับภาษาไทยใน Excel)
        csv = df_with_summary.to_csv(index=False).encode('utf-8-sig')
        st.download_button("Download Full CSV", csv, f"SROI_{res['project_name']}.csv", "text/csv")
    with e2:
        # Export PDF Summary
        def generate_pdf(data):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="SROI Summary Report", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Project: {data['project_name']}", ln=True)
            pdf.cell(200, 10, txt=f"SROI Ratio: {data['ratio']:.2f}", ln=True)
            pdf.cell(200, 10, txt=f"Total PV (TPV): {data['tpv']:,.2f} THB", ln=True)
            pdf.cell(200, 10, txt=f"Net PV (NPV): {data['npv']:,.2f} THB", ln=True)
            pdf.cell(200, 10, txt=f"Total Investment: {data['total_input']:,.2f} THB", ln=True)
            return pdf.output(dest='S').encode('latin-1')
        
        try:
            pdf_bytes = generate_pdf(res)
            st.download_button("Download PDF Summary", pdf_bytes, f"SROI_Summary_{res['project_name']}.pdf", "application/pdf")
        except:
            st.warning("หมายเหตุ: PDF รองรับเฉพาะภาษาอังกฤษครับ")
