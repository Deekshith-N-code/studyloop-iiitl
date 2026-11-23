# StudyLoop - IIIT Lucknow Edition

StudyLoop is a peer study & resource-sharing platform optimized for **IIIT Lucknow** campus students, designed to scale seamlessly across multiple batches, departments, and future campus network expansions.

## Key Features
- **Campus Email Validation**: Restricts access to official `@iiitl.ac.in` domain accounts.
- **Future-Ready Multi-Tenancy**: Built with `campus_id` schema tags to support future multi-institute scaling without breaking existing data.
- **Production Ready**: Configured with `gunicorn`, environment-variable driven configuration, and PostgreSQL compatibility.

## Local Setup
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Online Web Deployment (Render / Railway)
1. Push this repository to GitHub.
2. Link your repo to [Render](https://render.com).
3. Set Environment Command:
   - **Build Command**: `pip install -r studyloop/requirements.txt`
   - **Start Command**: `gunicorn studyloop.app:app`
4. Set Environment Variables:
   - `SECRET_KEY`: `<your-random-secret>`
   - `ALLOWED_DOMAINS`: `iiitl.ac.in`
