import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import os

# --- 1. การตั้งค่าหน้าจอ (Page Config) ---
st.set_page_config(page_title="SROI Professional Calculator", layout="wide")

# --- 2. ปรับแต่ง CSS - บังคับสีดำบนพื้นหลังขาวและส่วนบรรยาย ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    
    /* ส่วน Metric สรุปผล: ตัวหนังสือดำ พื้นหลังขาว */
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

    /* ส่วนหัวข้อแยกกลุ่มข้อมูล */
    .section-head {
        background-color: #ffffff; 
        padding: 10px; 
        border-radius: 5px;
        font-weight: bold; 
        color: #000000; 
        margin-bottom: 15px;
        border-left: 8px solid #3498db;
        border-bottom: 1px solid #dee2e6;
    }
    
    /* กล่องคำอธิบาย Glossary */
    .info-box { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 8px; 
        border: 1px solid #2980b9; 
        border-left: 10px solid #2980b9;
        margin-bottom: 25px;
        color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ฟังก์ชันสำหรับล้างข้อมูล (Reset) ---
def reset_system():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.num_rows = 1
    st.rerun()

st.title("📊 SROI Calculator for University Research")

# --- 4. ส่วนอธิบายศัพท์ (Glossary) ---
with st.expander("ℹ️ คำอธิบายศัพท์เทคนิคในการวิเคราะห์ SROI", expanded=False):
    st.markdown("""
    <div class="info-box">
    <p style='color:#000000;'><b>1. Deadweight:</b> ผลลัพธ์ที่จะเกิดขึ้นอยู่แล้วแม้ไม่มีโครงการ</p>
    <p style='color:#000000;'><b>2. Displacement:</b> การย้ายปัญหาจากจุดหนึ่งไปอีกจุดหนึ่ง หรือทำให้เกิดปัญหาที่อื่นแทน</p>
    <p style='color:#000000;'><b>3. Attribution:</b> ผลที่เกิดจากปัจจัยภายนอกที่ไม่ใช่โครงการเรา 100%</p>
    <p style='color:#000000;'><b>4. Drop-off:</b> อัตราที่ผลประโยชน์ลดลงในแต่ละปีหลังจากโครงการสิ้นสุดลง</p>
    </div>
    """, unsafe_allow_html=True)

# --- 5. Logic การคำนวณรายปี ---
def calculate_advanced_sroi(total_input, discount_rate, duration, outcomes):
    detailed_list = []
    yearly_totals = [0.0] * duration 
    
    for item in outcomes:
        if not item['stakeholder'] or not item['outcome_text']: continue
        
        # ทอนค่า % กลับเป็นทศนิยม
        dw_f = item['dw'] / 100
        disp_f = item['disp'] / 100
        att_f = item['attr'] / 100
        drp_f = item['drop_off'] / 100
        
        # Net Impact ปีแรก
        initial_impact = (item['proxy_val'] * item['qty']) * (1 - dw_f) * (1 - disp_f) * (1 - att_f)
        
        current_impact = initial_impact
        item_yearly_pvs = []
        item_total_pv = 0
        
        for year_idx in range(duration):
            year_num = year_idx + 1
            if year_num > 1:
                current_impact *= (1 - drp_f)
            
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
    t_input = st.number_input("งบประมาณรวม (Total Input)", value=100000, min_value=1, step=1000)
    d_rate = st.number_input("Discount Rate (%)", value=3.5, step=0.1)
    years = st.slider("ระยะเวลาวิเคราะห์ (ปี)", 1, 10, 5)
    st.divider()
    if st.button("🗑️ ล้างข้อมูลทั้งหมด", use_container_width=True):
        reset_system()
    st.caption("พัฒนาระบบโดย : สำนักวิจัย มหาวิทยาลัยพายัพ")

# --- 7. การจัดการรายการผู้มีส่วนได้เสีย (Value Map) ---
if 'num_rows' not in st.session_state:
    st.session_state.num_rows = 1

def add_row():
    if st.session_state.num_rows < 15: st.session_state.num_rows += 1
def remove_row():
    if st.session_state.num_rows > 1: st.session_state.num_rows -= 1

st.subheader("📝 รายละเอียดการวิเคราะห์การเปลี่ยนแปลง สามารถเพิ่มได้สูงสุด 10 รายการ")
col_b1, col_b2, _ = st.columns([1, 1, 4])
with col_b1: st.button("➕ เพิ่มรายการ", on_click=add_row, use_container_width=True)
with col_b2: st.button("➖ ลบรายการล่าสุด", on_click=remove_row, use_container_width=True)

outcomes_input = []
for i in range(st.session_state.num_rows):
    with st.expander(f"📍 การวิเคราะห์รายการที่ {i+1}", expanded=True):
        # ส่วนที่ 1: ข้อมูลเชิงคุณภาพ (Qualitative Data)
        st.markdown('<div class="section-head">1. ข้อมูลเชิงคุณภาพ (Value Map Description)</div>', unsafe_allow_html=True)
        q1, q2 = st.columns(2)
        stk = q1.text_input("ผู้มีส่วนได้ส่วนเสีย (Stakeholder)", key=f"stk_{i}")
        inp = q2.text_input("ปัจจัยที่ใช้ (Input)", key=f"inp_{i}")
        
        act = q1.text_area("กิจกรรม/กระบวนการ (Activity)", height=70, key=f"act_{i}")
        outp = q2.text_area("ผลผลิต (Output)", height=70, key=f"outp_{i}")
        
        outc = q1.text_area("ผลลัพธ์ (Outcome)", height=70, key=f"outc_{i}")
        ind = q2.text_area("ตัวชี้วัด (Indicator)", height=70, key=f"ind_{i}")
        
        prx_d = q1.text_input("คำอธิบายค่าแทนทางการเงิน (Proxy Description)", key=f"prxd_{i}")
        imp_d = q2.text_input("ผลกระทบ (Impact Description)", key=f"impd_{i}")
        
        # ส่วนที่ 2: ข้อมูลสำหรับการคำนวณ (Financial Data)
        st.markdown('<div class="section-head">2. การคำนวณและปัจจัยปรับลด (Financial & Impact Factors)</div>', unsafe_allow_html=True)
        f1, f2 = st.columns(2)
        prx_v = f1.number_input("ค่าแทนทางการเงิน (Proxy Value - บาท)", value=0, key=f"prxv_{i}")
        qty = f2.number_input("จำนวนหน่วย/ปริมาณ", value=0, key=f"qty_{i}")
        
        st.markdown("**ปัจจัยปรับลดมูลค่า (%)**")
        p1, p2, p3, p4 = st.columns(4)
        dw = p1.number_input("Deadweight (%)", 0.0, 100.0, 0.0, key=f"dw_{i}")
        disp = p2.number_input("Displacement (%)", 0.0, 100.0, 0.0, key=f"disp_{i}")
        attr = p3.number_input("Attribution (%)", 0.0, 100.0, 0.0, key=f"attr_{i}")
        drop = p4.number_input("Drop-off (%)", 0.0, 100.0, 0.0, key=f"drp_{i}")
        
        outcomes_input.append({
            "stakeholder": stk, "outcome_text": outc, "proxy_val": prx_v, 
            "qty": qty, "dw": dw, "disp": disp, "attr": attr, "drop_off": drop
        })

# --- 8. ประมวลผลและแสดงผลลัพธ์ ---
if st.button("🚀 คำนวณและประมวลผล SROI", type="primary", use_container_width=True):
    ratio, tpv, details, y_totals = calculate_advanced_sroi(t_input, d_rate, years, outcomes_input)
    st.session_state.res = {
        "ratio": ratio, "tpv": tpv, "npv": tpv - t_input,
        "details": details, "y_totals": y_totals, "t_input": t_input, "p_name": p_name
    }

if 'res' in st.session_state:
    r = st.session_state.res
    st.divider()
    
    # ส่วน Metrics (ตัวหนังสือดำ พื้นหลังขาว)
    st.subheader("📈 สรุปผลตัวชี้วัดทางการเงิน (Financial Indicators)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SROI Ratio", f"{r['ratio']:.2f}")
    m2.metric("Total PV (TPV)", f"฿{r['tpv']:,.2f}")
    m3.metric("Net PV (NPV)", f"฿{r['npv']:,.2f}")
    m4.metric("Total Input", f"฿{r['t_input']:,.2f}")

    # ตารางสรุปรายปี
    st.subheader("🗓️ ตารางมูลค่าปัจจุบันรายปี (Financial Summary Table)")
    df_final = pd.DataFrame(r['details'])
    summary_data = {"ผู้มีส่วนได้ส่วนเสีย": "รวมมูลค่าทั้งหมด", "ผลลัพธ์ (Outcome)": "PV PER YEAR", "Total PV (TPV)": r['tpv']}
    for idx, val in enumerate(r['y_totals']):
        summary_data[f"ปีที่ {idx+1} (PV)"] = val
    
    df_with_summary = pd.concat([df_final, pd.DataFrame([summary_data])], ignore_index=True)
    st.dataframe(df_with_summary.style.format(precision=2, thousands=","), use_container_width=True)

    # ดาวน์โหลดรายงาน
    st.subheader("📥 ดาวน์โหลดรายงาน")
    e1, e2 = st.columns(2)
    with e1:
        csv_data = df_with_summary.to_csv(index=False).encode('utf-8-sig')
        st.download_button("Download CSV (Excel)", csv_data, f"SROI_{r['p_name']}.csv", "text/csv")
    with e2:
        def generate_pdf(data):
            pdf = FPDF()
            font_path = "THSarabunNew.ttf"
            if os.path.exists(font_path):
                pdf.add_font("THSarabunNew", "", font_path)
                pdf.add_page()
                pdf.set_font("THSarabunNew", size=18)
            else:
                pdf.add_page()
                pdf.set_font("helvetica", size=14)
            
            pdf.cell(0, 10, txt=f"SROI Analysis Report: {data['p_name']}", align='C', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)
            pdf.cell(0, 10, txt=f"SROI Ratio: {data['ratio']:.2f}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 10, txt=f"Total PV (TPV): {data['tpv']:,.2f} บาท", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 10, txt=f"Net PV (NPV): {data['npv']:,.2f} บาท", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(10)
            pdf.cell(0, 10, txt="รายละเอียดผลลัพธ์:", new_x="LMARGIN", new_y="NEXT")
            for d in data['details']:
                name = d.get('ผู้มีส่วนได้ส่วนเสีย', '-')
                val = d.get('Total PV (TPV)', 0)
                pdf.cell(0, 10, txt=f"- {name}: {val:,.2f} บาท", new_x="LMARGIN", new_y="NEXT")
            return bytes(pdf.output())

        try:
            pdf_bytes = generate_pdf(r)
            st.download_button("Download PDF Report", pdf_bytes, f"SROI_Report_{r['p_name']}.pdf", "application/pdf")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการสร้าง PDF: {e}")
