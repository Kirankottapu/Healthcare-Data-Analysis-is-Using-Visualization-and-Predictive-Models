"""
===============================================================================
  app.py  –  Healthcare Data Analysis Flask Backend  (Enhanced Edition)
===============================================================================
  Security features:
    • CSRF protection on every POST form
    • Login rate-limiting with account lockout (5 attempts / 15 min)
    • Automatic session timeout (30 minutes)
    • Strong password enforcement (8+ chars, upper, lower, digit, special)
    • Last-login / login-count tracking
    • Change password from profile

  Advanced features:
    • Multi-disease prediction  (Heart Disease  +  Diabetes Risk)
    • Health Score calculator (0 – 100)
    • Advanced Analytics dashboard with rich Chart.js visuals
    • BMI Calculator & standalone Health Score page
    • CSV export of prediction history
    • Enhanced API endpoints for charts & analytics
===============================================================================
"""

import os
import io
import csv
import re
import json
import secrets
import random
import string
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from functools import wraps

import bcrypt
import certifi
import joblib
import numpy as np
from bson.objectid import ObjectId
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, make_response, abort, Response
)
from pymongo import MongoClient

# ──────────────────────────────────────────────────────────────────────────────
#  App Configuration
# ──────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'new_token')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Security constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION   = timedelta(minutes=15)
SESSION_TIMEOUT    = timedelta(minutes=30)

# ──────────────────────────────────────────────────────────────────────────────
#  MongoDB Connection with Retry Logic
# ──────────────────────────────────────────────────────────────────────────────
MONGO_URI = os.environ.get(
    'MONGO_URI',
    'mongodb+srv://svljyothikanookala_db_user:Health_user@cluster0.kricsn.mongodb.net/'
    'healthcare_db?retryWrites=true&w=majority&appName=Cluster0'
)

# Try multiple connection methods for MongoDB
client = None
db = None
mongo_connected = False
users_col = None
predictions_col = None
password_resets = None
login_attempts_col = None

# In-memory database fallback for Windows development
class MockCollection:
    """Mock MongoDB collection for fallback mode."""
    def __init__(self, name):
        self.name = name
        self.data = {}

    def _matches(self, doc, query):
        if not query:
            return True

        # Support $or
        if '$or' in query:
            return any(self._matches(doc, subq) for subq in query.get('$or', []))

        for key, value in query.items():
            if key == '$or':
                continue

            if isinstance(value, dict):
                # Support operators like $gt
                if '$gt' in value:
                    if doc.get(key) is None or not (doc.get(key) > value['$gt']):
                        return False
                else:
                    # Unknown operator block
                    return False
            else:
                if doc.get(key) != value:
                    return False

        return True
    
    def find_one(self, query):
        """Return first matching document or None."""
        for doc in self.data.values():
            if self._matches(doc, query):
                return doc
        return None
    
    def find(self, query):
        """Return list of matching documents."""
        return [doc for doc in self.data.values() if self._matches(doc, query)]
    
    def insert_one(self, doc):
        """Insert document; adds `_id` if missing."""
        if '_id' not in doc:
            doc['_id'] = ObjectId()

        _id = doc['_id']

        class InsertResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id

        self.data[str(_id)] = doc
        return InsertResult(_id)
    
    def update_one(self, query, update):
        """Update first matching document."""
        doc = self.find_one(query)

        class UpdateResult:
            matched_count = 0
            modified_count = 0

        result = UpdateResult()
        if not doc:
            return result

        if '$set' in update:
            for k, v in update['$set'].items():
                doc[k] = v

        if '$inc' in update:
            for k, v in update['$inc'].items():
                doc[k] = (doc.get(k, 0) or 0) + v

        result.matched_count = 1
        result.modified_count = 1
        return result
    
    def delete_one(self, query):
        """Mock delete_one"""
        to_delete = None
        for key, doc in self.data.items():
            if self._matches(doc, query):
                to_delete = key
                break

        class DeleteResult:
            deleted_count = 0

        result = DeleteResult()
        if to_delete is not None:
            del self.data[to_delete]
            result.deleted_count = 1
        return result
    
    def count_documents(self, query):
        """Mock count_documents"""
        return len(self.find(query))
    
    def create_index(self, *args, **kwargs):
        """Mock create_index"""
        pass
    
    def update_many(self, query, update):
        """Mock update_many"""
        matched = 0
        modified = 0
        for doc in self.data.values():
            if self._matches(doc, query):
                matched += 1
                if '$set' in update:
                    for k, v in update['$set'].items():
                        doc[k] = v
                if '$inc' in update:
                    for k, v in update['$inc'].items():
                        doc[k] = (doc.get(k, 0) or 0) + v
                modified += 1

        class UpdateResult:
            matched_count = matched
            modified_count = modified

        return UpdateResult()
    
    def delete_many(self, query):
        """Mock delete_many"""
        keys = [k for k, doc in self.data.items() if self._matches(doc, query)]
        for k in keys:
            del self.data[k]

        class DeleteResult:
            deleted_count = len(keys)

        return DeleteResult()

def connect_mongodb():
    """Connect to MongoDB Atlas with proper error handling."""
    global client, db, mongo_connected, users_col, predictions_col, password_resets, login_attempts_col
    
    try:
        print("[INFO] Attempting MongoDB Atlas connection...")

        # In production (e.g., Vercel/Linux), use strict TLS + certifi.
        # In local Windows dev, Atlas TLS can fail due to local SSL stack issues;
        # we fall back to MockCollection in that case.
        is_production = (os.environ.get('FLASK_ENV') == 'production') or (os.environ.get('VERCEL') == '1')

        mongo_kwargs = dict(
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
            retryWrites=True,
            w='majority',
        )

        if is_production:
            mongo_kwargs.update(
                tls=True,
                tlsCAFile=certifi.where(),
                tlsAllowInvalidCertificates=False,
                tlsAllowInvalidHostnames=False,
            )
        else:
            mongo_kwargs.update(
                tls=True,
                tlsAllowInvalidCertificates=True,
                tlsAllowInvalidHostnames=True,
            )

        client = MongoClient(MONGO_URI, **mongo_kwargs)
        
        # Force actual connection by trying to ping the server
        client.admin.command('ping')
        
        # Get database and collections
        db = client['healthcare_db']
        users_col = db['users']
        predictions_col = db['predictions']
        password_resets = db['password_resets']
        login_attempts_col = db['login_attempts']
        
        # Try to create indexes
        try:
            users_col.create_index('username', unique=True, sparse=True)
            users_col.create_index('email', unique=True, sparse=True)
            login_attempts_col.create_index('timestamp', expireAfterSeconds=900)
        except Exception as idx_err:
            print(f"[WARN] Index creation issue: {idx_err}")
        
        mongo_connected = True
        print("[OK] MongoDB Atlas connected successfully!")
        
        return True
        
    except Exception as e:
        error_str = str(e)[:100]
        print(f"[ERROR] MongoDB connection failed: {error_str}")
        print("[INFO] Using in-memory database fallback for testing...")
        
        # Use in-memory database for development
        try:
            users_col = MockCollection('users')
            predictions_col = MockCollection('predictions')
            password_resets = MockCollection('password_resets')
            login_attempts_col = MockCollection('login_attempts')
            mongo_connected = False  # Mark as not using real MongoDB
            print("[OK] In-memory database ready for testing")
            return False
        except Exception as fallback_err:
            print(f"[ERROR] Fallback failed: {fallback_err}")
            return False

# Try to connect
connect_mongodb()

