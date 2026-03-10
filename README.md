# Healthcare Data Analysis using Visualization and Predictive Models

A full-stack web application that predicts disease risk using AI-powered analysis and interactive visual dashboards.

## Tech Stack

| Layer           | Technology                     |
| --------------- | ------------------------------ |
| Backend         | Python Flask                   |
| Frontend        | HTML, CSS, JavaScript          |
| Machine Learning| Scikit-learn (Random Forest)   |
| Database        | MongoDB (PyMongo)              |
| Visualization   | Chart.js                       |

## Project Structure

```
├── app.py                  # Flask backend (main server)
├── train_model.py          # ML model training script
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── model/
│   ├── model.pkl           # Trained Random Forest model
│   └── model_meta.pkl      # Model metadata (accuracy, features)
├── static/
│   ├── css/
│   │   └── style.css       # Main stylesheet
│   └── js/
│       └── main.js         # Frontend JavaScript
└── templates/
    ├── home.html           # Landing page
    ├── login.html          # Login page
    ├── register.html       # Registration page
    ├── dashboard.html      # Main dashboard
    ├── health_form.html    # Health data input form
    ├── result.html         # Prediction result page
    ├── history.html        # Prediction history table
    └── profile.html        # User profile page
```

## Setup Instructions

### Prerequisites

1. **Python 3.8+** – Download from https://www.python.org/downloads/
2. **MongoDB** – Choose one option:
   - **Local MongoDB**: Download from https://www.mongodb.com/try/download/community
   - **MongoDB Atlas (Cloud)**: Free tier at https://www.mongodb.com/atlas

### Step 1: Install Python Dependencies

Open a terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

### Step 2: Set Up MongoDB

#### Option A: Local MongoDB
1. Install MongoDB Community Server
2. Start the MongoDB service:
   - **Windows**: MongoDB runs as a service automatically after installation
   - Or run: `mongod` in terminal
3. Default connection: `mongodb://localhost:27017/`

#### Option B: MongoDB Atlas (Cloud – Free)
1. Go to https://www.mongodb.com/atlas
2. Create a free account and cluster
3. Get your connection string (looks like: `mongodb+srv://username:password@cluster.xxxxx.mongodb.net/`)
4. Set the environment variable before running the app:

**Windows (PowerShell):**
```powershell
$env:MONGO_URI = "mongodb+srv://username:password@cluster.xxxxx.mongodb.net/"
```

**Windows (CMD):**
```cmd
set MONGO_URI=mongodb+srv://username:password@cluster.xxxxx.mongodb.net/
```

**Mac/Linux:**
```bash
export MONGO_URI="mongodb+srv://username:password@cluster.xxxxx.mongodb.net/"
```

### Step 3: Train the ML Model

```bash
python train_model.py
```

This will:
- Generate a healthcare dataset with realistic medical data
- Train a Random Forest classifier
- Display accuracy, precision, recall, and F1-score
- Save `model.pkl` and `model_meta.pkl` in the `model/` folder

### Step 4: Run the Application

```bash
python app.py
```

The server starts at: **http://localhost:5000**

### Step 5: Use the Application

1. Open **http://localhost:5000** in your browser
2. Click **Register** to create an account
3. **Login** with your credentials
4. On the **Dashboard**, click **Enter Health Details**
5. Fill in the health form and click **Predict Health Risk**
6. View your **result with charts**, health tips, and probability
7. Check **Prediction History** for past records
8. **Download reports** as text files

## Features

- **User Authentication**: Register/Login with bcrypt password hashing
- **Health Data Input**: Age, BP, sugar, height, weight, lifestyle habits
- **ML Prediction**: Random Forest model predicts High/Low risk with probability
- **Interactive Charts**: Pie charts, bar charts, and timeline graphs (Chart.js)
- **Prediction History**: Table of all past predictions with download option
- **User Profile**: View and update account information
- **Health Tips**: Contextual recommendations based on your data
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Report Download**: Download prediction reports as text files

## Troubleshooting

| Issue | Solution |
| ----- | -------- |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| MongoDB connection error | Ensure MongoDB is running (`mongod`) or check Atlas URI |
| Model not found | Run `python train_model.py` first |
| Port 5000 in use | Change port in `app.py` last line or kill existing process |

## MongoDB Collections

- **users**: `{username, email, password (hashed), created_at}`
- **predictions**: `{user_id, input_data, result, probability, tips, timestamp}`
