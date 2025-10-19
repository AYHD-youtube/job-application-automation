# LinkedIn Cookie Setup Guide

## Why Do You Need This?

LinkedIn has rate limiting that can block automated scraping. By providing your LinkedIn session cookie (`li_at`), the automation can make authenticated requests as if you're browsing LinkedIn normally, which:

✅ **Avoids rate limiting**  
✅ **Increases scraping success rate**  
✅ **Accesses more job details**  
✅ **Reduces blocked requests**

**Note:** This is **OPTIONAL** but highly recommended if you're processing many jobs.

---

## ⚠️ Security Warning

Your LinkedIn cookie grants access to your LinkedIn account. Keep it secure:

- ❌ **Never share it publicly**
- ❌ **Never commit it to Git** (it's in `.gitignore`)
- ✅ **Only use it in your local automation**
- ✅ **Regenerate if compromised** (log out and log back in)

---

## How to Get Your LinkedIn Cookie

### Method 1: Chrome/Edge

1. **Open LinkedIn** in Chrome or Edge
2. **Log in** to your LinkedIn account
3. **Open Developer Tools**:
   - Windows/Linux: Press `F12` or `Ctrl + Shift + I`
   - Mac: Press `Cmd + Option + I`
4. **Go to the "Application" tab** (top menu in DevTools)
5. **Expand "Cookies"** in the left sidebar
6. **Click on "https://www.linkedin.com"**
7. **Find the cookie named `li_at`** in the list
8. **Copy the "Value"** column (it's a long string starting with `AQED...`)

### Method 2: Firefox

1. **Open LinkedIn** in Firefox
2. **Log in** to your LinkedIn account
3. **Open Developer Tools**:
   - Windows/Linux: Press `F12` or `Ctrl + Shift + I`
   - Mac: Press `Cmd + Option + I`
4. **Go to the "Storage" tab** (top menu in DevTools)
5. **Expand "Cookies"** in the left sidebar
6. **Click on "https://www.linkedin.com"**
7. **Find the cookie named `li_at`** in the list
8. **Copy the "Value"** column

### Method 3: Safari

1. **Enable Developer Menu**:
   - Safari → Preferences → Advanced
   - Check "Show Develop menu in menu bar"
2. **Open LinkedIn** and log in
3. **Open Web Inspector**: `Cmd + Option + I`
4. **Go to "Storage" tab**
5. **Select "Cookies" → "https://www.linkedin.com"**
6. **Find `li_at` and copy its value**

---

## Visual Guide

Here's what you're looking for:

```
Cookie Name: li_at
Cookie Value: AQEDATXNAAABk1234567890abcdefghijklmnopqrstuvwxyz...
             ↑
             Copy this entire value
```

The value is typically:
- **Long** (100+ characters)
- **Starts with** `AQED` or similar
- **Contains** letters, numbers, and special characters

---

## How to Add It to Your Automation

### For Command-Line Usage (credentials_config.py)

1. Open `credentials_config.py`
2. Find the `LINKEDIN_COOKIE` line
3. Replace `None` with your cookie value:

```python
# Before:
LINKEDIN_COOKIE = None

# After:
LINKEDIN_COOKIE = "AQEDATXNAAABk1234567890abcdefghijklmnopqrstuvwxyz..."
```

4. Save the file

### For Web App Usage

1. Log in to the web app
2. Go to **Settings** page
3. Scroll to **Job Search Settings**
4. Find **LinkedIn Cookie (li_at)** field
5. Paste your cookie value
6. Click **Save Settings**

---

## Troubleshooting

### "Cookie not working / still getting rate limited"

**Solution:**
- Your cookie may have expired
- Log out of LinkedIn and log back in
- Get a fresh cookie value
- Update your configuration

### "Can't find the li_at cookie"

**Solution:**
- Make sure you're logged in to LinkedIn
- Clear your browser cache and log in again
- Try a different browser
- Check you're looking at `https://www.linkedin.com` cookies (not other domains)

### "Is this safe?"

**Answer:**
- The cookie is stored locally on your machine
- It's never sent anywhere except LinkedIn
- It's in `.gitignore` so it won't be committed to Git
- You can regenerate it anytime by logging out and back in

### "How long does the cookie last?"

**Answer:**
- LinkedIn cookies typically last 1-2 weeks
- If you log out, the cookie becomes invalid
- You'll need to get a new one if it expires

---

## Alternative: Run Without Cookie

If you don't want to use a cookie, you can:

1. **Leave the field empty** in settings
2. **Set `LINKEDIN_COOKIE = None`** in credentials_config.py
3. The automation will still work, but:
   - May get rate limited after 10-20 jobs
   - Might miss some job details
   - Could be blocked temporarily

---

## Best Practices

✅ **Update cookie every 1-2 weeks**  
✅ **Use a dedicated LinkedIn account** (optional, for safety)  
✅ **Don't scrape too aggressively** (respect rate limits)  
✅ **Monitor for blocks** (LinkedIn may still rate limit)  
✅ **Keep cookie secure** (treat it like a password)

---

## Legal & Ethical Considerations

⚖️ **LinkedIn Terms of Service:**
- Web scraping may violate LinkedIn's ToS
- Use at your own risk
- Consider using LinkedIn's official API for production use
- This is intended for personal job search automation only

🎯 **Recommended Use:**
- Personal job applications only
- Reasonable request rates (not hundreds per minute)
- Respect LinkedIn's robots.txt
- Don't scrape private/restricted data

---

## Questions?

If you have issues:
1. Check the troubleshooting section above
2. Verify your cookie is correct (no extra spaces)
3. Try logging out and back in to LinkedIn
4. Test without the cookie first to isolate the issue

**Remember:** The cookie is optional. The automation works without it, just with higher risk of rate limiting.

