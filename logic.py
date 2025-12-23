import time
import pandas as pd

def calculate_score(answer, direction):
    """הופך את הציון אם השאלה הפוכה"""
    if direction == -1:
        return 6 - answer  # הופך 5 ל-1, 4 ל-2 וכו'
    return answer

def analyze_consistency(answers_df):
    """
    בדיקת עקביות ראשונית: 
    מחפש שאלות מאותה תכונה עם תשובות קיצוניות הפוכות
    """
    # כאן נכניס לוגיקה שמשווה בין שאלות דומות בעתיד
    pass

def check_response_time(duration):
    """בדיקה אם זמן התגובה חשוד"""
    if duration < 1.5:
        return "מהיר מדי"
    if duration > 20:
        return "איטי מדי (השתהות)"
    return "תקין"

def process_results(user_responses):
    """
    מקבל רשימה של דיקשנריז עם:
    question_id, answer, time_taken, trait, direction
    """
    processed_data = []
    for resp in user_responses:
        final_score = calculate_score(resp['answer'], resp['direction'])
        time_status = check_response_time(resp['time_taken'])
        
        processed_data.append({
            'trait': resp['trait'],
            'score': final_score,
            'time_status': time_status,
            'duration': resp['time_taken']
        })
    
    return pd.DataFrame(processed_data)
