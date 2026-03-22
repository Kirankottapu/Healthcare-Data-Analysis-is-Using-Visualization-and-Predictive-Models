# Healthcare Data Analysis using Visualization and Predictive Models

A full-stack web application that predicts disease risk using AI-powered analysis and interactive visual dashboards.

## 🌟 Features

- **Multi-Disease Prediction**: Heart Disease & Diabetes risk assessment using advanced ML algorithms
- **Interactive Dashboards**: Rich visualizations with Chart.js for data analysis
- **Secure Authentication**: Complete user management with bcrypt encryption
- **Health Score Calculator**: Comprehensive 0-100 health scoring system  
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **Data Export**: CSV export and individual report downloads
- **Real-time Analytics**: Live charts and trend analysis

## 🛠️ Tech Stack

| Layer           | Technology                     |
| --------------- | ------------------------------ |
| Backend         | Python Flask                   |
| Frontend        | HTML, CSS, JavaScript          |
| Machine Learning| Scikit-learn (Random Forest & Gradient Boosting) |
| Database        | MongoDB Atlas (Cloud)          |
| Visualization   | Chart.js                       |
| Security        | bcrypt, CSRF protection, Rate limiting |

## 📁 Project Structure

```
├── app.py                          # Flask backend (main server)
├── train_model.py                  # ML model training script  
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── DOCUMENTATION.md                # Detailed project documentation
├── .gitignore                      # Git ignore patterns
├── model/
│   ├── heart_model.pkl             # Heart disease classifier
│   ├── diabetes_model.pkl          # Diabetes risk classifier
│   ├── model.pkl                   # Legacy heart model
│   └── model_meta.pkl              # Model metadata
├── static/
│   ├── css/
│   │   └── style.css               # Application styles
│   └── js/
│       └── main.js                 # Frontend JavaScript
├── templates/                      # HTML templates (12 pages)
│   ├── home.html                   # Landing page
│   ├── login.html                  # Login page
│   ├── register.html               # Registration page
│   ├── dashboard.html              # User dashboard
│   ├── health_form.html            # Health assessment form
│   ├── result.html                 # Prediction results
│   ├── history.html                # Prediction history
│   ├── analytics.html              # Analytics dashboard
│   ├── bmi_calculator.html         # BMI calculator
│   ├── profile.html                # User profile
│   ├── forgot_password.html        # Password reset
│   ├── verify_otp.html             # OTP verification
│   └── reset_password.html         # New password form
└── Healthcare_Data_Analysis_Academic_Report.docx  # Academic documentation
```

## 🚀 Setup Instructions

### Prerequisites

1. **Python 3.8+** – Download from [python.org](https://www.python.org/downloads/)
2. **MongoDB Atlas Account** – Free tier at [mongodb.com/atlas](https://www.mongodb.com/atlas)
3. **Git** (for cloning) – Download from [git-scm.com](https://git-scm.com/)

### Step 1: Clone the Repository

```bash
git clone https://github.com/Jyothika2406/Healthcare-Data-Analysis-is-Using-Visualization-and-Predictive-Models.git
cd Healthcare-Data-Analysis-is-Using-Visualization-and-Predictive-Models
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Set Up MongoDB Atlas

1. Create account at [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Create a new cluster (free M0 tier)
3. Add your IP to Network Access
4. Create database user with password
5. Get connection string

### Step 4: Train ML Models

```bash
python train_model.py
```

This will:
- Generate healthcare datasets with realistic medical data
- Train Random Forest (heart disease) and Gradient Boosting (diabetes) models
- Display performance metrics (accuracy, precision, recall, F1-score)
- Save trained models in the `model/` folder

### Step 5: Run the Application

```bash
python app.py
```

🌐 **Server starts at:** http://localhost:5000

### Step 6: Use the Application

1. Open **http://localhost:5000** in your browser
2. **Register** a new account or **Login**
3. Navigate to **Dashboard** → **New Prediction**
4. Fill in the health assessment form
5. View your **risk prediction with probability**
6. Explore **Analytics Dashboard** for visualizations
7. Check **Prediction History** for past assessments
8. Export data using **CSV export** functionality

## 🔐 Security Features

- **CSRF Protection**: All POST forms protected with security tokens
- **Rate Limiting**: 5 login attempts per 15 minutes before lockout  
- **Session Management**: 30-minute timeout with secure session handling
- **Password Security**: bcrypt hashing with salt for password encryption
- **Input Validation**: Server-side validation for all user inputs
- **Data Encryption**: HTTPS enforcement for secure data transmission

## 🤖 Machine Learning Models

### Heart Disease Prediction
- **Algorithm**: Random Forest Classifier
- **Accuracy**: ~81% (5-fold cross-validation)
- **AUC-ROC**: ~99%
- **Dataset**: UCI Cleveland Heart Disease Database (297 patients)

### Diabetes Risk Assessment  
- **Algorithm**: Gradient Boosting Classifier
- **Accuracy**: ~75% (5-fold cross-validation)
- **AUC-ROC**: ~94%
- **Dataset**: Pima Indians Diabetes Database (768 patients)

### Key Input Features (16 total)
- Age, Gender, Blood Pressure, Cholesterol
- Heart Rate, Blood Sugar, BMI
- Lifestyle factors (smoking, exercise, alcohol)
- Clinical indicators (ECG, chest pain, etc.)

## 📊 Dashboard Features

- **Risk Distribution Charts**: Interactive pie charts
- **Health Timeline**: Trend analysis over time
- **BMI Calculator**: Built-in body mass index calculator
- **Health Score**: Comprehensive 0-100 scoring system
- **Export Options**: CSV download and individual reports
- **Dark Mode**: Eye-friendly dark theme option

## 🩺 Use Cases

- **Educational**: Medical and CS students learning ML in healthcare
- **Research**: Healthcare informatics and predictive modeling studies
- **Screening**: Preliminary health risk assessment (not diagnostic)
- **Prevention**: Early detection for preventive healthcare strategies

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| MongoDB connection error | Check internet connection and Atlas IP whitelist |
| Model not found | Run `python train_model.py` first |
| Port 5000 in use | Change port in `app.py` or kill existing process |
| CSRF token error | Refresh page and clear browser cookies |

## 📚 Documentation

- **DOCUMENTATION.md**: Complete technical documentation
- **Academic Report**: Formal project report (Word document)
- **Code Comments**: Inline documentation throughout codebase
- **API Endpoints**: RESTful endpoints for data access

## 🌍 Database Collections

- **users**: User accounts with encrypted passwords
- **predictions**: Health assessment history with timestamps
- **password_resets**: OTP tokens for password recovery
- **login_attempts**: Failed login tracking for security

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License

This project is developed for educational and research purposes.

**⚠️ Disclaimer**: This application provides AI-based risk assessment and is NOT a substitute for professional medical diagnosis. Always consult qualified healthcare professionals for medical advice.

## 👩‍💻 Developer

Developed by **Jyothika** — passionate about leveraging AI and data science for healthcare innovation.

**Guide**: Mrs D. Hima Bindu, M.Tech (Ph.D.)  
**Institution**: Raghu Engineering College (Autonomous)  
**Department**: Computer Science and Engineering (AI & ML)

---

⭐ **Star this repository if you found it helpful!**
