import os
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'), static_url_path='')

# Configuration
ALLOWED_DOMAINS = os.getenv('ALLOWED_DOMAINS', 'iiitl.ac.in').split(',')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-dev-key-iiitl-studyloop')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'studyloop.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Heroku/Render Postgres compatibility fix
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

db = SQLAlchemy(app)
CORS(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    branch = db.Column(db.String(50), nullable=True)     # e.g., CS, IT, AI, CSB
    batch_year = db.Column(db.Integer, nullable=True)    # e.g., 2026
    campus_id = db.Column(db.String(20), default="iiitl")

class StudyGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    subject_code = db.Column(db.String(20), nullable=False)
    branch = db.Column(db.String(50), default="ALL")
    schedule = db.Column(db.String(100), default="Flexible / Online")
    location = db.Column(db.String(100), default="IIITL Library / Discord")
    description = db.Column(db.Text, nullable=True)
    members_count = db.Column(db.Integer, default=1)
    created_by = db.Column(db.String(80), default="IIITL Peer")
    campus_id = db.Column(db.String(20), default="iiitl")

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    subject_code = db.Column(db.String(20), nullable=False)
    resource_type = db.Column(db.String(30), default="Notes")  # Notes, PYQs, Slides, Cheatsheet
    link = db.Column(db.String(300), nullable=False)
    shared_by = db.Column(db.String(80), default="IIITL Student")
    campus_id = db.Column(db.String(20), default="iiitl")

def seed_initial_data():
    if StudyGroup.query.count() == 0:
        starter_groups = [
            StudyGroup(
                title="DSA & Competitive Programming Grind",
                subject_code="CS201",
                branch="CS / IT",
                schedule="Mon, Wed, Fri • 8:30 PM",
                location="Computer Center Lab 2",
                description="Solving Codeforces Div 2 C/D problems, dynamic programming patterns, and graph algorithms ahead of technical interviews.",
                members_count=18,
                created_by="Aarav Sharma (CS '27)",
                campus_id="iiitl"
            ),
            StudyGroup(
                title="Machine Learning & Deep Neural Nets",
                subject_code="AI302",
                branch="AI",
                schedule="Tue, Thu • 7:00 PM",
                location="Academic Block Room 204",
                description="Implementing transformers from scratch in PyTorch, reviewing research papers, and preparing mid-sem notes.",
                members_count=14,
                created_by="Ananya Verma (AI '26)",
                campus_id="iiitl"
            ),
            StudyGroup(
                title="Operating Systems & Concurrency Circle",
                subject_code="CS204",
                branch="CS / CSB",
                schedule="Saturday • 4:00 PM",
                location="Central Library Reading Hall",
                description="Deadlocks, memory paging, POSIX threads, and solving previous year IIITL end-sem exam papers together.",
                members_count=11,
                created_by="Rohan Gupta (CSB '27)",
                campus_id="iiitl"
            ),
            StudyGroup(
                title="Database Management & System Design",
                subject_code="IT205",
                branch="IT",
                schedule="Sunday • 5:30 PM",
                location="Hostel Common Room / Discord",
                description="Normalization, indexing internals, SQL query optimization, and scalable backend architecture discussions.",
                members_count=9,
                created_by="Priya Singh (IT '27)",
                campus_id="iiitl"
            )
        ]
        db.session.bulk_save_objects(starter_groups)

    if Resource.query.count() == 0:
        starter_resources = [
            Resource(
                title="End-Sem PYQ Archive (2022–2025) with Solutions",
                subject_code="CS201",
                resource_type="PYQs",
                link="https://iiitl.ac.in",
                shared_by="Academic Council IIITL",
                campus_id="iiitl"
            ),
            Resource(
                title="Complete OS Kernel & Scheduling Handwritten Notes",
                subject_code="CS204",
                resource_type="Notes",
                link="https://iiitl.ac.in",
                shared_by="Rohan Gupta",
                campus_id="iiitl"
            ),
            Resource(
                title="Linear Algebra & Optimization Formula Cheatsheet",
                subject_code="AI302",
                resource_type="Cheatsheet",
                link="https://iiitl.ac.in",
                shared_by="Ananya Verma",
                campus_id="iiitl"
            )
        ]
        db.session.bulk_save_objects(starter_resources)
    db.session.commit()

with app.app_context():
    db.create_all()
    seed_initial_data()

def is_valid_college_email(email):
    if '@' not in email:
        return False
    domain = email.split('@')[-1].lower()
    return domain in [d.strip().lower() for d in ALLOWED_DOMAINS]

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    name = data.get('name', '').strip() or 'IIITL Student'
    branch = data.get('branch', 'CS').strip()
    batch_year = data.get('batch_year', 2027)

    if not is_valid_college_email(email):
        return jsonify({
            'error': f'Access restricted to official IIIT Lucknow emails (@{", @".join(ALLOWED_DOMAINS)})'
        }), 403

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            name=name,
            branch=branch,
            batch_year=batch_year,
            campus_id=data.get('campus_id', 'iiitl')
        )
        db.session.add(user)
    else:
        if name and name != 'IIITL Student':
            user.name = name
        if branch:
            user.branch = branch
        if batch_year:
            user.batch_year = batch_year

    db.session.commit()

    return jsonify({
        'status': 'success',
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'branch': user.branch,
            'batch_year': user.batch_year,
            'campus_id': user.campus_id
        }
    })

