import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os

# --- 1. הגדרות תצוגה ועיצוב ---
st.set_page_config(page_title="מערכת HEXACO", layout="centered")

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

# --- 2. אתחול מפתחות (Secrets) ---
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

# --- 3. פונקציית AI משולבת (Flash -> Flash-8B -> Pro) ---
def generate_analysis(answers):
    # רשימת מודלים לפי סדר עדיפות לניצול מכסה מקסימלי
    models_to_try = [
        "models/gemini-1.5-flash", 
        "models/gemini-1.5-flash-8b", 
        "models/gemini-1.5-pro"
    ]
    
    prompt = f"""
    נתח מועמד לרפואה בשם {st.session_state.user_name}.
    נתוני המבחן (תשובות 1-5 וזמן מענה בשניות): {answers}.
    בצע ניתוח מעמיק בעברית על:
    1. אמינות המענה (לפי עקביות וזמני תגובה).
    2. תכונות HEXACO בולטות והתאמה למקצוע הרפואה.
    ענה בצורה מקצועית ומכבדת.
    """
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text, model_name
        except Exception as e:
            if "429" in str(e): # שגיאת מכסה - נמתין רגע וננסה מודל אחר
                time.sleep(1)
                continue
            continue
    return "כל המודלים חרגו מהמכסה כרגע. אנא המתן דקה ונסה שוב.", None

# --- 4. טעינת שאלון ---
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
    except:
        return []

# --- 5. ניהול ניווט ---
if 'page' not in st.session_state:
    st.session_state.page = "home"
    st.session_state.user_name = ""

# --- 6. דפי האפליקציה ---

# דף הבית
if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    st.session_state.user_name = st.text_input("הזן שם משתמש:", value=st.session_state.user_name)
    
    st.write("### בחר מסלול תרגול:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 שאלון מלא (200)"):
            if st.session_state.user_name:
                st.session_state.questions = load_quiz(200)
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
            else: st.warning("נא להזין שם")
    with col2:
        if st.button("⏱️ מקבץ מהיר (36)"):
            if st.session_state.user_name:
                st.session_state.questions = load_quiz(36)
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
            else: st.warning("נא להזין שם")
    
    st.write("---")
    if st.button("📂 ארכיון תוצאות והיסטוריה"):
        if st.session_state.user_name:
            st.session_state.page = "archive"; st.rerun()
        else: st.warning("נא להזין שם")

# דף השאלון
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

# דף ניתוח
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח AI מקצועי")
    with st.spinner("המערכת מנסה מספר מודלים כדי לעקוף עומס..."):
        analysis, model_used = generate_analysis(st.session_state.answers)
        if model_used:
            st.info(f"הניתוח בוצע בהצלחה")
            st.markdown(analysis)
            if fb_status:
                try:
                    st.session_state.db.collection('results').add({
                        'user': st.session_state.user_name,
                        'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                        'analysis': analysis
                    })
                except: pass
        else:
            st.error(analysis)
    if st.button("חזרה לתפריט"): st.session_state.page = "home"; st.rerun()

# דף ארכיון
elif st.session_state.page == "archive":
    st.title(f"📂 ארכיון: {st.session_state.user_name}")
    if fb_status:
        docs = st.session_state.db.collection('results').where('user', '==', st.session_state.user_name).stream()
        for doc in docs:
            data = doc.to_dict()
            with st.expander(f"מבחן מיום {data['date']}"):
                st.write(data['analysis'])
    else: st.error("ארכיון לא מחובר")
    if st.button("חזרה"): st.session_state.page = "home"; st.rerun()

st.markdown('<div class="custom-footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
