import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os

# --- 1. טעינת עיצוב חיצוני (Style.css) ---
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        # גיבוי עיצוב בסיסי אם הקובץ חסר
        st.markdown("""<style>
            .main { direction: rtl; text-align: right; }
            .stButton>button { width: 100%; height: 3em; border-radius: 10px; }
        </style>""", unsafe_allow_html=True)

local_css("style.css")

# --- 2. הגדרת Gemini בצורה מאובטחת ---
try:
    # משיכת המפתח מה-Secrets של Streamlit
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("שגיאה: מפתח ה-API לא נמצא ב-Secrets. אנא הגדר GEMINI_API_KEY.")
    st.stop()

def get_working_model():
    """מאתר מודל זמין למניעת שגיאת 404"""
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for name in available:
            if '1.5-flash' in name: return name
        return available[0] if available else 'models/gemini-1.5-flash'
    except:
        return 'models/gemini-1.5-flash'

# --- 3. אתחול Firebase (ארכיון) ---
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
    except Exception as e:
        pass # הארכיון פשוט לא יפעל אם אין הגדרות

# --- 4. פונקציות עזר לשאלון ---
def load_quiz(amount):
    try:
        df = pd.read_csv("questions.csv")
        # נוודא שהשאלות כוללות את המילים המיוחדות שלך gnarled, emits, clenched אם הן בקובץ
        traits = df['trait'].unique()
        q_per_trait = amount // len(traits)
        final_quiz = []
        for trait in traits:
            pool = df[df['trait'] == trait].to_dict('records')
            final_quiz.extend(random.sample(pool, min(q_per_trait, len(pool))))
        random.shuffle(final_quiz)
        return final_quiz
    except:
        st.error("קובץ questions.csv חסר ב-GitHub.")
        return []

# --- 5. ניהול מצב (Session State) ---
if 'page' not in st.session_state:
    st.session_state.page = "home"
    st.session_state.user_name = ""

# --- 6. דפי האפליקציה ---

# --- דף הבית ---
if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    st.write("ברוך הבא למערכת תרגול אמינות ואישיות.")
    
    st.session_state.user_name = st.text_input("הזן שם משתמש (לשמירת תוצאות):", value=st.session_state.user_name)
    
    st.write("### בחר מסלול תרגול:")
    
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
    
    if st.button("📂 ארכיון וחוות דעת מצטברת"):
        if st.session_state.user_name:
            st.session_state.page = "archive"; st.rerun()
        else: st.warning("נא להזין שם משתמש")

# --- דף השאלון ---
elif st.session_state.page == "quiz":
    q = st.session_state.questions
    step = st.session_state.current_step
    
    if step < len(q):
        st.write(f"נבחן: **{st.session_state.user_name}** | שאלה {step + 1} מתוך {len(q)}")
        st.progress((step + 1) / len(q))
        
        st.markdown(f"<h2 style='text-align: right;'>{q[step]['q']}</h2>", unsafe_allow_html=True)
        
        # כפתורי 1-5 רחבים (העיצוב נמצא ב-style.css)
        cols = st.columns(5)
        for i, col in enumerate(cols, 1):
            if col.button(str(i), key=f"btn_{step}_{i}"):
                elapsed = round(time.time() - st.session_state.start_time, 2)
                st.session_state.answers.append({
                    "trait": q[step]['trait'], 
                    "score": i, 
                    "time": elapsed
                })
                st.session_state.current_step += 1
                st.session_state.start_time = time.time()
                st.rerun()
    else:
        st.success("השאלון הושלם בהצלחה!")
        if st.button("לחץ כאן לקבלת ניתוח AI"):
            st.session_state.page = "analysis"; st.rerun()

# --- דף ניתוח AI ---
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח אמינות ואישיות")
    with st.spinner("ה-AI מנתח את התשובות..."):
        try:
            model_name = get_working_model()
            model = genai.GenerativeModel(model_name)
            
            prompt = f"""
            נתח מועמד לרפואה בשם {st.session_state.user_name}. 
            להלן תשובותיו למבחן HEXACO (כולל זמן מענה לכל שאלה): {st.session_state.answers}.
            כתוב חוות דעת מקצועית בעברית על רמת האמינות שלו, יציבותו הרגשית והתאמתו למקצוע הרפואה.
            """
            
            resp = model.generate_content(prompt)
            st.markdown(resp.text)
            
            # שמירה ל-Firebase
            if st.session_state.fb_status:
                st.session_state.db.collection('results').add({
                    'user': st.session_state.user_name,
                    'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'analysis': resp.text,
                    'raw_answers': st.session_state.answers
                })
        except Exception as e:
            st.error(f"שגיאה בניתוח ה-AI: {e}")
            
    if st.button("חזרה לתפריט"):
        st.session_state.page = "home"; st.rerun()

# --- דף ארכיון ---
elif st.session_state.page == "archive":
    st.title(f"📂 ארכיון עבור: {st.session_state.user_name}")
    if st.session_state.fb_status:
        docs = list(st.session_state.db.collection('results').where('user', '==', st.session_state.user_name).stream())
        if docs:
            for doc in docs:
                data = doc.to_dict()
                with st.expander(f"מבחן מיום {data['date']}"):
                    st.write(data['analysis'])
        else:
            st.info("לא נמצאו מבחנים קודמים למשתמש זה.")
    else:
        st.error("הארכיון אינו מחובר ל-Firebase (יש להגדיר Secrets).")
        
    if st.button("חזרה לתפריט"):
        st.session_state.page = "home"; st.rerun()

# --- 7. פוטר קבוע ---
st.markdown('<div class="custom-footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
