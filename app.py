import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="LM Colorimetric Smart Rapid Analyzer", layout="centered")

st.title("LM Colorimetric Smart Rapid Analyzer")
st.markdown(" Artificial Intelligence for Listeria monocytogenes Detection")

# --- ส่วนตั้งค่า (Sidebar) ---
st.sidebar.header("Settings")
lambda_pos = st.sidebar.number_input("Wavelength Positive (nm)", value=650)
lambda_neg = st.sidebar.number_input("Wavelength Negative (nm)", value=565)
threshold = st.sidebar.number_input("Threshold Ratio (A_pos/A_neg)", value=1.0)

# --- ฟังก์ชันสำหรับโหลดและคลีนไฟล์ ---
def load_and_clean_data(file):
    # ลองอ่านแบบ UTF-8 ก่อน ถ้าไม่ได้ให้ลอง ISO-8859-1 (สำหรับเครื่องรุ่นเก่า/Windows)
    try:
        df = pd.read_csv(file, skiprows=2, encoding='utf-8')
    except UnicodeDecodeError:
        file.seek(0)
        df = pd.read_csv(file, skiprows=2, encoding='ISO-8859-1')
    except Exception as e:
        st.error(f"Error reading file format: {e}")
        return None

    # ตั้งชื่อคอลัมน์ใหม่ให้เป็นมาตรฐาน
    if len(df.columns) >= 2:
        # สมมติว่าคอลัมน์ 1=Wave, 2=Abs เสมอ
        clean_cols = ['Wavelength', 'Absorbance'] + list(df.columns[2:])
        df.columns = clean_cols
    else:
        st.error("รูปแบบไฟล์ไม่ถูกต้อง: ไม่พบคอลัมน์ Wavelength/Absorbance")
        return None

    # กรองข้อมูล: แปลงเป็น String ก่อนเพื่อเช็คว่าบรรทัดไหนขึ้นต้นด้วย // แล้วลบทิ้ง
    df = df[~df['Wavelength'].astype(str).str.startswith('//')]
    
    # แปลงข้อมูลเป็นตัวเลข (อะไรที่ไม่ใช่ตัวเลขจะกลายเป็น NaN แล้วถูกลบ)
    df['Wavelength'] = pd.to_numeric(df['Wavelength'], errors='coerce')
    df['Absorbance'] = pd.to_numeric(df['Absorbance'], errors='coerce')
    
    # ลบแถวว่าง
    df = df.dropna(subset=['Wavelength', 'Absorbance'])
    
    return df

# --- ส่วนแสดงผลหลัก ---
tab1, tab2 = st.tabs(["📝 Value (Manual)", "📂 อัปโหลดไฟล์ (File Upload)"])

# Mode 1: Manual
with tab1:
    st.subheader("Measurement")
    col1, col2 = st.columns(2)
    with col1:
        abs_pos = st.number_input(f"Absorbance @ {lambda_pos} nm", min_value=0.0, format="%.3f")
    with col2:
        abs_neg = st.number_input(f"Absorbance @ {lambda_neg} nm", min_value=0.0, format="%.3f")

    if st.button("Analysis")
        if abs_neg > 0:
            ratio = abs_pos / abs_neg
            st.metric("Ratio", f"{ratio:.2f}")
            if ratio > threshold:
                st.success(f"✅ Result: POSITIVE (Blue Color)")
            else:
                st.error(f"⛔ Result: NEGATIVE (Violet Color)")

# Mode 2: File Upload
with tab2:
    st.subheader("วิเคราะห์จากไฟล์ CSV")
    uploaded_file = st.file_uploader("เลือกไฟล์ CSV ที่ได้จากเครื่อง", type=['csv', 'xlsx'])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = load_and_clean_data(uploaded_file)
            else:
                # กรณีเป็น Excel
                df = pd.read_excel(uploaded_file)
                df.columns = ['Wavelength', 'Absorbance'] + list(df.columns[2:])
            
            if df is not None and not df.empty:
                # หาค่าที่ใกล้เคียง Wavelength ที่ต้องการที่สุด
                row_pos = df.iloc[(df['Wavelength'] - lambda_pos).abs().argsort()[:1]]
                row_neg = df.iloc[(df['Wavelength'] - lambda_neg).abs().argsort()[:1]]
                
                if not row_pos.empty and not row_neg.empty:
                    val_pos = row_pos['Absorbance'].values[0]
                    val_neg = row_neg['Absorbance'].values[0]
                    ratio_file = val_pos / val_neg if val_neg != 0 else 0
                    
                    # Plot Graph
                    st.line_chart(df.set_index('Wavelength')['Absorbance'])
                    
                    # Show Metrics
                    c1, c2, c3 = st.columns(3)
                    c1.metric(f"Abs @{lambda_pos}", f"{val_pos:.3f}")
                    c2.metric(f"Abs @{lambda_neg}", f"{val_neg:.3f}")
                    c3.metric("Calculated Ratio", f"{ratio_file:.2f}")
                    
                    st.divider()
                    if ratio_file > threshold:
                        st.success(f"### ✅ ผลการวิเคราะห์: POSITIVE")
                        st.markdown(f"ค่าดูดกลืนแสงที่ **{lambda_pos} nm** สูงเด่นชัด (สารละลายสีฟ้า)")
                    else:
                        st.error(f"### ⛔ ผลการวิเคราะห์: NEGATIVE")
                        st.markdown(f"ค่าดูดกลืนแสงที่ **{lambda_neg} nm** สูงกว่า (สารละลายสีม่วง)")
                else:
                    st.warning("ไม่พบช่วงความยาวคลื่นที่ระบุในไฟล์")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")