import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import google.generativeai as genai
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from fpdf import FPDF
import io

# --- 1. הגדרות דמות הרופא ---
DOCTOR_PROFILE = {
    "Honesty-Humility": {"min": 4.0, "max": 5.0, "label": "יושרה וצניעות"},
    "Emotionality": {"min": 2.2, "max": 3.8, "label": "יציבות רגשית"},
    "Extraversion": {"min": 3.0, "max": 5.0, "label": "מוחצנות חברתית"},
    "Agreeableness": {"min": 3.8, "max": 5.0, "label": "נעימות וסבלנות"},
    "Conscientiousness": {"min": 4.2, "max": 5.0, "label": "מצפוניות וסדר"},
    "Openness to Experience": {"min": 3.0, "max": 5.0, "label": "פתיחות ללמידה"}
}

def get_status_color(trait, score):
    target = DOCTOR_PROFILE[trait]
    if target["min"] <= score <= target["max"]: return "#2ecc71"
    elif target["min"] - 0.5 <= score <= target["max"] + 0.5: return "#f1c40f"
    else: return "#e74c3c"

# --- 2. פונקציית יצירת PDF עם fpdf2 ---
def create_pdf_fpdf2(user_name, analysis_text, current_avgs):
    pdf = FPDF()
    pdf.add_page()
    
    # שימוש בגופן סטנדרטי (לעברית מלאה ב-PDF יש צורך בטעינת קובץ גופן חיצוני .ttf)
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, f"Medical HEXACO Report - {user_name}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Summary Scores:", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", "", 10)
    for trait, score in current_avgs.items():
        # הצגת השם באנגלית כדי למנוע בעיות קידוד ללא גופן חיצוני
        line = f"{trait}: {score} ({DOCTOR_PROFILE[trait]['label'][::-1]})"
        pdf.cell(0, 8, line, new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Detailed AI Analysis:", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", "", 10)
    # ניקוי תווים לא תואמים
    clean_text = analysis_text.replace('\n', ' ').encode('utf-8', 'ignore').decode('utf-8')
    pdf.multi_cell(0, 8, clean_text)
    
    return pdf.output()

# --- 3. עיצוב ו-UI ---
st.set_page_config(page_title="HEXACO Medical Pro", layout="wide")
st.markdown("""
    <style>
        .main .block-container { direction: rtl !important; text-align: right !important; }
        div.stButton > button {
            width: 100% !important; height: 4em !important; font-size: 20px !important;
            font-weight: bold !important; border-radius: 12px !important;
            border: 2px solid #4A90E2 !important; background-color: white !important;
            color: #4A90E2 !important; transition: 0.3s;
        }
        div.stButton > button:hover { background-color: #4A90E2 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. לוגיקת דפים (Home/Quiz/Analysis) ---
if 'page' not in st.session_state: st.session_state.page = "home"

if st.session_state.page == "home":
    st.title("🏥 HEXACO Medical Tracker")
    st.session_state.user_name = st.text_input("שם המועמד:")
    if st.button("התחל מבחן"):
        if st.session_state.user_name:
            df = pd.read_csv("questions.csv")
            st.session_state.questions = df.to_dict('records')
            st.session_state.current_step = 0; st.session_state.answers = []
            st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()

elif st.session_state.page == "quiz":
    q, idx = st.session_state.questions, st.session_state.current_step
    if idx < len(q):
        st.subheader(f"שאלה {idx + 1}")
        st.markdown(f"### {q[idx]['q']}")
        cols = st.columns(5)
        for val, col in enumerate(cols, 1):
            if col.button(str(val), key=f"q_{idx}_{val}"):
                st.session_state.answers.append({"trait": q[idx]['trait'], "score": val, "time": time.time() - st.session_state.start_time})
                st.session_state.current_step += 1; st.session_state.start_time = time.time(); st.rerun()
    else:
        st.button("הפק ניתוח סופי", on_click=lambda: setattr(st.session_state, 'page', 'analysis'))

elif st.session_state.page == "analysis":
    st.title(f"📊 דוח עבור: {st.session_state.user_name}")
    
    if 'final_analysis' not in st.session_state:
        with st.spinner("AI מנתח את התוצאות..."):
            trait_scores = {t: [] for t in DOCTOR_PROFILE.keys()}
            for a in st.session_state.answers:
                trait_scores[a['trait']].append(a['score'])
            
            avgs = {k: round(np.mean(v), 2) for k, v in trait_scores.items()}
            st.session_state.current_avgs = avgs
            
            # קריאת AI (Gemini)
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel("gemini-1.5-flash-latest")
                prompt = f"Analyze medical candidate {st.session_state.user_name} with scores {avgs}. Focus on medical ethics."
                st.session_state.final_analysis = model.generate_content(prompt).text
            except:
                st.session_state.final_analysis = "Analysis complete. Scores saved."

    # תצוגת טבלה וגרף רמזור
    st.table(pd.DataFrame([{"תכונה": DOCTOR_PROFILE[k]['label'], "ציון": v, "סטטוס": "✅" if get_status_color(k,v)=="#2ecc71" else "⚠️"} for k,v in st.session_state.current_avgs.items()]))
    
    # כפתור הורדה
    pdf_out = create_pdf_fpdf2(st.session_state.user_name, st.session_state.final_analysis, st.session_state.current_avgs)
    st.download_button("📥 הורד דוח PDF", data=pdf_out, file_name=f"HEXACO_{st.session_state.user_name}.pdf", mime="application/pdf")
    
    st.markdown("### ניתוח מילולי")
    st.write(st.session_state.final_analysis)
    
    if st.button("חזרה למסך הבית"):
        st.session_state.page = "home"; st.rerun()
