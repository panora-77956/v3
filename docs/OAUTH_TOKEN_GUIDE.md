# Google Labs OAuth Token Guide

This guide explains how to obtain fresh OAuth tokens for Google Labs Flow API when you encounter authentication errors.

## 🚨 When Do You Need This?

You'll need fresh tokens when you see errors like:
```
[ERROR] HTTP 401: Token #1 is invalid (401 Unauthorized)
[ERROR] All 1 authentication token(s) are invalid or expired.
```

**Why tokens expire:**
- OAuth bearer tokens typically expire after **1 hour**
- You need to refresh them periodically
- Invalid tokens cause video generation to fail immediately

---

## 🔑 How to Get Fresh OAuth Tokens

### Method 1: Browser DevTools (Recommended for Testing)

This is the quickest method for getting tokens manually.

#### Step-by-Step Instructions:

1. **Open Google Labs in your browser:**
   - Go to https://labs.google/flow or https://labs.google

2. **Open Browser Developer Tools:**
   - Press `F12` (Windows/Linux) or `Cmd+Option+I` (Mac)
   - Or right-click → "Inspect"

3. **Go to Network Tab:**
   - Click on the "Network" tab in DevTools
   - Check "Preserve log" checkbox

4. **Clear existing requests:**
   - Click the clear button (🚫) to start fresh

5. **Trigger an API call:**
   - Try generating a video or image
   - Or refresh the page while logged in

6. **Find the Authorization header:**
   - Look for requests to `aisandbox-pa.googleapis.com`
   - Click on any request
   - Go to "Headers" section
   - Find "Request Headers"
   - Look for `authorization: Bearer ya29...`

7. **Copy the token:**
   - Copy everything **after** "Bearer " (the `ya29...` part)
   - This is your OAuth token

#### Example:
```
authorization: Bearer ya29.a0AfH6SMA2XvT...rest_of_token
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     Copy this part only (without "Bearer ")
```

8. **Update your config.json:**
```json
{
  "tokens": ["ya29.a0AfH6SMA2XvT...your_new_token"],
  "default_project_id": "your-project-id",
  ...
}
```

---

### Method 2: Chrome Extension (Easiest)

Use a browser extension to automatically extract tokens.

#### Available Extensions:

**Google Labs Token Extractor:**
- Chrome Web Store: Search for "Google Labs Token Extractor"
- Automatically detects and displays your token when you visit labs.google
- One-click copy to clipboard

**Token DevTools Inspector:**
- Chrome Web Store: Search for "Token Devtools Inspector"  
- Shows all Authorization headers in a dedicated panel
- Useful for developers

---

### Method 3: Using gcloud CLI (For Advanced Users)

If you have Google Cloud SDK installed:

```bash
# Login to your Google account
gcloud auth login

# Get access token
gcloud auth print-access-token
```

Copy the output (starts with `ya29...`) and paste into `config.json`.

**Note:** This requires having a Google Cloud project set up with the correct APIs enabled.

---

### Method 4: OAuth 2.0 Playground (For Development)

1. Go to: https://developers.google.com/oauthplayground

2. Click gear icon (⚙️) → Check "Use your own OAuth credentials"

3. Enter your OAuth Client ID and Secret (from Google Cloud Console)

4. In Step 1, add scope:
   ```
   https://www.googleapis.com/auth/cloud-platform
   ```

5. Click "Authorize APIs" → Sign in

6. In Step 2, click "Exchange authorization code for tokens"

7. Copy the "Access token" (starts with `ya29...`)

---

## 📝 How to Update Tokens in Config

### Location: `config.json` in project root

```json
{
  "tokens": [
    "ya29.a0AfH6SMA2XvT...",  // ← Your new token here
    "ya29.a0AfH6SMB3YwU..."   // Optional: Add multiple tokens
  ],
  "default_project_id": "87b19267-13d6-49cd-a7ed-db19a90c9339",
  "google_keys": ["your-gemini-api-key"],
  "download_root": "/path/to/downloads"
}
```

### Multiple Tokens (Optional):

You can add multiple tokens for:
- **Load balancing**: Distribute API calls across tokens
- **Higher quota**: Use multiple Google accounts
- **Redundancy**: If one expires, others still work

