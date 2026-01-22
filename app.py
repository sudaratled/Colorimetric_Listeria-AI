import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import colorsys
import numpy as np

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="HNB LAMP Analyzer v4", layout="centered")

st.title("🧬 HNB LAMP Analyzer (Pro)")
st.markdown("วิเคราะห์ผลจากไฟล์ CSV หรือ รูปถ่าย (รองรับ Upload)")

# --- 1. ตั้งค่า Parameter (อัปเดตจากข้อมูลชุดล่าสุด) ---
st.sidebar.header("⚙️ Settings (UV-Vis)")
# ค่าจากการวิเคราะห์ไฟล์ HNB Update ล่าสุด
lambda_pos = st.sidebar.number_input("Wavelength Positive (nm)", value=644, help="แนะนำ 644 nm สำหรับชุดข้อมูลนี้") 
lambda_neg = st.sidebar.number_input("Wavelength Negative (nm)", value=536, help="แนะนำ 536 nm สำหรับชุดข้อมูลนี้") 
threshold = st.sidebar.number_input("Threshold Ratio (A_pos/A_neg)", value=1.0)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Settings (Image)")
hue_cutoff = st.sidebar.slider("Blue/Violet Cutoff (Hue)", 0, 360, 245)

# --- 2. ฟังก์ชันอ่านไฟล์ CSV ---
def load_and_clean_data(file):
    try:
        df = pd.read_csv(file, skiprows=2, encoding='utf-8')
    except UnicodeDecodeError:
        file.seek(0)
        df = pd.read_csv(file, skiprows=2, encoding='ISO-8859-1')
    except Exception:
        return None

    if len(df.columns) >= 2:
        clean_cols = ['Wavelength', 'Absorbance'] + list(df.columns[2:])
        df.columns = clean_cols
    else:
        st.error("Format ไฟล์ไม่ถูกต้อง")
        return None

    df = df[~df['Wavelength'].astype(str).str.startswith('//')]
    df['Wavelength'] = pd.to_numeric(df['Wavelength'], errors='coerce')
    df['Absorbance'] = pd.to_numeric(df['Absorbance'], errors='coerce')
    df = df.dropna(subset=['Wavelength', 'Absorbance'])
    
    return df

# --- 3. ฟังก์ชันวิเคราะห์ภาพ ---
def analyze_image_color(image):
    img_array = np.array(image)
    h, w, _ = img_array.shape
    center_h, center_w = h // 2, w // 2
    crop_h, crop_w = h // 6, w // 6 
    center_img = img_array[center_h - crop_h : center_h + crop_h, center_w - crop_w : center_w + crop_w]
    
    avg_rgb = np.average(np.average(center_img, axis=0), axis=0)
    r, g, b = avg_rgb
    h_hsv, s_hsv, v_hsv = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    
    return h_hsv * 360, (r, g, b), center_img

# --- 4. ส่วนแสดงผลหลัก ---
tab1, tab2, tab3 = st.tabs(["📂 ไฟล์กราฟ (UV-Vis)", "📷 วิเคราะห์รูปภาพ", "📝 กรอกค่าเอง"])

# --- Tab 1: UV-Vis File ---
with tab1:
    st.subheader("วิเคราะห์ผลจากไฟล์ CSV")
    uploaded_file = st.file_uploader("อัปโหลดไฟล์ CSV (เช่น Pos2.csv, Ne3.csv)", type=['csv', 'xlsx'])
    
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            df = load_and_clean_data(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        if df is not None:
            try:
                row_pos = df.iloc[(df['Wavelength'] - lambda_pos).abs().argsort()[:1]]
                row_neg = df.iloc[(df['Wavelength'] - lambda_neg).abs().argsort()[:1]]
                
                val_pos = row_pos['Absorbance'].values[0]
                val_neg = row_neg['Absorbance'].values[0]
                
                st.line_chart(df.set_index('Wavelength')['Absorbance'])
                
                c1, c2, c3 = st.columns(3)
                c1.metric(f"Abs @{lambda_pos:.0f}nm", f"{val_pos:.3f}")
                c2.metric(f"Abs @{lambda_neg:.0f}nm", f"{val_neg:.3f}")
                
                ratio = val_pos / val_neg if val_neg != 0 else 0
                c3.metric("Ratio", f"{ratio:.2f}")
                
                st.divider()
                if ratio > threshold:
                    st.success(f"### ✅ ผล: POSITIVE (Blue Signal)")
                    st.caption(f"Peak สูงที่ช่วงสีแดง ({lambda_pos}nm)")
                else:
                    st.error(f"### ⛔ ผล: NEGATIVE (Violet Signal)")
                    st.caption(f"Peak สูงที่ช่วงสีเขียว ({lambda_neg}nm)")
                    
            except IndexError:
                st.warning("ไม่พบช่วงความยาวคลื่นที่ต้องการในไฟล์นี้")

# --- Tab 2: Image Analysis (New Feature!) ---
with tab2:
    st.subheader("วิเคราะห์สีจากภาพถ่าย")
    
    # ตัวเลือก Input: จะถ่ายสด หรือ เลือกรูปเก่า
    input_method = st.radio("เลือกวิธีการนำรูปเข้า:", ["📸 เปิดกล้องถ่าย (Camera)", "🖼️ อัปโหลดรูปจากเครื่อง (Upload)"])
    
    img_file = None
    if input_method == "📸 เปิดกล้องถ่าย (Camera)":
        img_file = st.camera_input("กดปุ่มเพื่อถ่ายภาพ")
    else:
        img_file = st.file_uploader("เลือกรูปภาพ (.jpg, .png)", type=['jpg', 'jpeg', 'png'])

    # เริ่มประมวลผลเมื่อมีรูปเข้ามา
    if img_file:
        image = Image.open(img_file)
        
        # หมุนภาพให้อัตโนมัติ (แก้ปัญหาภาพตะแคงในบางรุ่น)
        try:
            from PIL import ImageOps
            image = ImageOps.exif_transpose(image)
        except:
            pass
            
        hue, rgb, crop = analyze_image_color(image)
        
        st.write("---")
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(crop, caption="พื้นที่วิเคราะห์ (กลางภาพ)")
            st.color_picker("สีที่อ่านได้", f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}", disabled=True)
        with c2:
            st.metric("Hue Value (เฉดสี)", f"{hue:.1f}°")
            
            # Progress bar เพื่อให้เห็นภาพว่าอยู่โซนไหน
            st.progress(min(hue/360, 1.0))
            st.caption("0°=Red, 120°=Green, 240°=Blue")
            
            if hue < hue_cutoff:
                st.success("### ✅ POSITIVE (Blue)")
                st.markdown("โทนสีฟ้า (Blue Sky)")
            else:
                st.error("### ⛔ NEGATIVE (Violet)")
                st.markdown("โทนสีม่วง (Violet)")

# --- Tab 3: Manual Input ---
with tab3:
    st.write("โหมดเครื่องคิดเลข (Manual)")
    m_pos = st.number_input("Abs Positive", 0.0)
    m_neg = st.number_input("Abs Negative", 0.0)
    if st.button("Calculate Ratio"):
        if m_neg > 0:
            r = m_pos/m_neg
            st.info(f"Ratio = {r:.2f}")
            if r > threshold: st.success("Positive") 
            else: st.error("Negative")