# 🚢 Deployment Guide

## Backend → Railway

1. Push your code to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select your BioScout repo
4. Add a PostgreSQL plugin (Railway provides one free)
5. Set environment variables in Railway dashboard:

```
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(50))">
DEBUG=False
ALLOWED_HOSTS=your-app.railway.app
DATABASE_URL=<auto-set by Railway PostgreSQL plugin>
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
BASE_URL=https://your-app.railway.app
```

6. Railway will auto-detect `railway.json` and run:
   - `python manage.py migrate`
   - `python manage.py build_rag_index`
   - `gunicorn backend.wsgi:application`

## Frontend → Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub repo
3. Set main file path: `frontend/app.py`
4. Add secrets in Streamlit Cloud dashboard (Settings → Secrets):

```toml
API_BASE = "https://your-app.railway.app/api"
```

5. Update `frontend/utils.py` to read `API_BASE` from `st.secrets` for production:

```python
import streamlit as st
API_BASE = st.secrets.get("API_BASE", "http://127.0.0.1:8000/api")
```

## Static Files

Run before deploying:
```bash
python manage.py collectstatic --noinput
```

WhiteNoise serves static files automatically in production.

## Media Files (Images)

For production, configure an S3 bucket or similar object storage.
Add `django-storages` and `boto3` to requirements.txt and configure
`DEFAULT_FILE_STORAGE` in settings.py.