# ──────────────────────────────────────────────────────────────────────────────
#  Load ML Models  (Heart Disease  +  Diabetes)
# ──────────────────────────────────────────────────────────────────────────────
MODEL_DIR      = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model')
heart_model    = None
diabetes_model = None
model_meta     = None

def load_models():
    global heart_model, diabetes_model, model_meta
    # Heart disease model
    for name in ('heart_model.pkl', 'model.pkl'):
        p = os.path.join(MODEL_DIR, name)
        if os.path.exists(p):
            heart_model = joblib.load(p)
            print(f"[OK] Heart disease model loaded ({name})")
            break
    else:
        print("[WARN] Heart disease model not found")

    # Diabetes model
    dp = os.path.join(MODEL_DIR, 'diabetes_model.pkl')
    if os.path.exists(dp):
        try:
            diabetes_model = joblib.load(dp)
            print("[OK] Diabetes risk model loaded")
        except Exception as e:
            print(f"[WARN] Diabetes model load error: {str(e)[:60]} - heart-only mode")
    else:
        print("[WARN] Diabetes model not found - heart-only mode")

    mp = os.path.join(MODEL_DIR, 'model_meta.pkl')
    if os.path.exists(mp):
        try:
            model_meta = joblib.load(mp)
        except Exception as e:
            print(f"[WARN] Model metadata load error: {str(e)[:60]}")

try:
    load_models()
except Exception as e:
    print(f"[ERROR] Model loading failed: {str(e)[:100]}")
    print("[INFO] Continuing with available models...")

# ──────────────────────────────────────────────────────────────────────────────
#  CSRF Protection
# ──────────────────────────────────────────────────────────────────────────────
def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token

# ──────────────────────────────────────────────────────────────────────────────
#  Before-request middleware  (CSRF + session timeout)
# ──────────────────────────────────────────────────────────────────────────────
@app.before_request
def security_middleware():
    # ── CSRF validation on every POST ──
    if request.method == 'POST':
        tok = session.get('csrf_token')
        ftk = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if not tok or tok != ftk:
            # Invalidate old token and force a fresh one on next page load
            session.pop('csrf_token', None)
            flash('Security token expired – please try again.', 'danger')
            return redirect(request.referrer or url_for('home'))

    # ── Session timeout ──
    session.permanent = True
    if 'user_id' in session:
        last = session.get('last_active')
        if last:
            try:
                if datetime.utcnow() - datetime.fromisoformat(last) > SESSION_TIMEOUT:
                    session.clear()
                    flash('Session expired. Please log in again.', 'warning')
                    return redirect(url_for('login'))
            except (ValueError, TypeError):
                pass
        session['last_active'] = datetime.utcnow().isoformat()

