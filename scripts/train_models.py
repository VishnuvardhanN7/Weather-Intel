#!/usr/bin/env python3
"""
Model Training Script for National Weather Platform.
Trains the ML models used for fake detection and event categorization.
"""

import os
import sys
import json
import logging
import joblib
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../backend")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("train_models")


def generate_training_data():
    from app.collectors.twitter_collector import INDIAN_STATES_AND_CITIES
    import random

    events = []

    fake_templates = [
        {"title": "ALERT: Government hiding true death toll from floods!!!", "description": "Share before they delete this! The real death toll from the recent floods is 10x what they're telling us. Forward to everyone you know. Click here for the TRUTH: fake-link.com", "is_fake": True},
        {"title": "URGENT - Send money to help flood victims NOW", "description": "Send Rs 500 to this account to help flood victims. Share this message to 10 people or you will have bad luck. This is 100% true!", "is_fake": True},
        {"title": "Miracle cure for heatstroke exposed", "description": "Doctors don't want you to know this! Secret method to survive any heatwave. Share before it's deleted. Act now!!!", "is_fake": True},
        {"title": "Cyclone heading straight for Delhi!!", "description": "Breaking: Massive cyclone formation in Arabian Sea heading directly for Delhi. Everyone evacuate immediately! Share widely before they delete this!", "is_fake": True},
        {"title": "Satellite image shows Mumbai will be underwater by tomorrow", "description": "Leaked satellite image shows complete submersion of Mumbai predicted for tomorrow. Government cover-up exposed! Forward to everyone!", "is_fake": True},
        {"title": "You won a prize - Weather alert system", "description": "Congratulations! You've been selected for our premium weather alert system. Click now to claim your free prize. Limited time offer!", "is_fake": True},
        {"title": "Conspiracy: IMD deliberately wrong forecasts", "description": "Exposed: IMD is deliberately giving wrong forecasts to manipulate crop prices. Share this before they censor it!", "is_fake": True},
        {"title": "Forward this to 10 people - Weather curse", "description": "If you don't forward this message to 10 people within 24 hours, you will face bad weather for the rest of the year. This is real!", "is_fake": True},
        {"title": "Secret weather weapon being used on India", "description": "Hidden truth revealed - foreign governments are using secret weather weapons to create disasters in India. Cover up exposed!", "is_fake": True},
        {"title": "End of the world weather event incoming", "description": "Biblical weather event approaching India. Never before seen in history. Act now or face the consequences!", "is_fake": True},
    ]

    real_templates = [
        {"title": "IMD issues red alert for Mumbai due to heavy rainfall", "description": "India Meteorological Department has issued a red alert for Mumbai and surrounding areas predicting heavy to very heavy rainfall over the next 48 hours. Citizens are advised to stay indoors and avoid unnecessary travel.", "is_fake": False},
        {"title": "Cyclone warning for Odisha coast - evacuations begin", "description": "A deep depression over the Bay of Bengal has intensified into a cyclonic storm. The India Meteorological Department has issued warnings for coastal Odisha. NDRF teams have been deployed and evacuation of low-lying areas is underway.", "is_fake": False},
        {"title": "Severe thunderstorm hits Delhi, multiple areas waterlogged", "description": "A severe thunderstorm with strong winds hit the national capital this afternoon, bringing heavy rainfall and causing waterlogging in several areas. The India Meteorological Department recorded wind speeds of 70 km/h.", "is_fake": False},
        {"title": "Heatwave conditions persist in Rajasthan, temperature crosses 45°C", "description": "Heatwave conditions continue to grip Rajasthan with temperatures exceeding 45 degrees Celsius in several districts. The state disaster management authority has issued advisories and activated cooling centers.", "is_fake": False},
        {"title": "Flash floods in Assam, over 2 lakh people affected", "description": "Assam is reeling under severe floods with over 2 lakh people affected across 12 districts. The Brahmaputra river and its tributaries are flowing above the danger mark. NDRF and SDRF teams are conducting rescue operations.", "is_fake": False},
        {"title": "Dense fog disrupts flight operations at Delhi airport", "description": "Dense fog conditions at Indira Gandhi International Airport have disrupted flight operations with several flights delayed and some diverted. Visibility dropped to less than 50 meters.", "is_fake": False},
        {"title": "Landslides reported in Himachal Pradesh after continuous rainfall", "description": "Multiple landslides have been reported in Shimla, Kullu, and Manali districts following continuous rainfall over the past three days. Several roads are blocked and traffic has been diverted.", "is_fake": False},
        {"title": "Heavy rainfall warning for Kerala - orange alert in 8 districts", "description": "The India Meteorological Department has issued an orange alert for 8 districts in Kerala predicting heavy to very heavy rainfall. Fishermen are advised not to venture into the sea.", "is_fake": False},
    ]

    for template in fake_templates:
        city_key = random.choice(list(INDIAN_STATES_AND_CITIES.keys()))
        city, state = INDIAN_STATES_AND_CITIES[city_key]
        events.append({
            "title": template["title"],
            "description": template["description"],
            "is_fake": template["is_fake"],
            "city": city,
            "state": state,
        })

    for template in real_templates:
        city_key = random.choice(list(INDIAN_STATES_AND_CITIES.keys()))
        city, state = INDIAN_STATES_AND_CITIES[city_key]
        events.append({
            "title": template["title"],
            "description": template["description"],
            "is_fake": template["is_fake"],
            "city": city,
            "state": state,
        })

    return events


