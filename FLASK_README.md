# 🌐 Flask Web Application - Job Application Automation

A beautiful, multi-user web interface for the automated job application system.

## 🎯 Features

### User Management
- ✅ User registration and authentication
- ✅ Secure password hashing
- ✅ Individual user settings and data
- ✅ Session management

### Dashboard
- ✅ Real-time statistics
- ✅ Application history
- ✅ Recent automation runs
- ✅ Quick actions

### Settings Page
- ✅ Upload resume (PDF)
- ✅ Configure API keys (Google Gemini, Hunter.io)
- ✅ Set email preferences
- ✅ Customize LinkedIn search URL
- ✅ **LinkedIn cookie for rate limit bypass** (optional)
- ✅ Adjust quality filters
- ✅ Custom AI prompts
- ✅ Exclude companies

### Automation
- ✅ One-click automation start
- ✅ Background job processing
- ✅ Progress tracking
- ✅ Email notifications

### Application Tracking
- ✅ View all applications
- ✅ Search by company
- ✅ Filter by score
- ✅ Track emails sent

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install Flask dependencies
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

The app will be available at: **http://localhost:5000**

### 3. Register an Account

1. Go to http://localhost:5000
2. Click "Register"
3. Fill in your details
4. Login with your credentials

### 4. Set Up Gmail API (One-Time Setup)

**⚠️ Important:** Before using the app, you need to set up Gmail API to send emails from your account!

1. Follow the complete guide: **`GMAIL_SETUP_GUIDE.md`**
2. Quick steps:
   - Create Google Cloud project
   - Enable Gmail API
   - Create OAuth credentials
   - Download `credentials.json`
   - Run `python auth_bootstrap.py`

**Each user needs their own Gmail setup!**

### 5. Configure Settings in Web App

1. Go to Settings page
2. Upload your resume (PDF)
3. Add your API keys:
   - Google Gemini API key
   - Hunter.io API key
4. Set your email preferences
5. Configure LinkedIn search URL
6. **(Optional)** Add LinkedIn cookie to avoid rate limiting
   - See `LINKEDIN_COOKIE_GUIDE.md` for instructions
7. Adjust filters and thresholds
8. Save settings

### 6. Start Automation

1. Go to Dashboard
2. Click "Start Automation"
3. Watch your applications being sent!

## 📁 Project Structure

```
Cold Email/
├── app.py                      # Flask application
├── templates/                  # HTML templates
│   ├── base.html              # Base template
│   ├── index.html             # Landing page
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── dashboard.html         # User dashboard
│   ├── settings.html          # Settings page
│   └── applications.html      # Applications list
├── static/                     # Static files (CSS, JS)
├── uploads/                    # User resume uploads
├── users.db                    # User database
├── user_*_jobs.db             # Per-user job databases
└── requirements.txt           # Python dependencies
```

## 🎨 Features in Detail

### User Dashboard

**Statistics Cards:**
- Total jobs processed
- Applications sent
- Jobs skipped
- Emails sent

**Recent Runs:**
- View last 5 automation runs
- See status, jobs processed, applications sent
- Track completion time

**Quick Actions:**
- Start automation (one click)
- Go to settings
- View applications

### Settings Page

**API Keys Section:**
- Google Gemini API key (for AI scoring)
- Hunter.io API key (for email discovery)
- Links to get API keys

**Email Settings:**
- Your name (for email signature)
- Your email (Gmail for sending)

**Job Search Settings:**
- LinkedIn search URL (with filters)
- Max days posted (1-90)
- Max applicants (1-10000)
- Min relevance score (0-100)
- Excluded companies (comma-separated)

**Custom AI Prompt:**
- Customize how AI scores jobs
- Use placeholders: {job_title}, {company}, {description}, {resume}
- Leave empty for default prompt

**Resume Upload:**
- Upload PDF resume
- See current resume status
- Replace anytime

### Applications Page

**Table View:**
- Company name
- Position title
- Relevance score (color-coded)
- Date applied
- Emails sent to
- Link to job posting

**Filtering:**
- Search by company
- Filter by score
- Sort by date

## 🔒 Security Features

### Password Security
- Passwords hashed with Werkzeug
- Secure password storage
- Session-based authentication

### Data Isolation
- Each user has separate database
- Resume files stored securely
- API keys encrypted in database

### Session Management
- Secure session cookies
- Auto-logout on browser close
- CSRF protection

## 🎨 UI/UX Features

### Modern Design
- Beautiful gradient backgrounds
- Card-based layout
- Responsive design (mobile-friendly)
- Bootstrap 5 components

### Icons
- Bootstrap Icons throughout
- Intuitive visual indicators
- Color-coded status badges

### Animations
- Smooth transitions
- Hover effects
- Loading indicators

### Alerts
- Flash messages for actions
- Color-coded alerts (success, error, warning)
- Auto-dismissible

## 🔧 Configuration

### Secret Key
⚠️ **Important:** Change the secret key in production!

```python
# In app.py
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
```

Generate a secure key:
```python
import secrets
print(secrets.token_hex(32))
```

### Upload Folder
```python
app.config['UPLOAD_FOLDER'] = 'uploads'
```

### Max File Size
```python
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
```

## 📊 Database Schema

### Users Table
- id (PRIMARY KEY)
- email (UNIQUE)
- password_hash
- name
- created_at

### User Settings Table
- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- google_api_key
- hunter_api_key
- sender_email
- sender_name
- resume_filename
- linkedin_search_url
- max_days_posted
- max_applicants
- min_relevance_score
- excluded_companies
- custom_prompt
- updated_at

### Job Runs Table
- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- status
- jobs_processed
- applications_sent
- started_at
- completed_at

## 🚀 Deployment

### Production Checklist

1. **Change Secret Key**
   ```python
   app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
   ```

2. **Disable Debug Mode**
   ```python
   app.run(debug=False)
   ```

3. **Use Production Server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

4. **Set Up HTTPS**
   - Use Let's Encrypt
   - Configure SSL certificates

5. **Environment Variables**
   ```bash
   export SECRET_KEY='your-secret-key'
   export FLASK_ENV='production'
   ```

6. **Database Backups**
   - Regular backups of users.db
   - Backup user job databases

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 🐛 Troubleshooting

### "No module named 'flask'"
```bash
pip install Flask Flask-Login
```

### "Upload folder doesn't exist"
```bash
mkdir uploads
```

### "Database locked"
- Close other connections
- Restart the application

### "Resume not found"
- Check uploads/ folder exists
- Verify file permissions

## 📈 Future Enhancements

- [ ] Email verification
- [ ] Password reset
- [ ] Real-time progress updates (WebSocket)
- [ ] Application analytics
- [ ] Export applications to CSV
- [ ] Schedule automation runs
- [ ] Email templates customization
- [ ] Multi-resume support
- [ ] Team/organization support

## 🎉 You're Ready!

Start the Flask app and enjoy the beautiful web interface!

```bash
python app.py
```

Then visit: **http://localhost:5000**

Happy job hunting! 🚀

