# 📧 Gmail API Setup Guide

## Why Do You Need This?

The app sends job applications from **YOUR Gmail account**. To do this securely, you need to set up Google OAuth credentials so the app can send emails on your behalf.

**Important:** Each user needs their own `credentials.json` file from their Google account!

---

## 🚀 Complete Setup (Step-by-Step)

### Step 1: Go to Google Cloud Console

1. Open: **https://console.cloud.google.com/**
2. Sign in with **your Gmail account** (the one you want to send emails from)

### Step 2: Create a New Project

1. Click the **project dropdown** at the top (says "Select a project")
2. Click **"NEW PROJECT"**
3. Fill in:
   - **Project name:** `Job Application Automation` (or any name)
   - **Organization:** Leave as default
4. Click **"CREATE"**
5. Wait a few seconds for the project to be created
6. Make sure the new project is selected (check top bar)

### Step 3: Enable Gmail API

1. In the left sidebar, click **"APIs & Services"** → **"Library"**
   - Or go directly to: https://console.cloud.google.com/apis/library
2. In the search bar, type: **"Gmail API"**
3. Click on **"Gmail API"**
4. Click the blue **"ENABLE"** button
5. Wait for it to enable (takes a few seconds)

### Step 4: Configure OAuth Consent Screen

**This is required before creating credentials!**

1. Go to **"APIs & Services"** → **"OAuth consent screen"**
   - Or: https://console.cloud.google.com/apis/credentials/consent
2. Choose **"External"** (unless you have Google Workspace)
3. Click **"CREATE"**
4. Fill in the required fields:
   - **App name:** `Job Application Automation`
   - **User support email:** Your email
   - **Developer contact email:** Your email
