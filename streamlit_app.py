import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. אתחול Firebase (Secrets) ---
if not firebase_admin._apps:
    try:
        fb_secrets = st.secrets["firebase"]
        cred = credentials.Certificate({
            "project_id": fb_secrets["project_id"],
            "private_key": fb_secrets["private_key"].replace('\\n', '\n'),
            "client_email": fb_secrets["client_email"],
            "token_uri": "https://oauth2.googleapis.com/token",
        })
        firebase_admin.initialize_app(cred)
    except:
        st.error("שגיאה בחיבור ל-Firebase. וודא שהגדרת Secrets.")

db = firestore.client()

# --- 2. הגדרת Gemini ---
GEMINI_API_KEY = "AIzaSyDnYMJpJkNcXpOT8TgqPe6ymyvZxnWGCBo"
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. פונקציית CSS לצביעת כפתורים ועיצוב ---
def local_css():
    st.markdown("""
        <style>
        div.stButton > button:active {
            background-color: #4CAF50 !important;
            color: white !important;
        }
        .footer {
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            background-color: white;
            color: gray;
            text-align: center;
            padding: 10px;
            font-size: 14px;
            border-top: 1px solid #e6e6e6;
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
        </script>
        """, height=0)

# --- 4. טעינת שאלות ---
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

# הגדרות עמוד
st.set_page_config(page_title="מערכת סימולציות HEXACO", layout="centered")
local_css()

if 'page' not in st.session_state:
    st.session_state.page = "home"
    st.session_state.user_name = ""
    st.session_state.start_time = None

# --- דף הבית ---
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
                st.session_state.page = "quiz"
                st.session_state.start_time = time.time()
                st.rerun()
            else: st.warning("נא להזין שם משתמש")
    with col2:
        if st.button("⏱️ מקבץ מהיר (36)", use_container_width=True):
            if st.session_state.user_name:
                st.session_state.questions = load_quiz(36)
                st.session_state.current_step = 0
                st.session_state.answers = []
                st.session_state.page = "quiz"
                st.session_state.start_time = time.time()
                st.rerun()
            else: st.warning("נא להזין שם משתמש")

    if st.button("📂 ארכיון תשובות והיסטוריה", use_container_width=True):
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
                    # חישוב זמן לתשובה
                    end_time = time.time()
                    time_taken = round(end_time - st.session_state.start_time, 2)
                    
                    st.session_state.answers.append({
                        "trait": q[step]['trait'], 
                        "score": i,
                        "time": time_taken
                    })
                    
                    # איפוס זמן לשאלה הבאה
                    st.session_state.start_time = time.time()
                    st.session_state.current_step += 1
                    time.sleep(0.1) # אפקט ויזואלי קטן
                    st.rerun()
    else:
        st.success("השאלון הושלם!")
        if st.button("קבל ניתוח אמינות ו-AI"):
            st.session_state.page = "analysis"
            st.rerun()

# --- דף ניתוח ---
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח מעריך AI ואמינות")
    with st.spinner("מנתח נתונים וזמני תגובה..."):
        # חישוב סטטיסטיקת זמן
        times = [a['time'] for a in st.session_state.answers]
        avg_time = sum(times) / len(times)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        נתח תוצאות HEXACO עבור מועמד לרפואה בשם {st.session_state.user_name}.
        תשובות: {st.session_state.answers}.
        זמן ממוצע לשאלה: {avg_time} שניות.
        דגשים לניתוח:
        1. האם זמני התגובה מעידים על אמינות (עקביות מול מהירות)?
        2. המלצות לשיפור לקראת מבחני מס"ר.
        """
        resp = model.generate_content(prompt)
        analysis_text = resp.text
        
        # שמירה ל-Firebase
        db.collection('results').add({
            'user': st.session_state.user_name,
            'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
            'avg_time': avg_time,
            'analysis': analysis_text
        })
        
        st.info(f"⏱️ זמן תגובה ממוצע: {avg_time:.2f} שניות לשאלה.")
        st.markdown(analysis_text)

    if st.button("חזרה לתפריט"):
        st.session_state.page = "home"
        st.rerun()

# --- דף ארכיון ---
elif st.session_state.page == "archive":
    st.title("📂 ארכיון")
    docs = db.collection('results').where('user', '==', st.session_state.user_name).stream()
    for doc in docs:
        d = doc.to_dict()
        with st.expander(f"שאלון מיום {d['date']} (זמן ממוצע: {d.get('avg_time', 0):.2f} ש')"):
            st.write(d['analysis'])
    
    if st.button("חזרה לתפריט"):
        st.session_state.page = "home"
        st.rerun()

# --- זכויות יוצרים (תמיד בתחתית) ---
st.markdown('<div class="footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