# ──────────────────────────────────────────────────────────────────────────────
#  Auth & Validation Helpers
# ──────────────────────────────────────────────────────────────────────────────
def login_required(f):
    """Redirect to login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def validate_password(password):
    """Return a list of strength errors (empty == strong)."""
    errs = []
    if len(password) < 8:
        errs.append('At least 8 characters required.')
    if not re.search(r'[A-Z]', password):
        errs.append('At least one uppercase letter required.')
    if not re.search(r'[a-z]', password):
        errs.append('At least one lowercase letter required.')
    if not re.search(r'\d', password):
        errs.append('At least one digit required.')
    if not re.search(r'[!@#$%^&*()\-_=+{};:,<.>?/\[\]\'\"\\|`~]', password):
        errs.append('At least one special character required.')
    return errs


def is_account_locked(username):
    """Return (locked: bool, remaining_attempts: int)."""
    if login_attempts_col is None:
        return False, MAX_LOGIN_ATTEMPTS  # Skip rate limiting if DB unavailable
    cutoff = datetime.utcnow() - LOCKOUT_DURATION
    count  = login_attempts_col.count_documents({
        'username': username.lower(),
        'timestamp': {'$gt': cutoff}
    })
    return count >= MAX_LOGIN_ATTEMPTS, max(0, MAX_LOGIN_ATTEMPTS - count)


def record_failed_login(username):
    if login_attempts_col is None:
        return  # Skip if DB unavailable
    login_attempts_col.insert_one({
        'username': username.lower(),
        'timestamp': datetime.utcnow(),
        'ip': request.remote_addr
    })


def clear_login_attempts(username):
    if login_attempts_col is None:
        return  # Skip if DB unavailable
    login_attempts_col.delete_many({'username': username.lower()})

# ──────────────────────────────────────────────────────────────────────────────
#  Health-Score & Tip Helpers
# ──────────────────────────────────────────────────────────────────────────────
def calculate_health_score(data):
    """0-100 holistic health score."""
    s = 100
    age = data.get('age', 30)
    if age > 65:   s -= 10
    elif age > 55: s -= 7
    elif age > 45: s -= 4

    bp = data.get('blood_pressure', 120)
    if bp > 160:   s -= 20
    elif bp > 140: s -= 15
    elif bp > 130: s -= 8
    elif bp < 90:  s -= 10

    sugar = data.get('sugar_level', 100)
    if sugar > 200:   s -= 20
    elif sugar > 140: s -= 15
    elif sugar > 126: s -= 10
    elif sugar > 110: s -= 5

    bmi = data.get('bmi', 24.0)
    if bmi > 35:     s -= 20
    elif bmi > 30:   s -= 15
    elif bmi > 27:   s -= 10
    elif bmi > 25:   s -= 5
    elif bmi < 18.5: s -= 10

    if data.get('smoking'):   s -= 15
    if not data.get('exercise'): s -= 10
    if data.get('alcohol'):  s -= 5

    return max(0, min(100, s))


def get_health_grade(score):
    if score >= 90: return 'A+', 'Excellent'
    if score >= 80: return 'A',  'Very Good'
    if score >= 70: return 'B',  'Good'
    if score >= 60: return 'C',  'Fair'
    if score >= 50: return 'D',  'Needs Improvement'
    return 'F', 'Critical – See a Doctor'


def analyze_symptoms(symptoms_text):
    """Analyze symptoms text and return disease-specific risk assessment."""
    symptoms_text = symptoms_text.lower().strip()
    
    # Comprehensive symptom database with disease associations
    symptom_database = {
        # Cardiovascular & Hypertension symptoms
        'chest pain': {'diseases': ['Heart Disease', 'Hypertension'], 'severity': 'High', 'risk_score': 25},
        'chest tightness': {'diseases': ['Heart Disease', 'Hypertension'], 'severity': 'High', 'risk_score': 20},
        'heart palpitations': {'diseases': ['Heart Disease', 'Hypertension'], 'severity': 'Medium', 'risk_score': 15},
        'irregular heartbeat': {'diseases': ['Heart Disease', 'Hypertension'], 'severity': 'High', 'risk_score': 20},
        'shortness of breath': {'diseases': ['Heart Disease', 'Asthma', 'Respiratory Disease'], 'severity': 'High', 'risk_score': 18},
        'high blood pressure': {'diseases': ['Hypertension', 'Heart Disease', 'Chronic Kidney Disease'], 'severity': 'High', 'risk_score': 22},
        
        # Respiratory & Asthma symptoms
        'breathing difficulty': {'diseases': ['Asthma', 'Respiratory Disease', 'Heart Disease'], 'severity': 'High', 'risk_score': 20},
        'wheezing': {'diseases': ['Asthma', 'Respiratory Disease'], 'severity': 'Medium', 'risk_score': 18},
        'persistent cough': {'diseases': ['Asthma', 'Respiratory Disease', 'Cancer'], 'severity': 'Medium', 'risk_score': 15},
        'cough': {'diseases': ['Respiratory Disease', 'Asthma'], 'severity': 'Low', 'risk_score': 8},
        'chest congestion': {'diseases': ['Respiratory Disease', 'Asthma'], 'severity': 'Medium', 'risk_score': 12},
        'rapid breathing': {'diseases': ['Asthma', 'Respiratory Disease'], 'severity': 'High', 'risk_score': 16},
        
        # Kidney Disease symptoms
        'frequent urination': {'diseases': ['Chronic Kidney Disease', 'Diabetes'], 'severity': 'Medium', 'risk_score': 15},
        'blood in urine': {'diseases': ['Chronic Kidney Disease', 'Cancer'], 'severity': 'High', 'risk_score': 25},
        'foamy urine': {'diseases': ['Chronic Kidney Disease'], 'severity': 'Medium', 'risk_score': 18},
        'swelling in legs': {'diseases': ['Chronic Kidney Disease', 'Heart Disease'], 'severity': 'Medium', 'risk_score': 16},
        'swelling in ankles': {'diseases': ['Chronic Kidney Disease', 'Heart Disease'], 'severity': 'Medium', 'risk_score': 16},
        'swelling in feet': {'diseases': ['Chronic Kidney Disease', 'Heart Disease'], 'severity': 'Medium', 'risk_score': 16},
        'decreased urine output': {'diseases': ['Chronic Kidney Disease'], 'severity': 'High', 'risk_score': 20},
        
        # Liver Disease symptoms
        'jaundice': {'diseases': ['Liver Disease', 'Cancer'], 'severity': 'High', 'risk_score': 25},
        'yellow skin': {'diseases': ['Liver Disease'], 'severity': 'High', 'risk_score': 25},
        'yellow eyes': {'diseases': ['Liver Disease'], 'severity': 'High', 'risk_score': 25},
        'abdominal swelling': {'diseases': ['Liver Disease', 'Cancer'], 'severity': 'High', 'risk_score': 20},
        'dark urine': {'diseases': ['Liver Disease', 'Chronic Kidney Disease'], 'severity': 'Medium', 'risk_score': 15},
        'pale stool': {'diseases': ['Liver Disease'], 'severity': 'Medium', 'risk_score': 15},
        'itchy skin': {'diseases': ['Liver Disease'], 'severity': 'Low', 'risk_score': 10},
        'easy bruising': {'diseases': ['Liver Disease', 'Cancer'], 'severity': 'Medium', 'risk_score': 14},
        
        # Cancer symptoms
        'unexplained weight loss': {'diseases': ['Cancer', 'Diabetes', 'Liver Disease'], 'severity': 'High', 'risk_score': 22},
        'persistent fatigue': {'diseases': ['Cancer', 'Mental Health Disorder'], 'severity': 'Medium', 'risk_score': 14},
        'lump': {'diseases': ['Cancer'], 'severity': 'High', 'risk_score': 25},
        'unusual bleeding': {'diseases': ['Cancer'], 'severity': 'High', 'risk_score': 25},
        'persistent pain': {'diseases': ['Cancer'], 'severity': 'Medium', 'risk_score': 15},
        'night sweats': {'diseases': ['Cancer', 'Infection'], 'severity': 'Medium', 'risk_score': 14},
        'loss of appetite': {'diseases': ['Cancer', 'Liver Disease', 'Mental Health Disorder'], 'severity': 'Medium', 'risk_score': 12},
        'skin changes': {'diseases': ['Cancer'], 'severity': 'Medium', 'risk_score': 15},
        
        # Obesity-related symptoms
        'excessive weight gain': {'diseases': ['Obesity', 'Metabolic Disorder'], 'severity': 'Medium', 'risk_score': 15},
        'difficulty exercising': {'diseases': ['Obesity', 'Heart Disease'], 'severity': 'Low', 'risk_score': 10},
        'sleep apnea': {'diseases': ['Obesity', 'Respiratory Disease'], 'severity': 'High', 'risk_score': 18},
        'joint pain': {'diseases': ['Obesity', 'Arthritis'], 'severity': 'Medium', 'risk_score': 10},
        'back pain': {'diseases': ['Obesity'], 'severity': 'Low', 'risk_score': 8},
        
        # Mental Health symptoms
        'anxiety': {'diseases': ['Mental Health Disorder'], 'severity': 'Medium', 'risk_score': 14},
        'depression': {'diseases': ['Mental Health Disorder'], 'severity': 'Medium', 'risk_score': 14},
        'panic attacks': {'diseases': ['Mental Health Disorder'], 'severity': 'High', 'risk_score': 18},
        'mood swings': {'diseases': ['Mental Health Disorder'], 'severity': 'Medium', 'risk_score': 12},
        'difficulty concentrating': {'diseases': ['Mental Health Disorder'], 'severity': 'Medium', 'risk_score': 10},
        'insomnia': {'diseases': ['Mental Health Disorder'], 'severity': 'Medium', 'risk_score': 12},
        'social withdrawal': {'diseases': ['Mental Health Disorder'], 'severity': 'Medium', 'risk_score': 13},
        
        # Diabetes symptoms
        'excessive thirst': {'diseases': ['Diabetes', 'Chronic Kidney Disease'], 'severity': 'Medium', 'risk_score': 15},
        'increased hunger': {'diseases': ['Diabetes'], 'severity': 'Low', 'risk_score': 10},
        'blurred vision': {'diseases': ['Diabetes', 'Hypertension'], 'severity': 'Medium', 'risk_score': 15},
        'slow healing wounds': {'diseases': ['Diabetes'], 'severity': 'Medium', 'risk_score': 14},
        'numbness in hands': {'diseases': ['Diabetes', 'Neurological'], 'severity': 'Medium', 'risk_score': 15},
        'numbness in feet': {'diseases': ['Diabetes', 'Neurological'], 'severity': 'Medium', 'risk_score': 15},
        'tingling': {'diseases': ['Diabetes', 'Neurological'], 'severity': 'Medium', 'risk_score': 12},
        
        # General symptoms
        'fatigue': {'diseases': ['General', 'Diabetes', 'Heart Disease'], 'severity': 'Low', 'risk_score': 8},
        'weakness': {'diseases': ['General', 'Chronic Kidney Disease'], 'severity': 'Low', 'risk_score': 10},
        'dizziness': {'diseases': ['Hypertension', 'Heart Disease'], 'severity': 'Medium', 'risk_score': 12},
        'nausea': {'diseases': ['Liver Disease', 'Chronic Kidney Disease'], 'severity': 'Low', 'risk_score': 8},
        'vomiting': {'diseases': ['Liver Disease', 'Chronic Kidney Disease'], 'severity': 'Medium', 'risk_score': 12},
        'fever': {'diseases': ['Infection'], 'severity': 'Medium', 'risk_score': 12},
        'headache': {'diseases': ['Hypertension', 'General'], 'severity': 'Low', 'risk_score': 8},
        'severe headache': {'diseases': ['Hypertension'], 'severity': 'High', 'risk_score': 18},
        'confusion': {'diseases': ['Chronic Kidney Disease', 'Liver Disease'], 'severity': 'High', 'risk_score': 20},
        'memory loss': {'diseases': ['Neurological'], 'severity': 'High', 'risk_score': 16},
    }
    
    detected_symptoms = []
    disease_risks = {}  # Track risk scores per disease
    
    # Initialize disease tracking
    all_diseases = [
        'Cancer', 'Obesity', 'Hypertension', 'Chronic Kidney Disease',
        'Asthma', 'Respiratory Disease', 'Liver Disease', 'Mental Health Disorder',
        'Heart Disease', 'Diabetes'
    ]
    
    for disease in all_diseases:
        disease_risks[disease] = {'score': 0, 'symptoms': []}
    
    # Analyze the symptoms text
    for symptom, info in symptom_database.items():
        if symptom in symptoms_text:
            detected_symptoms.append({
                'name': symptom.title(),
                'diseases': info['diseases'],
                'severity': info['severity'],
                'risk_score': info['risk_score']
            })
            
            # Add to disease-specific risks
            for disease in info['diseases']:
                if disease in disease_risks:
                    disease_risks[disease]['score'] += info['risk_score']
                    disease_risks[disease]['symptoms'].append(symptom.title())
    
    # Calculate overall risk and identify primary diseases
    total_risk_score = sum(symptom['risk_score'] for symptom in detected_symptoms)
    
    # Determine which diseases have significant risk
    diseases_at_risk = []
    for disease, data in disease_risks.items():
        if data['score'] > 0:
            risk_level = 'High' if data['score'] >= 30 else 'Medium' if data['score'] >= 15 else 'Low'
            diseases_at_risk.append({
                'name': disease,
                'risk_score': data['score'],
                'risk_level': risk_level,
                'symptom_count': len(data['symptoms']),
                'symptoms': data['symptoms']
            })
    
    # Sort diseases by risk score
    diseases_at_risk.sort(key=lambda x: x['risk_score'], reverse=True)
    
    # Determine overall risk level
    if total_risk_score >= 50:
        risk_level = 'Critical Risk'
        risk_category = 'Critical'
    elif total_risk_score >= 40:
        risk_level = 'High Risk'
        risk_category = 'Significant'
    elif total_risk_score >= 25:
        risk_level = 'High Risk'
        risk_category = 'Moderate'
    elif total_risk_score >= 15:
        risk_level = 'Medium Risk'
        risk_category = 'Mild'
    elif total_risk_score > 0:
        risk_level = 'Low Risk'
        risk_category = 'Minor'
    else:
        risk_level = 'No Risk'
        risk_category = 'Healthy'
    
    return {
        'detected_symptoms': detected_symptoms,
        'total_risk_score': total_risk_score,
        'risk_level': risk_level,
        'risk_category': risk_category,
        'diseases_at_risk': diseases_at_risk,
        'symptom_count': len(detected_symptoms)
    }


def generate_health_tips(risk, bp, sugar, bmi, smoking, exercise, alcohol):
    tips = []
    if risk == 'High Risk':
        tips.append('⚠️ Your risk level is HIGH. Please consult a healthcare provider soon.')
    else:
        tips.append('✅ Your risk level is LOW. Keep maintaining a healthy lifestyle!')
    if bp > 140:
        tips.append('🩸 Your blood pressure is elevated. Reduce salt intake and manage stress.')
    if sugar > 140:
        tips.append('🍬 Your sugar level is high. Monitor carbohydrate intake and stay active.')
    if bmi > 30:
        tips.append('⚖️ Your BMI indicates obesity. Aim for gradual weight loss with diet and exercise.')
    elif bmi > 25:
        tips.append('⚖️ Your BMI indicates overweight. Consider a balanced diet plan.')
    if smoking:
        tips.append('🚭 Smoking significantly increases health risks. Consider quitting.')
    if not exercise:
        tips.append('🏃 Regular exercise (30 min/day) can greatly improve heart health.')
    if alcohol:
        tips.append('🍷 Limit alcohol consumption to reduce cardiovascular risk.')
    tips.append('💧 Stay hydrated – drink at least 8 glasses of water daily.')
    tips.append('😴 Ensure 7-8 hours of quality sleep every night.')
    return tips

# ──────────────────────────────────────────────────────────────────────────────
#  OTP / Email Helpers
# ──────────────────────────────────────────────────────────────────────────────
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


def send_reset_email(to_email, otp_code):
    smtp_email = os.environ.get('SMTP_EMAIL')
    smtp_pass  = os.environ.get('SMTP_PASSWORD')
    if smtp_email and smtp_pass:
        try:
            msg = MIMEMultipart()
            msg['From']    = smtp_email
            msg['To']      = to_email
            msg['Subject'] = 'HealthAI – Password Reset OTP'
            body = f"""<html><body style="font-family:Arial,sans-serif;">
            <div style="max-width:480px;margin:auto;padding:30px;border:1px solid #e0e0e0;border-radius:12px;">
                <h2 style="color:#0d6efd;">HealthAI Password Reset</h2>
                <p>Use the OTP below to reset your password:</p>
                <div style="text-align:center;margin:24px 0;">
                    <span style="font-size:2rem;font-weight:800;letter-spacing:8px;color:#198754;
                                 background:#d1f5e0;padding:12px 28px;border-radius:8px;">{otp_code}</span>
                </div>
                <p style="color:#6c757d;font-size:0.9rem;">Valid for <strong>10 minutes</strong>.</p>
            </div></body></html>"""
            msg.attach(MIMEText(body, 'html'))
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(smtp_email, smtp_pass)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f'[WARN] Email error: {e}')
            return False
    else:
        print(f'📧  [DEV] OTP for {to_email}: {otp_code}')
        return True

# ══════════════════════════════════════════════════════════════════════════════
#  R O U T E S
# ══════════════════════════════════════════════════════════════════════════════

# ── Home ─────────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('home.html')

# ── Register (strong password) ───────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Check database availability
    if users_col is None:
        flash('Database not available. Please try again later or contact administrator.', 'danger')
        return render_template('register.html')
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        if len(username) < 3:
            flash('Username must be at least 3 characters.', 'danger')
            return redirect(url_for('register'))

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            flash('Username: only letters, numbers, and underscores.', 'danger')
            return redirect(url_for('register'))

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('register'))

        pwd_errs = validate_password(password)
        if pwd_errs:
            for e in pwd_errs:
                flash(f'🔒 {e}', 'danger')
            return redirect(url_for('register'))

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        if users_col.find_one({'$or': [{'username': username}, {'email': email}]}):
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('register'))

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        users_col.insert_one({
            'username':    username,
            'email':       email,
            'password':    hashed,
            'created_at':  datetime.utcnow(),
            'last_login':  None,
            'login_count': 0,
            'is_active':   True
        })
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# ── Login (rate-limited) ─────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check database availability
    if users_col is None:
        flash('Database not available. Please try again later or contact administrator.', 'danger')
        return render_template('login.html')
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        locked, remaining = is_account_locked(username)
        if locked:
            flash(f'🔒 Account temporarily locked. Try again in {LOCKOUT_DURATION.seconds // 60} minutes.', 'danger')
            return redirect(url_for('login'))

        user = users_col.find_one({'username': username})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            clear_login_attempts(username)
            session['user_id']     = str(user['_id'])
            session['username']    = user['username']
            session['last_active'] = datetime.utcnow().isoformat()
            users_col.update_one(
                {'_id': user['_id']},
                {'$set': {'last_login': datetime.utcnow()},
                 '$inc': {'login_count': 1}}
            )
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            record_failed_login(username)
            locked, remaining = is_account_locked(username)
            if locked:
                flash('🔒 Account locked due to too many failed attempts.', 'danger')
            else:
                flash(f'Invalid credentials. {remaining} attempt(s) remaining.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# ── Logout ───────────────────────────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# ── Forgot Password ──────────────────────────────────────────────────────────
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash('Please enter your registered email.', 'danger')
            return redirect(url_for('forgot_password'))

        user = users_col.find_one({'email': email})
        if not user:
            flash('No account found with that email address.', 'danger')
            return redirect(url_for('forgot_password'))

        otp = generate_otp()
        password_resets.delete_many({'email': email})
        password_resets.insert_one({
            'email':      email,
            'otp':        otp,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(minutes=10)
        })

        sent = send_reset_email(email, otp)
        smtp_cfg = os.environ.get('SMTP_EMAIL') and os.environ.get('SMTP_PASSWORD')
        if sent and smtp_cfg:
            flash('An OTP has been sent to your email.', 'success')
        elif sent:
            flash(f'[Dev Mode] Your OTP is: {otp}', 'info')
        else:
            flash('Failed to send OTP. Try again later.', 'danger')
            return redirect(url_for('forgot_password'))

        session['reset_email'] = email
        return redirect(url_for('verify_otp'))

    return render_template('forgot_password.html')

# ── Verify OTP ───────────────────────────────────────────────────────────────
@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = session.get('reset_email')
    if not email:
        flash('Please start the password reset process.', 'warning')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        entered = request.form.get('otp', '').strip()
        record = password_resets.find_one({
            'email':      email,
            'otp':        entered,
            'expires_at': {'$gt': datetime.utcnow()}
        })
        if record:
            session['otp_verified'] = True
            return redirect(url_for('reset_password'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'danger')
            return redirect(url_for('verify_otp'))

    return render_template('verify_otp.html', email=email)

# ── Reset Password ───────────────────────────────────────────────────────────
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email    = session.get('reset_email')
    verified = session.get('otp_verified')
    if not email or not verified:
        flash('Please verify your OTP first.', 'warning')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_pw  = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        pwd_errs = validate_password(new_pw)
        if pwd_errs:
            for e in pwd_errs:
                flash(f'🔒 {e}', 'danger')
            return redirect(url_for('reset_password'))

        if new_pw != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('reset_password'))

        hashed = bcrypt.hashpw(new_pw.encode('utf-8'), bcrypt.gensalt())
        users_col.update_one({'email': email}, {'$set': {'password': hashed}})
        password_resets.delete_many({'email': email})
        session.pop('reset_email', None)
        session.pop('otp_verified', None)
        flash('Password reset successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', email=email)

# ── Dashboard (enhanced) ─────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    uid  = session['user_id']
    user = users_col.find_one({'_id': ObjectId(uid)})

    recent            = list(predictions_col.find({'user_id': uid}).sort('timestamp', -1).limit(10))
    total_predictions = predictions_col.count_documents({'user_id': uid})
    high_risk_count   = predictions_col.count_documents({'user_id': uid, 'result': 'High Risk'})
    low_risk_count    = predictions_col.count_documents({'user_id': uid, 'result': 'Low Risk'})

    # Health score from most recent prediction
    avg_score = 0
    if recent:
        scores    = [calculate_health_score(r.get('input_data', {})) for r in recent[:5]]
        avg_score = round(sum(scores) / len(scores))
    grade, grade_desc = get_health_grade(avg_score)

    last = recent[0] if recent else None
    
    # Check if there's a new prediction to show risk visualization
    latest_prediction = session.get('latest_prediction')
    show_risk_analysis = latest_prediction is not None and latest_prediction.get('show_risk_analysis', False)
    
    # Clear the flag after displaying
    if show_risk_analysis and 'latest_prediction' in session:
        session['latest_prediction']['show_risk_analysis'] = False

    return render_template(
        'dashboard.html',
        username=session['username'],
        last_prediction=last,
        total_predictions=total_predictions,
        high_risk_count=high_risk_count,
        low_risk_count=low_risk_count,
        recent=recent,
        avg_health_score=avg_score,
        health_grade=grade,
        health_desc=grade_desc,
        last_login=user.get('last_login'),
        login_count=user.get('login_count', 0),
        latest_prediction=latest_prediction,
        show_risk_analysis=show_risk_analysis
    )

# ── Health Form ──────────────────────────────────────────────────────────────
@app.route('/health-form')
@login_required
def health_form():
    has_diabetes = diabetes_model is not None
    return render_template('health_form.html',
                           username=session['username'],
                           has_diabetes_model=has_diabetes)

# ── Predict (multi-disease) ──────────────────────────────────────────────────
@app.route('/predict', methods=['POST'])
@login_required
def predict():
    disease_type = request.form.get('disease_type', 'symptoms')

    try:
        age           = int(request.form.get('age', 30))
        gender        = int(request.form.get('gender', 0))
        bp            = int(request.form.get('blood_pressure', 120))
        sugar         = int(request.form.get('sugar_level', 100))
        height_cm     = float(request.form.get('height', 170))
        weight_kg     = float(request.form.get('weight', 70))
        symptoms_text = request.form.get('symptoms', '')
        symptom_tags  = request.form.getlist('symptom_tags')
        smoking       = 1 if request.form.get('smoking') else 0
        exercise      = 1 if request.form.get('exercise') else 0
        alcohol       = 1 if request.form.get('alcohol') else 0

        # Combine free-text symptoms with checklist selections for overall analysis
        combined_symptoms_parts = []
        if symptoms_text:
            combined_symptoms_parts.append(symptoms_text)
        if symptom_tags:
            combined_symptoms_parts.append(' '.join(symptom_tags))
        symptoms = ' '.join(combined_symptoms_parts).strip()

        bmi = round(weight_kg / ((height_cm / 100) ** 2), 1) if height_cm > 0 else 25.0

        input_data_doc = {
            'age': age, 'gender': 'Male' if gender == 1 else 'Female',
            'blood_pressure': bp, 'sugar_level': sugar,
            'height': height_cm, 'weight': weight_kg, 'bmi': bmi,
            'symptoms': symptoms,
            'smoking': bool(smoking), 'exercise': bool(exercise),
            'alcohol': bool(alcohol)
        }

        # Handle symptom-based analysis
        if disease_type == 'symptoms':
            # Analyze symptoms
            symptom_analysis = analyze_symptoms(symptoms)
            
            # Calculate overall risk based on symptoms + vital signs
            risk_score = symptom_analysis['total_risk_score']
            
            # Add risk from vital signs
            if bp > 160: risk_score += 20
            elif bp > 140: risk_score += 15
            elif bp > 130: risk_score += 10
            
            if sugar > 200: risk_score += 20
            elif sugar > 140: risk_score += 15
            elif sugar > 126: risk_score += 10
            
            if bmi > 35: risk_score += 15
            elif bmi > 30: risk_score += 10
            elif bmi > 25: risk_score += 5
            
            if smoking: risk_score += 15
            if alcohol: risk_score += 5
            if not exercise: risk_score += 10
            
            # Determine risk level
            if risk_score >= 50:
                risk_label = 'High Risk'
                probability = min(95, 70 + (risk_score - 50) * 0.5)
            elif risk_score >= 30:
                risk_label = 'High Risk'
                probability = min(70, 50 + (risk_score - 30) * 1.0)
            elif risk_score >= 15:
                risk_label = 'Medium Risk'
                probability = 30 + (risk_score - 15) * 1.3
            elif risk_score > 0:
                risk_label = 'Low Risk'
                probability = 10 + risk_score * 1.5
            else:
                risk_label = 'Low Risk'
                probability = 5
            
            probability = round(probability, 2)
            disease_name = 'General Health Assessment'
            
            # Generate disease-specific tips based on analysis
            tips = []
            if symptom_analysis['symptom_count'] > 0:
                tips.append(f"🔍 Detected {symptom_analysis['symptom_count']} symptom(s)")
                tips.append(f"⚠️ Overall risk level: {risk_label} with {probability}% risk probability")
                
                # Add disease-specific recommendations
                diseases_at_risk = symptom_analysis.get('diseases_at_risk', [])
                if diseases_at_risk:
                    tips.append(f"🏥 Potential health concerns detected in {len(diseases_at_risk)} area(s):")
                    
                    for disease_risk in diseases_at_risk[:5]:  # Show top 5
                        disease = disease_risk['name']
                        d_risk_level = disease_risk['risk_level']
                        symptom_count = disease_risk['symptom_count']
                        
                        if disease == 'Cancer':
                            tips.append(f'🔬 Cancer Risk: {d_risk_level} - {symptom_count} warning sign(s) detected. Consult oncologist for screening.')
                        elif disease == 'Hypertension':
                            tips.append(f'💊 Hypertension Risk: {d_risk_level} - {symptom_count} symptom(s). Monitor blood pressure regularly.')
                        elif disease == 'Chronic Kidney Disease':
                            tips.append(f'🔬 Kidney Disease Risk: {d_risk_level} - {symptom_count} symptom(s). Get kidney function tests.')
                        elif disease == 'Asthma' or disease == 'Respiratory Disease':
                            tips.append(f'🫁 Respiratory Risk: {d_risk_level} - {symptom_count} symptom(s). See pulmonologist for evaluation.')
                        elif disease == 'Liver Disease':
                            tips.append(f'🏥 Liver Health Risk: {d_risk_level} - {symptom_count} symptom(s). Get liver function tests.')
                        elif disease == 'Mental Health Disorder':
                            tips.append(f'🧠 Mental Health Concern: {d_risk_level} - {symptom_count} symptom(s). Consider consulting a mental health professional.')
                        elif disease == 'Obesity':
                            tips.append(f'⚖️ Weight Management: {d_risk_level} - {symptom_count} related symptom(s). Consult nutritionist for weight management plan.')
                        elif disease == 'Heart Disease':
                            tips.append(f'❤️ Cardiovascular Risk: {d_risk_level} - {symptom_count} symptom(s). See cardiologist for evaluation.')
                        elif disease == 'Diabetes':
                            tips.append(f'🩸 Diabetes Risk: {d_risk_level} - {symptom_count} symptom(s). Monitor blood sugar and consult endocrinologist.')
                else:
                    tips.append('✅ No specific disease patterns detected from symptoms alone.')
                    
            tips.extend(generate_health_tips(risk_label, bp, sugar, bmi, smoking, exercise, alcohol))
            
            # Store symptom analysis in session for detailed visualization
            input_data_doc['symptom_analysis'] = symptom_analysis
            
        # Handle ML-based disease predictions
        elif disease_type == 'heart':
            if heart_model is None:
                flash('Heart disease model not loaded.', 'danger')
                return redirect(url_for('health_form'))
                
            fbs = 1 if sugar > 120 else 0
            chol    = int(sugar * 2.0 + np.random.normal(0, 10))
            chol    = max(100, min(chol, 400))
            thalach = max(70, int(220 - age - (10 if smoking else 0) + (15 if exercise else 0)))
            exang   = 1 if (smoking and not exercise) else 0
            oldpeak = round(max(0.0, (bp - 120) * 0.03 + (0.5 if smoking else 0)), 1)
            restecg = 1 if bp > 140 else 0
            slope   = 1 if age > 55 else 0
            ca      = min(3, max(0, int((age - 40) / 15)))
            thal    = 2 if bp > 150 else 1

            features_heart = np.array([[
                age, gender, bp, chol, fbs, restecg,
                thalach, exang, oldpeak, slope, ca, thal,
                smoking, exercise, alcohol, bmi
            ]])

            prediction    = heart_model.predict(features_heart)[0]
            probabilities = heart_model.predict_proba(features_heart)[0]
            risk_label    = 'High Risk' if prediction == 1 else 'Low Risk'
            probability   = round(float(probabilities[1]) * 100, 2)
            disease_name  = 'Heart Disease'
            tips = generate_health_tips(risk_label, bp, sugar, bmi, smoking, exercise, alcohol)
            
        elif disease_type == 'diabetes':
            if diabetes_model is None:
                flash('Diabetes model not loaded.', 'danger')
                return redirect(url_for('health_form'))
                
            fbs = 1 if sugar > 120 else 0
            chol    = int(sugar * 2.0 + np.random.normal(0, 10))
            chol    = max(100, min(chol, 400))
            thalach = max(70, int(220 - age - (10 if smoking else 0) + (15 if exercise else 0)))
            exang   = 1 if (smoking and not exercise) else 0
            oldpeak = round(max(0.0, (bp - 120) * 0.03 + (0.5 if smoking else 0)), 1)
            restecg = 1 if bp > 140 else 0
            slope   = 1 if age > 55 else 0
            ca      = min(3, max(0, int((age - 40) / 15)))
            thal    = 2 if bp > 150 else 1

            features_heart = np.array([[
                age, gender, bp, chol, fbs, restecg,
                thalach, exang, oldpeak, slope, ca, thal,
                smoking, exercise, alcohol, bmi
            ]])
            
            # Diabetes uses same feature set
            prediction    = diabetes_model.predict(features_heart)[0]
            probabilities = diabetes_model.predict_proba(features_heart)[0]
            risk_label    = 'High Risk' if prediction == 1 else 'Low Risk'
            probability   = round(float(probabilities[1]) * 100, 2)
            disease_name  = 'Diabetes'
            tips = generate_health_tips(risk_label, bp, sugar, bmi, smoking, exercise, alcohol)

        health_score = calculate_health_score(input_data_doc)
        hs_grade, hs_desc = get_health_grade(health_score)

        pred_doc = {
            'user_id':      session['user_id'],
            'disease_type': disease_type,
            'disease_name': disease_name,
            'input_data':   input_data_doc,
            'result':       risk_label,
            'probability':  probability,
            'health_score': health_score,
            'tips':         tips,
            'timestamp':    datetime.utcnow()
        }
        result = predictions_col.insert_one(pred_doc)
        
        # Store the latest prediction in session for dashboard display
        session['latest_prediction'] = {
            'prediction_id': str(result.inserted_id),
            'disease_type': disease_type,
            'disease_name': disease_name,
            'result': risk_label,
            'probability': probability,
            'input_data': input_data_doc,
            'health_score': health_score,
            'health_grade': hs_grade,
            'health_desc': hs_desc,
            'tips': tips,
            'timestamp': pred_doc['timestamp'].strftime('%B %d, %Y  %H:%M'),
            'show_risk_analysis': True
        }
        
        flash(f'✅ {disease_name} complete! Risk Level: {risk_label} ({probability}%)', 'success')
        return redirect(url_for('dashboard'))

    except Exception as e:
        flash(f'Prediction error: {str(e)}', 'danger')
        return redirect(url_for('health_form'))

# ── History ──────────────────────────────────────────────────────────────────
@app.route('/history')
@login_required
def history():
    uid     = session['user_id']
    records = list(predictions_col.find({'user_id': uid}).sort('timestamp', -1))
    for r in records:
        r['_id'] = str(r['_id'])
    return render_template('history.html', username=session['username'], records=records)

# ── Analytics (NEW) ─────────────────────────────────────────────────────────
@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html', username=session['username'])

# ── BMI Calculator (NEW) ────────────────────────────────────────────────────
@app.route('/bmi-calculator')
@login_required
def bmi_calculator():
    return render_template('bmi_calculator.html', username=session['username'])

# ── Profile (enhanced – change password) ─────────────────────────────────────
@app.route('/profile')
@login_required
def profile():
    user  = users_col.find_one({'_id': ObjectId(session['user_id'])})
    total = predictions_col.count_documents({'user_id': session['user_id']})

    display_name = user.get('name', user.get('username', session['username']))
    return render_template(
        'profile.html',
        username=display_name,
        email=user['email'],
        created_at=user.get('created_at', datetime.utcnow()).strftime('%B %d, %Y'),
        last_login=user.get('last_login'),
        login_count=user.get('login_count', 0),
        total_predictions=total
    )

# ── Download Report ──────────────────────────────────────────────────────────
@app.route('/download-report/<pred_id>')
@login_required
def download_report(pred_id):
    try:
        pred = predictions_col.find_one({
            '_id': ObjectId(pred_id),
            'user_id': session['user_id']
        })
        if not pred:
            flash('Prediction not found.', 'danger')
            return redirect(url_for('history'))

        inp = pred['input_data']
        hs  = pred.get('health_score', 'N/A')
        dn  = pred.get('disease_name', 'Heart Disease')

        report = f"""
