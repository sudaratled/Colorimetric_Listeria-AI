import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import colorsys
import numpy as np

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="HNB LAMP Analyzer v3", layout="centered")

st.title("🧬 HNB LAMP Assay Analyzer (v3)")
st.markdown("เครื่องมือวิเคราะห์ผล Positive/Negative จากค่าดูดกลืนแสง และ สีของภาพ")

# --- ส่วนตั้งค่า (Sidebar) ---
st.sidebar.header("⚙️ Settings (UV-Vis)")
lambda_pos = st.sidebar.number_input("Wavelength Positive (nm)", value=650)
lambda_neg = st.sidebar.number_input("Wavelength Negative (nm)", value=565)
threshold = st.sidebar.number_input("Threshold Ratio (A_pos/A_neg)", value=1.0)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Settings (Image)")
# ค่า Hue (0-360): สีฟ้า ~200-230, สีม่วง ~260-290
hue_cutoff = st.sidebar.slider("Blue/Violet Cutoff (Hue Degree)", 0, 360, 245, help="ค่าจุดตัดระหว่างสีฟ้ากับสีม่วง")

# --- ฟังก์ชันสำหรับโหลดและคลีนไฟล์ CSV ---
def load_and_clean_data(file):
    try:
        df = pd.read_csv(file, skiprows=2, encoding='utf-8')
    except UnicodeDecodeError:
        file.seek(0)
        df = pd.read_csv(file, skiprows=2, encoding='ISO-8859-1')
    except Exception as e:
        st.error(f"Error reading file format: {e}")
        return None

    if len(df.columns) >= 2:
        clean_cols = ['Wavelength', 'Absorbance'] + list(df.columns[2:])
        df.columns = clean_cols
    else:
        st.error("รูปแบบไฟล์ไม่ถูกต้อง: ไม่พบคอลัมน์ Wavelength/Absorbance")
        return None

    df = df[~df['Wavelength'].astype(str).str.startswith('//')]
    df['Wavelength'] = pd.to_numeric(df['Wavelength'], errors='coerce')
    df['Absorbance'] = pd.to_numeric(df['Absorbance'], errors='coerce')
    df = df.dropna(subset=['Wavelength', 'Absorbance'])
    
    return df

# --- ฟังก์ชันวิเคราะห์สีจากภาพ ---
def analyze_image_color(image):
    # แปลงเป็น numpy array
    img_array = np.array(image)
    
    # ตัดขอบภาพออกเอาแค่ตรงกลาง (Center Crop 50%) เพื่อหลีกเลี่ยงพื้นหลัง
    h, w, _ = img_array.shape
    center_h, center_w = h // 2, w // 2
    crop_h, crop_w = h // 4, w // 4
    center_img = img_array[center_h - crop_h : center_h + crop_h, center_w - crop_w : center_w + crop_w]
    
    # หาค่าเฉลี่ย RGB
    avg_color_per_row = np.average(center_img, axis=0)
    avg_rgb = np.average(avg_color_per_row, axis=0)
    r, g, b = avg_rgb
    
    # แปลง RGB (0-255) เป็น HSV (0-1) แล้วคูณ 360 เพื่อเป็นองศา
    h_hsv, s_hsv, v_hsv = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    hue_degree = h_hsv * 360
    
    return hue_degree, (r, g, b), center_img

# --- ส่วนแสดงผลหลัก ---
tab1, tab2, tab3 = st.tabs(["📝 กรอกค่า (Manual)", "📂 ไฟล์กราฟ (UV-Vis)", "📷 วิเคราะห์ภาพ (Photo)"])

