import streamlit as st
import pandas as pd
from logic import DOCTOR_PROFILE, get_balanced_questions, calculate_results

# אתחול מצבי המערכת
if 'page' not in st.session_state: st.session_state.page = "home"
if 'answers' not in st.session_state: st.session_state.answers = []

st.set_page_config(page_title="Medical Personality Tracker", layout="wide")

# תפריט ניווט עליון (בשביל 5 המצבים)
with st.sidebar:
    st.title("ניווט")
    if st.button("🏠 בית"): st.session_state.page = "home"; st.rerun()
    if st.button("📜 ארכיון"): st.session_state.page = "archive"; st.rerun()
    if st.button("⚙️ הגדרות"): st.session_state.page = "settings"; st.rerun()

# --- מצב 1: דף בית ---
if st.session_state.page == "home":
    st.title("🏥 ברוכים הבאים למבחן אופי הרופא")
    name = st.text_input("שם המועמד:")
    
    st.subheader("בחר סוג שאלון:")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("בדיקה מהירה (36 שאלות)"):
            st.session_state.mode = 36
            start_quiz = True
    with col2:
        if st.button("סטנדרטי (120 שאלות)"):
            st.session_state.mode = 120
            start_quiz = True
    with col3:
        if st.button("מקיף (300 שאלות)"):
            st.session_state.mode = 300
            start_quiz = True

    if 'mode' in st.session_state and name:
        df = pd.read_csv("questions.csv")
        st.session_state.quiz_questions = get_balanced_questions(df, st.session_state.mode)
        st.session_state.current_idx = 0
        st.session_state.answers = []
        st.session_state.user_name = name
        st.session_state.page = "quiz"
        st.rerun()

# --- מצב 2: שאלון פעיל ---
elif st.session_state.page == "quiz":
    q_list = st.session_state.quiz_questions
    idx = st.session_state.current_idx
    
    st.progress((idx + 1) / len(q_list))
    st.write(f"### שאלה {idx + 1} מתוך {len(q_list)}")
    st.markdown(f"## {q_list[idx]['q']}")
    
    labels = ["כלל לא מסכים", "לא מסכים", "ניטרלי", "מסכים", "בהחלט מסכים"]
    cols = st.columns(5)
    for i, col in enumerate(cols):
        if col.button(labels[i], key=f"q_{idx}_{i}"):
            st.session_state.answers.append(i + 1)
            if idx + 1 < len(q_list):
                st.session_state.current_idx += 1
            else:
                st.session_state.page = "analysis"
            st.rerun()

# --- מצב 3: ניתוח תוצאות ---
elif st.session_state.page == "analysis":
    st.title(f"📊 ניתוח אופי: {st.session_state.user_name}")
    results = calculate_results(st.session_state.quiz_questions, st.session_state.answers)
    
    for trait, score in results.items():
        st.write(f"**{DOCTOR_PROFILE[trait]['label']}:** {score}")
        st.progress(score / 5.0)

# --- מצב 4: ארכיון ---
elif st.session_state.page == "archive":
    st.title("📜 היסטוריית מבחנים")
    st.info("כאן יוצגו נתונים מ-Firebase בעתיד.")

# --- מצב 5: הגדרות ---
elif st.session_state.page == "settings":
    st.title("⚙️ הגדרות מערכת")
    if st.button("נקה את כל הנתונים"):
        st.session_state.clear()
        st.rerun()