========================================
  HEALTH RISK ASSESSMENT REPORT
========================================
  Generated : {pred['timestamp'].strftime('%B %d, %Y  %H:%M UTC')}
  Patient   : {session['username']}
  Disease   : {dn}
========================================

--- Patient Information ---
  Age            : {inp['age']}
  Gender         : {inp['gender']}
  Blood Pressure : {inp['blood_pressure']} mm Hg
  Sugar Level    : {inp['sugar_level']} mg/dl
  Height         : {inp['height']} cm
  Weight         : {inp['weight']} kg
  BMI            : {inp['bmi']}
  Smoking        : {'Yes' if inp['smoking'] else 'No'}
  Exercise       : {'Yes' if inp['exercise'] else 'No'}
  Alcohol        : {'Yes' if inp['alcohol'] else 'No'}
  Symptoms       : {inp.get('symptoms', 'N/A')}

--- Prediction Result ---
  Risk Level     : {pred['result']}
  Probability    : {pred['probability']}%
  Health Score   : {hs}/100

--- Health Tips ---
"""
        for i, tip in enumerate(pred.get('tips', []), 1):
            report += f"  {i}. {tip}\n"
        report += """
========================================
  DISCLAIMER: AI-based risk assessment.
  NOT a medical diagnosis. Consult a
  qualified healthcare professional.
