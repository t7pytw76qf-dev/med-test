import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os

# --- 1. טעינת עיצוב ---
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# --- 2. אתחול Gemini ו-Firebase מה-Secrets ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    fb_status = False
    if "firebase" in st.secrets:
        if not firebase_admin._apps:
            fb_dict = dict(st.secrets["firebase"])
            fb_dict["private_key"] = fb_dict["private_key"].replace('\\n', '\n')
            cred = credentials.Certificate(fb_dict)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        fb_status = True
except Exception as e:
    st.error(f"שגיאה באתחול המערכת: {e}")

# --- 3. פונקציות עזר ---
def load_quiz(amount):
    try:
        df = pd.read_csv("questions.csv")
        traits = df['trait'].unique()
        q_per_trait = max(1, amount // len(traits))
        quiz = []
        for t in traits:
            pool = df[df['trait'] == t].to_dict('records')
            quiz.extend(random.sample(pool, min(q_per_trait, len(pool))))
        random.shuffle(quiz)
        return quiz[:amount]
    except: return []

# ניהול מצבי עמוד
if 'page' not in st.session_state: st.session_state.page = "home"

# --- 4. דף הבית ---
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

# --- 5. דף השאלון (כולל ניתוח זמנים) ---
elif st.session_state.page == "quiz":
    q = st.session_state.questions
    idx = st.session_state.current_step
    
    if idx < len(q):
        st.write(f"שאלה {idx + 1} מתוך {len(q)}")
        st.progress((idx + 1) / len(q))
        st.markdown(f"## {q[idx]['q']}")
        
        cols = st.columns(5)
        for i, col in enumerate(cols, 1):
            if col.button(str(i), key=f"btn_{idx}_{i}"):
                # חישוב זמן מענה לשאלה
                end_time = time.time()
                duration = round(end_time - st.session_state.start_time, 2)
                
                st.session_state.answers.append({
                    "trait": q[idx]['trait'],
                    "score": i,
                    "time_seconds": duration
                })
                st.session_state.current_step += 1
                st.session_state.start_time = time.time() # איפוס זמן לשאלה הבאה
                st.rerun()
    else:
        st.success("השאלון הושלם!")
        if st.button("קבל ניתוח AI"):
            st.session_state.page = "analysis"; st.rerun()

# --- 6. דף ניתוח AI ---
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח AI מקצועי")
    with st.spinner("מנתח נתונים וזמני תגובה..."):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""
            נתח מועמד לרפואה בשם {st.session_state.user_name}.
            תשובות וזמני מענה: {st.session_state.answers}.
            אנא התייחס בפירוט לעקביות, אמינות (לפי זמני תגובה), ותכונות HEXACO.
            ענה בעברית בלבד בצורה מקצועית.
            """
            response = model.generate_content(prompt)
            analysis_text = response.text
            st.markdown(analysis_text)
            
            # שמירה לארכיון
            if fb_status:
                db.collection('results').add({
                    'user': st.session_state.user_name,
                    'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'analysis': analysis_text,
                    'answers': st.session_state.answers
                })
        except Exception as e:
            st.error(f"שגיאה בניתוח: {e}")
    
    if st.button("חזרה לתפריט"): st.session_state.page = "home"; st.rerun()

# --- 7. דף ארכיון ---
elif st.session_state.page == "archive":
    st.title(f"📂 ארכיון: {st.session_state.user_name}")
    if fb_status:
        docs = db.collection('results').where('user', '==', st.session_state.user_name).order_by('date', direction='DESCENDING').stream()
        found = False
        for doc in docs:
            found = True
            res = doc.to_dict()
            with st.expander(f"מבחן מיום {res['date']}"):
                st.write(res['analysis'])
        if not found: st.info("לא נמצאו מבחנים קודמים.")
    else: st.error("הארכיון לא מחובר ל-Firebase.")
    
    if st.button("חזרה"): st.session_state.page = "home"; st.rerun()

st.markdown('<div class="custom-footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
