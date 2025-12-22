import streamlit as st
import pandas as pd
import google.generativeai as genai
import random

# הגדרת Gemini
GEMINI_API_KEY = "AIzaSyDnYMJpJkNcXpOT8TgqPe6ymyvZxnWGCBo"
genai.configure(api_key=GEMINI_API_KEY)

# פונקציה לשליטה מהמקלדת (1-5)
def keyboard_handler():
    st.components.v1.html(
        """
        <script>
        const doc = window.parent.document;
        doc.addEventListener('keydown', function(e) {
            if (['1', '2', '3', '4', '5'].includes(e.key)) {
                const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText === e.key);
                if (btn) btn.click();
            }
        });
        </script>
        """,
        height=0,
    )

# פונקציה לטעינת שאלון מאוזן מקובץ CSV
def load_balanced_quiz(amount):
    try:
        df = pd.read_csv("questions.csv")
        traits = df['trait'].unique()
        questions_per_trait = amount // len(traits)
        
        final_quiz = []
        for trait in traits:
            trait_pool = df[df['trait'] == trait].to_dict('records')
            if len(trait_pool) >= questions_per_trait:
                selected = random.sample(trait_pool, questions_per_trait)
            else:
                selected = trait_pool # אם אין מספיק שאלות, קח את כולן
            final_quiz.extend(selected)
            
        random.shuffle(final_quiz)
        return final_quiz
    except Exception as e:
        st.error(f"שגיאה בטעינת הקובץ: {e}")
        return []

# הגדרות תצוגה
st.set_page_config(page_title="HEXACO Med-System", layout="centered", page_icon="🏥")

if 'page' not in st.session_state:
    st.session_state.page = "home"

# --- דף הבית ---
if st.session_state.page == "home":
    st.title("🏥 מערכת סימולציה למס״ר")
    st.subheader("בחר מסלול תרגול:")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 שאלון מלא (200)", use_container_width=True):
            st.session_state.questions = load_balanced_quiz(200)
            st.session_state.current_step = 0
            st.session_state.answers = []
            st.session_state.page = "quiz"
            st.rerun()
    with col2:
        if st.button("⏱️ מקבץ מהיר (36)", use_container_width=True):
            st.session_state.questions = load_balanced_quiz(36)
            st.session_state.current_step = 0
            st.session_state.answers = []
            st.session_state.page = "quiz"
            st.rerun()
            
    if st.button("📂 ארכיון תשובות והיסטוריה", use_container_width=True):
        st.session_state.page = "archive"
        st.rerun()

# --- דף השאלון ---
elif st.session_state.page == "quiz":
    keyboard_handler()
    questions = st.session_state.questions
    step = st.session_state.current_step
    
    if step < len(questions):
        current_q = questions[step]
        st.write(f"**שאלה {step + 1} מתוך {len(questions)}**")
        st.progress((step + 1) / len(questions))
        
        st.markdown(f"### {current_q['q']}")
        st.write("בחר מספר או הקש במקלדת:")
        
        cols = st.columns(5)
        for i, col in enumerate(cols, 1):
            with col:
                if st.button(f"{i}", key=f"q_{step}_{i}", use_container_width=True):
                    st.session_state.answers.append({"trait": current_q['trait'], "score": i})
                    st.session_state.current_step += 1
                    st.rerun()
    else:
        st.success("השאלון הושלם!")
        if st.button("קבל ניתוח AI"):
            st.session_state.page = "analysis"
            st.rerun()

# --- דף ניתוח ---
elif st.session_state.page == "analysis":
    st.title("🧐 ניתוח מעריך מס״ר")
    # כאן תבוא הפנייה ל-Gemini לניתוח התשובות
    st.info("הניתוח מתבצע על בסיס התשובות שלך...")
    if st.button("חזרה לתפריט"):
        st.session_state.page = "home"
        st.rerun()

# --- דף ארכיון ---
elif st.session_state.page == "archive":
    st.title("📂 ארכיון")
    st.write("היסטוריית השאלונים שלך תופיע כאן.")
    if st.button("חזרה לתפריט"):
        st.session_state.page = "home"
        st.rerun()
