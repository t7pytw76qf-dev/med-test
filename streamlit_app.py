import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os
from fpdf import FPDF

# --- 1. הגדרות דף ועיצוב מוטמע (תיקון כפתורים וצבעים) ---
st.set_page_config(page_title="מערכת HEXACO", layout="centered")

st.markdown("""
    <style>
        /* הגדרת כיווניות לימין */
        .main .block-container { direction: rtl !important; text-align: right !important; }

        /* עיצוב כפתורי הדירוג 1-5 - תיקון גודל */
        .stButton > button {
            width: 100% !important;
            height: 4em !important;
            font-size: 22px !important;
            font-weight: bold !important;
            border-radius: 12px !important;
            border: 2px solid #4A90E2 !important;
            background-color: white !important;
            color: #4A90E2 !important;
            transition: all 0.2s ease !important;
            margin-bottom: 10px !important;
        }

        /* צביעת הכפתור בכחול בעת לחיצה (Focus/Active) */
        .stButton > button:active, 
        .stButton > button:focus,
        .stButton > button:hover {
            background-color: #4A90E2 !important;
            color: white !important;
            border: 2px solid #225796 !important;
        }

        /* פוטר קבוע */
        .custom-footer { 
            position: fixed; left: 0; bottom: 0; width: 100%; 
            background-color: white; text-align: center; padding: 10px; 
            font-weight: bold; border-top: 1px solid #eaeaea; z-index: 999; 
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציית PDF בסיסית ---
def create_pdf(text, user_name):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"HEXACO Analysis - {user_name}", ln=True, align='C')
        pdf.ln(10)
        clean_text = text.encode('ascii', 'ignore').decode('ascii')
        pdf.multi_cell(0, 10, txt=clean_text)
        return pdf.output(dest='S').encode('latin-1')
    except: return b""

# --- 3. אתחול מפתחות ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

fb_status = False
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

# --- 4. מנגנון AI משולש ---
def generate_analysis(answers):
    models = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-8b", "models/gemini-1.5-pro"]
    simplified_data = [{"trait": a['trait'], "score": a['score'], "time": a['time']} for a in answers]
    prompt = f"Analyze medical candidate {st.session_state.user_name}. Data: {simplified_data}. Answer in Hebrew about reliability, traits and suitability."
    
    for model_name in models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text, model_name
        except: continue
    return "שגיאת מכסה. נסה שוב בעוד דקה.", None

# --- 5. ניהול דפים ---
if 'page' not in st.session_state: st.session_state.page = "home"

# דף הבית
if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    user_name = st.text_input("שם משתמש:", key="main_user_input")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 שאלון מלא (200)"):
            if user_name:
                st.session_state.user_name = user_name
                st.session_state.questions = pd.read_csv("questions.csv").to_dict('records')
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
    with col2:
        if st.button("⏱️ מקבץ מהיר (36)"):
            if user_name:
                st.session_state.user_name = user_name
                df = pd.read_csv("questions.csv")
                st.session_state.questions = df.sample(n=min(36, len(df))).to_dict('records')
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
    if st.button("📂 ארכיון תוצאות"):
        if user_name: st.session_state.user_name = user_name; st.session_state.page = "archive"; st.rerun()

# דף השאלון
elif st.session_state.page == "quiz":
    q = st.session_state.questions
    idx = st.session_state.current_step
    if idx < len(q):
        st.write(f"שאלה {idx + 1} מתוך {len(q)}")
        st.progress((idx + 1) / len(q))
        st.markdown(f"### {q[idx]['q']}")
        
        # יצירת כפתורים גדולים
        cols = st.columns(5)
        for val, col in enumerate(cols, 1):
            if col.button(str(val), key=f"q_btn_{idx}_{val}"):
                duration = round(time.time() - st.session_state.start_time, 2)
                st.session_state.answers.append({"trait": q[idx]['trait'], "score": val, "time": duration})
                st.session_state.current_step += 1; st.session_state.start_time = time.time(); st.rerun()
    else:
        st.success("השאלון הושלם!")
        if st.button("לחץ לקבלת ניתוח AI"): st.session_state.page = "analysis"; st.rerun()

# דף ניתוח
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח AI")
    if 'final_analysis' not in st.session_state:
        with st.spinner("מנתח..."):
            text, model = generate_analysis(st.session_state.answers)
            st.session_state.final_analysis = text
            if fb_status and model:
                st.session_state.db.collection('results').add({
                    'user': st.session_state.user_name, 'date': datetime.now().strftime("%d/%m/%Y %H:%M"), 'analysis': text
                })
    
    st.markdown(st.session_state.final_analysis)
    pdf_bytes = create_pdf(st.session_state.final_analysis, st.session_state.user_name)
    if pdf_bytes:
        st.download_button("📥 הורד ניתוח כ-PDF (English Header)", data=pdf_bytes, file_name="analysis.pdf", mime="application/pdf")
    
    if st.button("חזרה לתפריט"):
        if 'final_analysis' in st.session_state: del st.session_state.final_analysis
        st.session_state.page = "home"; st.rerun()

# דף ארכיון
elif st.session_state.page == "archive":
    st.title(f"📂 ארכיון: {st.session_state.user_name}")
    if fb_status:
        docs = st.session_state.db.collection('results').where('user', '==', st.session_state.user_name).stream()
        for doc in docs:
            d = doc.to_dict()
            with st.expander(f"מבחן מ-{d['date']}"): st.write(d['analysis'])
    if st.button("חזרה"): st.session_state.page = "home"; st.rerun()

st.markdown('<div class="custom-footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
