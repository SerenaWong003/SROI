import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="SROI Professional Calculator", layout="wide")

# --- 2. ปรับแต่ง CSS - บังคับสีดำบนพื้นหลังขาวสำหรับ Metrics และ Glossary ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    
    /* ปรับแต่งส่วน Metric ให้พื้นหลังขาว ตัวหนังสือดำ */
    [data-testid="metric-container"] {
        background-color: #ffffff !important;
        border: 1px solid #dee2e6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricValue"] {
        color: #000000 !important;
        font-weight: bold;
    }
    [data-testid="stMetricLabel"] {
        color: #000000 !important;
        font-weight: 500;
    }

    /* ปรับแต่งส่วนคำอธิบาย Glossary ให้ตัวหนังสือดำชัดเจน */
    .info-box { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 8px; 
        border: 1px solid #2980b9; 
        border-left: 8px solid #2980b9;
        margin-bottom: 20px;
        color: #000000 !important;
    }
    .info-box b, .info-box p { color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ฟังก์ชันสำหรับล้างข้อมูลทั้งหมด (Clear Data) ---
def reset_system():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.num_rows = 1
    st.rerun()

st.title("📊 SROI Calculator (Full Financial Edition)")

# --- 4. ส่วนอธิบายศัพท์ (ตัวหนังสือสีดำ พื้นขาว) ---
with st.expander("ℹ️ คำอธิบายศัพท์เทคนิคและเกณฑ์การปรับมูลค่า (Glossary)", expanded=False):
    st.markdown("""
    <div class="info-box">
    <p><b>1. Deadweight:</b> ผลลัพธ์ที่จะเกิดขึ้นอยู่แล้วแม้ไม่มีโครงการ (เช่น รายได้ที่เพิ่มขึ้นเองตามกลไกตลาด)</p>
    <p><b>2. Displacement:</b> ผลของโครงการที่ไปทำให้เกิดปัญหาในพื้นที่อื่นแทน</p>
    <p><b>3. Attribution:</b> ผลที่เกิดจากหน่วยงานอื่นหรือปัจจัยภายนอกที่ไม่ใช่โครงการเรา 100%</p>
    <p><b>4. Drop-off:</b> อัตราที่ผลประโยชน์จะลดลงในแต่ละปี หลังจากโครงการเสร็จสิ้นลง</p>
    <p><b>5. Present Value (PV):</b> มูลค่าของเงินในอนาคตที่ถูกทอนกลับมาเป็นมูลค่าในปัจจุบัน</p>
    </div>
    """, unsafe_allow_html=True)

# --- 5. Logic การคำนวณรายปี ---
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
            
        row_data = {"Stakeholder/Outcome": item['stakeholder'], "Total PV (TPV)": item_total_pv}
        for y_idx, y_pv in enumerate(item_yearly_pvs):
            row_data[f"Y{y_idx+1} PV"] = y_pv
        detailed_list.append(row_data)
        
    total_pv_all = sum(yearly_totals)
    sroi_ratio = total_pv_all / total_input if total_input > 0 else 0
    return sroi_ratio, total_pv_all, detailed_list, yearly_totals

# --- 6. ส่วน Sidebar ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าโครงการ")
    p_name = st.text_input("ชื่อโครงการ", value="SROI_Project_2026")
    t_input = st.number_input("งบประมาณรวม (Total Input)", value=100000, step=1000)
    d_rate = st.number_input("Discount Rate (%)", value=3.5, step=0.1)
    years = st.slider("ระยะเวลาที่ต้องการวิเคราะห์ (ปี)", 1, 10, 5)
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

st.subheader("📝 รายละเอียดข้อมูลผลลัพธ์")
c_b1, c_b2, _ = st.columns([1, 1, 4])
with c_b1: st.button("➕ เพิ่มรายการ", on_click=add_row, use_container_width=True)
with c_b2: st.button("➖ ลบรายการ", on_click=remove_row, use_container_width=True)

outcomes_input = []
for i in range(st.session_state.num_rows):
    with st.expander(f"รายการที่ {i+1}", expanded=True):
        r1_c1, r1_c2, r1_c3 = st.columns([2, 1, 1])
        with r1_c1: stk = st.text_input("ชื่อผู้มีส่วนได้เสีย/ผลลัพธ์", key=f"stk_{i}")
        with r1_c2: prx = st.number_input("Proxy (บาท)", value=0, key=f"prx_{i}")
        with r1_c3: q = st.number_input("จำนวนหน่วย", value=0, key=f"q_{i}")
        
        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4) 
        with r2_c1: dw = st.slider("Deadweight", 0.0, 1.0, 0.0, key=f"dw_{i}")
        with r2_c2: disp = st.slider("Displacement", 0.0, 1.0, 0.0, key=f"disp_{i}")
        with r2_c3: att = st.slider("Attribution", 0.0, 1.0, 0.0, key=f"attr_{i}")
        with r2_c4: drp = st.slider("Drop-off", 0.0, 1.0, 0.0, key=f"drp_{i}")
        outcomes_input.append({"stakeholder": stk, "proxy": prx, "qty": q, "dw": dw, "disp": disp, "attr": att, "drop_off": drp})

# --- 8. ประมวลผลและแสดงผลลัพธ์ ---
if st.button("🚀 คำนวณและประมวลผล SROI", type="primary", use_container_width=True):
    ratio, tpv, details, y_totals = calculate_advanced_sroi(t_input, d_rate, years, outcomes_input)
    st.session_state.sroi_results = {
        "ratio": ratio, "tpv": tpv, "npv": tpv - t_input,
        "details": details, "y_totals": y_totals, "t_input": t_input, "p_name": p_name
    }

if 'sroi_results' in st.session_state:
    res = st.session_state.sroi_results
    st.divider()
    
    # ส่วน Metrics (ตัวหนังสือดำ พื้นขาว)
    st.subheader("📈 สรุปผลตัวชี้วัดทางการเงิน (Financial Indicators)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SROI Ratio", f"{res['ratio']:.2f}")
    m2.metric("Total PV (TPV)", f"฿{res['tpv']:,.2f}")
    m3.metric("Net PV (NPV)", f"฿{res['npv']:,.2f}")
    m4.metric("Total Input", f"฿{res['t_input']:,.2f}")

    # ตารางรายปี
    st.subheader("🗓️ ตารางมูลค่าปัจจุบันรายปี (Present Value of Each Year)")
    df_final = pd.DataFrame(res['details'])
    summary_row = {"Stakeholder/Outcome": "TOTAL PV PER YEAR", "Total PV (TPV)": res['tpv']}
    for idx, val in enumerate(res['y_totals']):
        summary_row[f"Y{idx+1} PV"] = val
    
    df_with_summary = pd.concat([df_final, pd.DataFrame([summary_row])], ignore_index=True)
    st.dataframe(df_with_summary.style.format(precision=2, thousands=","), use_container_width=True)

    # ส่งออก CSV
    csv_data = df_with_summary.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Download Full CSV Report", csv_data, f"SROI_{res['p_name']}.csv", "text/csv")
