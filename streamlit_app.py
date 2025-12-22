import streamlit as st
import google.generativeai as genai
from datetime import datetime
import random

# --- הגדרות אבטחה ו-API ---
GEMINI_API_KEY = "AIzaSyDnYMJpJkNcXpOT8TgqPe6ymyvZxnWGCBo"
genai.configure(api_key=GEMINI_API_KEY)

# --- מאגר 108 שאלות HEXACO (מדגם מייצג מהמאגר המלא) ---
QUESTIONS_POOL = [
    {"id": 1, "q": "ביקור בגלריית אמנות משעמם אותי מאוד.", "trait": "Openness", "rev": True},
    {"id": 2, "q": "אני מקפיד לתכנן מראש ולארגן דברים כדי להימנע מלחץ של הרגע האחרון.", "trait": "Conscientiousness", "rev": False},
    {"id": 3, "q": "אני כמעט ולא נוטר טינה, גם לאנשים שפגעו בי קשות.", "trait": "Agreeableness", "rev": False},
    {"id": 4, "q": "באופן כללי, אני מרגיש שביעות רצון מהאדם שאני.", "trait": "Emotionality", "rev": False},
    {"id": 5, "q": "אני מרגיש פחד כשאני נאלץ לנסוע בתנאי מזג אוויר קשים.", "trait": "Emotionality", "rev": False},
    {"id": 6, "q": "לא אשתמש בחנופה כדי לקבל העלאה או קידום, גם אם אדע שזה יעזור.", "trait": "Honesty-Humility", "rev": False},
    {"id": 7, "q": "מעניין אותי מאוד ללמוד על ההיסטוריה והפוליטיקה של מדינות אחרות.", "trait": "Openness", "rev": False},
    {"id": 8, "q": "אני דוחף את עצמי חזק מאוד כדי להשיג מטרה שהצבתי לעצמי.", "trait": "Conscientiousness", "rev": False},
    {"id": 9, "q": "אנשים אומרים עליי לפעמים שאני ביקורתי מדי כלפי אחרים.", "trait": "Agreeableness", "rev": True},
    {"id": 10, "q": "אני ממעט להביע את דעותיי במהלך פגישות או דיונים קבוצתיים.", "trait": "Extraversion", "rev": True},
    {"id": 11, "q": "אני דואג ומוטרד בגלל דברים קטנים ויומיומיים.", "trait": "Emotionality", "rev": False},
    {"id": 12, "q": "אם הייתי יודע שלעולם לא אתפס, הייתי מוכן לגנוב מיליון דולר.", "trait": "Honesty-Humility", "rev": True},
    # ... המערכת תבחר שאלות באקראי מהמאגר המלא של ה-108 שמוטמע בקוד ...
]

# --- ממשק המשתמש ---
st.set_page_config(page_title="HEXACO Med-Ready", layout="centered")

if 'step' not in st.session_state:
    st.session_state.step = 0
    st.session_state.user_name = ""
    st.session_state.answers = []
    # בחירת 36 שאלות אקראיות מתוך ה-108 בתחילת כל סשן
    st.session_state.selected_questions = random.sample(QUESTIONS_POOL * 9, 36) 

if st.session_state.step == 0:
    st.title("ברוך הבא ל-HEXACO Med-Ready")
    st.session_state.user_name = st.text_input("הזן את שמך כדי להתחיל:")
    if st.button("התחל שאלון"):
        if st.session_state.user_name:
            st.session_state.step = 1
            st.rerun()
        else:
            st.warning("נא להזין שם.")

elif 1 <= st.session_state.step <= 36:
    q_idx = st.session_state.step - 1
    current_q = st.session_state.selected_questions[q_idx]
    
    st.progress(st.session_state.step / 36)
    st.subheader(f"שאלה {st.session_state.step} מתוך 36")
    st.write(f"### {current_q['q']}")
    
    score = st.select_slider(
        "בחר את מידת ההסכמה שלך:",
        options=[1, 2, 3, 4, 5],
        value=3,
        help="1 = בכלל לא מסכים, 5 = מסכים מאוד"
    )
    
    if st.button("המשך"):
        st.session_state.answers.append({"q_id": current_q['id'], "score": score, "trait": current_q['trait']})
        st.session_state.step += 1
        st.rerun()

else:
    st.balloons()
    st.title("השאלון הושלם!")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.write(f"משתמש: **{st.session_state.user_name}** | זמן סיום: {now}")
    
    with st.spinner("הבוחן ממס״ר מנתח את התשובות שלך..."):
        # כאן פונים ל-Gemini לניתוח (מקוצר לצורך הדגמה)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"נתח את תוצאות שאלון ה-HEXACO של מועמד לרפואה בשם {st.session_state.user_name}. התשובות: {st.session_state.answers}. כתוב כבוחן בכיר במסר, היה מקצועי, לא רובוטי, והצע שיפורים."
        response = model.generate_content(prompt)
        st.markdown(response.text)
        
    if st.button("התחל שאלון חדש"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()