```json
{
  "tokens": [
    "ya29.a0AfH6SMA2XvT...",  // Account 1
    "ya29.a0AfH6SMB3YwU...",  // Account 2
    "ya29.a0AfH6SMC4ZxV..."   // Account 3
  ]
}
```

---

## ⚙️ Multi-Account Setup (Advanced)

For better quota management, use the Multi-Account Management feature:

1. Open app → **Settings** tab
2. Scroll to **"Multi-Account Management"**
3. Click **"➕ Add Account"**
4. Fill in:
   - **Account Name**: "Production" (or any name)
   - **Project ID**: Your Google Labs project ID
   - **OAuth Tokens**: Paste tokens (one per line)
5. Click **OK**
6. Repeat for additional accounts
7. Click **"💾 Save Settings"**

**Benefits:**
- Automatic token rotation
- 3x faster with 3 accounts (parallel processing)
- Better error handling per account

---

## 🔍 How to Find Your Project ID

Your Project ID is needed in `config.json` and multi-account setup.

### Method 1: From Network Requests

1. Open DevTools → Network tab
2. Generate a video/image on labs.google
3. Find request to `aisandbox-pa.googleapis.com`
4. Look in request payload for:
   ```json
   {
     "clientContext": {
       "projectId": "87b19267-13d6-49cd-a7ed-db19a90c9339"
     }
   }
   ```
5. Copy the `projectId` value

### Method 2: From URL

Sometimes visible in the URL when using Google Labs Flow:
```
https://labs.google/flow/projects/87b19267-13d6-49cd-a7ed-db19a90c9339
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                  This is your Project ID
```

---

## 🐛 Troubleshooting

### "All authentication tokens are invalid"

**Cause:** Your tokens have expired (after ~1 hour)

**Solution:** 
1. Get fresh tokens using Method 1 (Browser DevTools)
2. Update `config.json`
3. Restart the application

### "401 Unauthorized" on every request

**Possible causes:**
- Expired tokens (most common)
- Invalid token format (missing characters when copying)
- Using tokens from wrong Google account
- Tokens revoked due to security

**Solution:**
1. Verify you copied the **complete** token (starts with `ya29.`)
2. Ensure no extra spaces or newlines
3. Try generating a completely fresh token
4. Check you're logged into the correct Google account

### Multiple error messages

**Fixed in latest version!**

The application now shows only one clear error message instead of 4 duplicates:
```
[ERROR] HTTP 401: Token #1 is invalid (401 Unauthorized)
[ERROR] All 1 authentication token(s) are invalid or expired.
        Please update your Google Labs OAuth tokens in the API Credentials settings.
        To get new tokens, visit https://labs.google and inspect network requests.
```

---

## 🔒 Security Best Practices

### DO:
✅ Keep tokens private (never commit to GitHub)  
✅ Use environment variables for production  
✅ Refresh tokens regularly (every hour)  
✅ Use service accounts for automated workflows

### DON'T:
❌ Share tokens publicly  
❌ Hard-code tokens in source code  
❌ Use personal tokens in production  
❌ Store tokens in public repositories

---

## 📚 Related Documentation

- [Google OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Authentication](https://cloud.google.com/docs/authentication)
- [Vertex AI Authentication](https://cloud.google.com/vertex-ai/docs/authentication)

---

## 💡 Quick Reference

| Task | Command/Location |
|------|------------------|
| Get token via gcloud | `gcloud auth print-access-token` |
| Config file location | `config.json` (project root) |
| Token format | Starts with `ya29.` |
| Token lifespan | ~1 hour |
| API endpoint | `aisandbox-pa.googleapis.com` |
| OAuth Playground | https://developers.google.com/oauthplayground |

---

## ❓ Need Help?

If you're still having issues:

1. Check the [GitHub Issues](https://github.com/panora-77956/v3/issues)
2. Verify tokens are fresh (< 1 hour old)
3. Try with a single token first before multi-account
4. Check console logs for detailed error messages

---

**Last Updated:** 2025-11-08  
**Version:** v7 (Latest)
