#!/usr/bin/env python3
# app.py
"""
Flask web application for automated job applications
Multi-user support with authentication and customizable settings
"""
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import sqlite3
import json
from datetime import datetime
import threading
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import pickle

# Import our automation modules
from database import JobDatabase
from job_scraper import scrape_job_list, scrape_job_details, normalize_job_data, check_quality
from resume_handler import extract_text_from_pdf
from ai_scorer import score_job_relevance, generate_cover_letter
from email_finder import find_company_domain_and_emails, find_emails_with_fallback
from email_sender import send_to_multiple_recipients

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['CREDENTIALS_FOLDER'] = 'user_credentials'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Database directory
DATABASE_DIR = 'databases'
os.makedirs(DATABASE_DIR, exist_ok=True)

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CREDENTIALS_FOLDER'], exist_ok=True)

# OAuth 2.0 scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send', 
          'https://www.googleapis.com/auth/gmail.compose']

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    """User class for Flask-Login"""
    def __init__(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name


def get_user_db():
    """Get user database connection"""
    db_path = os.path.join(DATABASE_DIR, 'users.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_user_db():
    """Initialize user database"""
    conn = get_user_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # User settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            google_api_key TEXT,
            hunter_api_key TEXT,
            gmail_credentials TEXT,
            gmail_token BLOB,
            gmail_authenticated INTEGER DEFAULT 0,
            sender_email TEXT,
            sender_name TEXT,
            resume_filename TEXT,
            linkedin_search_url TEXT,
            linkedin_cookie TEXT,
            max_days_posted INTEGER DEFAULT 14,
            max_applicants INTEGER DEFAULT 500,
            min_relevance_score INTEGER DEFAULT 60,
            excluded_companies TEXT,
            custom_prompt TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Job runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'running',
            jobs_processed INTEGER DEFAULT 0,
            applications_sent INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()


# Initialize database on startup (runs when Gunicorn loads the app)
init_user_db()


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID"""
    conn = get_user_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data['id'], user_data['email'], user_data['name'])
    return None


@app.route('/')
def index():
    """Home page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        if not email or not password or not name:
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        conn = get_user_db()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            flash('Email already registered', 'error')
            conn.close()
            return render_template('register.html')
        
        # Create user
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            (email, password_hash, name)
        )
        user_id = cursor.lastrowid
        
        # Create default settings
        cursor.execute(
            "INSERT INTO user_settings (user_id) VALUES (?)",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_user_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data['id'], user_data['email'], user_data['name'])
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password', 'error')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    # Get user settings
    conn = get_user_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (current_user.id,))
    settings = cursor.fetchone()
    
    # Get recent job runs
    cursor.execute("""
        SELECT * FROM job_runs 
        WHERE user_id = ? 
        ORDER BY started_at DESC 
        LIMIT 5
    """, (current_user.id,))
    recent_runs = cursor.fetchall()
    
    conn.close()
    
    # Get application stats from user's database
    user_db_path = os.path.join(DATABASE_DIR, f"user_{current_user.id}_jobs.db")
    if os.path.exists(user_db_path):
        with JobDatabase(user_db_path) as db:
            stats = db.get_application_stats()
    else:
        stats = {'total_jobs': 0, 'applications_sent': 0, 'jobs_skipped': 0, 'emails_sent': 0}
    
    return render_template('dashboard.html', 
                         settings=settings, 
                         recent_runs=recent_runs,
                         stats=stats)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User settings page"""
    conn = get_user_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        
        # Ensure user_settings row exists (create if doesn't)
        cursor.execute("SELECT id FROM user_settings WHERE user_id = ?", (current_user.id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO user_settings (user_id) VALUES (?)", (current_user.id,))
        
        # Update settings
        cursor.execute("""
            UPDATE user_settings SET
                google_api_key = ?,
                hunter_api_key = ?,
                sender_email = ?,
                sender_name = ?,
                linkedin_search_url = ?,
                linkedin_cookie = ?,
                max_days_posted = ?,
                max_applicants = ?,
                min_relevance_score = ?,
                excluded_companies = ?,
                custom_prompt = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (
            request.form.get('google_api_key'),
            request.form.get('hunter_api_key'),
            request.form.get('sender_email'),
            request.form.get('sender_name'),
            request.form.get('linkedin_search_url'),
            request.form.get('linkedin_cookie', ''),
            request.form.get('max_days_posted', 14),
            request.form.get('max_applicants', 500),
            request.form.get('min_relevance_score', 60),
            request.form.get('excluded_companies', ''),
            request.form.get('custom_prompt', ''),
            current_user.id
        ))
        
        
        conn.commit()
        flash('Settings updated successfully!', 'success')
        
        # Redirect to GET to prevent form resubmission
        conn.close()
        return redirect(url_for('settings'))
    
    # GET request - fetch settings
    cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (current_user.id,))
    user_settings = cursor.fetchone()
    
    # If no settings exist yet (shouldn't happen but just in case)
    if not user_settings:
        cursor.execute("INSERT INTO user_settings (user_id) VALUES (?)", (current_user.id,))
        conn.commit()
        cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (current_user.id,))
        user_settings = cursor.fetchone()
    
    conn.close()
    
    
    return render_template('settings.html', settings=user_settings)


