# How to Deploy Vocabestie (Free)

The easiest way to get your app online 24/7 for free is using **Render.com**.

## Prerequisites
1.  **Push your code to GitHub** (Your project must be in a GitHub repository).
    *   Make sure `requirements.txt` is updated (I already added `gunicorn`).
    *   Make sure changes to `app/config.py` are pushed.

## Step 1: Create Account
1.  Go to [Render.com](https://render.com).
2.  Sign up (easiest to sign up *with GitHub*).

## Step 2: Create Database
1.  Click **"New +"** -> **"PostgreSQL"**.
2.  **Name**: `vocabestie-db`
3.  **Database**: `vocabestie`
4.  **User**: `vocabestie`
5.  **Region**: Choose one close to you (e.g., Frankfurt or Oregon).
6.  **Instance Type**: Select **"Free"**.
7.  Click **Create Database**.
8.  **Wait** for it to be created.
9.  **Copy the "Internal Database URL"** (starts with `postgres://...`). You will need this securely.

## Step 3: Create Web Service
1.  Click **"New +"** -> **"Web Service"**.
2.  **Connect GitHub**: Select your `vocabestie` repository.
3.  **Name**: `vocabestie-app`
4.  **Region**: Same as your database.
5.  **Branch**: `main`
6.  **Runtime**: **Python 3**.
7.  **Build Command**:
    ```bash
    pip install -r requirements.txt && alembic upgrade head && python scripts/seed_data.py
    ```
    *(This installs dependencies, updates the DB schema, and seeds vocabulary data).*
8.  **Start Command**:
    ```bash
    gunicorn -k uvicorn.workers.UvicornWorker app.main:app
    ```
9.  **Instance Type**: Select **"Free"**.
10. **Environment Variables** (Click "Advanced" or "Environment"):
    *   Add `PYTHON_VERSION`: `3.11.0`
    *   Add `DATABASE_URL`: Paste the **Internal Database URL** you copied earlier.
    *   Add `SECRET_KEY`: Generate a random string (e.g., smash your keyboard).
    *   Add `GOOGLE_CLIENT_ID`: (From your `oauth.json` or Google Console).
    *   Add `GOOGLE_CLIENT_SECRET`: (From your `oauth.json` or Google Console).
    *   Add `OAUTH_REDIRECT_URI`: `https://vocabestie-app.onrender.com/auth/callback/google`
        *   *(Note: You won't know the exact URL (`vocabestie-app.onrender.com`) until you create it, but you can guess or update this later)*.

## Step 4: Update Google Console
1.  Once deployed, Render gives you a URL (e.g., `https://vocabestie-app.onrender.com`).
2.  Go to **Google Cloud Console** -> **APIs & Services** -> **Credentials**.
3.  Edit your OAuth 2.0 Client.
4.  Add the Render URL to **Authorized Redirect URIs**:
    *   `https://vocabestie-app.onrender.com/auth/callback/google`
5.  Save.

## Done!
Your app will now run 24/7.
- **Note on Free Tier**: The web server "sleeps" after 15 minutes of inactivity. When you open it, it might take **30-60 seconds** to wake up. This is normal for free hosting.
