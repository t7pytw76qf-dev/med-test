import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. הגדרת Gemini (מפתח וחיפוש מודל) ---
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

# --- 3. עיצוב CSS (ניקוי סמלים, RTL ומרכוז פוטר) ---
st.markdown("""
    <style>
    /* הסתרת אלמנטים של Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    
    /* הגדרת RTL ויישור לימין */
    .main .block-container { direction: rtl; text-align: right; }
    
    /* עיצוב שורת זכויות יוצרים ממורכזת */
    .custom-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #f8f9fa; color: #333; text-align: center;
        padding: 10px; font-weight: bold; font-size: 14px;
        border-top: 2px solid #007bff; z-index: 1000;
        direction: ltr; 
    }
    .main-content { margin-bottom: 80px; }
    h1, h2, h3, p, span { text-align: right; }
    </style>
""", unsafe_allow_html=True)

# --- פונקציות עזר ---
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

st.markdown('<div class="main-content">', unsafe_allow_html=True)

# --- דף הבית ---
if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציות HEXACO")
    st.session_state.user_name = st.text_input("הזן שם משתמש:", st.session_state.user_name)
    
    st.subheader("בחר מסלול תרגול:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 שאלון מלא (200)", use_container_width=True):
            if st.session_state.user_name:
                st.session_state.questions = load_quiz(200); st.session_state.current_step = 0
                st.session_state.answers = []; st.session_state.start_time = time.time()
                st.session_state.page = "quiz"; st.rerun()
            else: st.warning("נא להזין שם משתמש")
    with col2:
        if st.button("⏱️ מקבץ מהיר (36)", use_container_width=True):
            if st.session_state.user_name:
                st.session_state.questions = load_quiz(36); st.session_state.current_step = 0
                st.session_state.answers = []; st.session_state.start_time = time.time()
                st.session_state.page = "quiz"; st.rerun()
            else: st.warning("נא להזין שם משתמש")
    
    if st.button("📂 ארכיון וחוות דעת מצטברת", use_container_width=True):
        if st.session_state.user_name:
            st.session_state.page = "archive"; st.rerun()

# --- דף השאלון ---
elif st.session_state.page == "quiz":
    q = st.session_state.questions; step = st.session_state.current_step
    if step < len(q):
        st.write(f"**שאלה {step + 1} מתוך {len(q)}**")
        st.progress((step + 1) / len(q))
        st.markdown(f"### {q[step]['q']}")
        cols = st.columns(5)
        for i, col in enumerate(cols, 1):
            if col.button(str(i), key=f"b{step}{i}", use_container_width=True):
                elapsed = round(time.time() - st.session_state.start_time, 2)
                st.session_state.answers.append({"trait": q[step]['trait'], "score": i, "time": elapsed})
                st.session_state.current_step += 1; st.session_state.start_time = time.time(); st.rerun()
    else:
        st.success("השאלון הושלם!")
        if st.button("נתח תוצאות ושלח ל-AI", use_container_width=True):
            st.session_state.page = "analysis"; st.rerun()

# --- דף ניתוח יחיד ---
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח אמינות ואישיות")
    with st.spinner("ה-AI מנתח את התוצאות..."):
        try:
            model_name = get_working_model()
            model = genai.GenerativeModel(model_name)
            prompt = f"נתח מועמד לרפואה בשם {st.session_state.user_name}. תשובות: {st.session_state.answers}. תן חוות דעת בעברית על אמינות ואישיות HEXACO."
            resp = model.generate_content(prompt)
            st.markdown(resp.text)
            
            if st.session_state.fb_status and db:
                db.collection('results').add({
                    'user': st.session_state.user_name, 'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'analysis': resp.text
                })
        except Exception as e:
            st.error(f"שגיאה בניתוח: {e}")
    if st.button("חזרה לתפריט", use_container_width=True):
        st.session_state.page = "home"; st.rerun()

# --- דף ארכיון וחוות דעת מצטברת ---
elif st.session_state.page == "archive":
    st.title(f"📂 היסטוריה עבור: {st.session_state.user_name}")
    if st.session_state.fb_status and db:
        docs = list(db.collection('results').where('user', '==', st.session_state.user_name).stream())
        if docs:
            if st.button("גבש חוות דעת AI מצטברת", use_container_width=True):
                with st.spinner("מנתח מגמות..."):
                    history = "\n".join([f"תאריך: {d.to_dict()['date']}, ניתוח: {d.to_dict()['analysis']}" for d in docs])
                    model = genai.GenerativeModel(get_working_model())
                    agg_prompt = f"להלן היסטוריית המבחנים של {st.session_state.user_name}. כתוב חוות דעת בעברית על מגמות ושיפורים:\n\n{history}"
                    agg_resp = model.generate_content(agg_prompt)
                    st.info(agg_resp.text)

            st.subheader("📜 מבחנים קודמים")
            for doc in docs:
                d = doc.to_dict()
                with st.expander(f"מבחן מיום {d['date']}"):
                    st.write(d['analysis'])
        else: st.info("לא נמצאו נתונים קודמים.")
    else: st.error("הארכיון דורש הגדרת Secrets.")
    if st.button("חזרה", use_container_width=True):
        st.session_state.page = "home"; st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="custom-footer">© כל הזכויות שמורות לניתאי מלכה</div>', unsafe_allow_html=True)
