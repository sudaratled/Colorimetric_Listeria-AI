import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image, ImageOps
import colorsys
import numpy as np
import time

# --- 1. ตั้งค่าหน้าเว็บ (ต้องอยู่บรรทัดแรกสุด) ---
st.set_page_config(page_title="Listeria monocytogenes (LM) Colorimetric Smart Rapid Analyzer v5", layout="centered")

# --- 2. กำหนด Username และ Password ที่ต้องการ ---
# ⚠️ ข้อควรระวัง: การใส่รหัสใน Code โดยตรงไม่ปลอดภัย 100% ถ้าใช้จริงจังควรใช้ Streamlit Secrets
AUTHORIZED_USER = "admin"
AUTHORIZED_PASS = "sudarat"

# --- 3. ระบบตรวจสอบการ Login (Session State) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def login():
    st.title("🔒 Login Required")
    st.markdown("Please Login to Listeria monocytogenes (LM) Colorimetric Smart Rapid Analyzer")
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("เข้าสู่ระบบ (Login)"):
        if username == AUTHORIZED_USER and password == AUTHORIZED_PASS:
            st.session_state['logged_in'] = True
            st.success("Login สำเร็จ!")
            time.sleep(0.5)
            st.rerun() # รีเฟรชหน้าเพื่อเข้าสู่โปรแกรมหลัก
        else:
            st.error("Username or Password are not corrected")

def logout():
    st.session_state['logged_in'] = False
    st.rerun()

# --- 4. ฟังก์ชันหลักของโปรแกรม (เหมือนเดิม) ---
def main_app():
    # ปุ่ม Logout มุมขวาบน
    with st.sidebar:
        st.write(f"ผู้ใช้งาน: **{AUTHORIZED_USER}**")
        if st.button("ออกจากระบบ (Logout)"):
            logout()
        st.divider()

    st.title("🧬 Listeria monocytogenes (LM) Colorimetric Smart Rapid Analyzer")
    st.markdown("Analysis CSV or Photo (Upload file)")

    # --- Settings ---
    st.sidebar.header("⚙️ Settings (UV-Vis)")
    lambda_pos = st.sidebar.number_input("Wavelength Positive (nm)", value=644, help="แนะนำ 644 nm") 
    lambda_neg = st.sidebar.number_input("Wavelength Negative (nm)", value=536, help="แนะนำ 536 nm") 
    threshold = st.sidebar.number_input("Threshold Ratio", value=1.0)

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Settings (Image)")
    hue_cutoff = st.sidebar.slider("Blue/Violet Cutoff (Hue)", 0, 360, 245)

    # --- Helper Functions ---
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

    # --- Display Tabs ---
    tab1, tab2, tab3 = st.tabs(["📂 File (UV-Vis)", "📷 Photo/Picture Analyzer", "📝 Customized"])

    # Tab 1: CSV
    with tab1:
        st.subheader("File Analysis (CSV or xlsx)")
        uploaded_file = st.file_uploader("Upload CSV", type=['csv', 'xlsx'])
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
                        st.success(f"### ✅ Result: POSITIVE (Blue Signal)")
                    else:
                        st.error(f"### ⛔ Result: NEGATIVE (Violet Signal)")
                except IndexError:
                    st.warning("No signal")

    # Tab 2: Image
    with tab2:
        st.subheader("วิเคราะห์สีจากภาพถ่าย")
        input_method = st.radio("เลือกวิธีการนำรูปเข้า:", ["📸 เปิดกล้องถ่าย (Camera)", "🖼️ อัปโหลดรูปจากเครื่อง (Upload)"])
        
        img_file = None
        if input_method == "📸 เปิดกล้องถ่าย (Camera)":
            img_file = st.camera_input("กดปุ่มเพื่อถ่ายภาพ")
        else:
            img_file = st.file_uploader("เลือกรูปภาพ (.jpg, .png)", type=['jpg', 'jpeg', 'png'])

        if img_file:
            image = Image.open(img_file)
            try:
                image = ImageOps.exif_transpose(image) # Fix rotation
            except:
                pass
            hue, rgb, crop = analyze_image_color(image)
            
            st.write("---")
            c1, c2 = st.columns([1, 2])
            with c1:
                st.image(crop, caption="จุดที่วิเคราะห์")
                st.color_picker("สีที่อ่านได้", f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}", disabled=True)
            with c2:
                st.metric("Hue Value", f"{hue:.1f}°")
                st.progress(min(hue/360, 1.0))
                if hue < hue_cutoff:
                    st.success("### ✅ POSITIVE (Blue)")
                else:
                    st.error("### ⛔ NEGATIVE (Violet)")

    # Tab 3: Manual
    with tab3:
        st.write("โหมดเครื่องคิดเลข")
        m_pos = st.number_input("Abs Positive", 0.0)
        m_neg = st.number_input("Abs Negative", 0.0)
        if st.button("Calculate Ratio"):
            if m_neg > 0:
                r = m_pos/m_neg
                st.info(f"Ratio = {r:.2f}")
                if r > threshold: st.success("Positive") 
                else: st.error("Negative")

# --- 5. Main Logic Controller ---
if st.session_state['logged_in']:
    main_app()
else:

    login()


