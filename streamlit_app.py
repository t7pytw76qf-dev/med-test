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

# --- 3. עיצוב CSS מתוקן (מסדר את תיבת הטקסט ומנקה סמלים) ---
st.markdown("""
    <style>
    /* הסתרת אלמנטים של Streamlit ו-GitHub */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stDecoration"] {display: none;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    
    /* הסרת רווחים מיותרים למעלה בלי לשבור את הדינמיקה של הדף */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 5rem !important;
    }

    /* הגדרת RTL ויישור לימין */
    .main .block-container { 
        direction: rtl; 
        text-align: right; 
    }
    
    /* סידור תיבת הטקסט - לוודא שהיא בולטת ועובדת */
    .stTextInput > div > div > input {
        text-align: right;
        direction: rtl;
    }

    /* פוטר זכויות יוצרים ממורכז ונקי */
    .custom-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: white; color: #333; text-align: center;
        padding: 10px; font-weight: bold; font-size: 13px;
        border-top: 1px solid #eaeaea; z-index: 1000;
    }
    
    /* כפתורים מותאמים */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        font-weight: bold;
        margin-top: 10px;
    }
    
    h1, h2, h3 { text-align: right; margin-bottom: 10px; }
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
        st.error("שגיאה בטעינת קובץ השאלות questions.csv")
        return []

# --- ניהול דפים ---
if 'page' not in st.session_state:
    st.session_state.page = "home"
    st.session_state.user_name = ""

# --- דף הבית ---
if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    
    # תיבת הזנת שם משתמש משופרת
    st.session_state.user_name = st.text_input("הזן שם משתמש:", value=st.session_state.user_name)
    
    st.write("---")
    st.subheader("בחר מסלול תרגול:")
    
    if st.button("📝 שאלון מלא (200 שאלות)"):
        if st.session_state.user_name:
            st.session_state.questions = load_quiz(200)
            if st.session_state.questions:
                st.session_state.current_step = 0
                st.session_state.answers = []
                st.session_state.start_time = time.time()
                st.session_state.page = "quiz"
                st.rerun()
        else: st.warning("נא להזין שם משתמש כדי להתחיל")
        
    if st.button("⏱️ מקבץ מהיר (36 שאלות)"):
        if st.session_state.user_name:
            st.session_state.questions = load_
            
