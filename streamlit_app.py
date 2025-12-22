import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. אתחול Firebase ---
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
        st.info("מערכת הארכיון תופעל לאחר הגדרת Secrets.")

db = st.session_state.db

# --- 2. הגדרת Gemini ---
GEMINI_API_KEY = "AIzaSyDnYMJpJkNcXpOT8TgqPe6ymyvZxnWGCBo"
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. עיצוב (CSS) - RTL לתוכן ומרכוז לזכויות יוצרים ---
st.markdown("""
    <style>
    /* הגדרת כיווניות לימין עבור כל האפליקציה */
    .main .block-container {
        direction: rtl;
        text-align: right;
    }
    
    /* צביעת כפתור בבחירה */
    div.stButton > button:active {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    
    /* קיבוע זכויות יוצרים לתחתית ומירכוז הטקסט */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f8f9fa;
        color: #333;
        text-align: center; /* שמירה על הטקסט באמצע */
        padding: 10px;
        font-weight: bold;
        font-size: 14px;
        border-top: 2px solid #007bff;
        z-index: 1000;
        direction: ltr; /* מבטיח שהמירכוז יעבוד נכון ללא קשר ל-RTL הכללי */
    }
    .main-content { margin-bottom: 80px; }
    
    h1, h2, h3, p, span {
        text-align: right;
    }
    </style>
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

# --- תוכן הדף ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)

if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    st.session_state.user_name = st.text_input("הזן שם משתמש:", st.session_state.user_name)
    
    st.subheader("בחר מסלול תרגול:")
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
            if col.button(str(i), key=f"b{step}{i}", use_container_width=True):
                elapsed = round(time.time() - st.session_state.start_time, 2)
                st.session_state.answers.append({"trait": q[step]['trait'], "score": i, "time": elapsed})
                st.session_state.current_step += 1
                st.session_state.start_time = time.time()
                st.rerun()
    else:
        st.success("השאלון הושלם!")
        if st.button("קבל ניתוח אמינות ו-AI", use_container_width=True):
            st.session_state.page = "analysis"
            st.rerun()

elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח אמינות ואישיות")
    with st.spinner("מנתח נתונים..."):
        times = [a['time'] for a in st.session_state.answers]
        avg_time = sum(times) / len(times)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"נתח מועמד לרפואה: {st.session_state.user_name}. תשובות: {st.session_state.answers}. זמן ממוצע: {avg_time} ש'. התייחס לאמינות המענה ונתח לפי מודל HEXACO בעברית."
        resp = model.generate_content(prompt)
        
        st.info(f"⏱️ זמן תגובה ממוצע: {avg_time:.2f} שניות לשאלה.")
        st.markdown(resp.text)
        
        if st.session_state.fb_status and db:
            db.collection('results').add({
                'user': st.session_state.user_name, 'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'analysis': resp.text, 'avg_time': avg_time
            })

    if st.button("חזרה לתפריט", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()

elif st.session_state.page == "archive":
    st.title("📂 ארכיון אישי")
    if st.session_state.fb_status and db:
        docs = db.collection('results').where('user', '==', st.session_state.user_name).stream()
        for doc in docs:
            d = doc.to_dict()
            with st.expander(f"שאלון מיום {d['date']} (זמן ממוצע: {d.get('avg_time', 0):.2f} ש')"):
                st.write(d['analysis'])
    else:
        st.error("הארכיון לא זמין.")
    if st.button("חזרה לתפריט", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
