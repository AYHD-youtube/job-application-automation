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
import sqlite3
import os
import json
from datetime import datetime
import threading
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle

# Import our automation modules
from database import JobDatabase
from job_scraper import scrape_job_list, scrape_job_details, normalize_job_data, check_quality
from resume_handler import extract_text_from_pdf
from ai_scorer import score_job_relevance, generate_cover_letter
from email_finder import find_company_domain_and_emails, find_emails_with_fallback
from email_sender import send_to_multiple_recipients
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['CREDENTIALS_FOLDER'] = 'user_credentials'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure Flask to work behind a reverse proxy (Caddy)
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=0)

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
            custom_cover_letter_prompt TEXT,
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
            stop_requested INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Migration: Add stop_requested column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE job_runs ADD COLUMN stop_requested INTEGER DEFAULT 0")
        print("Added stop_requested column to job_runs table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("stop_requested column already exists")
        else:
            print(f"Error adding stop_requested column: {e}")
    
    # Migration: Add custom_cover_letter_prompt column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN custom_cover_letter_prompt TEXT")
        print("Added custom_cover_letter_prompt column to user_settings table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("custom_cover_letter_prompt column already exists")
        else:
            print(f"Error adding custom_cover_letter_prompt column: {e}")
    
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
    
    # Check if automation is currently running (only recent ones, not stuck ones)
    cursor.execute("""
        SELECT id, started_at FROM job_runs 
        WHERE user_id = ? AND status = 'running' AND started_at > datetime('now', '-10 minutes')
        ORDER BY started_at DESC 
        LIMIT 1
    """, (current_user.id,))
    current_run = cursor.fetchone()
    
    # Clean up stuck "running" status runs (older than 10 minutes)
    cursor.execute("""
        UPDATE job_runs 
        SET status = 'failed', completed_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND status = 'running' 
        AND started_at < datetime('now', '-10 minutes')
    """, (current_user.id,))
    conn.commit()
    conn.close()
    
    # Get stats from user's job database
    user_db_path = os.path.join(DATABASE_DIR, f"user_{current_user.id}_jobs.db")
    if os.path.exists(user_db_path):
        try:
            with JobDatabase(user_db_path) as db:
                stats = db.get_application_stats()
        except Exception as e:
            print(f"Error reading user database: {e}")
            stats = {'total_jobs': 0, 'applications_sent': 0, 'jobs_skipped': 0, 'emails_sent': 0}
    else:
        stats = {'total_jobs': 0, 'applications_sent': 0, 'jobs_skipped': 0, 'emails_sent': 0}
    
    return render_template('dashboard.html', 
                         settings=settings, 
                         recent_runs=recent_runs,
                         current_run=current_run,
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
                custom_cover_letter_prompt = ?,
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
            request.form.get('custom_cover_letter_prompt', ''),
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
        # Create flow - force HTTPS for redirect URI
        redirect_uri = url_for('gmail_callback', _external=True)
        if redirect_uri.startswith('http://'):
            redirect_uri = redirect_uri.replace('http://', 'https://')
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
        # Create flow - force HTTPS for redirect URI
        redirect_uri = url_for('gmail_callback', _external=True)
        if redirect_uri.startswith('http://'):
            redirect_uri = redirect_uri.replace('http://', 'https://')
        
        flow = Flow.from_client_secrets_file(
            credentials_path,
            scopes=SCOPES,
            state=state,
            redirect_uri=redirect_uri
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
    # Try to revoke the token with Google first
    conn = get_user_db()
    cursor = conn.cursor()
    cursor.execute("SELECT gmail_token FROM user_settings WHERE user_id = ?", (current_user.id,))
    result = cursor.fetchone()
    
    if result and result['gmail_token']:
        try:
            import requests
            creds_data = pickle.loads(result['gmail_token'])
            if 'token' in creds_data and creds_data['token']:
                # Revoke the token with Google
                revoke_url = 'https://oauth2.googleapis.com/revoke'
                requests.post(revoke_url, 
                            params={'token': creds_data['token']},
                            headers={'content-type': 'application/x-www-form-urlencoded'})
        except Exception as e:
            print(f"Error revoking token: {e}")
    
    # Clear the token from database
    cursor.execute("""
        UPDATE user_settings 
        SET gmail_token = NULL, gmail_authenticated = 0
        WHERE user_id = ?
    """, (current_user.id,))
    conn.commit()
    conn.close()
    
    flash('Gmail authorization revoked. You can now re-authorize with the correct scopes.', 'info')
    return redirect(url_for('settings'))


@app.route('/run_automation', methods=['POST'])
@login_required
def run_automation():
    """Start automation run"""
    # Check if there's already a running automation (only recent ones)
    conn = get_user_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM job_runs WHERE user_id = ? AND status = 'running' AND started_at > datetime('now', '-10 minutes')",
        (current_user.id,)
    )
    if cursor.fetchone():
        conn.close()
        flash('Automation is already running!', 'warning')
        return redirect(url_for('dashboard'))
    
    # Clean up any stuck "running" status runs before starting new one
    cursor.execute(
        "UPDATE job_runs SET status = 'failed', completed_at = CURRENT_TIMESTAMP WHERE user_id = ? AND status = 'running'",
        (current_user.id,)
    )
    conn.commit()
    
    # Create job run record
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


@app.route('/stop_automation', methods=['POST'])
@login_required
def stop_automation():
    """Stop running automation"""
    conn = get_user_db()
    cursor = conn.cursor()
    
    # Find the current running automation (only recent ones, not stuck ones)
    cursor.execute(
        "SELECT id FROM job_runs WHERE user_id = ? AND status = 'running' AND started_at > datetime('now', '-10 minutes')",
        (current_user.id,)
    )
    run = cursor.fetchone()
    
    if run:
        # Mark as stop requested
        cursor.execute(
            "UPDATE job_runs SET stop_requested = 1 WHERE id = ?",
            (run[0],)
        )
        conn.commit()
        flash('Stop request sent. Automation will stop after current job.', 'info')
    else:
        # Clean up any stuck "running" status runs
        cursor.execute(
            "UPDATE job_runs SET status = 'failed', completed_at = CURRENT_TIMESTAMP WHERE user_id = ? AND status = 'running'",
            (current_user.id,)
        )
        conn.commit()
        flash('No active automation found. Any stuck runs have been cleaned up.', 'warning')
    
    conn.close()
    return redirect(url_for('dashboard'))


def should_apply_to_job(job_data, settings):
    """Check if job meets quality criteria"""
    try:
        # Check if company is excluded
        excluded_companies = settings.get('excluded_companies', '').lower().split(',')
        company = job_data.get('company', '').lower().strip()
        if company in excluded_companies:
            return False
        
        # Check job age
        max_days = settings.get('max_days_posted', 14)
        if 'days_posted' in job_data and job_data['days_posted'] > max_days:
            return False
        
        # Check applicant count
        max_applicants = settings.get('max_applicants', 500)
        if 'applicant_count' in job_data and job_data['applicant_count'] > max_applicants:
            return False
        
        return True
    except Exception as e:
        print(f"Error checking job quality: {e}")
        return False


def score_job_with_ai(job_data, resume_text, google_api_key):
    """Score job relevance using AI"""
    try:
        return score_job_relevance(job_data, resume_text, google_api_key)
    except Exception as e:
        print(f"Error scoring job: {e}")
        return 0


def find_company_domain_and_email(company_name, hunter_api_key):
    """Find company domain and HR email using Hunter.io"""
    try:
        # Use the existing email finder function
        result = find_company_domain_and_emails(company_name, hunter_api_key)
        
        if result and result.get('emails'):
            # Return the domain and first email found
            domain = result.get('domain', '')
            email = result['emails'][0]  # Get first email from list
            print(f"  Found email: {email} for {company_name}")
            return domain, email
        
        print(f"  No emails found for {company_name}")
        return '', ''
    except Exception as e:
        print(f"Error finding company email: {e}")
        return '', ''


def send_application_email(sender_email, sender_name, hr_email, job_title, company, cover_letter, settings):
    """Send application email with resume attachment using Gmail API"""
    try:
        # Get Gmail credentials
        conn = get_user_db()
        cursor = conn.cursor()
        cursor.execute("SELECT gmail_token FROM user_settings WHERE user_id = ?", (settings.get('user_id', 1),))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result['gmail_token']:
            print("No Gmail token found")
            return False
        
        # Load credentials
        creds_data = pickle.loads(result['gmail_token'])
        
        # Create credentials object
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
        # Refresh credentials if needed
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                print("Credentials are invalid and cannot be refreshed")
                return False
        
        service = build('gmail', 'v1', credentials=creds)
        
        # Get resume file path
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], settings['resume_filename'])
        if not os.path.exists(resume_path):
            print(f"Resume file not found: {resume_path}")
            return False
        
        # Read resume file
        with open(resume_path, 'rb') as f:
            resume_data = f.read()
        
        # Create multipart email with attachment
        import email.mime.multipart
        import email.mime.text
        import email.mime.base
        
        # Create message
        msg = email.mime.multipart.MIMEMultipart()
        msg['To'] = hr_email
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['Subject'] = f"Application for {job_title} at {company}"
        
        # Add cover letter as HTML body
        html_part = email.mime.text.MIMEText(cover_letter, 'html')
        msg.attach(html_part)
        
        # Add resume as attachment
        resume_attachment = email.mime.base.MIMEBase('application', 'pdf')
        resume_attachment.set_payload(resume_data)
        import email.encoders
        email.encoders.encode_base64(resume_attachment)
        resume_attachment.add_header(
            'Content-Disposition',
            f'attachment; filename="{settings["resume_filename"]}"'
        )
        msg.attach(resume_attachment)
        
        # Encode message
        import base64
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        
        # Send email
        message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        print(f"  Email sent successfully with resume attachment: {message.get('id')}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def run_automation_task(user_id, run_id):
    """Background task to run automation"""
    try:
        # Get user settings
        conn = get_user_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
        settings = dict(cursor.fetchone())
        settings['user_id'] = user_id  # Add user_id to settings
        conn.close()
        
        # Check if required settings are configured
        if not settings.get('linkedin_search_url'):
            print(f"User {user_id}: No LinkedIn search URL configured")
            return
        
        if not settings.get('google_api_key'):
            print(f"User {user_id}: No Google API key configured")
            return
            
        if not settings.get('hunter_api_key'):
            print(f"User {user_id}: No Hunter API key configured")
            return
        
        # Initialize user's database
        user_db_path = os.path.join(DATABASE_DIR, f"user_{user_id}_jobs.db")
        
        # Ensure the databases directory exists
        os.makedirs(DATABASE_DIR, exist_ok=True)
        print(f"User {user_id}: Creating database at {user_db_path}")
        
        db = JobDatabase(user_db_path)
        print(f"User {user_id}: Database created successfully")
        
        # Get resume text
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], settings['resume_filename'])
        if not os.path.exists(resume_path):
            print(f"User {user_id}: Resume file not found at {resume_path}")
            return
            
        with open(resume_path, 'rb') as f:
            resume_text = extract_text_from_pdf(f.read())
        
        print(f"User {user_id}: Starting job scraping...")
        
        # Scrape jobs
        linkedin_cookie = settings.get('linkedin_cookie')
        job_urls = scrape_job_list(settings['linkedin_search_url'], linkedin_cookie)
        
        print(f"User {user_id}: Found {len(job_urls)} job URLs")
        
        jobs_processed = 0
        applications_sent = 0
        jobs_skipped = 0
        
        # Process each job
        for i, job_url in enumerate(job_urls[:20]):  # Limit to 20 jobs
            try:
                # Check for stop request before processing each job
                conn = get_user_db()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT stop_requested FROM job_runs WHERE id = ?",
                    (run_id,)
                )
                stop_requested = cursor.fetchone()
                conn.close()
                
                if stop_requested and stop_requested[0]:
                    print(f"User {user_id}: Stop requested, ending automation")
                    break
                
                print(f"User {user_id}: Processing job {i+1}/{min(len(job_urls), 20)}: {job_url}")
                
                # Check if already applied
                if db.job_already_applied(job_url):
                    print(f"User {user_id}: Job already applied to, skipping")
                    jobs_skipped += 1
                    continue
                
                # Scrape job details
                try:
                    job_data = scrape_job_details(job_url, linkedin_cookie)
                    if not job_data:
                        print(f"User {user_id}: Failed to scrape job details")
                        jobs_skipped += 1
                        continue
                except Exception as e:
                    print(f"User {user_id}: Error scraping job details from {job_url}: {e}")
                    jobs_skipped += 1
                    # Add delay after rate limiting errors
                    if "429" in str(e):
                        print(f"User {user_id}: Rate limited, waiting 5 seconds...")
                        time.sleep(5)
                    continue
                
                jobs_processed += 1
                
                # Apply filters
                if not should_apply_to_job(job_data, settings):
                    print(f"User {user_id}: Job filtered out")
                    jobs_skipped += 1
                    continue
                
                # Score job with AI
                score_result = score_job_with_ai(job_data, resume_text, settings['google_api_key'])
                
                # Handle both dict and int return types
                if isinstance(score_result, dict):
                    relevance_score = score_result.get('score', 0)
                else:
                    relevance_score = score_result
                
                print(f"User {user_id}: Job scored {relevance_score}/100")
                
                if relevance_score < settings.get('min_relevance_score', 60):
                    print(f"User {user_id}: Job score too low ({relevance_score})")
                    jobs_skipped += 1
                    continue
                
                # Find company domain and email
                company_domain, hr_email = find_company_domain_and_email(
                    job_data.get('company', ''), 
                    settings['hunter_api_key']
                )
                
                if not hr_email:
                    print(f"User {user_id}: No HR email found for {job_data.get('company', '')}")
                    jobs_skipped += 1
                    continue
                
                # Generate cover letter
                # Create scoring data from the AI score result
                scoring_data = {
                    'score': relevance_score,
                    'reasoning': 'AI-generated cover letter',
                    'key_matches': [],
                    'missing_skills': []
                }
                
                # Create resume URL - use a more reliable approach
                resume_url = f"Resume attached as PDF file"
                
                cover_letter = generate_cover_letter(
                    job_data, 
                    resume_text, 
                    scoring_data,
                    settings['google_api_key'],
                    resume_url,
                    settings.get('custom_cover_letter_prompt')
                )
                
                # Send email
                if send_application_email(
                    settings['sender_email'],
                    settings['sender_name'],
                    hr_email,
                    job_data.get('job_title', ''),
                    job_data.get('company', ''),
                    cover_letter,
                    settings
                ):
                    print(f"User {user_id}: Application sent to {hr_email}")
                    applications_sent += 1
                    
                    # Record application in database
                    try:
                        app_id = db.record_application(
                            job_url=job_url,
                            job_title=job_data.get('job_title', ''),
                            company=job_data.get('company', ''),
                            hr_email=hr_email,
                            relevance_score=relevance_score,
                            status='sent'
                        )
                        print(f"User {user_id}: Application recorded with ID {app_id}")
                    except Exception as e:
                        print(f"User {user_id}: Error recording application: {e}")
                else:
                    print(f"User {user_id}: Failed to send email to {hr_email}")
                    jobs_skipped += 1
                
                # Small delay between applications
                time.sleep(2)
                
            except Exception as e:
                print(f"User {user_id}: Error processing job {job_url}: {str(e)}")
                jobs_skipped += 1
                continue
        
        # Check if automation was stopped
        conn = get_user_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT stop_requested FROM job_runs WHERE id = ?",
            (run_id,)
        )
        stop_requested = cursor.fetchone()
        
        if stop_requested and stop_requested[0]:
            print(f"User {user_id}: Automation stopped by user - Processed: {jobs_processed}, Applied: {applications_sent}, Skipped: {jobs_skipped}")
            status = 'stopped'
        else:
            print(f"User {user_id}: Automation completed - Processed: {jobs_processed}, Applied: {applications_sent}, Skipped: {jobs_skipped}")
            status = 'completed'
        
        # Debug: Check what's in the user database
        try:
            stats = db.get_application_stats()
            print(f"User {user_id}: Database stats after completion: {stats}")
        except Exception as e:
            print(f"User {user_id}: Error getting database stats: {e}")
        
        # Update run status
        cursor.execute("""
            UPDATE job_runs SET
                status = ?,
                jobs_processed = ?,
                applications_sent = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, jobs_processed, applications_sent, run_id))
        conn.commit()
        conn.close()
        
        db.close()
        
    except Exception as e:
        print(f"User {user_id}: Automation failed: {str(e)}")
        
        # Update run status to failed
        conn = get_user_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE job_runs SET
                status = 'failed',
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (run_id,))
        conn.commit()
        conn.close()


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

