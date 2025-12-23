import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from logic import DOCTOR_PROFILE, get_status_color, create_pdf_report, generate_ai_analysis

# עיצוב CSS
st.set_page_config(page_title="Medical HEXACO Pro", layout="wide")
st.markdown("""
    <style>
        .main .block-container { direction: rtl !important; text-align: right !important; }
        div.stButton > button {
            width: 100% !important; height: 4em !important; font-size: 20px !important;
            font-weight: bold !important; border-radius: 12px !important;
            border: 2px solid #4A90E2 !important; background-color: white !important;
            color: #4A90E2 !important; transition: 0.3s;
        }
    </style>
    """, unsafe_allow_html=True)

# אתחול Firebase
if "firebase" in st.secrets and not firebase_admin._apps:
    fb_dict = dict(st.secrets["firebase"])
    fb_dict["private_key"] = fb_dict["private_key"].replace('\\n', '\n')
    cred = credentials.Certificate(fb_dict)
    firebase_admin.initialize_app(cred)
db = firestore.client() if firebase_admin._apps else None

# ניהול דפים
if 'page' not in st.session_state: st.session_state.page = "home"

if st.session_state.page == "home":
    st.title("🏥 מערכת HEXACO למועמדי רפואה")
    user_name = st.text_input("שם מלא:")
    
    if st.button("📝 התחל שאלון 200 שאלות"):
        if user_name:
            st.session_state.user_name = user_name
            df = pd.read_csv("questions.csv")
            st.session_state.questions = df.to_dict('records')
            st.session_state.current_step = 0
            st.session_state.answers = []
            st.session_state.start_time = time.time()
            st.session_state.page = "quiz"
            st.rerun()
        else:
            st.warning("אנא הזן שם.")

elif st.session_state.page == "quiz":
    q, idx = st.session_state.questions, st.session_state.current_step
    if idx < len(q):
        st.subheader(f"שאלה {idx + 1} מתוך {len(q)}")
        st.progress((idx + 1) / len(q))
        st.write(f"### {q[idx]['q']}")
        cols = st.columns(5)
        for val, col in enumerate(cols, 1):
            if col.button(str(val), key=f"q_{idx}_{val}"):
                st.session_state.answers.append({"trait": q[idx]['trait'], "score": val})
                st.session_state.current_step += 1
                st.rerun()
    else:
        if st.button("🚀 הצג תוצאות וניתוח"):
            st.session_state.page = "analysis"
            st.rerun()

elif st.session_state.page == "analysis":
    st.title(f"📊 ניתוח תוצאות: {st.session_state.user_name}")
    
    # חישוב ממוצעים
    trait_scores = {t: [] for t in DOCTOR_PROFILE.keys()}
    for a in st.session_state.answers:
        trait_scores[a['trait']].append(a['score'])
    avgs = {k: round(np.mean(v), 2) for k, v in trait_scores.items()}
    st.session_state.current_avgs = avgs
    
    # טבלת רמזור
    res_data = []
    for t, s in avgs.items():
        color = get_status_color(t, s)
        status = "✅" if color == "#2ecc71" else ("⚠️" if color == "#f1c40f" else "❌")
        res_data.append({"תכונה": DOCTOR_PROFILE[t]['label'], "ציון": s, "סטטוס": status})
    st.table(pd.DataFrame(res_data).sort_values("ציון", ascending=False))
    
    # AI ו-PDF
    if 'final_analysis' not in st.session_state:
        st.session_state.final_analysis = generate_ai_analysis(st.session_state.user_name, avgs, [])
    
    st.write(st.session_state.final_analysis)
    
    pdf_bytes = create_pdf_report(st.session_state.user_name, st.session_state.final_analysis, avgs)
    st.download_button("📥 הורד דוח PDF", data=bytes(pdf_bytes), file_name="Report.pdf")
    
    if st.button("🏠 חזרה לבית"):
        st.session_state.page = "home"; st.rerun()
