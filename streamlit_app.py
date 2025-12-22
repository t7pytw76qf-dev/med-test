import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. הגדרת Gemini עם תיקון לשגיאת 404 ---
API_KEY = "AIzaSyDnYMJpJkNcXpOT8TgqPe6ymyvZxnWGCBo"
genai.configure(api_key=API_KEY)

def get_working_model():
    """פונקציה שמוודאת בחירת מודל קיים למניעת שגיאת 404"""
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # מחפש מודל פלאש עדכני
                if 'gemini-1.5-flash' in m.name:
                    return m.name
        return 'models/gemini-1.5-flash' # ברירת מחדל
    except:
        return 'models/gemini-1.5-flash'

# --- 2. אתחול Firebase ---
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

db = st.session_state.db

# --- 3. עיצוב CSS (פתרון בעיות תצוגה והסתרת סמלים) ---
st.markdown("""
    <style>
    /* הסתרת אלמנטים של Streamlit (הסימונים הירוקים) */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stDecoration"] {display: none;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    
    /* הגדרת RTL ויישור לימין */
    .main .block-container { 
        direction: rtl !important; 
        text-align: right !important; 
        padding-top: 2rem !important;
        max-width: 800px;
        margin: 0 auto;
    }

    /* תיקון שורת הזנת השם */
    div[data-testid="stTextInput"] {
        width: 100% !important;
        direction: rtl !important;
    }
    input {
        text-align: right !important;
        direction: rtl !important;
    }

    /* כפתורים רחבים ומסודרים */
    .stButton > button {
        width: 100% !important;
        border-radius: 12px !important;
        height: 3.5em !important;
        font-weight: bold !important;
        font-size: 18px !important;
        margin-bottom: 10px !important;
    }

    /* זכויות יוצרים במרכז */
    .custom-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: white; color: #333; text-align: center;
        padding: 10px; font-weight: bold; font-size: 13px;
        border-top: 1px solid #eaeaea; z-index: 1000;
    }
    
    h1, h2, h3 { text-align: right !important; }
    </style>
""", unsafe_allow_html=True)

# --- פונקציות לוגיקה ---
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

if 'page' not in st.session_state:
    st.session_state.page = "home"
    st.session_state.user_name = ""

# --- דף הבית ---
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

# --- דף השאלון ---
elif st.session_state.page == "quiz":
    q = st.session_state.questions; step = st.session_state.current_step
    if step < len(q):
        st.write(f"שאלה {step + 1} מתוך {len(q)}")
        st.progress((step + 1) / len(q))
        st.markdown(f"### {q[step]['q']}")
        cols = st.columns(5)
        for i, col in enumerate(cols, 1):
            if col.button(str(i), key=f"q_{step}_{i}"):
                elapsed = round(time.time() - st.session_state.start_time, 2)
                st.session_state.answers.append({"trait": q[step]['trait'], "score": i, "time": elapsed})
                st.session_state.current_step += 1; st.session_state.start_time = time.time(); st.rerun()
    else:
        if st.button("סיימתי, עבור לניתוח"):
            st.session_state.page = "analysis"; st.rerun()

# --- דף ניתוח (כאן התיקון לשגיאת 404) ---
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח AI")
    with st.spinner("ה-AI מנתח את התוצאות..."):
        try:
            working_model = get_working_model()
            model = genai.GenerativeModel(working_model)
            prompt = f"נתח מועמד לרפואה בשם {st.session_state.user_name}. תשובות: {st.session_state.answers}. ענה בעברית."
            resp = model.generate_content(prompt)
            st.markdown(resp.text)
            
            if st.session_state.fb_status and db:
                db.collection('results').add({'user': st.session_state.user_name, 'date': datetime.now().strftime("%d/%m/%Y %H:%M"), 'analysis': resp.text})
        except Exception as e:
            st.error(f"שגיאת AI (נסיון תיקון): {e}")
            
    if st.button("חזרה לתפריט"): st.session_state.page = "home"; st.rerun()

# --- דף ארכיון ---
elif st.session_state.page == "archive":
    st.title(f"📂 ארכיון: {st.session_state.user_name}")
    if st.session_state.fb_status and db:
        docs = list(db.collection('results').where('user', '==', st.session_state.user_name).stream())
        if docs:
            for doc in docs:
                d = doc.to_dict()
                with st.expander(f"מבחן מיום {d['date']}"): st.write(d['analysis'])
        else: st.info("לא נמצאו מבחנים קודמים.")
    if st.button("חזרה"): st.session_state.page = "home"; st.rerun()

st.markdown('<div class="custom-footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