5. Click **"SAVE AND CONTINUE"**
6. **Scopes page:** Click **"SAVE AND CONTINUE"** (skip this)
7. **Test users page:** 
   - Click **"+ ADD USERS"**
   - Enter **your Gmail address** (the one you'll use)
   - Click **"ADD"**
   - Click **"SAVE AND CONTINUE"**
8. **Summary page:** Click **"BACK TO DASHBOARD"**

### Step 5: Create OAuth 2.0 Credentials

1. Go to **"APIs & Services"** → **"Credentials"**
   - Or: https://console.cloud.google.com/apis/credentials
2. Click **"+ CREATE CREDENTIALS"** at the top
3. Select **"OAuth client ID"**
4. If prompted to configure consent screen, you already did it in Step 4
5. Fill in:
   - **Application type:** Select **"Desktop app"**
   - **Name:** `Job Automation Desktop` (or any name)
6. Click **"CREATE"**
7. A popup appears with your credentials
8. Click **"DOWNLOAD JSON"**
9. Save the file

### Step 6: Rename and Place the File

1. The downloaded file has a long name like:
   ```
   client_secret_123456789-abcdefg.apps.googleusercontent.com.json
   ```
2. **Rename it to:** `credentials.json`
3. **Move it to your project folder:**
   ```
   /Users/ayhd/Development/Cold Email/credentials.json
   ```

### Step 7: Run Authentication

Now you need to authorize the app to use your Gmail:

```bash
# Make sure you're in the project directory
cd "/Users/ayhd/Development/Cold Email"

# Activate virtual environment
source venv/bin/activate

# Run authentication
python auth_bootstrap.py
```

**What happens:**
1. A browser window will open
2. You'll see "Google hasn't verified this app" - **This is normal!**
3. Click **"Advanced"** → **"Go to Job Application Automation (unsafe)"**
4. Click **"Allow"** to grant permissions
5. The browser will show "The authentication flow has completed"
6. A file called `token.json` will be created

**Done!** Your Gmail is now connected! ✅

---

## 🔒 Security & Privacy

### Is This Safe?

**Yes!** Here's why:
- ✅ You're creating credentials in **your own** Google account
- ✅ OAuth is Google's official secure authentication method
- ✅ The app can only access what you explicitly allow
- ✅ You can revoke access anytime from Google Account settings
- ✅ `credentials.json` and `token.json` are in `.gitignore` (never uploaded to GitHub)

### What Permissions Does It Need?

The app requests:
- **Gmail Send** - To send application emails from your account
- **Gmail Compose** - To create email drafts

It **CANNOT**:
- ❌ Read your existing emails
- ❌ Delete emails
- ❌ Access other Google services (unless you enable them)

### Revoke Access Anytime

1. Go to: https://myaccount.google.com/permissions
2. Find "Job Application Automation"
3. Click "Remove Access"

---

## 📋 Troubleshooting

### "Google hasn't verified this app"

**This is normal!** You're the developer of your own app. 

**Solution:**
1. Click **"Advanced"**
2. Click **"Go to [Your App Name] (unsafe)"**
3. Click **"Allow"**

This warning appears because you haven't submitted your app to Google for verification (which is only needed for public apps with 100+ users).

### "Access blocked: This app's request is invalid"

**Cause:** OAuth consent screen not configured.

**Solution:** Go back to Step 4 and complete the OAuth consent screen setup.

### "The OAuth client was not found"

**Cause:** Wrong project selected or credentials not created.

**Solution:** 
1. Make sure you're in the correct project (check top bar)
2. Go to Credentials page and verify OAuth client exists

### "credentials.json not found"

**Solution:**
1. Make sure you downloaded the JSON file
2. Rename it to exactly `credentials.json` (no extra characters)
3. Place it in the project root directory
4. Check the file exists: `ls -la credentials.json`

### "redirect_uri_mismatch"

**Cause:** Wrong application type selected.

**Solution:** 
1. Delete the OAuth client
2. Create a new one
3. Make sure to select **"Desktop app"** (not "Web application")

### Browser doesn't open automatically

**Solution:**
1. Look for a URL in the terminal output
2. Copy and paste it into your browser manually
3. Complete the authorization
4. Copy the authorization code back to the terminal if prompted

---

## 👥 For Your Friends

### Each User Needs Their Own Setup!

**Important:** Each person using the app needs to:

1. ✅ Create their own Google Cloud project
2. ✅ Enable Gmail API in their project
3. ✅ Create their own OAuth credentials
4. ✅ Download their own `credentials.json`
5. ✅ Run `python auth_bootstrap.py` with their Gmail account

**Why?** Because emails will be sent from **their** Gmail account, not yours!

### Quick Setup for Friends

Send them this checklist:

```
□ Go to: https://console.cloud.google.com/
□ Create new project: "Job Automation"
□ Enable Gmail API
□ Configure OAuth consent screen (External)
□ Add yourself as test user
□ Create OAuth 2.0 credentials (Desktop app)
□ Download JSON as credentials.json
□ Place in project folder
□ Run: python auth_bootstrap.py
□ Authorize in browser
```

---

## 🎯 What Files You'll Have

After setup, you'll have:

```
Cold Email/
├── credentials.json       ← Your OAuth credentials (keep private!)
├── token.json             ← Access token (auto-generated, keep private!)
├── auth_bootstrap.py      ← Script to run authentication
└── ...other files
```

**Both files are in `.gitignore`** - they will never be uploaded to GitHub! ✅

---

## 🔄 Re-authentication

If `token.json` expires or you want to use a different Gmail account:

```bash
# Delete old token
rm token.json

# Run authentication again
python auth_bootstrap.py
```

---

## 📞 Still Having Issues?

1. **Check you're using the right Google account** - The one you want to send emails from
2. **Make sure Gmail API is enabled** - Check in Google Cloud Console
3. **Verify OAuth consent screen is configured** - Must be done before creating credentials
4. **Use "Desktop app" type** - Not "Web application"
5. **Add yourself as a test user** - In OAuth consent screen settings

---

## ✅ Success Checklist

- [ ] Google Cloud project created
- [ ] Gmail API enabled
- [ ] OAuth consent screen configured
- [ ] You added yourself as test user
- [ ] OAuth 2.0 credentials created (Desktop app)
- [ ] `credentials.json` downloaded and renamed
- [ ] `credentials.json` placed in project folder
- [ ] `python auth_bootstrap.py` completed successfully
- [ ] `token.json` file exists
- [ ] Browser authorization completed

**All done?** You're ready to send emails! 🎉

---

## 🎓 Understanding OAuth

**What is OAuth?**
- Industry-standard protocol for authorization
- Lets apps access your account without knowing your password
- You can revoke access anytime
- More secure than using passwords directly

**What are these files?**
- `credentials.json` - Your app's identity (like an app ID)
- `token.json` - Your authorization (like a temporary key)

**Why is this better than app passwords?**
- ✅ More secure
- ✅ Granular permissions
- ✅ Easy to revoke
- ✅ Official Google method
- ✅ No password sharing

---

**Need help?** Check the troubleshooting section above or create an issue on GitHub!

