import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. אתחול Firebase בצורה מאובטחת ---
if not firebase_admin._apps:
    # משיכת הפרטים מה-Secrets של Streamlit
    fb_secrets = st.secrets["firebase"]
    cred = credentials.Certificate({
        "project_id": fb_secrets["project_id"],
        "private_key": fb_secrets["private_key"].replace('\\n', '\n'),
        "client_email": fb_secrets["client_email"],
        "token_uri": "https://oauth2.googleapis.com/token",
    })
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 2. הגדרת Gemini AI ---
GEMINI_API_KEY = "AIzaSyDnYMJpJkNcXpOT8TgqPe6ymyvZxnWGCBo"
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. פונקציית מקלדת (1-5) ---
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
    except Exception as e:
        st.error(f"שגיאה בטעינת הקובץ: {e}")
        return []

# הגדרות עמוד
st.set_page_config(page_title="מערכת סימולציות HEXACO", layout="centered")

if 'page' not in st.session_state:
    st.session_state.page = "home"
    st.session_state.user_name = ""

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
                st.rerun()
            else: st.warning("נא להזין שם משתמש")
            
    with col2:
        if st.button("⏱️ מקבץ מהיר (36)", use_container_width=True):
            if st.session_state.user_name:
                st.session_state.questions = load_quiz(36)
                st.session_state.current_step = 0
                st.session_state.answers = []
                st.session_state.page = "quiz"
                st.rerun()
            else: st.warning("נא להזין שם משתמש")

    if st.button("📂 ארכיון תשובות והיסטוריה", use_container_width=True):
        st.session_state.page = "archive"
        st.rerun()

    st.markdown("<br><br><p style='text-align: center; color: gray;'>© כל הזכויות שמורות לניתאי מלכה</p>", unsafe_allow_html=True)

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
                    st.session_state.answers.append({"trait": q[step]['trait'], "score": i})
                    st.session_state.current_step += 1
                    st.rerun()
    else:
        st.success("השאלון הושלם!")
        if st.button("קבל ניתוח AI ושמור בארכיון"):
            st.session_state.page = "analysis"
            st.rerun()

# --- דף ניתוח ---
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח AI")
    with st.spinner("מנתח נתונים..."):
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"נתח תוצאות HEXACO עבור המועמד {st.session_state.user_name}. תשובות: {st.session_state.answers}. כתוב המלצות למסר."
        resp = model.generate_content(prompt)
        
        # שמירה ל-Firebase
        db.collection('results').add({
            'user': st.session_state.user_name,
            'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
            'analysis': resp.text
        })
        st.markdown(resp.text)
        st.success("התוצאות נשמרו בארכיון!")

    if st.button("חזרה לתפריט"):
        st.session_state.page = "home"
        st.rerun()

# --- דף ארכיון ---
elif st.session_state.page == "archive":
    st.title("📂 ארכיון")
    if st.session_state.user_name:
        docs = db.collection('results').where('user', '==', st.session_state.user_name).stream()
        for doc in docs:
            d = doc.to_dict()
            with st.expander(f"שאלון מיום {d['date']}"):
                st.write(d['analysis'])
    else:
        st.warning("נא להזין שם משתמש בדף הבית כדי לראות ארכיון.")
    
    if st.button("חזרה לתפריט"):
        st.session_state.page = "home"
        st.rerun()
