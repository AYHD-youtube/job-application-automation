# 🌐 Automated Job Application Web App

A beautiful Flask web application that automates your job search! Scrape LinkedIn jobs, score them with AI, generate personalized cover letters, find HR emails, and send applications automatically.

## ✨ Features

### 🎯 Core Automation
- **LinkedIn Job Scraping** - Automatically scrapes job listings from LinkedIn
- **AI-Powered Scoring** - Uses Google Gemini AI to score job relevance
- **Smart Filtering** - Filters by posting date, applicant count, and quality
- **Cover Letter Generation** - AI-generated personalized cover letters
- **Email Discovery** - Finds HR emails using Hunter.io API
- **Automated Sending** - Sends applications via Gmail API
- **LinkedIn Cookie Support** - Avoid rate limiting with authenticated requests

### 🌐 Web Interface
- **User Registration & Login** - Secure multi-user support
- **Beautiful Dashboard** - View stats and recent applications
- **Settings Page** - Configure everything in one place
- **Resume Upload** - Upload your PDF resume
- **Application Tracking** - View all your applications
- **One-Click Automation** - Start automation with a button

### 🔒 Security
- Password hashing with Werkzeug
- Per-user databases and settings
- Secure session management
- API keys stored securely

## 📋 Prerequisites

- Python 3.8 or higher
- Google Cloud account (for Gmail API and Gemini AI)
- Hunter.io account (for email finding)
- Gmail account

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Mac/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up Gmail API (Required for Each User)

**⚠️ Important:** Each person needs their own Gmail API credentials to send emails from their account!

**Quick Setup:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "Job Automation")
3. Enable **Gmail API**
4. Configure **OAuth consent screen** (External, add yourself as test user)
5. Create **OAuth 2.0 credentials** (Desktop app type)
6. Download as `credentials.json` and place in project folder
7. Run authentication:
   ```bash
   python auth_bootstrap.py
   ```
   This opens a browser for authorization and creates `token.json`

**📖 Detailed Guide:** See `GMAIL_SETUP_GUIDE.md` for complete step-by-step instructions with screenshots descriptions and troubleshooting.

**For Your Friends:** Each user must do this setup with their own Google account to send emails from their Gmail!

### 3. Get API Keys

**Google Gemini API:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create API key
3. Copy the key

**Hunter.io API:**
1. Sign up at [Hunter.io](https://hunter.io/)
2. Go to API section
3. Copy your API key (free tier: 25 searches/month)

### 4. Run the Web App

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the Flask app
python app.py
```

The app will be available at: **http://localhost:5000**

### 5. Configure in Web Interface

1. **Register Account**
   - Go to http://localhost:5000
   - Click "Register"
   - Fill in your details

2. **Login**
   - Use your email and password

3. **Configure Settings**
   - Click "Settings" in navbar
   - Upload your resume (PDF)
   - Add your API keys:
     - Google Gemini API key
     - Hunter.io API key
   - Set your email preferences
   - Configure LinkedIn search URL
   - **(Optional)** Add LinkedIn cookie to avoid rate limiting
   - Adjust quality filters
   - Save settings

4. **Start Automation**
   - Go to Dashboard
   - Click "Start Automation"
   - Watch your applications!

## 📖 Documentation

- **README.md** - This file (main documentation)
- **GMAIL_SETUP_GUIDE.md** - Complete Gmail API setup guide (step-by-step)
- **FLASK_README.md** - Web app documentation and features
- **LINKEDIN_COOKIE_GUIDE.md** - How to get LinkedIn cookie for rate limit bypass

## 🎯 How It Works

1. **Scrape** - Fetches job listings from your LinkedIn search URL
2. **Filter** - Applies quality filters (days posted, applicant count, etc.)
3. **Score** - AI scores each job based on your resume (0-100)
4. **Generate** - Creates personalized cover letter for high-scoring jobs
5. **Find** - Discovers HR email addresses using Hunter.io
6. **Send** - Sends application email via Gmail
7. **Track** - Logs everything in database

## 🔧 Configuration Options

### Job Search Settings
- LinkedIn search URL (customize job type, location, etc.)
- Max days posted (1-90 days)
- Max applicants (competition level)
- Min relevance score (60-100)
- Excluded companies (comma-separated)

### Advanced Settings
- Custom AI prompts for scoring
- LinkedIn cookie for rate limit bypass
- Email templates

## 📊 Database

The app uses SQLite databases:
- `users.db` - User accounts and settings
- `user_1_jobs.db`, `user_2_jobs.db`, etc. - Per-user job tracking

Each user's database tracks:
- All processed jobs
- Application status
- Emails sent
- Skipped jobs with reasons

## 🔒 Privacy & Security

- All data stored locally
- API keys encrypted in database
- Per-user data isolation
- Passwords hashed with Werkzeug
- No data sharing between users

## 🛠️ Project Structure

```
Cold Email/
├── app.py                     # Flask web application
├── requirements.txt           # Python dependencies
├── auth_bootstrap.py          # Google OAuth setup
│
├── Backend Modules:
│   ├── job_scraper.py         # LinkedIn scraping
│   ├── resume_handler.py      # Resume processing
│   ├── ai_scorer.py           # AI scoring & letters
│   ├── email_finder.py        # Email discovery
│   ├── email_sender.py        # Gmail sending
│   ├── database.py            # SQLite database
│   └── linkedin.py            # HTML parsing
│
├── Web App:
│   ├── templates/             # HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   ├── settings.html
│   │   └── applications.html
│   ├── static/                # CSS/JS (optional)
│   └── uploads/               # User resume uploads
│
├── Documentation:
│   ├── README.md              # This file
│   ├── FLASK_README.md        # Detailed web app guide
│   └── LINKEDIN_COOKIE_GUIDE.md # Cookie setup
│
└── User Data (gitignored):
    ├── credentials.json       # Google OAuth credentials
    ├── token.json             # OAuth token
    ├── users.db               # User accounts
    ├── user_*_jobs.db         # Job tracking databases
    └── venv/                  # Virtual environment
```

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"
```bash
pip install Flask Flask-Login
```

### "Address already in use" (Port 5000)
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Or change port in app.py
app.run(port=5001)
```

### "credentials.json not found"
You need to set up Google OAuth credentials. See step 2 above.

### "Can't upload resume"
```bash
mkdir -p uploads
```

### Rate Limited by LinkedIn
Add your LinkedIn cookie in Settings. See `LINKEDIN_COOKIE_GUIDE.md` for instructions.

## ⚖️ Legal & Ethical Considerations

**Important Disclaimer:**
- Web scraping may violate LinkedIn's Terms of Service
- Use at your own risk
- Intended for personal job search automation only
- Don't scrape aggressively (respect rate limits)
- Consider LinkedIn's official API for production use

**Best Practices:**
- Personal use only
- Reasonable request rates
- Respect robots.txt
- Don't scrape private data
- Use responsibly

## 🎉 Features Roadmap

- [ ] Email templates customization
- [ ] Application scheduling
- [ ] Email analytics
- [ ] Job recommendations
- [ ] Chrome extension
- [ ] Mobile responsive design

## 📝 License

This project is for educational and personal use only. Use responsibly and at your own risk.

## 🤝 Contributing

This is a personal automation project. Feel free to fork and customize for your needs!

## 📧 Support

For issues or questions:
1. Check `FLASK_README.md` for detailed documentation
2. Check `LINKEDIN_COOKIE_GUIDE.md` for cookie setup
3. Review troubleshooting section above

---

**Happy Job Hunting! 🚀**

Built with ❤️ using Flask, Google Gemini AI, and Hunter.io
