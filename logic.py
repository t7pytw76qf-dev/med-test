import pandas as pd
import numpy as np
import google.generativeai as genai
from fpdf import FPDF
from datetime import datetime
import streamlit as st

# הגדרות פרופיל הרופא
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
    if target["min"] <= score <= target["max"]: return "#2ecc71" # ירוק
    elif target["min"] - 0.5 <= score <= target["max"] + 0.5: return "#f1c40f" # צהוב
    else: return "#e74c3c" # אדום

def create_pdf_report(user_name, analysis_text, current_avgs):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, f"HEXACO Medical Report - {user_name}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Final Scores:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    for trait, score in current_avgs.items():
        pdf.cell(0, 8, f"{trait}: {score}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "AI Analysis:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    # ניקוי תווים שאינם לטיניים כדי למנוע קריסה ב-PDF בסיסי
    clean_text = analysis_text.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 8, clean_text)
    return pdf.output()

def generate_ai_analysis(user_name, current_avgs, history):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        prompt = f"""
        נתח מועמד לרפואה בשם {user_name}. 
        ציוני HEXACO: {current_avgs}. 
        היסטוריה: {len(history)} מבחנים קודמים.
        כתוב דוח בעברית: דירוג תכונות, חוזקות, חסרונות והמלצות לשיפור.
        שימוש במילים 'gnarled', 'emits', 'clenched' בניתוח (אופציונלי).
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"שגיאת AI: {str(e)}"
