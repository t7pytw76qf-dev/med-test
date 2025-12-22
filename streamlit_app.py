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

# --- 1. הגדרות דף ועיצוב מוטמע (RTL + כפתורים כחולים) ---
st.set_page_config(page_title="מערכת HEXACO", layout="centered")

st.markdown("""
    <style>
        .main .block-container { direction: rtl !important; text-align: right !important; }
        
        /* עיצוב כפתורי הדירוג 1-5 */
        div.stButton > button[key^="q_"] {
            width: 100% !important;
            height: 4.5em !important;
            font-size: 20px !important;
            font-weight: bold !important;
            border-radius: 12px !important;
            border: 2px solid #4A90E2 !important;
            background-color: white !important;
            color: #4A90E2 !important;
            transition: all 0.2s ease-in-out !important;
        }

        /* צבע כחול בעת לחיצה */
        div.stButton > button[key^="q_"]:active, 
        div.stButton > button[key^="q_"]:focus {
            background-color: #4A90E2 !important;
            color: white !important;
        }

        .stButton > button { width: 100% !important; border-radius: 10px !important; font-weight: bold !important; }
        
        .custom-footer { 
            position: fixed; left: 0; bottom: 0; width: 100%; 
            background-color: white; text-align: center; padding: 10px; 
            font-weight: bold; border-top: 1px solid #eaeaea; z-index: 999; 
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציה ליצירת PDF (תומכת בסיסית) ---
def create_pdf(text, user_name):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"HEXACO Personality Analysis - {user_name}", ln=True, align='C')
        pdf.ln(10)
        
        # ניקוי תווים שאינם נתמכים ב-Latin-1 בסיסי
        clean_text = text.encode('ascii', 'ignore').decode('ascii')
        pdf.multi_cell(0, 10, txt=clean_text)
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        return str(e).encode()

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
    except:
        pass

# --- 4. מנגנון ניתוח AI משולש (Flash, 8B, Pro) ---
def generate_analysis(answers):
    models = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-8b", "models/gemini-1.5-pro"]
    # צמצום נתונים לחיסכון במכסה
    simplified_data = [{"trait": a['trait'], "score": a['score'], "time": a['time']} for a in answers]
    
    prompt = f"""
    Analyze the following HEXACO test results for a medical school candidate named {st.session_state.user_name}.
    Data (Trait, Score 1-5, Response Time): {simplified_data}.
    Please provide a detailed analysis in Hebrew regarding:
    1. Reliability (based on consistency and response times).
    2. Key personality traits.
    3. Suitability for the medical profession.
    """
    
    for model_name in models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text, model_name
        except:
            continue
    return "שגיאת מכסה: כל המודלים עמוסים. נסה שוב בעוד דקה.", None

# --- 5. לוגיקת דפים ---
if 'page' not in st.session_state:
    st.session_state.page = "home"

# --- דף הבית ---
if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    user_name = st.text_input("שם משתמש:", key="user_input")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 שאלון מלא (200)"):
            if user_name:
                st.session_state.user_name = user_name
                st.session_state.questions = pd.read_csv("questions.csv").to_dict('records')
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
            else: st.warning("נא להזין שם")
    
    with col2:
        if st.button("⏱️ מקבץ מהיר (36)"):
            if user_name:
                st.session_state.user_name = user_name
                st.session_state.questions = pd.read_csv("questions.csv").sample(n=min(36, len(pd.read_csv("questions.csv")))).to_dict('records')
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
            else: st.warning("נא להזין שם")
    
    st.write("---")
    if st.button("📂 ארכיון תוצאות"):
        if user_name:
            st.session_state.user_name = user_name; st.session_state.page = "archive"; st.rerun()
        else: st.warning("נא להזין שם")

# --- דף השאלון ---
elif st.session_state.page == "quiz":
    q = st.session_state.questions
    idx = st.session_state.current_step
    
    if idx < len(q):
        st.write(f"שאלה {idx + 1} מתוך {len(q)}")
        st.progress((idx + 1) / len(q))
        st.markdown(f"## {q[idx]['q']}")
        
        cols = st.columns(5)
        for val, col in enumerate(cols, 1):
            if col.button(str(val), key=f"q_{idx}_{val}"):
                duration = round(time.time() - st.session_state.start_time, 2)
                st.session_state.answers.append({"trait": q[idx]['trait'], "score": val, "time": duration})
                st.session_state.current_step += 1; st.session_state.start_time = time.time(); st.rerun()
    else:
        st.success("השאלון הושלם!")
        if st.button("עבור לניתוח AI"):
            st.session_state.page = "analysis"; st.rerun()

# --- דף ניתוח AI ---
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח AI מקצועי")
    
    if 'final_analysis' not in st.session_state:
        with st.spinner("המערכת מנתחת נתונים..."):
            text, model = generate_analysis(st.session_state.answers)
            st.session_state.final_analysis = text
            st.session_state.used_model = model
            
            if fb_status and model:
                try:
                    st.session_state.db.collection('results').add({
                        'user': st.session_state.user_name,
                        'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                        'analysis': text
                    })
                except: pass

    st.info(f"מודל מבצע: {st.session_state.used_model}")
    st.markdown(st.session_state.final_analysis)
    
    # כפתור הורדת PDF
    try:
        pdf_bytes = create_pdf(st.session_state.final_analysis, st.session_state.user_name)
        st.download_button(label="📥 הורד ניתוח כ-PDF", data=pdf_bytes, 
                           file_name=f"analysis_{st.session_state.user_name}.pdf", mime="application/pdf")
    except:
        st.error("שגיאה ביצירת ה-PDF.")

    if st.button("חזרה לתפריט"):
        if 'final_analysis' in st.session_state: del st.session_state.final_analysis
        st.session_state.page = "home"; st.rerun()

# --- דף ארכיון ---
elif st.session_state.page == "archive":
    st.title(f"📂 ארכיון עבור: {st.session_state.user_name}")
    if fb_status:
        docs = st.session_state.db.collection('results').where('user', '==', st.session_state.user_name).stream()
        for doc in docs:
            d = doc.to_dict()
            with st.expander(f"מבחן מתאריך {d['date']}"):
                st.write(d['analysis'])
    else:
        st.error("ארכיון לא זמין.")
    if st.button("חזרה"): st.session_state.page = "home"; st.rerun()

st.markdown('<div class="custom-footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
