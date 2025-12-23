import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import google.generativeai as genai
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os

# --- 1. הגדרות דמות הרופא (טווחים וצבעי רמזור) ---
DOCTOR_PROFILE = {
    "Honesty-Humility": {"min": 4.0, "max": 5.0, "label": "יושרה וצניעות"},
    "Emotionality": {"min": 2.2, "max": 3.8, "label": "יציבות רגשית"},
    "Extraversion": {"min": 3.0, "max": 5.0, "label": "מוחצנות חברתית"},
    "Agreeableness": {"min": 3.8, "max": 5.0, "label": "נעימות וסבלנות"},
    "Conscientiousness": {"min": 4.2, "max": 5.0, "label": "מצפוניות וסדר"},
    "Openness to Experience": {"min": 3.0, "max": 5.0, "label": "פתיחות ללמידה"}
}

def get_status_color(trait, score):
    target = DOCTOR_PROFILE[trait]
    if target["min"] <= score <= target["max"]:
        return "#2ecc71"  # ירוק
    elif target["min"] - 0.5 <= score <= target["max"] + 0.5:
        return "#f1c40f"  # צהוב
    else:
        return "#e74c3c"  # אדום

# --- 2. עיצוב CSS מתקדם (RTL + אפקטים לכפתורים) ---
st.set_page_config(page_title="HEXACO Medical Tracker", layout="wide")

