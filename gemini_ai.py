import google.generativeai as genai
import streamlit as st

def get_ai_analysis(results_summary):
    keys = [st.secrets["GEMINI_KEY_1"], st.secrets["GEMINI_KEY_2"]]
    
    prompt = f"""
    אתה מומחה לניתוח מבחני אישיות HEXACO לקבלה לרפואה.
    נתח את התוצאות הבאות וספק דוח הכולל:
    1. רמת התאמה לפרופיל רופא (ירוק/צהוב/אדום).
    2. ניתוח זמני תגובה (האם המשתמש אמין או ניסה לזייף).
    3. שאלות ספציפיות שחרגו מהטווח.
    
    הנתונים: {results_summary}
    ענה בעברית מקצועית ומעודדת.
    """

    for key in keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            continue # מנסה את המפתח הבא אם נכשל
    
    return "שגיאה: לא ניתן היה להתחבר ל-AI. אנא נסה שוב מאוחר יותר."