@app.route('/upload_resume', methods=['POST'])
@login_required
def upload_resume():
    """Upload resume file"""
    if 'resume' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('settings'))
    
    file = request.files['resume']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('settings'))
    
    if file and file.filename.endswith('.pdf'):
        filename = f"user_{current_user.id}_resume.pdf"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Update settings
        conn = get_user_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE user_settings SET resume_filename = ? WHERE user_id = ?",
            (filename, current_user.id)
        )
        conn.commit()
        conn.close()
        
        flash('Resume uploaded successfully!', 'success')
    else:
        flash('Please upload a PDF file', 'error')
    
    return redirect(url_for('settings'))


@app.route('/upload_gmail_credentials', methods=['POST'])
@login_required
def upload_gmail_credentials():
    """Upload Gmail OAuth credentials.json file"""
    if 'credentials' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('settings'))
    
    file = request.files['credentials']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('settings'))
    
    if file and file.filename.endswith('.json'):
        try:
            # Read and validate JSON
            credentials_data = json.load(file)
            
            # Check if it's a valid OAuth credentials file
            if 'installed' not in credentials_data and 'web' not in credentials_data:
                flash('Invalid credentials file. Please upload the credentials.json from Google Cloud Console.', 'error')
                return redirect(url_for('settings'))
            
            # Save credentials for this user
            filename = f"user_{current_user.id}_credentials.json"
            filepath = os.path.join(app.config['CREDENTIALS_FOLDER'], filename)
            
            # Reset file pointer and save
            file.seek(0)
            file.save(filepath)
            
            # Update database
            conn = get_user_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE user_settings SET gmail_credentials = ?, gmail_authenticated = 0 WHERE user_id = ?",
                (filename, current_user.id)
            )
            conn.commit()
            conn.close()
            
            flash('Gmail credentials uploaded! Now click "Authorize Gmail" to complete setup.', 'success')
        except json.JSONDecodeError:
            flash('Invalid JSON file', 'error')
        except Exception as e:
            flash(f'Error uploading credentials: {str(e)}', 'error')
    else:
        flash('Please upload a JSON file', 'error')
    
    return redirect(url_for('settings'))