@app.route('/api/groups', methods=['GET'])
def get_groups():
    campus = request.args.get('campus_id', 'iiitl')
    groups = StudyGroup.query.filter_by(campus_id=campus).order_by(StudyGroup.id.desc()).all()
    return jsonify([{
        'id': g.id,
        'title': g.title,
        'subject_code': g.subject_code,
        'branch': g.branch,
        'schedule': g.schedule,
        'location': g.location,
        'description': g.description,
        'members_count': g.members_count,
        'created_by': g.created_by,
        'campus_id': g.campus_id
    } for g in groups])

@app.route('/api/groups', methods=['POST'])
def create_group():
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    subject_code = data.get('subject_code', '').strip().upper()
    if not title or not subject_code:
        return jsonify({'error': 'Title and Subject Code are required.'}), 400

    group = StudyGroup(
        title=title,
        subject_code=subject_code,
        branch=data.get('branch', 'ALL').strip() or 'ALL',
        schedule=data.get('schedule', 'Flexible / Evening').strip() or 'Flexible / Evening',
        location=data.get('location', 'IIITL Campus / Online').strip() or 'IIITL Campus / Online',
        description=data.get('description', '').strip(),
        members_count=1,
        created_by=data.get('created_by', 'IIITL Student'),
        campus_id=data.get('campus_id', 'iiitl')
    )
    db.session.add(group)
    db.session.commit()
    return jsonify({'status': 'success', 'id': group.id}), 201

@app.route('/api/groups/<int:group_id>/join', methods=['POST'])
def join_group(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    group.members_count = (group.members_count or 1) + 1
    db.session.commit()
    return jsonify({'status': 'success', 'members_count': group.members_count})

@app.route('/api/resources', methods=['GET'])
def get_resources():
    campus = request.args.get('campus_id', 'iiitl')
    resources = Resource.query.filter_by(campus_id=campus).order_by(Resource.id.desc()).all()
    return jsonify([{
        'id': r.id,
        'title': r.title,
        'subject_code': r.subject_code,
        'resource_type': r.resource_type,
        'link': r.link,
        'shared_by': r.shared_by,
        'campus_id': r.campus_id
    } for r in resources])

@app.route('/api/resources', methods=['POST'])
def add_resource():
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    subject_code = data.get('subject_code', '').strip().upper()
    link = data.get('link', '').strip()
    if not title or not subject_code or not link:
        return jsonify({'error': 'Title, Subject Code, and Resource Link are required.'}), 400

    res = Resource(
        title=title,
        subject_code=subject_code,
        resource_type=data.get('resource_type', 'Notes'),
        link=link,
        shared_by=data.get('shared_by', 'IIITL Student'),
        campus_id=data.get('campus_id', 'iiitl')
    )
    db.session.add(res)
    db.session.commit()
    return jsonify({'status': 'success', 'id': res.id}), 201

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
