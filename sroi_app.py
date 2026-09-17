import streamlit as st
import pandas as pd
import datetime
import os
import io
import base64
import urllib.request
import textwrap

# ==========================================
# 0. ระบบตั้งค่าเริ่มต้นและตรวจสอบไลบรารี
# ==========================================
st.set_page_config(page_title="SROI Professional Calculator", layout="wide", page_icon="📊")

# ตรวจสอบว่าติดตั้ง ReportLab หรือยัง (แก้ปัญหาเว็บพัง)
try:
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.pagesizes import A4
except ImportError:
    st.error("🚨 ระบบแจ้งเตือนความเสี่ยง: ไม่พบเครื่องมือ 'reportlab'")
    st.info("นายหญิงโปรดเพิ่มคำว่า `reportlab` ลงในไฟล์ `requirements.txt` บน GitHub แล้วรอระบบรีสตาร์ทสักครู่ครับ")
    st.stop() # หยุดการทำงานชั่วคราวเพื่อป้องกัน Error สีแดง

# ระบบดาวน์โหลดฟอนต์ภาษาไทย (THSarabunNew) อัตโนมัติ
FONT_FILE = "THSarabunNew.ttf"
FONT_URL = "https://github.com/gungunss/ThaiFonts/raw/master/THSarabunNew.ttf"

@st.cache_resource
def load_thai_font():
    if not os.path.exists(FONT_FILE):
        try:
            urllib.request.urlretrieve(FONT_URL, FONT_FILE)
        except Exception:
            pass
load_thai_font()

