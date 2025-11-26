# GitHub Pages Deployment Guide

## Overview

The TellTims Automator uses a **split architecture**:
- **Frontend** (Static HTML/JS) - Hosted on GitHub Pages
- **Backend** (Flask/Python/Selenium) - Hosted on Replit or Render

## Step 1: Deploy Backend to Replit

### Option A: Replit (Recommended - Free)

1. **Create Replit Account**
   - Go to [replit.com](https://replit.com) and sign up

2. **Create New Repl**
   - Click "Create Repl"
   - Select "Import from GitHub"
   - Paste your repository URL

3. **Verify Files**
   - Ensure `replit.nix` exists (installs Chrome & Tesseract)
   - Ensure `app.py` exists
   - Ensure `requirements.txt` exists

4. **Run the Backend**
   - Click "Run" button
   - Wait for packages to install
   - Note the URL (e.g., `https://your-repl.username.repl.co`)

5. **Test Backend**
   ```
   Visit: https://your-repl.username.repl.co/
   ```

### Option B: Render (Free Tier)

1. **Create Render Account**
   - Go to [render.com](https://render.com)

2. **Create New Web Service**
   - Connect GitHub repository
   - Runtime: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`

3. **Note the URL**
   - Save your Render URL (e.g., `https://telltims-automator.onrender.com`)

## Step 2: Deploy Frontend to GitHub Pages

1. **Enable GitHub Pages**
   - Go to your repository settings
   - Scroll to "Pages" section
   - Source: Deploy from branch
   - Branch: Select your branch (e.g., `main` or your feature branch)
   - Folder: `/` (root)
   - Click Save

2. **Wait for Deployment**
   - GitHub will deploy `index.html` automatically
   - Your site will be at: `https://username.github.io/repository-name/`

3. **Note**: The `index.html` file is already in your repo root, so GitHub Pages will serve it automatically.

## Step 3: Configure Frontend to Use Backend

1. **Visit Your GitHub Pages Site**
   ```
   https://yourusername.github.io/TimsSurvey/
   ```

2. **Enter Backend URL**
   - You'll see a yellow configuration notice at the top
   - Enter your Replit or Render backend URL
   - Example: `https://your-repl.username.repl.co`
   - The URL is saved in browser localStorage

## Features

### Camera Support
- Click "Take Photo" button
- Allow camera permissions
- Take photo of receipt
- OCR runs directly in browser using Tesseract.js

### Image Upload
- Click "Upload Image"
- Select receipt image
- OCR extracts survey code automatically

### Survey Automation
- Enter code (manually or via OCR)
- Click "Start Survey"
- Backend runs Selenium automation
- Real-time status updates displayed
- Final validation code shown when complete

## Architecture

```
┌─────────────────────────┐
│   GitHub Pages          │
│   (index.html)          │
│   - Camera/OCR UI       │
│   - Tesseract.js        │
└──────────┬──────────────┘
           │ HTTPS POST
           ▼
┌─────────────────────────┐
│   Replit/Render         │
│   (app.py)              │
│   - Flask API           │
│   - Selenium/Chrome     │
│   - Survey Automation   │
└─────────────────────────┘
```

## Troubleshooting

### Backend Not Responding
- Verify backend URL is correct
- Check backend is running (visit URL in browser)
- Check browser console for CORS errors

### OCR Not Working
- Tesseract.js loads from CDN - check internet connection
- Try uploading clearer image
- Ensure code is visible and not blurry

### Survey Automation Fails
- Backend needs Chrome/Tesseract installed
- For Replit: Ensure `replit.nix` is present
- Check backend status logs

## Security Note

The backend URL is stored in browser localStorage, so users need to configure it once per browser.

## Updating

### Update Frontend
- Edit `index.html`
- Commit and push to GitHub
- GitHub Pages updates automatically

### Update Backend
- Edit `app.py`
- Push to GitHub
- Replit auto-updates
- Render: Trigger manual deploy or auto-deploys on push