========================================
"""
        resp = make_response(report)
        resp.headers['Content-Type'] = 'text/plain'
        resp.headers['Content-Disposition'] = f'attachment; filename=health_report_{pred_id}.txt'
        return resp
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'danger')
        return redirect(url_for('history'))

# ── Export CSV (NEW) ─────────────────────────────────────────────────────────
@app.route('/export-csv')
@login_required
def export_csv():
    """Export all predictions for the current user as CSV."""
    uid     = session['user_id']
    records = list(predictions_col.find({'user_id': uid}).sort('timestamp', -1))

    si  = io.StringIO()
    w   = csv.writer(si)
    w.writerow([
        'Date', 'Disease Type', 'Age', 'Gender', 'Blood Pressure',
        'Sugar Level', 'BMI', 'Smoking', 'Exercise', 'Alcohol',
        'Result', 'Probability (%)', 'Health Score'
    ])
    for r in records:
        inp = r.get('input_data', {})
        w.writerow([
            r['timestamp'].strftime('%Y-%m-%d %H:%M'),
            r.get('disease_name', 'Heart Disease'),
            inp.get('age', ''), inp.get('gender', ''),
            inp.get('blood_pressure', ''), inp.get('sugar_level', ''),
            inp.get('bmi', ''),
            'Yes' if inp.get('smoking') else 'No',
            'Yes' if inp.get('exercise') else 'No',
            'Yes' if inp.get('alcohol') else 'No',
            r.get('result', ''), r.get('probability', ''),
            r.get('health_score', '')
        ])

    output = make_response(si.getvalue())
    output.headers['Content-Type'] = 'text/csv'
    output.headers['Content-Disposition'] = 'attachment; filename=health_predictions.csv'
    return output

# ══════════════════════════════════════════════════════════════════════════════
#  API  ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/chart-data')
@login_required
def chart_data():
    uid     = session['user_id']
    records = list(predictions_col.find({'user_id': uid}).sort('timestamp', -1).limit(20))
    high = sum(1 for r in records if r['result'] == 'High Risk')
    low  = sum(1 for r in records if r['result'] == 'Low Risk')
    timeline = [{
        'date':        r['timestamp'].strftime('%Y-%m-%d'),
        'probability': r['probability'],
        'result':      r['result']
    } for r in reversed(records)]
    return jsonify({'risk_distribution': {'high': high, 'low': low}, 'timeline': timeline})


@app.route('/api/analytics-data')
@login_required
def analytics_data():
    """Rich analytics data for the analytics page."""
    uid     = session['user_id']
    records = list(predictions_col.find({'user_id': uid}).sort('timestamp', -1).limit(50))

    if not records:
        return jsonify({'empty': True})

    # Risk distribution
    high = sum(1 for r in records if r['result'] == 'High Risk')
    low  = sum(1 for r in records if r['result'] == 'Low Risk')

    # Timeline data
    timeline = []
    bp_data  = []
    sugar_data = []
    bmi_data   = []
    score_data = []

    for r in reversed(records):
        inp  = r.get('input_data', {})
        date = r['timestamp'].strftime('%Y-%m-%d')
        timeline.append({
            'date': date,
            'probability': r.get('probability', 0),
            'result': r['result']
        })
        bp_data.append({'date': date, 'value': inp.get('blood_pressure', 0)})
        sugar_data.append({'date': date, 'value': inp.get('sugar_level', 0)})
        bmi_data.append({'date': date, 'value': inp.get('bmi', 0)})
        score_data.append({'date': date, 'value': r.get('health_score', calculate_health_score(inp))})

    # Averages
    all_bp    = [r.get('input_data', {}).get('blood_pressure', 0) for r in records if r.get('input_data', {}).get('blood_pressure')]
    all_sugar = [r.get('input_data', {}).get('sugar_level', 0) for r in records if r.get('input_data', {}).get('sugar_level')]
    all_bmi   = [r.get('input_data', {}).get('bmi', 0) for r in records if r.get('input_data', {}).get('bmi')]
    all_scores = [r.get('health_score', 0) for r in records if r.get('health_score')]

    # Lifestyle breakdown
    smokers    = sum(1 for r in records if r.get('input_data', {}).get('smoking'))
    exercisers = sum(1 for r in records if r.get('input_data', {}).get('exercise'))
    drinkers   = sum(1 for r in records if r.get('input_data', {}).get('alcohol'))
    total      = len(records)

    # Disease type breakdown
    heart_count    = sum(1 for r in records if r.get('disease_type', 'heart') == 'heart')
    diabetes_count = sum(1 for r in records if r.get('disease_type') == 'diabetes')

    # Age distribution
    ages = [r.get('input_data', {}).get('age', 0) for r in records]

    return jsonify({
        'empty': False,
        'risk_distribution': {'high': high, 'low': low},
        'timeline': timeline,
        'bp_trend':    bp_data,
        'sugar_trend': sugar_data,
        'bmi_trend':   bmi_data,
        'score_trend': score_data,
        'averages': {
            'bp':    round(sum(all_bp) / len(all_bp), 1) if all_bp else 0,
            'sugar': round(sum(all_sugar) / len(all_sugar), 1) if all_sugar else 0,
            'bmi':   round(sum(all_bmi) / len(all_bmi), 1) if all_bmi else 0,
            'score': round(sum(all_scores) / len(all_scores), 1) if all_scores else 0,
        },
        'lifestyle': {
            'smoking':  smokers,
            'exercise': exercisers,
            'alcohol':  drinkers,
            'total':    total
        },
        'disease_types': {'heart': heart_count, 'diabetes': diabetes_count},
        'age_data': ages,
        'total_records': total
    })


@app.route('/api/health-score', methods=['POST'])
@login_required
def api_health_score():
    """Calculate health score from JSON input (for BMI calculator page)."""
    data = request.get_json(force=True)
    score = calculate_health_score(data)
    grade, desc = get_health_grade(score)
    return jsonify({
        'score': score,
        'grade': grade,
        'description': desc
    })


@app.route('/api/risk-visualization')
@login_required
def api_risk_visualization():
    """Get risk visualization data for the latest prediction."""
    prediction_data = session.get('latest_prediction')
    
    if not prediction_data:
        # Fallback: get the most recent prediction from database
        uid = session['user_id']
        recent_pred = predictions_col.find_one({'user_id': uid}, sort=[('timestamp', -1)])
        if not recent_pred:
            return jsonify({'error': 'No prediction data available'}), 404
        
        input_data = recent_pred.get('input_data', {})
        prediction_data = {
            'disease_type': recent_pred.get('disease_type', 'heart'),
            'disease_name': recent_pred.get('disease_name', 'Heart Disease'),
            'result': recent_pred.get('result', 'Unknown'),
            'probability': recent_pred.get('probability', 0),
            'health_score': recent_pred.get('health_score', 0),
            'input_data': input_data
        }
    
    input_data = prediction_data.get('input_data', {})
    
    # Risk factors analysis
    risk_factors = []
    
    # Age factor
    age = input_data.get('age', 30)
    if age > 65:
        risk_factors.append({'name': 'Age', 'value': age, 'risk': 'High', 'impact': 25})
    elif age > 50:
        risk_factors.append({'name': 'Age', 'value': age, 'risk': 'Medium', 'impact': 15})
    else:
        risk_factors.append({'name': 'Age', 'value': age, 'risk': 'Low', 'impact': 5})
    
    # Blood Pressure factor
    bp = input_data.get('blood_pressure', 120)
    if bp > 160:
        risk_factors.append({'name': 'Blood Pressure', 'value': f'{bp} mmHg', 'risk': 'High', 'impact': 30})
    elif bp > 140:
        risk_factors.append({'name': 'Blood Pressure', 'value': f'{bp} mmHg', 'risk': 'Medium', 'impact': 20})
    else:
        risk_factors.append({'name': 'Blood Pressure', 'value': f'{bp} mmHg', 'risk': 'Low', 'impact': 8})
    
    # Sugar level factor
    sugar = input_data.get('sugar_level', 100)
    if sugar > 200:
        risk_factors.append({'name': 'Blood Sugar', 'value': f'{sugar} mg/dl', 'risk': 'High', 'impact': 25})
    elif sugar > 140:
        risk_factors.append({'name': 'Blood Sugar', 'value': f'{sugar} mg/dl', 'risk': 'Medium', 'impact': 15})
    else:
        risk_factors.append({'name': 'Blood Sugar', 'value': f'{sugar} mg/dl', 'risk': 'Low', 'impact': 5})
    
    # BMI factor
    bmi = input_data.get('bmi', 24.0)
    if bmi > 30:
        risk_factors.append({'name': 'BMI', 'value': f'{bmi:.1f}', 'risk': 'High', 'impact': 20})
    elif bmi > 25:
        risk_factors.append({'name': 'BMI', 'value': f'{bmi:.1f}', 'risk': 'Medium', 'impact': 10})
    else:
        risk_factors.append({'name': 'BMI', 'value': f'{bmi:.1f}', 'risk': 'Low', 'impact': 3})
    
    # Lifestyle factors
    if input_data.get('smoking'):
        risk_factors.append({'name': 'Smoking', 'value': 'Yes', 'risk': 'High', 'impact': 25})
    else:
        risk_factors.append({'name': 'Smoking', 'value': 'No', 'risk': 'Low', 'impact': 0})
    
    if not input_data.get('exercise'):
        risk_factors.append({'name': 'Exercise', 'value': 'No Regular Exercise', 'risk': 'Medium', 'impact': 15})
    else:
        risk_factors.append({'name': 'Exercise', 'value': 'Regular Exercise', 'risk': 'Low', 'impact': 0})
    
    # Risk distribution for pie chart
    total_risk = sum(factor['impact'] for factor in risk_factors)
    safe_score = max(0, 100 - total_risk)
    
    # Check for detailed symptom analysis
    symptom_analysis = input_data.get('symptom_analysis')
    detected_symptoms_data = []
    diseases_at_risk = []
    
    if symptom_analysis and symptom_analysis.get('detected_symptoms'):
        # Add detected symptoms as risk factors
        for symptom in symptom_analysis['detected_symptoms']:
            diseases_list = ', '.join(symptom.get('diseases', ['General']))
            risk_factors.append({
                'name': symptom['name'],
                'value': diseases_list,
                'risk': symptom['severity'],
                'impact': symptom['risk_score']
            })
            detected_symptoms_data.append(symptom)
        
        # Get disease-specific risks
        diseases_at_risk = symptom_analysis.get('diseases_at_risk', [])
        
        total_risk = sum(factor['impact'] for factor in risk_factors)
        safe_score = max(0, 100 - total_risk)
    
    # Fallback symptom analysis for older predictions
    elif input_data.get('symptoms'):
        symptoms_text = input_data['symptoms'].lower()
        high_risk_symptoms = ['chest pain', 'shortness of breath', 'fatigue', 'dizziness', 'nausea']
        for symptom in high_risk_symptoms:
            if symptom in symptoms_text:
                risk_factors.append({'name': symptom.title(), 'value': 'Detected', 'risk': 'High', 'impact': 10})
                total_risk += 10
        safe_score = max(0, 100 - total_risk)
    
    response_data = {
        'prediction': {
            'disease_name': prediction_data.get('disease_name', 'Heart Disease'),
            'risk_level': prediction_data.get('result', 'Unknown'),
            'probability': prediction_data.get('probability', 0),
            'health_score': prediction_data.get('health_score', 0)
        },
        'risk_factors': risk_factors,
        'risk_distribution': {
            'high_risk': total_risk,
            'safe_zone': safe_score
        },
        'charts': {
            'risk_breakdown': [
                {'label': 'Risk Factors', 'value': total_risk, 'color': '#dc3545'},
                {'label': 'Safe Zone', 'value': safe_score, 'color': '#28a745'}
            ],
            'factor_impact': risk_factors
        }
    }
    
    # Add detailed symptom and disease data if available
    if detected_symptoms_data:
        response_data['detected_symptoms'] = detected_symptoms_data
    
    if diseases_at_risk:
        response_data['diseases_at_risk'] = diseases_at_risk
    
    return jsonify(response_data)

# ──────────────────────────────────────────────────────────────────────────────
#  Error Handlers
# ──────────────────────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template('home.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('home.html'), 500

# ──────────────────────────────────────────────────────────────────────────────
#  Run
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("[START] Healthcare Analysis Server (Enhanced)")
    print(f"    URL: http://localhost:5000")
    print(f"    CSRF protection: ON")
    print(f"    Login rate-limit: {MAX_LOGIN_ATTEMPTS} attempts / {LOCKOUT_DURATION.seconds//60} min")
    print(f"    Session timeout: {SESSION_TIMEOUT.seconds//60} min")
    app.run(debug=True, host='0.0.0.0', port=5000)
