import pandas as pd
import numpy as np
import random
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

def get_balanced_questions(df, num_to_select):
    """בוחר מספר שווה של שאלות מכל תכונה מתוך המאגר"""
    traits = df['trait'].unique()
    questions_per_trait = num_to_select // len(traits)
    selected_questions = []
    
    for trait in traits:
        trait_pool = df[df['trait'] == trait].to_dict('records')
        if len(trait_pool) >= questions_per_trait:
            selected_questions.extend(random.sample(trait_pool, questions_per_trait))
        else:
            selected_questions.extend(trait_pool) # אם אין מספיק, לוקח הכל
            
    random.shuffle(selected_questions)
    return selected_questions

def calculate_results(questions, answers):
    """מחשב ציונים כולל שאלות הפוכות"""
    trait_scores = {t: [] for t in DOCTOR_PROFILE.keys()}
    
    for i, ans in enumerate(answers):
        q_data = questions[i]
        trait = q_data['trait']
        score = int(ans)
        
        # לוגיקת היפוך
        is_rev = str(q_data.get('reverse', 'False')).strip().lower() == 'true'
        final_val = (6 - score) if is_rev else score
        
        if trait in trait_scores:
            trait_scores[trait].append(final_val)
            
    return {k: round(np.mean(v), 2) for k, v in trait_scores.items() if v}