@app.route('/authorize_gmail')
@login_required
def authorize_gmail():
    """Initiate Gmail OAuth flow"""
    # Get user's credentials file
    conn = get_user_db()
    cursor = conn.cursor()
    cursor.execute("SELECT gmail_credentials FROM user_settings WHERE user_id = ?", (current_user.id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result or not result['gmail_credentials']:
        flash('Please upload credentials.json first', 'error')
        return redirect(url_for('settings'))
    
    credentials_path = os.path.join(app.config['CREDENTIALS_FOLDER'], result['gmail_credentials'])
    
    if not os.path.exists(credentials_path):
        flash('Credentials file not found. Please upload again.', 'error')
        return redirect(url_for('settings'))
    
    try:
        # Create flow
        redirect_uri = url_for('gmail_callback', _external=True)
        print(f"DEBUG: Gmail redirect URI: {redirect_uri}")
        
        flow = Flow.from_client_secrets_file(
            credentials_path,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Store state in session
        session['oauth_state'] = state
        session['oauth_user_id'] = current_user.id
        
        return redirect(authorization_url)
    except Exception as e:
        flash(f'Error starting authorization: {str(e)}', 'error')
        return redirect(url_for('settings'))


@app.route('/gmail/callback')
def gmail_callback():
    """Handle Gmail OAuth callback"""
    if 'oauth_state' not in session or 'oauth_user_id' not in session:
        flash('Invalid OAuth state', 'error')
        return redirect(url_for('login'))
    
    user_id = session['oauth_user_id']
    state = session['oauth_state']
    
    # Get user's credentials file
    conn = get_user_db()
    cursor = conn.cursor()
    cursor.execute("SELECT gmail_credentials FROM user_settings WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if not result or not result['gmail_credentials']:
        conn.close()
        flash('Credentials not found', 'error')
        return redirect(url_for('settings'))
    
    credentials_path = os.path.join(app.config['CREDENTIALS_FOLDER'], result['gmail_credentials'])
    
    try:
        # Create flow
        flow = Flow.from_client_secrets_file(
            credentials_path,
            scopes=SCOPES,
            state=state,
            redirect_uri=url_for('gmail_callback', _external=True)
        )
        
        # Fetch token
        flow.fetch_token(authorization_response=request.url)
        
        # Get credentials
        credentials = flow.credentials
        
        # Serialize credentials
        creds_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        # Save to database
        cursor.execute("""
            UPDATE user_settings 
            SET gmail_token = ?, gmail_authenticated = 1, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (pickle.dumps(creds_data), user_id))
        conn.commit()
        conn.close()
        
        # Clear session
        session.pop('oauth_state', None)
        session.pop('oauth_user_id', None)
        
        flash('Gmail authorized successfully! You can now send emails.', 'success')
        return redirect(url_for('settings'))
        
    except Exception as e:
        conn.close()
        flash(f'Error completing authorization: {str(e)}', 'error')
        return redirect(url_for('settings'))


@app.route('/revoke_gmail')
@login_required
def revoke_gmail():
    """Revoke Gmail authorization"""
    conn = get_user_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_settings 
        SET gmail_token = NULL, gmail_authenticated = 0
        WHERE user_id = ?
    """, (current_user.id,))
    conn.commit()
    conn.close()
    
    flash('Gmail authorization revoked', 'info')
    return redirect(url_for('settings'))


@app.route('/run_automation', methods=['POST'])
@login_required
def run_automation():
    """Start automation run"""
    # Create job run record
    conn = get_user_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO job_runs (user_id, status) VALUES (?, 'running')",
        (current_user.id,)
    )
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Start automation in background thread
    thread = threading.Thread(
        target=run_automation_task,
        args=(current_user.id, run_id)
    )
    thread.daemon = True
    thread.start()
    
    flash('Automation started! Check back soon for results.', 'success')
    return redirect(url_for('dashboard'))


def run_automation_task(user_id, run_id):
    """Background task to run automation"""
    # This is a simplified version - you'd want to add more error handling
    # and progress tracking in production
    
    # Get user settings
    conn = get_user_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
    settings = dict(cursor.fetchone())
    conn.close()
    
    # Initialize user's database
    user_db_path = os.path.join(DATABASE_DIR, f"user_{user_id}_jobs.db")
    db = JobDatabase(user_db_path)
    
    # Get resume text
    resume_path = os.path.join(app.config['UPLOAD_FOLDER'], settings['resume_filename'])
    with open(resume_path, 'rb') as f:
        resume_text = extract_text_from_pdf(f.read())
    
    # Scrape jobs
    linkedin_cookie = settings.get('linkedin_cookie')
    job_urls = scrape_job_list(settings['linkedin_search_url'], linkedin_cookie)
    
    jobs_processed = 0
    applications_sent = 0
    
    # Process each job (simplified)
    for job_url in job_urls[:10]:  # Limit to 10 for demo
        if db.job_already_applied(job_url):
            continue
        
        # Process job (simplified - you'd want the full logic from main.py)
        jobs_processed += 1
        # ... rest of processing logic
    
    # Update run status
    conn = get_user_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE job_runs SET
            status = 'completed',
            jobs_processed = ?,
            applications_sent = ?,
            completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (jobs_processed, applications_sent, run_id))
    conn.commit()
    conn.close()
    
    db.close()


@app.route('/applications')
@login_required
def applications():
    """View user's applications"""
    user_db_path = os.path.join(DATABASE_DIR, f"user_{current_user.id}_jobs.db")
    
    if not os.path.exists(user_db_path):
        return render_template('applications.html', applications=[])
    
    with JobDatabase(user_db_path) as db:
        apps = db.get_recent_applications(50)
    
    return render_template('applications.html', applications=apps)


if __name__ == '__main__':
    init_user_db()
    app.run(debug=True, host='0.0.0.0', port=3000)

