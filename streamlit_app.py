import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os
from fpdf import FPDF # ספרייה ליצירת PDF

# --- 1. הגדרות דף ועיצוב מוטמע ---
st.set_page_config(page_title="מערכת HEXACO", layout="centered")

st.markdown("""
    <style>
        .main .block-container { direction: rtl !important; text-align: right !important; }
        div.stButton > button[key^="q_"] {
            width: 100% !important; height: 4.5em !important;
            font-size: 20px !important; font-weight: bold !important;
            border-radius: 12px !important; border: 2px solid #4A90E2 !important;
            background-color: white !important; color: #4A90E2 !important;
            transition: all 0.2s ease-in-out !important;
        }
        div.stButton > button[key^="q_"]:active, div.stButton > button[key^="q_"]:focus {
            background-color: #4A90E2 !important; color: white !important;
        }
        .stButton > button { width: 100% !important; border-radius: 10px !important; font-weight: bold !important; }
        .custom-footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: white; 
                        text-align: center; padding: 10px; font-weight: bold; border-top: 1px solid #eaeaea; z-index: 999; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציה ליצירת PDF (תומכת עברית בסיסית) ---
def create_pdf(text, user_name):
    pdf = FPDF()
    pdf.add_page()
    # הערה: FPDF זקוקה לגופן שתומך בעברית כדי להציג טקסט תקין. 
    # כברירת מחדל בענן ללא העלאת גופן, נשתמש בטקסט אנגלי ככותרת ודיווח.
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"HEXACO Personality Analysis - {user_name}", ln=True, align='C')
    pdf.ln(10)
    # ניקוי תווים מיוחדים שעלולים לשבור את ה-PDF
    clean_text = text.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. אתחול מפתחות (Secrets) ---
fb_status = False
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

if "firebase" in st.secrets:
    try:
        if not firebase_admin._apps:
            fb_dict = dict(st.secrets["firebase"])
            fb_dict["private_key"] = fb_dict["private_key"].replace('\\n', '\n')
            cred = credentials.Certificate(fb_dict)
            firebase_admin.initialize_app(cred)
        st.session_state.db = firestore.client()
        fb_status = True
    except: pass

# --- 4. מנגנון ניתוח AI משולש ---
def generate_analysis(answers):
    models = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-8b", "models/gemini-1.5-pro"]
    simplified_data = [{"trait": a['trait'], "score": a['score'], "time": a['time']} for a in answers]
    prompt = f"Analyze candidate {st.session_state.user_name} for medical school. Data: {simplified_data}. Answer in Hebrew."
    
    for model_name in models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text, model_name
        except: continue
    return "שגיאת מכסה. נסה שוב בעוד דקה.", None

# --- 5. לוגיקת דפים ---
if 'page' not in st.session_state: st.session_state.page = "home"

if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    user_name = st.text_input("שם משתמש:", key="user_input")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 שאלון מלא (200)"):
            if user_name:
                st.session_state.user_name = user_name
                st.session_state.questions = pd.read_csv("questions.csv").to_dict('records') # טעינה פשוטה לטסט
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
    with col2:
        if st.button("⏱️ מקבץ מהיר (36)"):
            if user_name:
                st.session_state.user_name = user_name
                st.session_state.questions = pd.read_csv("questions.csv").sample(36).to_dict('records')
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
    if st.button("📂 ארכיון"):
        if user_name: st.session_state.user_name = user_name; st.session_state.page = "archive"; st.rerun()

elif st.session_state.page == "quiz":
    q = st.session_state.questions
    idx = st.session_state.current_step
    if idx < len(q):
        st.write(f"שאלה {idx + 1} מתוך {len(q)}")
        st.markdown(f"## {q[idx]['q']}")
        cols = st.columns(5)
        for val, col in enumerate(cols, 1):
            if col.button(str(val), key=f"q_{idx}_{val}"):
                duration = round(time.time() - st.session_state.start_time, 2)
                st.session_state.answers.append({"trait": q[idx]['trait'], "score": val, "time": duration})
                st.session_state.current_step += 1; st.session_state.start_time = time.time(); st.rerun()
    else:
        if st.button("עבור לניתוח AI"): st.session_state.page = "analysis"; st.rerun()

elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח AI")
    if 'final_analysis' not in st.session_state:
        with st.spinner("מנתח..."):
            text, model = generate_analysis(st.session_state.answers)
            st.session_state.final_analysis = text
            st.session_state.used_model = model
    
    st.write(st.session_state.final_analysis)
    
    # כפתור הורדת PDF
    pdf_data = create_pdf(st.session_state.final_analysis, st.session_state.user_name)
    st.download_button(label="📥 הורד ניתוח כ-PDF", data=pdf_data, 
                       file_name=f"analysis_{st.session_state.user_name}.pdf", mime="application/pdf")
    
    if st.button("חזרה לתפריט"): 
        del st.session_state.final_analysis
        st.session_state.page = "home"; st.rerun()

st.markdown('<div class="custom-footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
