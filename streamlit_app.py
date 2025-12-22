import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os

# --- 1. טעינת עיצוב חיצוני (style.css) ---
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# --- 2. מנגנון בחירת מודל דינמי (פתרון לשגיאת 404) ---
def get_working_model():
    try:
        # סריקת מודלים זמינים
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # עדיפות ל-flash 1.5
        for m in available_models:
            if 'gemini-1.5-flash' in m: return m
        # עדיפות לגרסת ה-latest
        for m in available_models:
            if 'gemini-pro' in m: return m
        return available_models[0]
    except:
        return 'models/gemini-1.5-flash-latest' # ברירת מחדל בטוחה יותר

# --- 3. אתחול Gemini ו-Firebase מה-Secrets ---
fb_status = False
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    if "firebase" in st.secrets:
        if not firebase_admin._apps:
            fb_dict = dict(st.secrets["firebase"])
            fb_dict["private_key"] = fb_dict["private_key"].replace('\\n', '\n')
            cred = credentials.Certificate(fb_dict)
            firebase_admin.initialize_app(cred)
        st.session_state.db = firestore.client()
        fb_status = True
except Exception as e:
    st.sidebar.error(f"שגיאת חיבור: {e}")

# --- 4. פונקציית טעינת שאלון ---
def load_quiz(amount):
    try:
        df = pd.read_csv("questions.csv")
        # וודא שהמילים gnarled, emits, clenched נמצאות בקובץ ה-CSV שלך
        traits = df['trait'].unique()
        q_per_trait = max(1, amount // len(traits))
        quiz = []
        for t in traits:
            pool = df[df['trait'] == t].to_dict('records')
            quiz.extend(random.sample(pool, min(q_per_trait, len(pool))))
        random.shuffle(quiz)
        return quiz[:amount]
    except: return []

# ניהול ניווט
if 'page' not in st.session_state: st.session_state.page = "home"

# --- 5. דף הבית ---
if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    user_name = st.text_input("הזן שם משתמש:", key="input_user")
    
    st.write("### בחר מסלול תרגול:")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝 שאלון מלא (200)"):
            if user_name:
                st.session_state.user_name = user_name
                st.session_state.questions = load_quiz(200)
                st.session_state.answers = []
                st.session_state.current_step = 0
                st.session_state.start_time = time.time()
                st.session_state.page = "quiz"; st.rerun()
            else: st.warning("נא להזין שם")

    with col2:
        if st.button("⏱️ מקבץ מהיר (36)"):
            if user_name:
                st.session_state.user_name = user_name
                st.session_state.questions = load_quiz(36)
                st.session_state.answers = []
                st.session_state.current_step = 0
                st.session_state.start_time = time.time()
                st.session_state.page = "quiz"; st.rerun()
            else: st.warning("נא להזין שם")

    st.write("---")
    if st.button("📂 ארכיון תוצאות"):
        if user_name:
            st.session_state.user_name = user_name
            st.session_state.page = "archive"; st.rerun()
        else: st.warning("נא להזין שם")

# --- 6. דף השאלון (זמנים ועיצוב) ---
elif st.session_state.page == "quiz":
    q = st.session_state.questions
    idx = st.session_state.current_step
    
    if idx < len(q):
        st.write(f"נבחן: {st.session_state.user_name} | שאלה {idx + 1} מתוך {len(q)}")
        st.progress((idx + 1) / len(q))
        st.markdown(f"## {q[idx]['q']}")
        
        cols = st.columns(5)
        for i, col in enumerate(cols, 1):
            # לחיצה על כפתור צובעת אותו (דרך ה-CSS) ועוברת שאלה
            if col.button(str(i), key=f"btn_{idx}_{i}"):
                duration = round(time.time() - st.session_state.start_time, 2)
                st.session_state.answers.append({
                    "trait": q[idx]['trait'],
                    "score": i,
                    "time": duration
                })
                st.session_state.current_step += 1
                st.session_state.start_time = time.time()
                st.rerun()
    else:
        st.success("השאלון הושלם!")
        if st.button("עבור לניתוח AI"):
            st.session_state.page = "analysis"; st.rerun()

# --- 7. דף ניתוח AI ---
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח AI")
    with st.spinner("מנתח נתונים..."):
        try:
            model = genai.GenerativeModel(get_working_model())
            prompt = f"נתח מועמד לרפואה בשם {st.session_state.user_name}. תשובות וזמני מענה: {st.session_state.answers}. ענה בעברית על אמינות והתאמה."
            response = model.generate_content(prompt)
            analysis_text = response.text
            st.markdown(analysis_text)
            
            if fb_status:
                st.session_state.db.collection('results').add({
                    'user': st.session_state.user_name,
                    'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'analysis': analysis_text
                })
        except Exception as e:
            st.error(f"שגיאה בניתוח: {e}")
    
    if st.button("חזרה לתפריט"): st.session_state.page = "home"; st.rerun()

# --- 8. דף ארכיון ---
elif st.session_state.page == "archive":
    st.title(f"📂 ארכיון: {st.session_state.user_name}")
    if fb_status:
        docs = st.session_state.db.collection('results').where('user', '==', st.session_state.user_name).stream()
        for doc in docs:
            res = doc.to_dict()
            with st.expander(f"מבחן מיום {res['date']}"):
                st.write(res['analysis'])
    else: st.error("הארכיון לא מחובר.")
    if st.button("חזרה"): st.session_state.page = "home"; st.rerun()

st.markdown('<div class="custom-footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