st.markdown("""
    <style>
        .main .block-container { direction: rtl !important; text-align: right !important; }
        
        /* עיצוב כפתורי השאלון */
        div.stButton > button {
            width: 100% !important;
            height: 4.5em !important;
            font-size: 22px !important;
            font-weight: bold !important;
            border-radius: 12px !important;
            border: 2px solid #4A90E2 !important;
            background-color: white !important;
            color: #4A90E2 !important;
            transition: all 0.3s ease-in-out !important;
            margin-bottom: 10px !important;
        }

        /* Hover - מעבר עכבר */
        div.stButton > button:hover {
            background-color: #4A90E2 !important;
            color: white !important;
            box-shadow: 0 6px 12px rgba(74, 144, 226, 0.3) !important;
            transform: translateY(-2px);
        }

        /* Active/Focus - לחיצה */
        div.stButton > button:active, div.stButton > button:focus {
            background-color: #1a4373 !important;
            color: white !important;
            border-color: #1a4373 !important;
            transform: scale(0.95) !important;
        }

        /* עיצוב טבלאות */
        .stTable { direction: rtl !important; }
        
        /* כותרות */
        h1, h2, h3 { color: #1a4373; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. אתחול Firebase ---
if "firebase" in st.secrets and not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        fb_dict["private_key"] = fb_dict["private_key"].replace('\\n', '\n')
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
    except: pass
db = firestore.client() if firebase_admin._apps else None

# --- 4. פונקציות נתונים וגרפים ---
def get_history(user_name):
    if not db: return []
    try:
        docs = db.collection('results').where('user', '==', user_name).order_by('timestamp').stream()
        return [d.to_dict() for d in docs]
    except: return []

def plot_traffic_chart(current_avgs, history):
    traits = list(DOCTOR_PROFILE.keys())
    labels = [DOCTOR_PROFILE[t]['label'] for t in traits]
    scores = [current_avgs.get(t, 0) for t in traits]
    colors = [get_status_color(t, current_avgs.get(t, 0)) for t in traits]
    
    fig = go.Figure()
    # עמודות מבחן נוכחי
    fig.add_trace(go.Bar(name='נוכחי', x=labels, y=scores, marker_color=colors, text=scores, textposition='auto'))
    
    # נקודות ממוצע עבר
    if history:
        hist_scores = []
        for t in traits:
            vals = [h['averages'].get(t, 0) for h in history if 'averages' in h]
            hist_scores.append(round(np.mean(vals), 2) if vals else 0)
        fig.add_trace(go.Scatter(name='ממוצע עבר (X)', x=labels, y=hist_scores, mode='markers', marker=dict(color='black', size=14, symbol='x')))

    # קווי טווח יעד
    for i, t in enumerate(traits):
        fig.add_shape(type="line", x0=i-0.3, x1=i+0.3, y0=DOCTOR_PROFILE[t]["min"], y1=DOCTOR_PROFILE[t]["min"], line=dict(color="black", width=2, dash="dash"))
        fig.add_shape(type="line", x0=i-0.3, x1=i+0.3, y0=DOCTOR_PROFILE[t]["max"], y1=DOCTOR_PROFILE[t]["max"], line=dict(color="black", width=2, dash="dash"))

    fig.update_layout(title="ניתוח רמזור מול יעדי רפואה וממוצע עבר", yaxis=dict(range=[1, 5]), barmode='group', template="plotly_white")
    return fig

# --- 5. מנוע AI ---
def generate_ai_analysis(user_name, current_avgs, history, consistency_warnings):
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    hist_summary = f"למועמד יש {len(history)} מבחנים קודמים במאגר." if history else "זהו המבחן הראשון."
    prompt = f"""
    נתח מועמד לרפואה: {user_name}. 
    ציונים נוכחיים: {current_avgs}. 
    אזהרות עקביות: {consistency_warnings}.
    היסטוריה: {hist_summary}.

    כתוב דוח בעברית הכולל:
    1. דירוג התכונות מהחזקה לחלשה ביחס לרופא אידיאלי.
    2. ניתוח אמינות: האם התשובות עקביות או שיש חשד לזיוף?
    3. יתרונות וחסרונות: 3 חוזקות ו-3 נקודות תורפה לשיפור.
    4. ניתוח מגמה: האם יש שיפור לעומת מבחני עבר?
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "הניתוח אינו זמין כרגע - בדוק את חיבור ה-API."

# --- 6. ניהול דפים ---
if 'page' not in st.session_state: st.session_state.page = "home"

if st.session_state.page == "home":
    st.title("🏥 מערכת HEXACO למעקב ומיוני רפואה")
    st.write("ברוך הבא למערכת הניתוח המצטברת. הזן את שמך כדי להתחיל או לראות התקדמות.")
    st.session_state.user_name = st.text_input("שם מלא (לזיהוי במערכת):")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 התחל שאלון מלא"):
            if st.session_state.user_name:
                df = pd.read_csv("questions.csv")
                st.session_state.questions = df.to_dict('records')
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
    with col2:
        if st.button("📂 צפה בהיסטוריית מבחנים"):
            if st.session_state.user_name: st.session_state.page = "analysis"; st.rerun()

elif st.session_state.page == "quiz":
    q, idx = st.session_state.questions, st.session_state.current_step
    if idx < len(q):
        st.subheader(f"שאלה {idx + 1} מתוך {len(q)}")
        st.progress((idx + 1) / len(q))
        st.markdown(f"### {q[idx]['q']}")
        
        cols = st.columns(5)
        for val, col in enumerate(cols, 1):
            if col.button(str(val), key=f"q{idx}_{val}"):
                st.session_state.answers.append({
                    "trait": q[idx]['trait'], 
                    "score": val, 
                    "time": round(time.time() - st.session_state.start_time, 2)
                })
                st.session_state.current_step += 1
                st.session_state.start_time = time.time()
                st.rerun()
    else:
        st.success("השאלון הסתיים בהצלחה!")
        if st.button("🚀 הפק דוח רמזור וניתוח מגמות"):
            st.session_state.page = "analysis"; st.rerun()

elif st.session_state.page == "analysis":
    st.title(f"📊 דוח ביצועים ומגמות: {st.session_state.user_name}")
    
    if 'final_analysis' not in st.session_state:
        with st.spinner("שואב נתונים היסטוריים ומנתח עקביות..."):
            # חישוב ממוצעים נוכחיים (אם יש תשובות חדשות)
            if 'answers' in st.session_state and st.session_state.answers:
                trait_scores = {}
                consistency_warnings = []
                for a in st.session_state.answers:
                    t = a['trait']
                    if t not in trait_scores: trait_scores[t] = []
                    trait_scores[t].append(a['score'])
                
                # בדיקת עקביות (סטיית תקן)
                for t, scores in trait_scores.items():
                    if len(scores) > 1 and np.std(scores) > 1.4:
                        consistency_warnings.append(DOCTOR_PROFILE[t]['label'])

                st.session_state.current_avgs = {k: round(np.mean(v), 2) for k, v in trait_scores.items()}
                st.session_state.warnings = consistency_warnings
                
                if db:
                    db.collection('results').add({
                        'user': st.session_state.user_name,
                        'averages': st.session_state.current_avgs,
                        'timestamp': datetime.now()
                    })
            
            # שליפת היסטוריה
            st.session_state.history = get_history(st.session_state.user_name)
            # ניתוח AI
            st.session_state.final_analysis = generate_ai_analysis(
                st.session_state.user_name, 
                st.session_state.current_avgs, 
                st.session_state.history,
                st.session_state.get('warnings', [])
            )

    # 1. טבלת דירוג רמזור
    st.subheader("📌 סטטוס נוכחי ודירוג")
    rank_data = []
    for t, s in st.session_state.current_avgs.items():
        color = get_status_color(t, s)
        emoji = "✅" if color == "#2ecc71" else ("⚠️" if color == "#f1c40f" else "❌")
        rank_data.append({
            "תכונה": DOCTOR_PROFILE[t]['label'], 
            "ציון": s, 
            "טווח יעד": f"{DOCTOR_PROFILE[t]['min']}-{DOCTOR_PROFILE[t]['max']}", 
            "סטטוס": emoji
        })
    st.table(pd.DataFrame(rank_data).sort_values("ציון", ascending=False))

    # 2. גרף רמזור + היסטוריה
    st.plotly_chart(plot_traffic_chart(st.session_state.current_avgs, st.session_state.history), use_container_width=True)

    # 3. ניתוח AI
    st.markdown("---")
    st.subheader("💡 ניתוח AI, חוזקות ותכנית שיפור")
    st.write(st.session_state.final_analysis)

    # 4. טיפים לשיפור
    with st.expander("🛠️ טיפים קליניים לשיפור הציון"):
        st.info("**יושרה:** הימנע מקיצוניות בשאלות על כבוד או ממון. מחפשים רופא צנוע אך יציב.")
        st.info("**נעימות:** במיון מחפשים 'Team Player'. אם הציון נמוך, בדוק אם ענית בקיצוניות על שאלות של עמידה על עקרונות.")
        st.info("**מצפוניות:** זו התכונה הכי חשובה לבטיחות המטופל. אם הציון נמוך, עליך להראות יותר דייקנות בפרטים.")

    if st.button("🏠 חזרה למסך הבית"):
        for key in ['final_analysis', 'current_avgs', 'history', 'warnings', 'answers']:
            if key in st.session_state: del st.session_state[key]
        st.session_state.page = "home"; st.rerun()

st.markdown('<div style="text-align:center; padding:20px; color:gray;">© כל הזכויות שמורות לניתאי מלכה - מערכת הכנה למיוני רפואה 2025</div>', unsafe_allow_html=True)
