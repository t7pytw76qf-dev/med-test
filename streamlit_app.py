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

# --- 1. הגדרות דף ועיצוב CSS מתקדם (כולל Hover ו-Focus) ---
st.set_page_config(page_title="מערכת HEXACO - ניתוח AI", layout="centered")

st.markdown("""
    <style>
        /* יישור RTL */
        .main .block-container { direction: rtl !important; text-align: right !important; }
        
        /* עיצוב כפתורי הדירוג */
        div.stButton > button {
            width: 100% !important;
            height: 4.5em !important;
            font-size: 22px !important;
            font-weight: bold !important;
            border-radius: 12px !important;
            border: 2px solid #4A90E2 !important;
            background-color: white !important;
            color: #4A90E2 !important;
            /* אנימציה חלקה למעבר עכבר ולחיצה */
            transition: background-color 0.3s ease, color 0.3s ease, transform 0.1s !important;
            margin-bottom: 10px !important;
        }

        /* מצב מעבר עכבר (Hover) */
        div.stButton > button:hover {
            background-color: #4A90E2 !important;
            color: white !important;
            border-color: #225796 !important;
        }

        /* מצב לחיצה ופוקוס (נשאר כחול) */
        div.stButton > button:active, div.stButton > button:focus {
            background-color: #225796 !important;
            color: white !important;
            border: 2px solid #1a4373 !important;
            transform: scale(0.98) !important;
        }

        /* פוטר קבוע */
        .custom-footer { 
            position: fixed; left: 0; bottom: 0; width: 100%; 
            background-color: white; text-align: center; padding: 10px; 
            font-weight: bold; border-top: 1px solid #eaeaea; z-index: 999; 
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציית יצירת PDF ---
def create_pdf(text, user_name):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"HEXACO AI Analysis - {user_name}", ln=True, align='C')
        pdf.ln(10)
        clean_text = text.encode('ascii', 'ignore').decode('ascii')
        pdf.multi_cell(0, 10, txt=clean_text)
        return pdf.output(dest='S').encode('latin-1')
    except: return b""

# --- 3. אתחול Firebase ---
if "firebase" in st.secrets and not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        fb_dict["private_key"] = fb_dict["private_key"].replace('\\n', '\n')
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
    except: pass
db = firestore.client() if firebase_admin._apps else None

# --- 4. מנגנון AI חסין עומסים ---
def generate_analysis(answers):
    # סבב מפתחות API (מומלץ להוסיף GEMINI_API_KEY_2 ב-Secrets)
    api_keys = [st.secrets.get("GEMINI_API_KEY"), st.secrets.get("GEMINI_API_KEY_2")]
    api_keys = [k for k in api_keys if k]
    
    # ניסיון מודלים שונים כדי לעקוף מכסות
    models_to_try = ["gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.5-pro"]
    
    prompt = f"Analyze the HEXACO test for {st.session_state.user_name}. Results: {str(answers)[:2000]}. Provide a professional Hebrew report."

    for key in api_keys:
        genai.configure(api_key=key)
        for m_name in models_to_try:
            try:
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(prompt)
                if response.text: return response.text
            except: continue
    return "שגיאה: מכסת ה-AI נוצלה. אנא המתן דקה ונסה שוב."

# --- 5. פונקציית טעינת קובץ שאלות ---
def load_questions():
    paths = ["questions.csv", "/mount/src/med-test/questions.csv", "./questions.csv"]
    for p in paths:
        if os.path.exists(p):
            try: return pd.read_csv(p)
            except: continue
    return None

# --- 6. ניהול דפים ---
if 'page' not in st.session_state: st.session_state.page = "home"
if 'user_name' not in st.session_state: st.session_state.user_name = ""

# דף הבית
if st.session_state.page == "home":
    st.title("🏥 מערכת HEXACO - ניתוח AI")
    st.session_state.user_name = st.text_input("שם מועמד:", value=st.session_state.user_name)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 שאלון מלא"):
            df = load_questions()
            if df is not None and st.session_state.user_name:
                st.session_state.questions = df.to_dict('records')
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
            else: st.error("הזן שם או וודא שקובץ questions.csv קיים.")
    
    with col2:
        if st.button("⏱️ מקבץ מהיר (36)"):
            df = load_questions()
            if df is not None and st.session_state.user_name:
                st.session_state.questions = df.sample(n=min(36, len(df))).to_dict('records')
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
            else: st.error("הזן שם או וודא שקובץ questions.csv קיים.")

    if st.button("📂 ארכיון תוצאות"):
        if st.session_state.user_name: st.session_state.page = "archive"; st.rerun()

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
            if col.button(str(val), key=f"btn_{idx}_{val}"):
                st.session_state.answers.append({
                    "trait": q[idx]['trait'], 
                    "score": val, 
                    "time": round(time.time() - st.session_state.start_time, 2)
                })
                st.session_state.current_step += 1
                st.session_state.start_time = time.time()
                st.rerun()
    else:
        st.success("השאלון הושלם!")
        if st.button("🚀 הפק ניתוח AI"):
            st.session_state.page = "analysis"; st.rerun()

# דף ניתוח
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח AI סופי")
    if 'final_analysis' not in st.session_state:
        with st.spinner("מנתח נתונים..."):
            res = generate_analysis(st.session_state.answers)
            st.session_state.final_analysis = res
            if db and "שגיאה" not in res:
                try:
                    db.collection('results').add({
                        'user': st.session_state.user_name,
                        'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                        'analysis': res
                    })
                except: pass
    
    st.markdown(st.session_state.final_analysis)
    
    col_a, col_b = st.columns(2)
    with col_a:
        pdf_bytes = create_pdf(st.session_state.final_analysis, st.session_state.user_name)
        if pdf_bytes: st.download_button("📥 הורד PDF", data=pdf_bytes, file_name="analysis.pdf")
    with col_b:
        if st.button("חזרה לתפריט"):
            if 'final_analysis' in st.session_state: del st.session_state.final_analysis
            st.session_state.page = "home"; st.rerun()

# דף ארכיון
elif st.session_state.page == "archive":
    st.title(f"📂 ארכיון: {st.session_state.user_name}")
    if db:
        try:
            docs = db.collection('results').where('user', '==', st.session_state.user_name).stream()
            for doc in docs:
                d = doc.to_dict()
                with st.expander(f"מבחן מ-{d['date']}"): st.write(d['analysis'])
        except: st.error("שגיאת גישה לארכיון.")
    
    if st.button("חזרה"): st.session_state.page = "home"; st.rerun()

st.markdown('<div class="custom-footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
