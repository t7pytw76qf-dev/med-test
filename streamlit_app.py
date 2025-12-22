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

# --- 1. עיצוב RTL, כפתורים כחולים וגדולים ---
st.set_page_config(page_title="מערכת HEXACO", layout="centered")

st.markdown("""
    <style>
        .main .block-container { direction: rtl !important; text-align: right !important; }
        
        /* עיצוב כפתורי הדירוג 1-5 */
        div.stButton > button[key^="q_btn_"] {
            width: 100% !important;
            height: 4.5em !important;
            font-size: 22px !important;
            font-weight: bold !important;
            border-radius: 12px !important;
            border: 2px solid #4A90E2 !important;
            background-color: white !important;
            color: #4A90E2 !important;
            transition: all 0.2s ease !important;
        }

        /* צביעת הכפתור בכחול בעת לחיצה */
        div.stButton > button[key^="q_btn_"]:active, 
        div.stButton > button[key^="q_btn_"]:focus {
            background-color: #4A90E2 !important;
            color: white !important;
            border: 2px solid #225796 !important;
        }

        /* עיצוב כפתורי תפריט */
        .stButton > button { border-radius: 10px !important; font-weight: bold !important; }
        
        .custom-footer { 
            position: fixed; left: 0; bottom: 0; width: 100%; 
            background-color: white; text-align: center; padding: 10px; 
            font-weight: bold; border-top: 1px solid #eaeaea; z-index: 999; 
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציית PDF מתוקנת ---
def create_pdf(text, user_name):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"HEXACO Analysis Report - {user_name}", ln=True, align='C')
        pdf.ln(10)
        # ניקוי תווים למניעת קריסה
        clean_text = text.encode('ascii', 'ignore').decode('ascii')
        pdf.multi_cell(0, 10, txt=clean_text)
        return pdf.output(dest='S').encode('latin-1')
    except:
        return b""

# --- 3. אתחול Firebase ---
if "firebase" in st.secrets and not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        fb_dict["private_key"] = fb_dict["private_key"].replace('\\n', '\n')
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client() if firebase_admin._apps else None

# --- 4. מנגנון AI משולב (סבב מפתחות + מודלים) ---
def generate_analysis(answers):
    # שימוש בשני מפתחות API לגיבוי
    keys = [st.secrets.get("GEMINI_API_KEY"), st.secrets.get("GEMINI_API_KEY_2")]
    keys = [k for k in keys if k]
    models = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-8b", "models/gemini-1.5-pro"]
    
    # מידע מקופל לחיסכון במכסה
    data_summary = [{"t": a['trait'], "s": a['score'], "d": a['time']} for a in answers]
    
    prompt = f"""
    Analyze the medical candidate {st.session_state.user_name}.
    Data: {data_summary}.
    Include knowledge of words: gnarled, emits, clenched if relevant.
    Analyze in Hebrew: Reliability (based on speed/consistency), HEXACO traits, and medical suitablity.
    """

    for k in keys:
        genai.configure(api_key=k)
        for m in models:
            try:
                model = genai.GenerativeModel(m)
                response = model.generate_content(prompt)
                return response.text, m
            except: continue
    return "כל המכסות הסתיימו. נסה שוב בעוד דקה.", None

# --- 5. ניהול דפים ---
if 'page' not in st.session_state: st.session_state.page = "home"
if 'user_name' not in st.session_state: st.session_state.user_name = ""

# דף הבית
if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    st.session_state.user_name = st.text_input("הזן שם משתמש:", value=st.session_state.user_name)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 שאלון מלא (200)"):
            if st.session_state.user_name:
                st.session_state.questions = pd.read_csv("questions.csv").to_dict('records')
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
            else: st.error("⚠️ נא להזין שם משתמש!")
    
    with col2:
        if st.button("⏱️ מקבץ מהיר (36)"):
            if st.session_state.user_name:
                df = pd.read_csv("questions.csv")
                st.session_state.questions = df.sample(n=min(36, len(df))).to_dict('records')
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
            else: st.error("⚠️ נא להזין שם משתמש!")

    st.write("---")
    if st.button("📂 ארכיון תוצאות"):
        if st.session_state.user_name: st.session_state.page = "archive"; st.rerun()
        else: st.warning("הזן שם כדי לצפות בארכיון")

# דף השאלון
elif st.session_state.page == "quiz":
    q = st.session_state.questions
    idx = st.session_state.current_step
    
    if idx < len(q):
        st.write(f"שאלה {idx + 1} מתוך {len(q)}")
        st.progress((idx + 1) / len(q))
        st.markdown(f"### {q[idx]['q']}")
        
        cols = st.columns(5)
        for val, col in enumerate(cols, 1):
            if col.button(str(val), key=f"q_btn_{idx}_{val}"):
                duration = round(time.time() - st.session_state.start_time, 2)
                st.session_state.answers.append({"trait": q[idx]['trait'], "score": val, "time": duration})
                st.session_state.current_step += 1; st.session_state.start_time = time.time(); st.rerun()
    else:
        st.balloons()
        st.success("✅ השאלון הושלם בהצלחה!")
        if st.button("🚀 הפק ניתוח AI"): st.session_state.page = "analysis"; st.rerun()

# דף ניתוח
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח AI")
    if 'final_analysis' not in st.session_state:
        with st.spinner("מנתח..."):
            text, model = generate_analysis(st.session_state.answers)
            st.session_state.final_analysis = text
            if db and model:
                db.collection('results').add({
                    'user': st.session_state.user_name, 'date': datetime.now().strftime("%d/%m/%Y %H:%M"), 'analysis': text
                })
    
    st.markdown(st.session_state.final_analysis)
    pdf_b = create_pdf(st.session_state.final_analysis, st.session_state.user_name)
    if pdf_b: st.download_button("📥 הורד PDF", data=pdf_b, file_name="analysis.pdf")
    if st.button("חזרה"): 
        if 'final_analysis' in st.session_state: del st.session_state.final_analysis
        st.session_state.page = "home"; st.rerun()

# דף ארכיון
elif st.session_state.page == "archive":
    st.title(f"📂 ארכיון: {st.session_state.user_name}")
    if db:
        docs = db.collection('results').where('user', '==', st.session_state.user_name).stream()
        for doc in docs:
            d = doc.to_dict()
            with st.expander(f"מבחן מ-{d['date']}"): st.write(d['analysis'])
    if st.button("חזרה"): st.session_state.page = "home"; st.rerun()

st.markdown('<div class="custom-footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
