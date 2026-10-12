# ProductPilot AI + Gemini (Render deploy)

This package keeps the existing ProductPilot HTML UI, browser-demo login/signup/forgot-password screens, and interactive dashboard charts, and routes AI research through a Flask backend to Gemini. The Gemini key is never stored in the HTML or browser localStorage.

## 1. Add your files to GitHub

Create a new GitHub repository (or a new branch/repository for this version), then upload these files while preserving this structure:

```text
ProductPilot_AI_Gemini_Deploy/
├── app.py
├── requirements.txt
├── README.md
└── templates/
    └── index.html
```

Do not commit your API key or put it into `index.html`.

## 2. Deploy on Render (free for testing)

1. Sign in at https://render.com and choose **New → Web Service**.
2. Connect the GitHub repository containing these files.
3. Set **Language** to Python 3.
4. Set **Build Command** to `pip install -r requirements.txt`.
5. Set **Start Command** to `gunicorn app:app`.
6. Choose the **Free** instance for a demo/hobby deployment.
7. Under **Environment**, add `GEMINI_API_KEY` and paste your API key as its value. Optional: add `GEMINI_MODEL` with value `gemini-3.8-flash` if you want to set the model explicitly.
8. Click **Create Web Service** and wait for deploy to finish.
9. Open the public `https://<your-service>.onrender.com` URL. Use Settings → **Test connection**, then run a research report.

Render free web services can sleep after 15 minutes idle and take about a minute to wake. Their local filesystem is ephemeral, so the current browser-local demo accounts/history are not a reliable shared database.

## 3. Local test (optional)

Python 3.10+ recommended:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GEMINI_API_KEY="paste-your-key-here"
python app.py
```

Then open http://127.0.0.1:5000. Never share screenshots/logs containing your API key.

## Important limitations

- The existing signup/login/forgot-password flow is preserved as a **browser-only demo**. It is not secure production authentication and accounts are not shared between browsers/devices. Real multi-user login/reset requires backend auth and a persistent database.
- Charts remain interactive, but some chart/history series and trend/competitor panels are based on the app's existing generated/demo data. Gemini product suggestions are model-generated estimates, not live verified market data or web-sourced citations.
- Protect your API key, monitor Google AI Studio quota/usage, and never expose the key in frontend JavaScript.
