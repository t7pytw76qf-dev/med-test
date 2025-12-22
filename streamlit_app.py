import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os

# --- 1. הגדרות תצוגה ועיצוב (RTL) ---
st.set_page_config(page_title="מערכת HEXACO", layout="centered")

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        # גיבוי עיצוב בתוך הקוד אם style.css חסר
        st.markdown("""
        <style>
            .main { direction: rtl; text-align: right; }
            div[data-testid="column"] button { width: 100%; height: 5em; font-size: 20px; font-weight: bold; border-radius: 15px; border: 2px solid #4A90E2; background-color: white; transition: 0.3s; }
            div[data-testid="column"] button:active, div[data-testid="column"] button:focus { background-color: #4A90E2 !important; color: white !important; }
            .stButton>button { width: 100%; height: 4em; border-radius: 12px; }
            .custom-footer { position: fixed; left: 0; bottom: 0; width: 100%; background: white; text-align: center; padding: 10px; border-top: 1px solid #eaeaea; font-weight: bold; }
        </style>
        """, unsafe_allow_html=True)

local_css("style.css")

# --- 2. אתחול מפתחות ואבטחה (Secrets) ---
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
    st.sidebar.warning("שים לב: הארכיון או ה-AI לא מחוברים כראוי.")

# --- 3. פונקציית AI משולבת (Flash + Pro) ---
def generate_analysis_with_fallback(data):
    # מנסה קודם את Flash (מהיר וחינמי יותר) ואז את Pro כגיבוי
    models = ["models/gemini-1.5-flash", "models/gemini-1.5-pro"]
    prompt = f"""
    נתח מועמד לרפואה בשם {st.session_state.user_name}.
    להלן תוצאות מבחן HEXACO כולל זמני מענה (בשניות): {data}.
    אנא נתח:
    1. אמינות המענה (לפי עקביות וזמנים). התייחס למילים gnarled, emits, clenched אם הופיעו.
    2. תכונות אישיות בולטות.
    3. התאמה למקצוע הרפואה.
    ענה בעברית מקצועית ומפורטת.
    """
    
    for model_name in models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text, model_name
        except Exception:
            continue 
    return "שגיאה: שני המודלים חרגו מהמכסה. נסה שוב בעוד דקה.", None

# --- 4. לוגיקת טעינת שאלות ---
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
        st.error("קובץ questions.csv לא נמצא.")
        return []

# --- 5. ניהול מצבי עמוד ---
if 'page' not in st.session_state:
    st.session_state.page = "home"
    st.session_state.user_name = ""

# --- 6. דפי האפליקציה ---

# --- דף הבית ---
if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    st.session_state.user_name = st.text_input("הזן שם משתמש:", value=st.session_state.user_name)
    
    st.write("### בחר מסלול תרגול:")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝 שאלון מלא (200)"):
            if st.session_state.user_name:
                st.session_state.questions = load_quiz(200)
                st.session_state.current_step = 0
                st.session_state.answers = []
                st.session_state.start_time = time.time()
                st.session_state.page = "quiz"; st.rerun()
            else: st.warning("נא להזין שם משתמש")

    with col2:
        if st.button("⏱️ מקבץ מהיר (36)"):
            if st.session_state.user_name:
                st.session_state.questions = load_quiz(36)
                st.session_state.current_step = 0
                st.session_state.answers = []
                st.session_state.start_time = time.time()
                st.session_state.page = "quiz"; st.rerun()
            else: st.warning("נא להזין שם משתמש")

    st.write("---")
    if st.button("📂 ארכיון תוצאות והיסטוריה"):
        if st.session_state.user_name:
            st.session_state.page = "archive"; st.rerun()
        else: st.warning("נא להזין שם משתמש")

# --- דף השאלון ---
elif st.session_state.page == "quiz":
    q = st.session_state.questions
    idx = st.session_state.current_step
    
    if idx < len(q):
        st.write(f"נבחן: **{st.session_state.user_name}** | שאלה {idx + 1} מתוך {len(q)}")
        st.progress((idx + 1) / len(q))
        st.markdown(f"<h2 style='text-align: right;'>{q[idx]['q']}</h2>", unsafe_allow_html=True)
        
        cols = st.columns(5)
        for i, col in enumerate(cols, 1):
            if col.button(str(i), key=f"btn_{idx}_{i}"):
                duration = round(time.time() - st.session_state.start_time, 2)
                st.session_state.answers.append({
                    "trait": q[idx]['trait'], "score": i, "time": duration
                })
                st.session_state.current_step += 1
                st.session_state.start_time = time.time()
                st.rerun()
    else:
        st.success("השאלון הושלם בהצלחה!")
        if st.button("עבור לניתוח AI"):
            st.session_state.page = "analysis"; st.rerun()

# --- דף ניתוח AI ---
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח AI מקצועי")
    with st.spinner("המערכת מנתחת נתונים... (מנסה מודל Flash/Pro)"):
        analysis, model_used = generate_analysis_with_fallback(st.session_state.answers)
        st.info(f"מודל מבצע: {model_used if model_used else 'N/A'}")
        st.markdown(analysis)
        
        # שמירה לארכיון ב-Firebase
        if fb_status and model_used:
            try:
                st.session_state.db.collection('results').add({
                    'user': st.session_state.user_name,
                    'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'analysis': analysis,
                    'score_summary': st.session_state.answers
                })
            except: pass

    if st.button("חזרה לתפריט ראשי"):
        st.session_state.page = "home"; st.rerun()

# --- דף ארכיון ---
elif st.session_state.page == "archive":
    st.title(f"📂 ארכיון עבור: {st.session_state.user_name}")
    if fb_status:
        docs = st.session_state.db.collection('results').where('user', '==', st.session_state.user_name).stream()
        found = False
        for doc in docs:
            found = True
            data = doc.to_dict()
            with st.expander(f"מבחן מתאריך {data['date']}"):
                st.write(data['analysis'])
        if not found: st.info("לא נמצאו מבחנים קודמים למשתמש זה.")
    else:
        st.error("הארכיון אינו זמין (חסר חיבור Firebase ב-Secrets).")
    
    if st.button("חזרה"):
        st.session_state.page = "home"; st.rerun()

# --- פוטר קבוע ---
st.markdown('<div class="custom-footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
