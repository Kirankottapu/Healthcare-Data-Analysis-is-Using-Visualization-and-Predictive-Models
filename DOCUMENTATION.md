# Healthcare Data Analysis - Using Visualization and Predictive Models

## Documentation

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Installation & Setup](#installation--setup)
6. [Machine Learning Models](#machine-learning-models)
7. [API Endpoints](#api-endpoints)
8. [Pages & Routes](#pages--routes)
9. [Security Features](#security-features)
10. [Database Schema](#database-schema)
11. [Usage Guide](#usage-guide)
12. [Troubleshooting](#troubleshooting)

---

## Project Overview

A comprehensive healthcare web application that uses **Machine Learning** to predict health risks for:

- **Heart Disease Risk** - Using Random Forest Classifier
- **Diabetes Risk** - Using Gradient Boosting Classifier

The application provides data visualization, health score calculations, and personalized health tips based on user inputs.

---

## Features

### Core Features
| Feature | Description |
|---------|-------------|
| **Multi-Disease Prediction** | Heart Disease & Diabetes risk assessment |
| **Health Score Calculator** | 0-100 holistic health scoring system |
| **BMI Calculator** | Built-in BMI calculation tool |
| **Analytics Dashboard** | Rich visualizations with Chart.js |
| **Prediction History** | Track all past health assessments |
| **CSV Export** | Download prediction history as CSV |
| **PDF Reports** | Generate individual health reports |

### Security Features
| Feature | Description |
|---------|-------------|
| CSRF Protection | Token-based protection on all POST forms |
| Rate Limiting | 5 login attempts / 15 min before lockout |
| Session Timeout | Auto logout after 30 minutes inactivity |
| Strong Passwords | 8+ chars with uppercase, lowercase, digit, special |
| Password Reset | OTP-based email verification |

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Flask 3.0.0 (Python) |
| **Database** | MongoDB Atlas |
| **ML Models** | scikit-learn (RandomForest, GradientBoosting) |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Charts** | Chart.js |
| **Authentication** | bcrypt encryption |

---

## Project Structure

```
Healthcare Data Analysis/
├── app.py                    # Main Flask application
├── train_model.py            # ML model training script
├── requirements.txt          # Python dependencies
├── README.md                 # Basic readme
├── DOCUMENTATION.md          # This documentation
│
├── model/                    # Trained ML models
│   ├── heart_model.pkl       # Heart disease classifier
│   ├── diabetes_model.pkl    # Diabetes risk classifier
│   ├── model.pkl             # Legacy heart model
│   └── model_meta.pkl        # Model metadata
│
├── static/
│   ├── css/
│   │   └── style.css         # Application styles
│   └── js/
│       └── main.js           # Frontend JavaScript
│
└── templates/                # Jinja2 HTML templates
    ├── home.html             # Landing page
    ├── login.html            # Login form
    ├── register.html         # Registration form
    ├── dashboard.html        # User dashboard
    ├── health_form.html      # Health assessment form
    ├── result.html           # Prediction results
    ├── history.html          # Prediction history
    ├── analytics.html        # Analytics dashboard
    ├── bmi_calculator.html   # BMI calculator
    ├── profile.html          # User profile
    ├── forgot_password.html  # Password reset request
    ├── verify_otp.html       # OTP verification
    └── reset_password.html   # New password form
```

---

## Installation & Setup

### Prerequisites
- Python 3.8+
- MongoDB Atlas account (or local MongoDB)
- pip package manager

### Step 1: Clone/Download the Project

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

**Dependencies:**
```
Flask==3.0.0
pymongo==4.6.1
bcrypt==4.1.2
scikit-learn==1.3.2
pandas==2.0.3
numpy==1.24.4
joblib==1.3.2
certifi==2023.11.17
imbalanced-learn==0.11.0
```

### Step 3: Train the Models (if needed)
```bash
python train_model.py
```

### Step 4: Run the Application
```bash
python app.py
```

### Step 5: Access the Application
Open browser and navigate to: **http://localhost:5000**

---

## Machine Learning Models

### Heart Disease Model

| Property | Value |
|----------|-------|
| **Algorithm** | Random Forest Classifier |
| **Data Source** | UCI Cleveland Heart Disease Database |
| **Original Samples** | 297 real patient records |
| **Training Samples** | 1500 (augmented with SMOTE) |
| **Accuracy** | ~81% (5-fold cross-validation) |
| **AUC-ROC** | ~99% |

### Diabetes Model

| Property | Value |
|----------|-------|
| **Algorithm** | Gradient Boosting Classifier |
| **Data Source** | Pima Indians Diabetes Database |
| **Original Samples** | 768 real patient records |
| **Training Samples** | 1500 (augmented with SMOTE) |
| **Accuracy** | ~75% (5-fold cross-validation) |
| **AUC-ROC** | ~94% |

### Input Features (16 features)

| # | Feature | Description | Range |
|---|---------|-------------|-------|
| 1 | age | Patient age in years | 25-80 |
| 2 | sex | Gender (0=Female, 1=Male) | 0-1 |
| 3 | trestbps | Resting blood pressure (mm Hg) | 80-200 |
| 4 | chol | Serum cholesterol (mg/dl) | 100-400 |
| 5 | fbs | Fasting blood sugar > 120 mg/dl | 0-1 |
| 6 | restecg | Resting ECG results | 0-2 |
| 7 | thalach | Maximum heart rate achieved | 70-210 |
| 8 | exang | Exercise induced angina | 0-1 |
| 9 | oldpeak | ST depression induced by exercise | 0-6 |
| 10 | slope | Slope of peak exercise ST segment | 0-2 |
| 11 | ca | Number of major vessels colored | 0-3 |
| 12 | thal | Thalassemia | 1-3 |
| 13 | smoking | Patient smokes | 0-1 |
| 14 | exercise | Regular exercise | 0-1 |
| 15 | alcohol | Alcohol consumption | 0-1 |
| 16 | bmi | Body Mass Index | 15-50 |

---

## API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/register` | User registration |
| GET/POST | `/login` | User login |
| GET | `/logout` | Logout user |
| GET/POST | `/forgot-password` | Initiate password reset |
| GET/POST | `/verify-otp` | Verify OTP code |
| GET/POST | `/reset-password` | Set new password |

### Main Application Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | Home page | No |
| GET | `/dashboard` | User dashboard | Yes |
| GET | `/health-form` | Health assessment form | Yes |
| POST | `/predict` | Submit health prediction | Yes |
| GET | `/history` | View prediction history | Yes |
| GET | `/analytics` | Analytics dashboard | Yes |
| GET | `/bmi-calculator` | BMI calculator page | Yes |
| GET | `/profile` | User profile | Yes |

### API Data Endpoints

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/api/chart-data` | Basic chart data | JSON |
| GET | `/api/analytics-data` | Full analytics data | JSON |
| POST | `/api/health-score` | Calculate health score | JSON |

### Export Endpoints

| Method | Endpoint | Description | Format |
|--------|----------|-------------|--------|
| GET | `/export-csv` | Export all predictions | CSV |
| GET | `/download-report/<id>` | Download single report | TXT |

---

## Pages & Routes

### Public Pages (No Login Required)
- **/** - Home page with app introduction
- **/login** - User login form
- **/register** - New user registration
- **/forgot-password** - Password reset request

### Protected Pages (Login Required)
- **/dashboard** - Main user dashboard with stats
- **/health-form** - Health data input form
- **/result** - Prediction results display
- **/history** - All past predictions
- **/analytics** - Visual analytics dashboard
- **/bmi-calculator** - BMI calculation tool
- **/profile** - User profile information

---

## Security Features

### 1. CSRF Protection
Every POST form includes a CSRF token validated on the server.

### 2. Login Rate Limiting
```python
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 15 minutes
```
After 5 failed attempts, the account is locked for 15 minutes.

### 3. Session Management
```python
SESSION_TIMEOUT = 30 minutes
```
Sessions expire after 30 minutes of inactivity.

### 4. Password Requirements
- Minimum 8 characters
- At least 1 uppercase letter (A-Z)
- At least 1 lowercase letter (a-z)
- At least 1 digit (0-9)
- At least 1 special character (!@#$%^&*...)

### 5. Password Encryption
Passwords are hashed with **bcrypt** (salt + hash).

---

## Database Schema

### Users Collection
```javascript
{
  "_id": ObjectId,
  "username": String (unique),
  "email": String (unique),
  "password": Binary (bcrypt hash),
  "created_at": DateTime,
  "last_login": DateTime,
  "login_count": Number,
  "is_active": Boolean
}
```

### Predictions Collection
```javascript
{
  "_id": ObjectId,
  "user_id": String,
  "disease_type": String ("heart" | "diabetes"),
  "disease_name": String,
  "input_data": {
    "age": Number,
    "gender": String,
    "blood_pressure": Number,
    "sugar_level": Number,
    "height": Number,
    "weight": Number,
    "bmi": Number,
    "symptoms": String,
    "smoking": Boolean,
    "exercise": Boolean,
    "alcohol": Boolean
  },
  "result": String ("High Risk" | "Low Risk"),
  "probability": Number (0-100),
  "health_score": Number (0-100),
  "tips": Array[String],
  "timestamp": DateTime
}
```

### Password Resets Collection
```javascript
{
  "email": String,
  "otp": String,
  "created_at": DateTime,
  "expires_at": DateTime
}
```

---

## Usage Guide

### 1. Registration
1. Go to `/register`
2. Enter username, email, and strong password
3. Click "Register"

### 2. Login
1. Go to `/login`
2. Enter credentials
3. Click "Login"

### 3. Make a Health Prediction
1. Go to Dashboard → "New Prediction" or `/health-form`
2. Select disease type (Heart Disease or Diabetes)
3. Fill in all health data:
   - Age, Gender
   - Blood Pressure, Sugar Level
   - Height, Weight
   - Lifestyle factors (smoking, exercise, alcohol)
   - Any symptoms
4. Click "Predict"
5. View results with risk level, probability, and tips

### 4. View Analytics
1. Go to `/analytics`
2. View charts:
   - Risk distribution pie chart
   - Probability trend over time
   - Blood pressure, sugar, BMI trends
   - Health score progression

### 5. Export Data
- **CSV Export**: Dashboard → "Export CSV"
- **Individual Report**: History → "Download Report"

---

## Troubleshooting

### MongoDB Connection Error
```
⚠️ MongoDB not available at startup: SSL handshake failed
```
**Solutions:**
1. Check internet connection
2. Update Python SSL certificates: `pip install --upgrade certifi`
3. Use a local MongoDB instance

### Model Not Found Error
```
⚠️ Heart disease model not found
```
**Solution:** Run `python train_model.py` to train & save models

### Port Already in Use
```
Address already in use: 5000
```
**Solution:** Change port in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

### CSRF Token Error
```
Security token expired – please try again.
```
**Solution:** Refresh the page and try again. Clear browser cookies if persists.

---

## Environment Variables (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | Auto-generated |
| `MONGO_URI` | MongoDB connection string | Atlas cluster |
| `SMTP_EMAIL` | Email for password reset | None (dev mode) |
| `SMTP_PASSWORD` | Email app password | None (dev mode) |

---

## Credits

### Data Sources
- **Heart Disease**: UCI Machine Learning Repository - Cleveland Database
  - 303 real patient records from Cleveland Clinic Foundation
- **Diabetes**: Pima Indians Diabetes Database
  - 768 real patient records from National Institute of Diabetes

---

## License

This project is developed for educational purposes.

**Disclaimer:** This application provides AI-based risk assessment and is NOT a substitute for professional medical diagnosis. Always consult a qualified healthcare professional for medical advice.

---

**Application URL:** http://localhost:5000

**Last Updated:** March 2026
