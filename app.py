import os
import re
from datetime import datetime
from urllib.parse import urlsplit
from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.exceptions import HTTPException

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'), static_url_path='')

# Configuration
ALLOWED_DOMAINS = os.getenv('ALLOWED_DOMAINS', 'iiitl.ac.in').split(',')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-dev-key-iiitl-studyloop')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'studyloop.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024

# Heroku/Render Postgres compatibility fix
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

db = SQLAlchemy(app)

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

BRANCHES = ('CS', 'IT', 'AI', 'CSB')
RESOURCE_TYPES = ('Notes', 'PYQs', 'Cheatsheet', 'Slides')
EMAIL_LOCAL_RE = re.compile(r'[a-z0-9_+-]+(\.[a-z0-9_+-]+)*')
CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ud800-\udfff]')


class ValidationError(Exception):
    pass


@app.errorhandler(ValidationError)
def handle_validation_error(err):
    return jsonify({'error': str(err)}), 400


@app.errorhandler(HTTPException)
def handle_http_error(err):
    if request.path.startswith('/api/'):
        return jsonify({'error': err.description}), err.code
    return err


@app.before_request
def block_cross_site_writes():
    # Covers requests that need no CORS preflight, such as the body-less join.
    if request.method == 'POST' and request.headers.get('Sec-Fetch-Site') == 'cross-site':
        return jsonify({'error': 'Cross-site requests are not allowed.'}), 403


def get_json_object():
    data = request.get_json()
    if not isinstance(data, dict):
        raise ValidationError('Request body must be a JSON object.')
    return data


def text_field(data, key, label, max_length, default='', required=False):
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ValidationError(f'{label} must be text.')
    value = value.strip() or default
    if required and not value:
        raise ValidationError(f'{label} is required.')
    if len(value) > max_length:
        raise ValidationError(f'{label} must be {max_length} characters or fewer.')
    if CONTROL_CHARS_RE.search(value):
        raise ValidationError(f'{label} contains invalid characters.')
    return value


def choice_field(data, key, label, choices, default):
    value = text_field(data, key, label, 50, default)
    if value not in choices:
        raise ValidationError(f'{label} must be one of: {", ".join(choices)}.')
    return value


def batch_year_field(data):
    value = data.get('batch_year', 2027)
    latest = datetime.now().year + 6
    if type(value) is not int or not 2015 <= value <= latest:
        raise ValidationError(f'Batch must be a year between 2015 and {latest}.')
    return value


def link_field(data):
    value = text_field(data, 'link', 'Resource Link', 300, required=True)
    try:
        parts = urlsplit(value)
        valid = parts.scheme in ('http', 'https') and bool(parts.hostname)
    except ValueError:
        valid = False
    if not valid or re.search(r'[\s"<>\\]', value):
        raise ValidationError('Resource Link must be a valid http or https URL.')
    return value


def is_valid_college_email(email):
    local, _, domain = email.rpartition('@')
    return bool(EMAIL_LOCAL_RE.fullmatch(local)) and \
        domain in [d.strip().lower() for d in ALLOWED_DOMAINS]

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = get_json_object()
    email = text_field(data, 'email', 'Email', 120, required=True).lower()
    name = text_field(data, 'name', 'Name', 80, 'IIITL Student')
    branch = choice_field(data, 'branch', 'Branch', BRANCHES, 'CS')
    batch_year = batch_year_field(data)
    campus_id = text_field(data, 'campus_id', 'Campus', 20, 'iiitl')

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
            campus_id=campus_id
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
    data = get_json_object()
    group = StudyGroup(
        title=text_field(data, 'title', 'Title', 100, required=True),
        subject_code=text_field(data, 'subject_code', 'Subject Code', 20, required=True).upper()[:20],
        branch=choice_field(data, 'branch', 'Branch', ('ALL',) + BRANCHES, 'ALL'),
        schedule=text_field(data, 'schedule', 'Schedule', 100, 'Flexible / Evening'),
        location=text_field(data, 'location', 'Location', 100, 'IIITL Campus / Online'),
        description=text_field(data, 'description', 'Description', 2000),
        members_count=1,
        created_by=text_field(data, 'created_by', 'Host', 80, 'IIITL Student'),
        campus_id=text_field(data, 'campus_id', 'Campus', 20, 'iiitl')
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
    data = get_json_object()
    res = Resource(
        title=text_field(data, 'title', 'Title', 120, required=True),
        subject_code=text_field(data, 'subject_code', 'Subject Code', 20, required=True).upper()[:20],
        resource_type=choice_field(data, 'resource_type', 'Category', RESOURCE_TYPES, 'Notes'),
        link=link_field(data),
        shared_by=text_field(data, 'shared_by', 'Shared by', 80, 'IIITL Student'),
        campus_id=text_field(data, 'campus_id', 'Campus', 20, 'iiitl')
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
