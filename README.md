# StudyLoop - IIIT Lucknow Edition

StudyLoop is a peer study & resource-sharing platform built for **IIIT Lucknow** campus students, supporting `@iiitl.ac.in` campus verification, study circles, and a PYQ/Notes vault.

## Local Setup
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Deploy on Render
1. Push all files in this folder directly to the root of your GitHub repository (`Deekshith-N-code/studyloop-iiitl`).
2. Render automatically uses:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
