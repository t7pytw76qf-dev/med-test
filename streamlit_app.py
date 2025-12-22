import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os

# --- טעינת עיצוב חיצוני ---
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

# --- הגדרת Gemini (מנוע AI) ---
API_KEY = "AIzaSyDnYMJpJkNcXpOT8TgqPe6ymyvZxnWGCBo"
genai.configure(api_key=API_KEY)

def get_working_model():
    """מנגנון תיקון שגיאת 404 - בחירה דינמית של מודל פלאש"""
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for name in available:
            if 'flash' in name: return name
        return available[0] if available else 'models/gemini-1.5-flash'
    except:
        return 'models/gemini-1.5-flash'

# --- אתחול Firebase ---
if 'db' not in st.session_state:
    st.session_state.db = None
    st.session_state.fb_status = False

if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            fb_dict = dict(st.secrets["firebase"])
            fb_dict["private_key"] = fb_dict["private_key"].replace('\\n', '\n')
            cred = credentials.Certificate(fb_dict)
            firebase_admin.initialize_app(cred)
            st.session_state.db = firestore.client()
            st.session_state.fb_status = True
    except: pass

# --- לוגיקת האפליקציה ---
if 'page' not in st.session_state:
    st.session_state.page = "home"
    st.session_state.user_name = ""

def load_quiz(amount):
    try:
        df = pd.read_csv("questions.csv")
        traits = df['trait'].unique()
        q_per_trait = amount // len(traits)
        final_quiz = []
        for trait in traits:
            pool = df[df['trait'] == trait].to_dict('records')
            final_quiz.extend(random.sample(pool, min(q_per_trait, len(pool))))
        random.shuffle(final_quiz)
        return final_quiz
    except: return []

# --- תצוגת דפים ---
if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    st.session_state.user_name = st.text_input("הזן שם משתמש:", value=st.session_state.user_name)
    
    st.write("### בחר מסלול תרגול:")
    if st.button("📝 שאלון מלא (200 שאלות)"):
        if st.session_state.user_name:
            st.session_state.questions = load_quiz(200)
            st.session_state.current_step = 0; st.session_state.answers = []
            st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
        else: st.warning("נא להזין שם משתמש")
        
    if st.button("⏱️ מקבץ מהיר (36 שאלות)"):
        if st.session_state.user_name:
            st.session_state.questions = load_quiz(36)
            st.session_state.current_step = 0; st.session_state.answers = []
            st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
        else: st.warning("נא להזין שם משתמש")
    
    if st.button("📂 ארכיון וחוות דעת מצטברת"):
        if st.session_state.user_name:
            st.session_state.page = "archive"; st.rerun()
        else: st.warning("נא להזין שם משתמש")

elif st.session_state.page == "quiz":
    q = st.session_state.questions; step = st.session_state.current_step
    if step < len(q):
        st.write(f"נבחן: {st.session_state.user_name} | שאלה {step + 1} מתוך {len(q)}")
        st.progress((step + 1) / len(q))
        st.markdown(f"## {q[step]['q']}")
        cols = st.columns(5)
        for i, col in enumerate(cols, 1):
            if col.button(str(i), key=f"b_{step}_{i}"):
                elapsed = round(time.time() - st.session_state.start_time, 2)
                st.session_state.answers.append({"trait": q[step]['trait'], "score": i, "time": elapsed})
                st.session_state.current_step += 1; st.session_state.start_time = time.time(); st.rerun()
    else:
        if st.button("לחץ לקבלת ניתוח AI"):
            st.session_state.page = "analysis"; st.rerun()

elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח AI")
    with st.spinner("מנתח..."):
        try:
            model = genai.GenerativeModel(get_working_model())
            resp = model.generate_content(f"נתח מועמד לרפואה בשם {st.session_state.user_name}. תשובות: {st.session_state.answers}. ענה בעברית.")
            st.markdown(resp.text)
            if st.session_state.fb_status:
                st.session_state.db.collection('results').add({'user': st.session_state.user_name, 'date': datetime.now().strftime("%d/%m/%Y %H:%M"), 'analysis': resp.text})
        except Exception as e: st.error(f"שגיאה: {e}")
    if st.button("חזרה לתפריט"): st.session_state.page = "home"; st.rerun()

elif st.session_state.page == "archive":
    st.title(f"📂 ארכיון: {st.session_state.user_name}")
    if st.session_state.fb_status:
        docs = list(st.session_state.db.collection('results').where('user', '==', st.session_state.user_name).stream())
        for doc in docs:
            with st.expander(f"מבחן מיום {doc.to_dict()['date']}"): st.write(doc.to_dict()['analysis'])
    if st.button("חזרה"): st.session_state.page = "home"; st.rerun()

st.markdown('<div class="custom-footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
