import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. אתחול Firebase בטוח ---
# יצירת משתנה db ריק כברירת מחדל
if 'db' not in st.session_state:
    st.session_state.db = None
    st.session_state.fb_status = False

if not firebase_admin._apps:
    try:
        # ניסיון משיכת Secrets
        if "firebase" in st.secrets:
            fb_dict = dict(st.secrets["firebase"])
            fb_dict["private_key"] = fb_dict["private_key"].replace('\\n', '\n')
            cred = credentials.Certificate(fb_dict)
            firebase_admin.initialize_app(cred)
            st.session_state.db = firestore.client()
            st.session_state.fb_status = True
        else:
            st.warning("המערכת פועלת ללא חיבור לארכיון (Secrets חסרים).")
    except Exception as e:
        st.error(f"שגיאה באתחול Firebase: {e}")

# הגדרת משתנה db לעבודה נוחה
db = st.session_state.db

# --- 2. הגדרת Gemini ---
GEMINI_API_KEY = "AIzaSyDnYMJpJkNcXpOT8TgqPe6ymyvZxnWGCBo"
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. עיצוב וזכויות יוצרים ---
st.markdown("""
    <style>
    div.stButton > button:active { background-color: #4CAF50 !important; color: white !important; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f9f9f9; color: #555; 
              text-align: center; padding: 10px; font-size: 14px; border-top: 1px solid #ddd; z-index: 100; }
    </style>
    <div class="footer">© כל הזכויות שמורות לניתאי מלכה</div>
""", unsafe_allow_html=True)

def keyboard_handler():
    st.components.v1.html("""
        <script>
        const doc = window.parent.document;
        doc.addEventListener('keydown', function(e) {
            if (['1', '2', '3', '4', '5'].includes(e.key)) {
                const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText === e.key);
                if (btn) btn.click();
            }
        });
        </script>""", height=0)

# --- 4. פונקציות עזר ---
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
        return []

if 'page' not in st.session_state:
    st.session_state.page = "home"
    st.session_state.user_name = ""

# --- דף הבית ---
if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    st.session_state.user_name = st.text_input("הזן שם משתמש:", st.session_state.user_name)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 שאלון מלא (200)", use_container_width=True):
            if st.session_state.user_name:
                st.session_state.questions = load_quiz(200)
                st.session_state.current_step = 0
                st.session_state.answers = []
                st.session_state.start_time = time.time()
                st.session_state.page = "quiz"
                st.rerun()
            else: st.warning("נא להזין שם משתמש")
    with col2:
        if st.button("⏱️ מקבץ מהיר (36)", use_container_width=True):
            if st.session_state.user_name:
                st.session_state.questions = load_quiz(36)
                st.session_state.current_step = 0
                st.session_state.answers = []
                st.session_state.start_time = time.time()
                st.session_state.page = "quiz"
                st.rerun()
            else: st.warning("נא להזין שם משתמש")
    
    if st.button("📂 ארכיון תשובות", use_container_width=True):
        st.session_state.page = "archive"
        st.rerun()

# --- דף השאלון ---
elif st.session_state.page == "quiz":
    keyboard_handler()
    q = st.session_state.questions
    step = st.session_state.current_step
    
    if step < len(q):
        st.write(f"**שאלה {step + 1} מתוך {len(q)}**")
        st.progress((step + 1) / len(q))
        st.markdown(f"### {q[step]['q']}")
        
        cols = st.columns(5)
        for i, col in enumerate(cols, 1):
            with col:
                if st.button(f"{i}", key=f"btn_{step}_{i}", use_container_width=True):
                    elapsed = round(time.time() - st.session_state.start_time, 2)
                    st.session_state.answers.append({"trait": q[step]['trait'], "score": i, "time": elapsed})
                    st.session_state.current_step += 1
                    st.session_state.start_time = time.time()
                    st.rerun()
    else:
        st.success("השאלון הושלם!")
        if st.button("קבל ניתוח אמינות ו-AI"):
            st.session_state.page = "analysis"
            st.rerun()

# --- דף ניתוח ---
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח אמינות ואישיות")
    with st.spinner("ה-AI מנתח את התשובות..."):
        times = [a['time'] for a in st.session_state.answers]
        avg_time = sum(times) / len(times)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"נתח מועמד לרפואה: {st.session_state.user_name}. תשובות: {st.session_state.answers}. זמן ממוצע: {avg_time} ש'. התייחס לאמינות המענה."
        resp = model.generate_content(prompt)
        
        # שמירה רק אם החיבור הצליח
        if st.session_state.fb_status and db:
            db.collection('results').add({
                'user': st.session_state.user_name, 'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'avg_time': avg_time, 'analysis': resp.text
            })
            st.success("התוצאות נשמרו בארכיון!")
        
        st.info(f"⏱️ זמן תגובה ממוצע: {avg_time:.2f} שניות לשאלה.")
        st.markdown(resp.text)
    
    if st.button("חזרה לתפריט"):
        st.session_state.page = "home"
        st.rerun()

# --- דף ארכיון ---
elif st.session_state.page == "archive":
    st.title("📂 ארכיון אישי")
    if st.session_state.fb_status and db:
        docs = db.collection('results').where('user', '==', st.session_state.user_name).stream()
        for doc in docs:
            d = doc.to_dict()
            with st.expander(f"שאלון מיום {d['date']}"):
                st.write(d['analysis'])
    else:
        st.error("הארכיון לא זמין - וודא שהגדרת Secrets כראוי ב-Streamlit Cloud.")
    
    if st.button("חזרה לתפריט"):
        st.session_state.page = "home"
        st.rerun()