# Mode 1: Manual
with tab1:
    st.subheader("คำนวณแบบป้อนค่า Absorbance")
    col1, col2 = st.columns(2)
    with col1:
        abs_pos = st.number_input(f"Absorbance @ {lambda_pos} nm", min_value=0.0, format="%.3f")
    with col2:
        abs_neg = st.number_input(f"Absorbance @ {lambda_neg} nm", min_value=0.0, format="%.3f")

    if st.button("วิเคราะห์ผล (Calculate)", key="btn_manual"):
        if abs_neg > 0:
            ratio = abs_pos / abs_neg
            st.metric("Ratio", f"{ratio:.2f}")
            if ratio > threshold:
                st.success(f"✅ Result: POSITIVE (Blue Color)")
            else:
                st.error(f"⛔ Result: NEGATIVE (Violet Color)")

# Mode 2: File Upload
with tab2:
    st.subheader("วิเคราะห์จากไฟล์ CSV (UV-Vis)")
    uploaded_file = st.file_uploader("เลือกไฟล์ CSV ที่ได้จากเครื่อง", type=['csv', 'xlsx'])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = load_and_clean_data(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
                df.columns = ['Wavelength', 'Absorbance'] + list(df.columns[2:])
            
            if df is not None and not df.empty:
                row_pos = df.iloc[(df['Wavelength'] - lambda_pos).abs().argsort()[:1]]
                row_neg = df.iloc[(df['Wavelength'] - lambda_neg).abs().argsort()[:1]]
                
                if not row_pos.empty and not row_neg.empty:
                    val_pos = row_pos['Absorbance'].values[0]
                    val_neg = row_neg['Absorbance'].values[0]
                    ratio_file = val_pos / val_neg if val_neg != 0 else 0
                    
                    st.line_chart(df.set_index('Wavelength')['Absorbance'])
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric(f"Abs @{lambda_pos}", f"{val_pos:.3f}")
                    c2.metric(f"Abs @{lambda_neg}", f"{val_neg:.3f}")
                    c3.metric("Ratio", f"{ratio_file:.2f}")
                    
                    st.divider()
                    if ratio_file > threshold:
                        st.success(f"### ✅ UV-Vis Result: POSITIVE")
                    else:
                        st.error(f"### ⛔ UV-Vis Result: NEGATIVE")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

# Mode 3: Image Analysis (New!)
with tab3:
    st.subheader("วิเคราะห์จากภาพถ่ายหลอดทดลอง")
    st.info("💡 คำแนะนำ: ควรถ่ายภาพในที่สว่างพื้นหลังขาว และให้หลอดทดลองอยู่ตรงกลางภาพ")
    
    img_file = st.file_uploader("อัปโหลดรูปภาพ (jpg, png)", type=['jpg', 'jpeg', 'png'])
    
    if img_file is not None:
        image = Image.open(img_file)
        
        # แสดงรูปต้นฉบับ
        st.image(image, caption="รูปภาพต้นฉบับ", use_container_width=True)
        
        if st.button("วิเคราะห์สี (Analyze Color)"):
            hue, rgb, crop_img = analyze_image_color(image)
            
            st.write("---")
            col_img1, col_img2 = st.columns([1, 2])
            
            with col_img1:
                st.image(crop_img, caption="พื้นที่วิเคราะห์ (กลางภาพ)")
                # แสดงกล่องสีที่ตรวจจับได้
                st.color_picker("สีเฉลี่ยที่ตรวจจับได้", f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}", disabled=True)
            
            with col_img2:
                st.metric("Detected Hue (เฉดสี)", f"{hue:.1f}°")
                
                # Logic การตัดสินผลจาก Hue
                # Sky Blue (Pos) มักจะอยู่ที่ Hue < 245
                # Violet (Neg) มักจะอยู่ที่ Hue > 245
                
                if hue < hue_cutoff:
                    st.success("### ✅ Photo Result: POSITIVE")
                    st.markdown(f"ตรวจพบโทน **สีฟ้า (Blue)** (Hue < {hue_cutoff})")
                else:
                    st.error("### ⛔ Photo Result: NEGATIVE")
                    st.markdown(f"ตรวจพบโทน **สีม่วง (Violet)** (Hue > {hue_cutoff})")