import pandas as pd
import random

def get_balanced_questions(df, num_questions):
    traits = df['trait'].unique()
    questions_per_trait = num_questions // len(traits)
    
    selected_questions = []
    
    for trait in traits:
        trait_pool = df[df['trait'] == trait]
        # דגימה אקראית מכל תכונה
        sampled = trait_pool.sample(n=questions_per_trait)
        selected_questions.append(sampled)
    
    result = pd.concat(selected_questions)
    # ערבוב סופי של כל השאלות יחד
    return result.sample(frac=1).reset_index(drop=True)
