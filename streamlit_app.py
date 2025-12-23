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

# --- 2. עיצוב CSS מתקדם (RTL + אפקטים) ---
st.set_page_config(page_title="HEXACO Medical Tracker", layout="wide")

st.markdown("""
    <style>
        .main .block-container { direction: rtl !important; text-align: right !important; }
        
        div.stButton > button {
            width: 100% !important;
            height: 4em !important;
            font-size: 20px !important;
            font-weight: bold !important;
            border-radius: 12px !important;
            border: 2px solid #4A90E2 !important;
            background-color: white !important;
            color: #4A90E2 !important;
            transition: all 0.3s ease-in-out !important;
        }

        div.stButton > button:hover {
            background-color: #4A90E2 !important;
            color: white !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }

        div.stButton > button:active {
            transform: scale(0.95);
            background-color: #1a4373 !important;
        }

        .stProgress > div > div > div > div { background-color: #4A90E2; }
        .stTable { direction: rtl !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. אתחול Firebase ---
if "firebase" in st.secrets and not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        fb_dict["private_key"] = fb_dict["private_key"].replace('\\n', '\n')
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"שגיאת חיבור ל-Firebase: {e}")

db = firestore.client() if firebase_admin._apps else None

# --- 4. פונקציות נתונים ---
def get_history(user_name):
    if not db: return []
    try:
        docs = db.collection('results').where('user', '==', user_name).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
        return [d.to_dict() for d in docs]
    except: return []

def plot_traffic_chart(current_avgs, history):
    traits = list(DOCTOR_PROFILE.keys())
    labels = [DOCTOR_PROFILE[t]['label'] for t in traits]
    scores = [current_avgs.get(t, 0) for t in traits]
    colors = [get_status_color(t, current_avgs.get(t, 0)) for t in traits]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='נוכחי', x=labels, y=scores, marker_color=colors, text=scores, textposition='auto'))
    
    if history:
        hist_avgs = []
        for t in traits:
            vals = [h['averages'].get(t, 0) for h in history if 'averages' in h]
            hist_avgs.append(round(np.mean(vals), 2) if vals else 0)
        fig.add_trace(go.Scatter(name='ממוצע עבר (X)', x=labels, y=hist_avgs, mode='markers', marker=dict(color='black', size=12, symbol='x')))

    for i, t in enumerate(traits):
        fig.add_shape(type="line", x0=i-0.3, x1=i+0.3, y0=DOCTOR_PROFILE[t]["min"], y1=DOCTOR_PROFILE[t]["min"], line=dict(color="black", width=1, dash="dot"))
        fig.add_shape(type="line", x0=i-0.3, x1=i+0.3, y0=DOCTOR_PROFILE[t]["max"], y1=DOCTOR_PROFILE[t]["max"], line=dict(color="black", width=1, dash="dot"))

    fig.update_layout(title="ניתוח רמזור מול יעדי רפואה", yaxis=dict(range=[1, 5]), template="plotly_white", barmode='group')
    return fig

# --- 5. מנוע AI (מתוקן למניעת שגיאות מכסה) ---
def generate_ai_analysis(user_name, current_avgs, history, consistency_warnings):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return "חסר מפתח API ב-Secrets."
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    
    hist_text = f"למועמד {len(history)} מבחנים קודמים." if history else "זהו המבחן הראשון."
    prompt = f"""
    ניתוח מועמד לרפואה: {user_name}. ציונים: {current_avgs}. אזהרות: {consistency_warnings}. {hist_text}
    כתוב בעברית:
    1. דירוג התכונות (חזק עד חלש).
    2. ניתוח אמינות (עקביות התשובות).
    3. 3 יתרונות ו-3 חסרונות לשיפור.
    4. השוואת מגמה לעומת עבר.
    """
    try:
        response = model.generate_content(prompt)
        return response.text if response else "לא התקבלה תשובה מה-AI."
    except Exception as e:
        return f"שגיאת AI (ייתכן עומס): {str(e)}"

# --- 6. ניהול דפים ---
if 'page' not in st.session_state: st.session_state.page = "home"

if st.session_state.page == "home":
    st.title("🏥 HEXACO Medical Tracker")
    st.write("מערכת ניתוח מבוססת AI למיוני רפואה (מו\"ר / מרקם)")
    st.session_state.user_name = st.text_input("שם מלא לזיהוי:")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 התחל שאלון"):
            if st.session_state.user_name:
                df = pd.read_csv("questions.csv")
                st.session_state.questions = df.to_dict('records')
                st.session_state.current_step = 0; st.session_state.answers = []
                st.session_state.start_time = time.time(); st.session_state.page = "quiz"; st.rerun()
    with col2:
        if st.button("📂 היסטוריית ציונים"):
            if st.session_state.user_name: st.session_state.page = "analysis"; st.rerun()

elif st.session_state.page == "quiz":
    q, idx = st.session_state.questions, st.session_state.current_step
    if idx < len(q):
        st.progress((idx + 1) / len(q))
        st.subheader(f"שאלה {idx + 1}: {q[idx]['q']}")
        cols = st.columns(5)
        for val, col in enumerate(cols, 1):
            if col.button(str(val), key=f"btn_{idx}_{val}"):
                st.session_state.answers.append({
                    "trait": q[idx]['trait'], "score": val, 
                    "time": round(time.time() - st.session_state.start_time, 2)
                })
                st.session_state.current_step += 1; st.session_state.start_time = time.time(); st.rerun()
    else:
        st.success("השאלון הושלם!")
        if st.button("🚀 הפק דוח סופי"): st.session_state.page = "analysis"; st.rerun()

elif st.session_state.page == "analysis":
    st.title(f"📊 ניתוח עבור: {st.session_state.user_name}")
    
    if 'current_avgs' not in st.session_state:
        with st.spinner("מנתח נתונים..."):
            if 'answers' in st.session_state and st.session_state.answers:
                trait_scores = {}
                warnings = []
                for a in st.session_state.answers:
                    t = a['trait']
                    if t not in trait_scores: trait_scores[t] = []
                    trait_scores[t].append(a['score'])
                
                avgs = {k: round(np.mean(v), 2) for k, v in trait_scores.items()}
                for t, scores in trait_scores.items():
                    if len(scores) > 1 and np.std(scores) > 1.4: warnings.append(DOCTOR_PROFILE[t]['label'])
                
                st.session_state.current_avgs = avgs
                st.session_state.warnings = warnings
                
                if db:
                    db.collection('results').add({
                        'user': st.session_state.user_name, 'averages': avgs, 'timestamp': datetime.now()
                    })
            
            st.session_state.history = get_history(st.session_state.user_name)
            st.session_state.final_analysis = generate_ai_analysis(
                st.session_state.user_name, st.session_state.current_avgs, 
                st.session_state.history, st.session_state.get('warnings', [])
            )

    # הצגת טבלה
    rank_data = []
    for t, s in st.session_state.current_avgs.items():
        color = get_status_color(t, s)
        emoji = "✅" if color == "#2ecc71" else ("⚠️" if color == "#f1c40f" else "❌")
        rank_data.append({"תכונה": DOCTOR_PROFILE[t]['label'], "ציון": s, "סטטוס": emoji})
    st.table(pd.DataFrame(rank_data).sort_values("ציון", ascending=False))

    # גרף
    st.plotly_chart(plot_traffic_chart(st.session_state.current_avgs, st.session_state.history), use_container_width=True)

    # AI
    st.markdown("### 💡 ניתוח עומק והמלצות")
    st.write(st.session_state.final_analysis)

    if st.button("🏠 חזרה"):
        for k in ['final_analysis', 'current_avgs', 'answers']: 
            if k in st.session_state: del st.session_state[k]
        st.session_state.page = "home"; st.rerun()

st.markdown('<div style="text-align:center; padding:30px; color:gray;">© ניתאי מלכה - הכנה לרפואה 2025</div>', unsafe_allow_html=True)