# ==========================================
# 1. การตกแต่งหน้าจอ (CSS)
# ==========================================
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
        background-color: #ffffff; padding: 15px; border-radius: 8px; 
        border: 1px solid #2980b9; border-left: 10px solid #2980b9;
        margin-bottom: 20px; color: #000000 !important;
        font-size: 0.9rem; line-height: 1.4;
    }
    .section-head {
        background-color: #e8f4f8; padding: 10px; border-radius: 5px;
        font-weight: bold; color: #2c3e50; margin-bottom: 15px;
        border-left: 5px solid #3498db;
    }
    </style>
    """, unsafe_allow_html=True)

def reset_system():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.num_rows = 1
    st.rerun()

# ==========================================
# 2. ฟังก์ชันคำนวณ SROI ทางคณิตศาสตร์
# ==========================================
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
            if year_num > 1:
                current_impact *= (1 - drp_f)
            
            pv = current_impact / ((1 + (discount_rate/100)) ** year_num)
            item_yearly_pvs.append(pv)
            item_total_pv += pv
            yearly_totals[year_idx] += pv
        
        row_data = {
            "ผู้มีส่วนได้ส่วนเสีย": item['stakeholder'],
            "ปัจจัยที่ใช้ (Input)": item['input_text'],
            "กิจกรรม (Activity)": item['activity_text'],
            "ผลผลิต (Output)": item['output_text'],
            "ผลลัพธ์ (Outcome)": item['outcome_text'],
            "ตัวชี้วัด (Indicator)": item['indicator_text'],
            "Proxy Description": item['proxy_desc'],
            "Impact Description": item['impact_desc'],
            "ค่าแทนทางการเงิน (บาท)": item['proxy_val'],
            "จำนวน": item['qty'],
            "Deadweight (%)": item['dw'],
            "Displacement (%)": item['disp'],
            "Attribution (%)": item['attr'],
            "Drop-off (%)": item['drop_off'],
            "Total PV (TPV)": item_total_pv
        }
        for y_idx, y_pv in enumerate(item_yearly_pvs):
            row_data[f"ปีที่ {y_idx+1} (PV)"] = y_pv
            
        detailed_list.append(row_data)
        
    total_pv_sum = sum(yearly_totals)
    sroi_ratio = total_pv_sum / total_input if total_input > 0 else 0
    return sroi_ratio, total_pv_sum, detailed_list, yearly_totals

# ==========================================
# 3. หน้าจอการใช้งาน (UI)
# ==========================================
st.title("📊 SROI Calculator (Official Report Edition)")

with st.sidebar:
    st.header("⚙️ ตั้งค่าโครงการ")
    p_name = st.text_input("ชื่อโครงการ", value="SROI_Project_2026")
    t_input = st.number_input("งบประมาณรวม (Total Input)", value=100000.0, min_value=1.0)
    d_rate = st.number_input("Discount Rate (%)", value=3.5, step=0.1)
    years_val = st.slider("ระยะเวลาวิเคราะห์ (ปี)", 1, 10, 5)
    st.divider()
    if st.button("🗑️ ล้างข้อมูลทั้งหมด", use_container_width=True):
        reset_system()
    st.caption("พัฒนาระบบโดย: สำนักวิจัย มหาวิทยาลัยพายัพ")

st.subheader("📝 บันทึกข้อมูล Value Map และการคำนวณ")
st.markdown("""
    <div class="info-box">
    <b>💡 คำนิยามปัจจัยปรับลด (Deduction Factors):</b><br>
    • <b>Deadweight:</b> ผลลัพธ์ที่จะเกิดขึ้นอยู่แล้วแม้ไม่มีโครงการ<br>
    • <b>Displacement:</b> การย้ายปัญหาจากจุดหนึ่งไปอีกจุดหนึ่ง<br>
    • <b>Attribution:</b> ผลที่เกิดจากปัจจัยภายนอกหรือหน่วยงานอื่น <br>
    • <b>Drop-off:</b> อัตราที่ผลประโยชน์ลดลงในแต่ละปีหลังจากจบโครงการ
    </div>
    """, unsafe_allow_html=True)

if 'num_rows' not in st.session_state: st.session_state.num_rows = 1
def add_row(): st.session_state.num_rows += 1
def remove_row():
    if st.session_state.num_rows > 1: st.session_state.num_rows -= 1

c_b1, c_b2, _ = st.columns([1, 1, 4])
with c_b1: st.button("➕ เพิ่มรายการ", on_click=add_row, use_container_width=True)
with c_b2: st.button("➖ ลบรายการล่าสุด", on_click=remove_row, use_container_width=True)

outcomes_input = []
for i in range(st.session_state.num_rows):
    with st.expander(f"📍 การวิเคราะห์รายการที่ {i+1}", expanded=True):
        st.markdown('<div class="section-head">1. ข้อมูลเชิงคุณภาพ (Value Map)</div>', unsafe_allow_html=True)
        q1, q2 = st.columns(2)
        stk = q1.text_input("ผู้มีส่วนได้ส่วนเสีย", key=f"stk_{i}")
        inp = q2.text_input("ปัจจัยที่ใช้ (Input)", key=f"inp_{i}")
        act = q1.text_area("กิจกรรม/กระบวนการ", height=70, key=f"act_{i}")
        outp = q2.text_area("ผลผลิต (Output)", height=70, key=f"outp_{i}")
        outc = q1.text_area("ผลลัพธ์ (Outcome)", height=70, key=f"outc_{i}")
        ind = q2.text_area("ตัวชี้วัด (Indicator)", height=70, key=f"ind_{i}")
        prx_desc = q1.text_input("คำอธิบายค่าแทนทางการเงิน (Proxy)", key=f"prx_d_{i}")
        imp_desc = q2.text_input("ผลกระทบ (Impact)", key=f"imp_d_{i}")
        
        st.markdown('<div class="section-head">2. ข้อมูลสำหรับการคำนวณ (Financials)</div>', unsafe_allow_html=True)
        f1, f2, f3 = st.columns([2, 1, 1])
        prx_val = f1.number_input("มูลค่าแทน (บาท)", value=0.0, key=f"prx_v_{i}")
        qty = f2.number_input("จำนวน", value=0, key=f"qty_{i}")
        
        p1, p2, p3, p4 = st.columns(4)
        dw = p1.number_input("Deadweight %", 0.0, 100.0, 0.0, key=f"dw_{i}")
        disp = p2.number_input("Displacement %", 0.0, 100.0, 0.0, key=f"disp_{i}")
        attr = p3.number_input("Attribution %", 0.0, 100.0, 0.0, key=f"att_{i}")
        drop = p4.number_input("Drop-off %", 0.0, 100.0, 0.0, key=f"drp_{i}")
        
        outcomes_input.append({
            "stakeholder": stk, "input_text": inp, "activity_text": act,
            "output_text": outp, "outcome_text": outc, "indicator_text": ind,
            "proxy_desc": prx_desc, "impact_desc": imp_desc,
            "proxy_val": prx_val, "qty": qty, "dw": dw, "disp": disp, "attr": attr, "drop_off": drop
        })

# ==========================================
# 4. ประมวลผลและสร้างรายงาน PDF / CSV
# ==========================================
if st.button("🚀 ประมวลผลและคำนวณ SROI", type="primary", use_container_width=True):
    analysis_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ratio, tpv, details, y_totals = calculate_advanced_sroi(t_input, d_rate, years_val, outcomes_input)
    st.session_state.res = {
        "ratio": ratio, "tpv": tpv, "npv": tpv - t_input,
        "details": details, "y_totals": y_totals, "t_input": t_input, 
        "p_name": p_name, "years": years_val, "time": analysis_time
    }

if 'res' in st.session_state:
    r = st.session_state.res
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SROI Ratio", f"{r['ratio']:.2f}")
    m2.metric("Total PV (TPV)", f"฿{r['tpv']:,.2f}")
    m3.metric("Net PV (NPV)", f"฿{r['npv']:,.2f}")
    m4.metric("Total Input", f"฿{r['t_input']:,.2f}")

    df_full = pd.DataFrame(r['details'])
    st.dataframe(df_full.style.format(precision=2, thousands=","), use_container_width=True)

    c1, c2 = st.columns(2)
    
    with c1:
        header_df = pd.DataFrame({
            "ชื่อโครงการ": [r['p_name']],
            "งบประมาณรวม": [f"{r['t_input']:,.2f}"],
            "ระยะเวลาวิเคราะห์": [f"{r['years']} ปี"],
            "วันที่ทำการวิเคราะห์": [r['time']]
        })
        csv_buffer = header_df.to_csv(index=False) + "\n" + df_full.to_csv(index=False)
        st.download_button("📥 Download CSV (Full Data)", csv_buffer.encode('utf-8-sig'), f"SROI_Detailed_{r['p_name']}.csv", "text/csv")
    
    def generate_full_pdf_report(data):
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=A4)
        width, height = A4
        
        font_name = "Helvetica"
        if os.path.exists(FONT_FILE):
            pdfmetrics.registerFont(TTFont('ThaiFont', FONT_FILE))
            font_name = 'ThaiFont'
            
        def write_multiline(x, y, text, max_width=80):
            lines = textwrap.wrap(str(text), width=max_width)
            for line in lines:
                can.drawString(x, y, line)
                y -= 20
            return y
        
        # --- หน้า 1 ---
        can.setFont(font_name, 22)
        can.drawCentredString(width/2, height - 50, "SROI Analysis Official Report")
        
        can.setFont(font_name, 16)
        y_pos = height - 100
        line_height = 25
        
        can.drawString(50, y_pos, f"ชื่อโครงการ: {data['p_name']}")
        y_pos -= line_height
        can.drawString(50, y_pos, f"งบประมาณโครงการ (Total Input): {data['t_input']:,.2f} บาท")
        y_pos -= line_height
        can.drawString(50, y_pos, f"ระยะเวลาการวิเคราะห์: {data['years']} ปี")
        y_pos -= line_height
        can.drawString(50, y_pos, f"วันที่ทำการวิเคราะห์: {data['time']}")
        y_pos -= (line_height * 2)
        
        can.setFont("Helvetica-Bold" if font_name == "Helvetica" else font_name, 18)
        can.drawString(50, y_pos, f"SROI Ratio: {data['ratio']:.2f}")
        y_pos -= line_height
        can.setFont(font_name, 16)
        can.drawString(50, y_pos, f"Net Present Value (NPV): {data['npv']:,.2f} บาท")
        y_pos -= line_height
        can.drawString(50, y_pos, f"Total Present Value (TPV): {data['tpv']:,.2f} บาท")
        y_pos -= (line_height * 2)
        
        can.setFont("Helvetica-Bold" if font_name == "Helvetica" else font_name, 16)
        can.drawString(50, y_pos, "[ สรุปประมาณการมูลค่าปัจจุบันรายปีรวม ]")
        y_pos -= line_height
        can.setFont(font_name, 16)
        
        for idx, val in enumerate(data['y_totals']):
            can.drawString(70, y_pos, f"- ปีที่ {idx+1}: {val:,.2f} บาท")
            y_pos -= line_height
            
        can.showPage() 
        
        # --- หน้า 2 ---
        can.setFont("Helvetica-Bold" if font_name == "Helvetica" else font_name, 18)
        can.drawString(50, height - 50, "[ รายละเอียดการวิเคราะห์ Value Map ]")
        y_pos = height - 90
        
        for i, d in enumerate(data['details']):
            if y_pos < 200:
                can.showPage()
                y_pos = height - 50
            
            can.setFont("Helvetica-Bold" if font_name == "Helvetica" else font_name, 16)
            y_pos = write_multiline(50, y_pos, f"รายการที่ {i+1}: {d['ผลลัพธ์ (Outcome)']}", 90)
            
            can.setFont(font_name, 14)
            y_pos = write_multiline(70, y_pos, f"ผู้มีส่วนได้เสีย: {d['ผู้มีส่วนได้ส่วนเสีย']}")
            y_pos = write_multiline(70, y_pos, f"กิจกรรม: {d['กิจกรรม (Activity)']}")
            y_pos = write_multiline(70, y_pos, f"ตัวชี้วัด: {d['ตัวชี้วัด (Indicator)']}")
            
            can.drawString(70, y_pos, f"มูลค่า TPV ของรายการนี้: {d['Total PV (TPV)']:,.2f} บาท")
            y_pos -= 25
            
            can.drawString(70, y_pos, "มูลค่ารายปี (PV): ")
            x_pos_year = 160
            for j in range(len(data['y_totals'])):
                if x_pos_year > 450: 
                    y_pos -= 20
                    x_pos_year = 160
                can.drawString(x_pos_year, y_pos, f"ปีที่ {j+1}: {d[f'ปีที่ {j+1} (PV)']:,.2f}")
                x_pos_year += 100
            
            y_pos -= 35 
            can.setStrokeColorRGB(0.8, 0.8, 0.8)
            can.line(50, y_pos + 15, 545, y_pos + 15) 

        can.save()
        packet.seek(0)
        return packet.read()

    pdf_bytes = generate_full_pdf_report(r)

    with c2:
        st.download_button("📥 Download PDF (Full Report)", pdf_bytes, f"SROI_Report_{r['p_name']}.pdf", "application/pdf")

    st.divider()
    st.markdown('<div class="section-head">🖨️ ตัวอย่างรายงาน (กดไอคอนเครื่องปริ้นเตอร์เพื่อ Print as PDF)</div>', unsafe_allow_html=True)
    
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)
