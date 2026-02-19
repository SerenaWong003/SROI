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
    <p><b>1. Deadweight (ผลลัพธ์ส่วนเกิน):</b> มูลค่าของผลลัพธ์ที่คาดว่าจะเกิดขึ้นอยู่แล้วแม้ไม่มีโครงการ</p>
    <p><b>2. Displacement (การแทนที่):</b> การย้ายปัญหาจากจุดหนึ่งไปอีกจุดหนึ่ง หรือทำให้เกิดปัญหาที่อื่นแทน</p>
    <p><b>3. Attribution (การรับรองสิทธิ์):</b> ผลที่เกิดจากหน่วยงานอื่น หรือปัจจัยภายนอกที่มีส่วนช่วย ไม่ใช่เรา 100%</p>
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

# --- 7. การจัดการรายการผู้มีส่วนได้เสีย ---
if 'num_rows' not in st.session_state:
    st.session_state.num_rows = 1

def add_row():
    if st.session_state.num_rows < 10: st.session_state.num_rows += 1
def remove_row():
    if st.session_state.num_rows > 1: st.session_state.num_rows -= 1

st.subheader("📝 รายละเอียดข้อมูลและปัจจัยปรับลด")
c_b1, c_b2, _ = st.columns([1, 1, 4])
with c_b1: st.button("➕ เพิ่มแถว", on_click=add_row, use_container_width=True)
with c_b2: st.button("➖ ลบแถว", on_click=remove_row, use_container_width=True)

outcomes_input = []
for i in range(st.session_state.num_rows):
    with st.expander(f"รายการที่ {i+1}", expanded=True):
        r1_c1, r1_c2, r1_c3 = st.columns([2, 1, 1])
        with r1_c1: stk = st.text_input("ชื่อผู้มีส่วนได้เสีย/ผลลัพธ์", key=f"stk_{i}")
        with r1_c2: prx = st.number_input("ค่าแทนทางการเงิน (Proxy)", value=0, key=f"prx_{i}")
        with r1_c3: q = st.number_input("จำนวน/ปริมาณ", value=0, key=f"q_{i}")
        
        st.markdown("**ปัจจัยปรับลดมูลค่า (%)**")
        
        # ฟังก์ชันสร้าง Slider + Number Input คู่กัน (Sync 100%)
        def dual_input(label, key_id):
            col_s, col_n = st.columns([3, 1])
            # ใช้ st.number_input เป็นตัวคุมค่าหลัก
            val_n = col_n.number_input(f"{label} (%)", min_value=0.0, max_value=100.0, step=1.0, key=f"num_{key_id}")
            # ใช้ st.slider แสดงผลและปรับตาม
            val_s = col_s.slider(label, 0.0, 100.0, value=val_n, key=f"sli_{key_id}", label_visibility="collapsed")
            return val_n # คืนค่าจากช่องกรอกเพื่อความแม่นยำ

        dw = dual_input("Deadweight", f"dw_{i}")
        disp = dual_input("Displacement", f"disp_{i}")
        attr = dual_input("Attribution", f"att_{i}")
        drop = dual_input("Drop-off", f"drp_{i}")
        
        outcomes_input.append({"stakeholder": stk, "proxy": prx, "qty": q, "dw": dw, "disp": disp, "attr": attr, "drop_off": drop})

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
    
    st.subheader("📈 สรุปผลตัวชี้วัดทางการเงิน (Financial Indicators)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SROI Ratio", f"{r['ratio']:.2f}")
    m2.metric("Total PV (TPV)", f"฿{r['tpv']:,.2f}")
    m3.metric("Net PV (NPV)", f"฿{r['npv']:,.2f}")
    m4.metric("Total Input", f"฿{r['t_input']:,.2f}")

    st.subheader("🗓️ ตารางมูลค่าปัจจุบันรายปี (Present Value of Each Year)")
    df_final = pd.DataFrame(r['details'])
    summary_row = {"ผู้มีส่วนได้เสีย/ผลลัพธ์": "TOTAL PV PER YEAR", "Total PV (TPV)": r['tpv']}
    for idx, val in enumerate(r['y_totals']):
        summary_row[f"ปีที่ {idx+1} (PV)"] = val
    
    df_with_summary = pd.concat([df_final, pd.DataFrame([summary_row])], ignore_index=True)
    st.dataframe(df_with_summary.style.format(precision=2, thousands=","), use_container_width=True)

    st.subheader("📥 ดาวน์โหลดรายงาน")
    e_col1, e_col2 = st.columns(2)
    with e_col1:
        csv_data = df_with_summary.to_csv(index=False).encode('utf-8-sig')
        st.download_button("Download CSV (Excel)", csv_data, f"SROI_{r['p_name']}.csv", "text/csv")
    
    with e_col2:
        def generate_pdf(data):
            pdf = FPDF()
            font_path = "THSarabunNew.ttf"
            font_name = "THSarabunNew"
            if os.path.exists(font_path):
                pdf.add_font(font_name, "", font_path)
                pdf.add_page()
                pdf.set_font(font_name, size=18)
            else:
                pdf.add_page()
                pdf.set_font("helvetica", size=14)
            
            pdf.cell(0, 10, txt="SROI Analysis Report", align='C', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)
            pdf.cell(0, 10, txt=f"ชื่อโครงการ: {data['p_name']}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 10, txt=f"SROI Ratio: {data['ratio']:.2f}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 10, txt=f"Total PV (TPV): {data['tpv']:,.2f} บาท", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(10)
            pdf.cell(0, 10, txt="รายละเอียดผลลัพธ์:", new_x="LMARGIN", new_y="NEXT")
            for d in data['details']:
                name = d.get('ผู้มีส่วนได้เสีย/ผลลัพธ์', '-')
                val = d.get('Total PV (TPV)', 0)
                pdf.cell(0, 10, txt=f"- {name}: {val:,.2f} บาท", new_x="LMARGIN", new_y="NEXT")
            return bytes(pdf.output())

        try:
            pdf_bytes = generate_pdf(r)
            st.download_button("Download PDF (Report)", pdf_bytes, f"SROI_Report_{r['p_name']}.pdf", "application/pdf")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการสร้าง PDF: {e}")