def extract_features(text):
    import re
    from collections import Counter

    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)

    features = {}

    features['length'] = len(text)
    features['word_count'] = len(words)
    features['exclamation_count'] = text.count('!')
    features['question_count'] = text.count('?')
    features['uppercase_ratio'] = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    features['url_count'] = len(re.findall(r'https?://\S+', text))

    fake_keywords = ['urgent', 'share', 'forward', 'breaking', 'conspiracy', 'exposed', 'secret',
                     'miracle', 'send money', 'click', 'deleted', 'act now', '100% true',
                     'fake', 'hoax', 'prank', 'satire', 'congratulations', 'you won']
    features['fake_keyword_count'] = sum(1 for kw in fake_keywords if kw in text_lower)

    real_keywords = ['imd', 'meteorological', 'department', 'official', 'alert', 'warning',
                     'recorded', 'measured', 'ndrf', 'sdrf', 'disaster management']
    features['real_keyword_count'] = sum(1 for kw in real_keywords if kw in text_lower)

    sentiment_words_positive = ['good', 'safe', 'normal', 'mild', 'light']
    sentiment_words_negative = ['danger', 'threat', 'catastrophic', 'devastating', 'emergency', 'death', 'destroy']
    features['positive_sentiment'] = sum(1 for w in sentiment_words_positive if w in text_lower)
    features['negative_sentiment'] = sum(1 for w in sentiment_words_negative if w in text_lower)

    features['avg_word_length'] = np.mean([len(w) for w in words]) if words else 0
    features['unique_word_ratio'] = len(set(words)) / max(len(words), 1)

    return features


def train_fake_detector():
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.metrics import classification_report, accuracy_score
    from sklearn.preprocessing import StandardScaler

    logger.info("Training Fake Detector Model...")

    events = generate_training_data()

    texts = [f"{e['title']} {e['description']}" for e in events]
    labels = [1 if e['is_fake'] else 0 for e in events]

    feature_dicts = [extract_features(t) for t in texts]
    feature_names = list(feature_dicts[0].keys())
    X = np.array([[fd[f] for f in feature_names] for fd in feature_dicts])
    y = np.array(labels)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X_scaled, y)

    scores = cross_val_score(model, X_scaled, y, cv=min(3, len(y)), scoring='accuracy')
    logger.info(f"Cross-validation accuracy: {scores.mean():.3f} (+/- {scores.std():.3f})")

    y_pred = model.predict(X_scaled)
    logger.info(f"Training accuracy: {accuracy_score(y, y_pred):.3f}")
    logger.info(f"\nClassification Report:\n{classification_report(y, y_pred, target_names=['Real', 'Fake'])}")

    model_dir = os.path.join(os.path.dirname(__file__), "..", "ml_pipeline", "models")
    os.makedirs(model_dir, exist_ok=True)

    joblib.dump(model, os.path.join(model_dir, "fake_detector_model.joblib"))
    joblib.dump(scaler, os.path.join(model_dir, "fake_detector_scaler.joblib"))
    joblib.dump(feature_names, os.path.join(model_dir, "fake_detector_features.joblib"))

    logger.info("Fake detector model saved to ml_pipeline/models/")
    return model, scaler, feature_names


def train_categorizer():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.model_selection import cross_val_score
    from sklearn.metrics import classification_report
    import random

    logger.info("Training Event Categorizer Model...")

    from app.ml.categorizer import WEATHER_CATEGORY_KEYWORDS

    events = []
    for category, keywords in WEATHER_CATEGORY_KEYWORDS.items():
        for _ in range(20):
            selected_keywords = random.sample(keywords, min(5, len(keywords)))
            city_key = random.choice(list(WEATHER_CATEGORY_KEYWORDS.keys()))
            text = f"Weather event: {', '.join(selected_keywords)}. Reporting from India. Category: {category}."
            events.append({"text": text, "category": category})

    texts = [e['text'] for e in events]
    labels = [e['category'] for e in events]

    vectorizer = TfidfVectorizer(max_features=500, ngram_range=(1, 2))
    X = vectorizer.fit_transform(texts)

    model = MultinomialNB(alpha=0.1)
    model.fit(X, labels)

    scores = cross_val_score(model, X, labels, cv=min(3, len(texts)), scoring='accuracy')
    logger.info(f"Cross-validation accuracy: {scores.mean():.3f}")

    model_dir = os.path.join(os.path.dirname(__file__), "..", "ml_pipeline", "models")
    os.makedirs(model_dir, exist_ok=True)

    joblib.dump(model, os.path.join(model_dir, "categorizer_model.joblib"))
    joblib.dump(vectorizer, os.path.join(model_dir, "categorizer_vectorizer.joblib"))

    logger.info("Categorizer model saved to ml_pipeline/models/")
    return model, vectorizer


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting model training pipeline")
    logger.info("=" * 60)

    logger.info("\n--- Fake Detector ---")
    train_fake_detector()

    logger.info("\n--- Categorizer ---")
    train_categorizer()

    logger.info("\n" + "=" * 60)
    logger.info("All models trained and saved successfully!")
    logger.info("=" * 60)
