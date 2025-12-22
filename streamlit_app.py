import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. הגדרת Gemini ---
API_KEY = "AIzaSyDnYMJpJkNcXpOT8TgqPe6ymyvZxnWGCBo"
genai.configure(api_key=API_KEY)

def get_working_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if '1.5-flash' in m.name: return m.name
        return 'gemini-1.5-flash'
    except: return 'gemini-1.5-flash'

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

# --- 3. עיצוב CSS (סדר כפתורים, RTL וניקיון) ---
st.markdown("""
    <style>
    /* הסתרת אלמנטים של Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stDecoration"] {display: none;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    
    /* הגדרת RTL ויישור לימין */
    .main .block-container { 
        direction: rtl; 
        text-align: right; 
        padding-top: 3rem !important;
    }

    /* סידור תיבת הטקסט */
    .stTextInput > label { text-align: right; width: 100%; font-weight: bold; }
    input { text-align: right; direction: rtl; }

    /* כפתורים מסודרים וגדולים */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        font-weight: bold;
        margin-top: 15px;
    }

    /* פוטר זכויות יוצרים ממורכז */
    .custom-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: white; color: #333; text-align: center;
        padding: 10px; font-weight: bold; font-size: 13px;
        border-top: 1px solid #eaeaea; z-index: 1000;
    }
    
    h1, h2, h3 { text-align: right; }
    </style>
""", unsafe_allow_html=True)

# --- פונקציית טעינת שאלות ---
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
    except:
        st.error("שגיאה: וודא שקובץ questions.csv קיים ב-GitHub")
        return []

# --- ניהול דפים ---
if 'page' not in st.session_state:
    st.session_state.page = "home"
    st.session_state.user_name = ""

# --- דף הבית ---
if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    
    # 1. הזנת שם
    st.session_state.user_name = st.text_input("הזן שם משתמש:", value=st.session_state.user_name)
    
    st.write("### בחר מסלול תרגול:")
    
    # 2. כפתורי המבחנים
    if st.button("📝 שאלון מלא (200 שאלות)"):
        if st.session_state.user_name:
            st.session_state.questions = load_quiz(200)
            if st.session_state.questions:
                st.session_state.current_step = 0
                st.session_state.answers = []
                st.session_state.start_time = time.time()
                st.session_state.page = "quiz"
                st.rerun()
        else: st.warning("נא להזין שם משתמש")
        
    if st.button("⏱️ מקבץ מהיר (36 שאלות)"):
        if st.session_state.user_name:
            st.session_state.questions = load_quiz(36)
            if st.session_state.questions:
                st.session_state.current_step = 0
                st.session_state.answers = []
                st.session_state.start_time = time.time()
                st.session_state.page = "quiz"
                st.rerun()
        else: st.warning("נא להזין שם משתמש")
    
    # 3. כפתור ארכיון (תמיד מופיע)
    if st.button("📂 ארכיון וחוות דעת מצטברת"):
        if st.session_state.user_name:
            st.session_state.page = "archive"; st.rerun()
        else: st.warning("נא להזין שם משתמש כדי לצפות בארכיון")

# --- דף השאלון ---
elif st.session_state.page == "quiz":
    q = st.session_state.questions; step = st.session_state.current_step
    if step < len(q):
        st.write(f"נבחן: **{st.session_state.user_name}** | שאלה {step + 1} מתוך {len(q)}")
        st.progress((step + 1) / len(q))
        st.markdown(f"### {q[step]['q']}")
        
        cols = st.columns(5)
        for i, col in enumerate(cols, 1):
            if col.button(str(i), key=f"q_{step}_{i}"):
                elapsed = round(time.time() - st.session_state.start_time, 2)
                st.session_state.answers.append({"trait": q[step]['trait'], "score": i, "time": elapsed})
                st.session_state.current_step += 1
                st.session_state.start_time = time.time()
                st.rerun()
    else:
        st.success("השאלון הושלם!")
        if st.button("לחץ לניתוח AI"):
            st.session_state.page = "analysis"; st.rerun()

# --- דף ניתוח ---
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח AI")
    with st.spinner("מנתח..."):
        try:
            model = genai.GenerativeModel(get_working_model())
            prompt = f"נתח מועמד לרפואה בשם {st.session_state.user_name}. תשובות: {st.session_state.answers}. ענה בעברית."
            resp = model.generate_content(prompt)
            st.markdown(resp.text)
            
            if st.session_state.fb_status and db:
                db.collection('results').add({
                    'user': st.session_state.user_name, 'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'analysis': resp.text
                })
        except Exception as e:
            st.error(f"שגיאה: {e}")
    if st.button("חזרה לתפריט"): st.session_state.page = "home"; st.rerun()

# --- דף ארכיון ---
elif st.session_state.page == "archive":
    st.title(f"📂 ארכיון: {st.session_state.user_name}")
    if st.session_state.fb_status and db:
        docs = list(db.collection('results').where('user', '==', st.session_state.user_name).stream())
        if docs:
            for doc in docs:
                d = doc.to_
