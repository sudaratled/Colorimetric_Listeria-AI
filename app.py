import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import colorsys
import numpy as np

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="HNB Analysis V.New Data", layout="centered")

st.title("🧬 HNB LAMP Analyzer (New Dataset)")
st.markdown("วิเคราะห์ผลจากไฟล์ข้อมูล HNB Update และภาพถ่าย")

# --- 1. ตั้งค่า Parameter (นำค่าจาก Code ส่วนที่ 1 มาแก้ตรง value นี้) ---
st.sidebar.header("⚙️ Settings (UV-Vis)")
# ลองใส่ค่าประมาณการณ์จากข้อมูลชุดใหม่ (คุณสามารถแก้ได้ถ้าผล Run Code ส่วนที่ 1 เปลี่ยนไป)
lambda_pos = st.sidebar.number_input("Wavelength Positive (nm)", value=650) 
lambda_neg = st.sidebar.number_input("Wavelength Negative (nm)", value=565) 
threshold = st.sidebar.number_input("Threshold Ratio (A_pos/A_neg)", value=1.0)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Settings (Image)")
hue_cutoff = st.sidebar.slider("Blue/Violet Cutoff (Hue)", 0, 360, 245)

# --- 2. ฟังก์ชันอ่านไฟล์ที่อัปเกรดให้รองรับไฟล์ชุดใหม่ ---
def load_and_clean_data(file):
    try:
        # อ่านไฟล์โดยข้าม 2 บรรทัดแรก (ตามไฟล์ Pos1.csv)
        df = pd.read_csv(file, skiprows=2, encoding='utf-8')
    except UnicodeDecodeError:
        file.seek(0)
        df = pd.read_csv(file, skiprows=2, encoding='ISO-8859-1')
    except Exception:
        return None

    # จัดการชื่อ Column ให้มาตรฐาน
    if len(df.columns) >= 2:
        # บังคับชื่อ 2 คอลัมน์แรก ส่วนที่เหลือช่างมัน
        clean_cols = ['Wavelength', 'Absorbance'] + list(df.columns[2:])
        df.columns = clean_cols
    else:
        st.error("Format ไฟล์ไม่ถูกต้อง")
        return None

    # Clean Data: ลบบรรทัดที่มี // หรือไม่ใช่ตัวเลข
    df = df[~df['Wavelength'].astype(str).str.startswith('//')]
    df['Wavelength'] = pd.to_numeric(df['Wavelength'], errors='coerce')
    df['Absorbance'] = pd.to_numeric(df['Absorbance'], errors='coerce')
    df = df.dropna(subset=['Wavelength', 'Absorbance'])
    
    return df

# --- 3. ฟังก์ชันวิเคราะห์ภาพ (เหมือนเดิม) ---
def analyze_image_color(image):
    img_array = np.array(image)
    h, w, _ = img_array.shape
    center_h, center_w = h // 2, w // 2
    crop_h, crop_w = h // 6, w // 6 # Crop เล็กลงหน่อยเพื่อความแม่นยำ
    center_img = img_array[center_h - crop_h : center_h + crop_h, center_w - crop_w : center_w + crop_w]
    
    avg_rgb = np.average(np.average(center_img, axis=0), axis=0)
    r, g, b = avg_rgb
    h_hsv, s_hsv, v_hsv = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    
    return h_hsv * 360, (r, g, b), center_img

# --- 4. ส่วนแสดงผล ---
tab1, tab2, tab3 = st.tabs(["📂 วิเคราะห์ไฟล์กราฟ", "📷 วิเคราะห์จากกล้อง", "📝 กรอกค่าเอง"])

with tab1:
    st.subheader("วิเคราะห์ผลจากไฟล์ CSV (HNB Update)")
    uploaded_file = st.file_uploader("อัปโหลดไฟล์ CSV (เช่น Pos1.csv, Ne1.csv)", type=['csv', 'xlsx'])
    
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            df = load_and_clean_data(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file) # เผื่อกรณี Excel
        
        if df is not None:
            # หาค่า Absorbance ที่ความยาวคลื่นเป้าหมาย
            try:
                # ใช้ iloc หาแถวที่ wavelength ใกล้เคียงที่สุด
                row_pos = df.iloc[(df['Wavelength'] - lambda_pos).abs().argsort()[:1]]
                row_neg = df.iloc[(df['Wavelength'] - lambda_neg).abs().argsort()[:1]]
                
                val_pos = row_pos['Absorbance'].values[0]
                val_neg = row_neg['Absorbance'].values[0]
                
                # Plot Graph
                st.line_chart(df.set_index('Wavelength')['Absorbance'])
                
                # Display Results
                col1, col2, col3 = st.columns(3)
                col1.metric(f"Abs @{lambda_pos:.0f}nm", f"{val_pos:.3f}")
                col2.metric(f"Abs @{lambda_neg:.0f}nm", f"{val_neg:.3f}")
                
                ratio = val_pos / val_neg if val_neg != 0 else 0
                col3.metric("Ratio (Pos/Neg)", f"{ratio:.2f}")
                
                st.divider()
                
                # Logic การตัดสินผล
                if ratio > threshold:
                    st.success(f"### ✅ ผล: POSITIVE (สีฟ้า)")
                    st.caption(f"กราฟสูงขึ้นที่ {lambda_pos}nm ชัดเจน")
                else:
                    st.error(f"### ⛔ ผล: NEGATIVE (สีม่วง)")
                    st.caption(f"กราฟสูงขึ้นที่ {lambda_neg}nm หรือ Ratio ต่ำ")
                    
            except IndexError:
                st.warning("ไม่พบช่วงความยาวคลื่นที่ต้องการในไฟล์นี้")

with tab2:
    st.subheader("ถ่ายภาพเพื่อวิเคราะห์สี")
    img_file = st.camera_input("ถ่ายภาพหลอดทดลอง (วางบนพื้นขาว)")
    
    if img_file:
        image = Image.open(img_file)
        hue, rgb, crop = analyze_image_color(image)
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(crop, caption="จุดที่วิเคราะห์")
            st.color_picker("สีที่อ่านได้", f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}", disabled=True)
        with c2:
            st.metric("Hue Value", f"{hue:.1f}°")
            if hue < hue_cutoff:
                st.success("### ✅ POSITIVE (Blue Tone)")
            else:
                st.error("### ⛔ NEGATIVE (Violet Tone)")

with tab3:
    st.write("โหมดคำนวณมือ (Manual Calculator)")
    m_pos = st.number_input("Abs Positive", 0.0)
    m_neg = st.number_input("Abs Negative", 0.0)
    if st.button("Calculate"):
        if m_neg > 0:
            r = m_pos/m_neg
            st.info(f"Ratio = {r:.2f}")
            if r > threshold: st.success("Positive") 
            else: st.error("Negative")