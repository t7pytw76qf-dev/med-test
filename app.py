import streamlit as st
import time
import pandas as pd
from logic import calculate_score, check_response_time
from gemini_ai import get_ai_analysis

# הגדרות דף ו-RTL
st.set_page_config(page_title="HEXACO Medical Prep", layout="wide")

# עיצוב CSS לאפקט Hover כחול אחיד
st.markdown("""
    <style>
    .stApp { text-align: right; direction: rtl; }
    div.stButton > button {
        width: 100%; border-radius: 12px; border: 1px solid #d1d8e0;
        height: 60px; font-size: 18px; transition: all 0.2s;
    }
    div.stButton > button:hover {
        border-color: #2e86de; background-color: #f0f7ff; color: #2e86de;
    }
    .question-text { font-size: 30px; font-weight: bold; text-align: center; padding: 40px; }
    </style>
    """, unsafe_allow_html=True)

# אתחול משתני מערכת (Session State)
if 'step' not in st.session_state: st.session_state.step = 'HOME'
if 'responses' not in st.session_state: st.session_state.responses = []
if 'current_q' not in st.session_state: st.session_state.current_q = 0
if 'start_time' not in st.session_state: st.session_state.start_time = time.time()

# --- פונקציית מעבר שאלה ---
def record_answer(ans_value, q_data):
    end_time = time.time()
    duration = end_time - st.session_state.start_time
    
    # שמירת נתוני התשובה כולל זמן
    st.session_state.responses.append({
        'question': q_data['question_text'],
        'trait': q_data['trait'],
        'answer': ans_value,
        'direction': q_data['direction'],
        'time_taken': duration
    })
    
    # מעבר לשאלה הבאה או סיום
    st.session_state.current_q += 1
    st.session_state.start_time = time.time() # איפוס טיימר לשאלה הבאה

# --- מסך בית ---
if st.session_state.step == 'HOME':
    st.title("🏥 מערכת סימולציה HEXACO לרפואה")
    st.write("ברוך הבא לסימולטור ההכנה. בחר מסלול כדי להתחיל בתרגול:")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⏳ תרגול מהיר (36)"): 
            st.session_state.limit = 36
            st.session_state.step = 'QUIZ'
            st.rerun()
    # הערה: כרגע נשתמש ברשימה זמנית עד שתעלה את ה-CSV המלא
    dummy_questions = [
        {"question_text": "אני תמיד משתדל להיות ישר עם אחרים", "trait": "Honesty", "direction": 1},
        {"question_text": "אני נלחץ בקלות במצבי חירום", "trait": "Emotionality", "direction": 1},
        {"question_text": "אני נהנה לפתור בעיות מורכבות", "trait": "Openness", "direction": 1}
    ]
    st.session_state.questions = dummy_questions

# --- מסך שאלון פעיל ---
elif st.session_state.step == 'QUIZ':
    q_idx = st.session_state.current_q
    
    if q_idx < len(st.session_state.questions):
        q_data = st.session_state.questions[q_idx]
        
        # הצגת השאלה
        st.markdown(f'<p class="question-text">{q_data["question_text"]}</p>', unsafe_allow_html=True)
        
        # סולם ליקרט
        cols = st.columns(5)
        labels = ["בכלל לא מסכים", "לא מסכים", "נייטרלי", "מסכים", "מסכים מאוד"]
        for i, label in enumerate(labels):
            if cols[i].button(label):
                record_answer(i+1, q_data)
                st.rerun()
    else:
        st.session_state.step = 'RESULTS'
        st.rerun()

# --- מסך תוצאות וניתוח AI ---
elif st.session_state.step == 'RESULTS':
    st.title("📊 ניתוח סימולציה ודוח אמינות")
    
    # יצירת טבלה לעיבוד
    df = pd.DataFrame(st.session_state.responses)
    
    # הצגת ניתוח זמנים בסיסי
    st.subheader("בדיקת אמינות (זמני תגובה)")
    for index, row in df.iterrows():
        status = check_response_time(row['time_taken'])
        if status != "תקין":
            st.warning(f"שאלה {index+1}: {status} ({row['time_taken']:.2f} שניות)")

    # הפעלת AI
    if st.button("צור ניתוח AI מעמיק עם Gemini"):
        with st.spinner("ה-AI מנתח את הפרופיל שלך..."):
            summary = df[['trait', 'answer', 'time_taken']].to_string()
            analysis = get_ai_analysis(summary)
            st.markdown("### חוות דעת מומחה:")
            st.write(analysis)
