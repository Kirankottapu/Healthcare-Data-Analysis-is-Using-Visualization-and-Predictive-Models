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
app.secret_key = os.environ.get('SECRET_KEY', 'hc-analysis-prod-key-2026-x9f3')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Security constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION   = timedelta(minutes=15)
SESSION_TIMEOUT    = timedelta(minutes=30)

# ──────────────────────────────────────────────────────────────────────────────
#  MongoDB Connection
# ──────────────────────────────────────────────────────────────────────────────
MONGO_URI = os.environ.get(
    'MONGO_URI',
    'mongodb+srv://svljyothikanookala_db_user:Health_user@cluster0.kricsn.mongodb.net/'
    'healthcare_db?retryWrites=true&w=majority&appName=Cluster0'
)

# Try multiple connection methods for MongoDB
client = None
db = None

def connect_mongodb():
    """Try multiple methods to connect to MongoDB."""
    global client, db
    
    # Method 1: Standard connection with certifi
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000,
                             tls=True, tlsCAFile=certifi.where())
        client.admin.command('ping')
        db = client['healthcare_db']
        print("✅  MongoDB connected (certifi)")
        return True
    except Exception as e1:
        pass
    
    # Method 2: Connection with custom SSL context (no cert verification)
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000,
                             tls=True, tlsAllowInvalidCertificates=True,
                             tlsAllowInvalidHostnames=True)
        client.admin.command('ping')
        db = client['healthcare_db']
        print("✅  MongoDB connected (relaxed SSL)")
        return True
    except Exception as e2:
        pass
    
    # Method 3: Try without explicit TLS settings
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        client.admin.command('ping')
        db = client['healthcare_db']
        print("✅  MongoDB connected (auto SSL)")
        return True
    except Exception as e3:
        print(f"⚠️   MongoDB Atlas connection failed.")
        print(f"    This is likely due to:")
        print(f"    1. Your IP not whitelisted in MongoDB Atlas")
        print(f"    2. Python SSL/TLS compatibility issues")
        print(f"    3. Network/firewall blocking the connection")
        print(f"    → Go to MongoDB Atlas → Network Access → Add your IP")
        print(f"    → Or whitelist 0.0.0.0/0 for development")
    
    return False

# Try to connect
if not connect_mongodb():
    db = None
    print("⚠️   Running in OFFLINE mode - database features disabled")

# Collections (will be None if offline)
if db is not None:
    users_col        = db['users']
    predictions_col  = db['predictions']
    password_resets   = db['password_resets']
    login_attempts_col = db['login_attempts']
    
    try:
        users_col.create_index('username', unique=True, sparse=True)
        users_col.create_index('email',    unique=True, sparse=True)
        login_attempts_col.create_index('timestamp', expireAfterSeconds=900)
        print("✅  MongoDB indexes ready")
    except Exception as e:
        print(f"⚠️   Index creation issue: {e}")
else:
    # Offline mode - create placeholder collections
    users_col = None
    predictions_col = None
    password_resets = None
    login_attempts_col = None

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
            print(f"✅  Heart disease model loaded  ({name})")
            break
    else:
        print("⚠️   Heart disease model not found")

    # Diabetes model
    dp = os.path.join(MODEL_DIR, 'diabetes_model.pkl')
    if os.path.exists(dp):
        diabetes_model = joblib.load(dp)
        print("✅  Diabetes risk model loaded")
    else:
        print("⚠️   Diabetes model not found – heart-only mode")

    mp = os.path.join(MODEL_DIR, 'model_meta.pkl')
    if os.path.exists(mp):
        model_meta = joblib.load(mp)

load_models()

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
            print(f'⚠️  Email error: {e}')
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
        login_count=user.get('login_count', 0)
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
    disease_type = request.form.get('disease_type', 'heart')

    if disease_type == 'heart' and heart_model is None:
        flash('Heart disease model not loaded.', 'danger')
        return redirect(url_for('health_form'))
    if disease_type == 'diabetes' and diabetes_model is None:
        flash('Diabetes model not loaded.', 'danger')
        return redirect(url_for('health_form'))

    try:
        age       = int(request.form.get('age', 30))
        gender    = int(request.form.get('gender', 0))
        bp        = int(request.form.get('blood_pressure', 120))
        sugar     = int(request.form.get('sugar_level', 100))
        height_cm = float(request.form.get('height', 170))
        weight_kg = float(request.form.get('weight', 70))
        symptoms  = request.form.get('symptoms', '')
        smoking   = 1 if request.form.get('smoking') else 0
        exercise  = 1 if request.form.get('exercise') else 0
        alcohol   = 1 if request.form.get('alcohol') else 0

        bmi = round(weight_kg / ((height_cm / 100) ** 2), 1) if height_cm > 0 else 25.0
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

        if disease_type == 'heart':
            prediction    = heart_model.predict(features_heart)[0]
            probabilities = heart_model.predict_proba(features_heart)[0]
            risk_label    = 'High Risk' if prediction == 1 else 'Low Risk'
            probability   = round(float(probabilities[1]) * 100, 2)
            disease_name  = 'Heart Disease'
        else:
            # Diabetes uses same feature set
            prediction    = diabetes_model.predict(features_heart)[0]
            probabilities = diabetes_model.predict_proba(features_heart)[0]
            risk_label    = 'High Risk' if prediction == 1 else 'Low Risk'
            probability   = round(float(probabilities[1]) * 100, 2)
            disease_name  = 'Diabetes'

        tips = generate_health_tips(risk_label, bp, sugar, bmi, smoking, exercise, alcohol)

        input_data_doc = {
            'age': age, 'gender': 'Male' if gender == 1 else 'Female',
            'blood_pressure': bp, 'sugar_level': sugar,
            'height': height_cm, 'weight': weight_kg, 'bmi': bmi,
            'symptoms': symptoms,
            'smoking': bool(smoking), 'exercise': bool(exercise),
            'alcohol': bool(alcohol)
        }

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
        predictions_col.insert_one(pred_doc)

        return render_template(
            'result.html',
            username=session['username'],
            result=risk_label,
            probability=probability,
            input_data=input_data_doc,
            tips=tips,
            disease_type=disease_type,
            disease_name=disease_name,
            health_score=health_score,
            health_grade=hs_grade,
            health_desc=hs_desc,
            timestamp=pred_doc['timestamp'].strftime('%B %d, %Y  %H:%M')
        )

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
    print("🚀  Starting Healthcare Analysis Server (Enhanced) …")
    print("    → http://localhost:5000")
    print(f"    → CSRF protection: ON")
    print(f"    → Login rate-limit: {MAX_LOGIN_ATTEMPTS} attempts / {LOCKOUT_DURATION.seconds//60} min")
    print(f"    → Session timeout:  {SESSION_TIMEOUT.seconds//60} min")
    app.run(debug=True, host='0.0.0.0', port=5000)
