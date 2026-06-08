import pickle
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, session, send_file
import io
import os
import json
import sqlite3



def init_db():
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
USER_FILE = 'users.json'

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_FILE, 'w') as f:
        json.dump(users, f)

users = load_users()

app = Flask(__name__)
init_db()
app.secret_key = 'churnpredictor123'

users = {}

# Model load karo
model = pickle.load(open('models/model.sav', 'rb'))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()

        try:
            cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login', message='Account created successfully'))
        except:
            conn.close()
            return render_template('signup.html', message="Username already exists!")
        save_users(users)
        return redirect(url_for('login', message='Account created successfully'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = request.args.get('message', '')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cur.fetchone()

        conn.close()

        if user:
            session['username'] = username
            return redirect(url_for('predict'))
        else:
            message = 'Invalid username or password!'
    return render_template('login.html', message=message)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/predict')
def predict():
    return render_template('predict.html')

@app.route('/manual', methods=['GET', 'POST'])
def manual():
    if request.method == 'POST':
        gender = request.form['gender']
        senior_citizen = int(request.form['senior_citizen'])
        contract = request.form['contract']
        tenure_group = request.form['tenure_group']
        internet_service = request.form['internet_service']
        monthly_charges = float(request.form['monthly_charges'])
        tenure = float(request.form['tenure'])
        total_charges = monthly_charges * tenure
        payment_method = request.form['payment_method']
        online_security = request.form['online_security']
        tech_support = request.form['tech_support']

        input_dict = {
            'SeniorCitizen': [senior_citizen],
            'MonthlyCharges': [monthly_charges],
            'TotalCharges': [total_charges],
            'gender_Female': [1 if gender == 'Female' else 0],
            'gender_Male': [1 if gender == 'Male' else 0],
            'Contract_Month-to-month': [1 if contract == 'Month-to-month' else 0],
            'Contract_One year': [1 if contract == 'One year' else 0],
            'Contract_Two year': [1 if contract == 'Two year' else 0],
            'InternetService_DSL': [1 if internet_service == 'DSL' else 0],
            'InternetService_Fiber optic': [1 if internet_service == 'Fiber optic' else 0],
            'InternetService_No': [1 if internet_service == 'No' else 0],
            'PaymentMethod_Bank transfer (automatic)': [1 if payment_method == 'Bank transfer (automatic)' else 0],
            'PaymentMethod_Credit card (automatic)': [1 if payment_method == 'Credit card (automatic)' else 0],
            'PaymentMethod_Electronic check': [1 if payment_method == 'Electronic check' else 0],
            'PaymentMethod_Mailed check': [1 if payment_method == 'Mailed check' else 0],
            'OnlineSecurity_No': [1 if online_security == 'No' else 0],
            'OnlineSecurity_No internet service': [1 if online_security == 'No internet service' else 0],
            'OnlineSecurity_Yes': [1 if online_security == 'Yes' else 0],
            'TechSupport_No': [1 if tech_support == 'No' else 0],
            'TechSupport_No internet service': [1 if tech_support == 'No internet service' else 0],
            'TechSupport_Yes': [1 if tech_support == 'Yes' else 0],
            'tenure_group_1 - 12': [1 if tenure_group == '1 - 12' else 0],
            'tenure_group_13 - 24': [1 if tenure_group == '13 - 24' else 0],
            'tenure_group_25 - 36': [1 if tenure_group == '25 - 36' else 0],
            'tenure_group_37 - 48': [1 if tenure_group == '37 - 48' else 0],
            'tenure_group_49 - 60': [1 if tenure_group == '49 - 60' else 0],
            'tenure_group_61 - 72': [1 if tenure_group == '61 - 72' else 0],
        }

        input_df = pd.DataFrame(input_dict)
        model_columns = model.feature_names_in_
        for col in model_columns:
            if col not in input_df.columns:
                input_df[col] = 0
        input_df = input_df[model_columns]

        proba = model.predict_proba(input_df)[0]
        prediction = model.predict(input_df)[0]

        if prediction == 1:
            probability = round(proba[1] * 100, 1)
            confidence = round(max(proba) * 100, 1)
            pred_text = 'Churn'
            risk = 'High Risk: Churn'
        else:
            probability = round(proba[1] * 100, 1)
            confidence = round(max(proba) * 100, 1)
            pred_text = 'No Churn'
            risk = 'Low Risk: No Churn'

        return redirect(url_for('result',
                        prob=probability,
                        confidence=confidence,
                        pred=pred_text,
                        class_pred=int(prediction),
                        risk=risk))

    return render_template('manual.html')


@app.route('/result')
def result():
    prob = float(request.args.get('prob'))
    confidence = float(request.args.get('confidence'))
    pred = request.args.get('pred')
    class_pred = request.args.get('class_pred')
    risk = request.args.get('risk')
    return render_template('result.html', prob=prob, confidence=confidence,
                           pred=pred, class_pred=class_pred, risk=risk)


@app.route('/csv', methods=['POST'])
def csv_upload():
    if request.method == 'POST':
        # File lo
        file = request.files['csv_file']
        df = pd.read_csv(file)

        # ✅ DATA CLEANING
        # Missing values handle karo
        df.dropna(how='all', inplace=True)
        df.fillna(df.mode().iloc[0], inplace=True)

        # TotalCharges numeric karo
        if 'TotalCharges' in df.columns:
            df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce')
            df['TotalCharges'].fillna(df['TotalCharges'].median(), inplace=True)

        # Churn column drop karo agar hai
        if 'Churn' in df.columns:
            df.drop(columns=['Churn'], inplace=True)

        # customerID drop karo agar hai
        if 'customerID' in df.columns:
            df.drop(columns=['customerID'], inplace=True)

        # tenure_group banao agar tenure column hai
        if 'tenure' in df.columns:
            labels = ["{0} - {1}".format(i, i + 11) for i in range(1, 72, 12)]
            df['tenure_group'] = pd.cut(df['tenure'], range(1, 80, 12),
                                         right=False, labels=labels)
            df.drop(columns=['tenure'], inplace=True)

        # ✅ DUMMIES BANAO
        df_dummies = pd.get_dummies(df, dtype=int)

        # Model columns ke saath align karo
        model_columns = model.feature_names_in_
        for col in model_columns:
            if col not in df_dummies.columns:
                df_dummies[col] = 0
        df_dummies = df_dummies[model_columns]

        # ✅ PREDICTION KARO
        predictions = model.predict(df_dummies)
        probabilities = model.predict_proba(df_dummies)[:, 1] * 100

        # Risk category assign karo
        def get_risk(prob):
            if prob >= 70:
                return 'High Risk'
            elif prob >= 40:
                return 'Medium Risk'
            else:
                return 'Low Risk'

        df['Churn_Prediction'] = predictions
        df['Churn_Probability'] = probabilities.round(1)
        df['Risk_Category'] = df['Churn_Probability'].apply(get_risk)

        # ✅ STATS CALCULATE KARO
        total = len(df)
        high_risk = len(df[df['Risk_Category'] == 'High Risk'])
        medium_risk = len(df[df['Risk_Category'] == 'Medium Risk'])
        low_risk = len(df[df['Risk_Category'] == 'Low Risk'])

        # ✅ KEY FEATURES
        feature_importance = pd.Series(
            model.feature_importances_,
            index=model_columns
        ).sort_values(ascending=False).head(5)

        key_features = feature_importance.index.tolist()

        # ✅ PREVIEW - first 15 rows
        preview = df.head(15).to_dict(orient='records')
        columns = df.columns.tolist()

        # Session mein store karo download ke liye
        output_path = 'static/output/churn_predictions.csv'
        os.makedirs('static/output', exist_ok=True)
        df.to_csv(output_path, index=False)

        return render_template('csv_result.html',
                               preview=preview,
                               columns=columns,
                               total=total,
                               high_risk=high_risk,
                               medium_risk=medium_risk,
                               low_risk=low_risk,
                               key_features=key_features)

    return render_template('csv_upload.html')


@app.route('/download_csv')
def download_csv():
    return send_file('static/output/churn_predictions.csv',
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='churn_predictions.csv')

@app.route('/dashboard')
def dashboard():
    # CSV data load karo
    try:
        df = pd.read_csv('static/output/churn_predictions.csv')

        total = len(df)
        high_risk = len(df[df['Risk_Category'] == 'High Risk'])
        medium_risk = len(df[df['Risk_Category'] == 'Medium Risk'])
        low_risk = len(df[df['Risk_Category'] == 'Low Risk'])
        churn_count = len(df[df['Churn_Prediction'] == 1])
        no_churn_count = len(df[df['Churn_Prediction'] == 0])

        # Feature importance
        feature_importance = pd.Series(
            model.feature_importances_,
            index=model.feature_names_in_
        ).sort_values(ascending=False).head(8)
        feature_names = feature_importance.index.tolist()
        feature_scores = feature_importance.values.round(3).tolist()

        # Probabilities
        probabilities = df['Churn_Probability'].tolist()

        # Analysis data
        gender_data = {}
        if 'gender' in df.columns:
            gender_data = df['gender'].value_counts().to_dict()

        contract_data = {}
        if 'Contract' in df.columns:
            contract_data = df['Contract'].value_counts().to_dict()

        internet_data = {}
        if 'InternetService' in df.columns:
            internet_data = df['InternetService'].value_counts().to_dict()

        payment_data = {}
        if 'PaymentMethod' in df.columns:
            payment_data = df['PaymentMethod'].value_counts().to_dict()

        monthly_charges = []
        if 'MonthlyCharges' in df.columns:
            monthly_charges = df['MonthlyCharges'].tolist()

        return render_template('dashboard.html',
                               total=total,
                               high_risk=high_risk,
                               medium_risk=medium_risk,
                               low_risk=low_risk,
                               churn_count=churn_count,
                               no_churn_count=no_churn_count,
                               feature_names=feature_names,
                               feature_scores=feature_scores,
                               probabilities=probabilities,
                               gender_data=gender_data,
                               contract_data=contract_data,
                               internet_data=internet_data,
                               payment_data=payment_data,
                               monthly_charges=monthly_charges)

    except:
        return render_template('dashboard.html',
                               total=0, high_risk=0, medium_risk=0,
                               low_risk=0, churn_count=0, no_churn_count=0,
                               feature_names=[], feature_scores=[],
                               probabilities=[], gender_data={},
                               contract_data={}, internet_data={},
                               payment_data={}, monthly_charges=[])

@app.route('/csv_result')
def csv_result_page():
    try:
        df = pd.read_csv('static/output/churn_predictions.csv')
        total = len(df)
        high_risk = len(df[df['Risk_Category'] == 'High Risk'])
        medium_risk = len(df[df['Risk_Category'] == 'Medium Risk'])
        low_risk = len(df[df['Risk_Category'] == 'Low Risk'])
        key_features = pd.Series(
            model.feature_importances_,
            index=model.feature_names_in_
        ).sort_values(ascending=False).head(5).index.tolist()
        preview = df.head(15).to_dict(orient='records')
        columns = df.columns.tolist()
        return render_template('csv_result.html',
                               preview=preview,
                               columns=columns,
                               total=total,
                               high_risk=high_risk,
                               medium_risk=medium_risk,
                               low_risk=low_risk,
                               key_features=key_features)
    except:
        return redirect(url_for('predict'))

if __name__ == '__main__':
    app.run(debug=True)


