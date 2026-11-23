import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')

# Configuration
ALLOWED_DOMAINS = os.getenv('ALLOWED_DOMAINS', 'iiitl.ac.in').split(',')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-dev-key-iiitl-studyloop')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///studyloop.db')
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
    campus_id = db.Column(db.String(20), default="iiitl") # Built-in multi-tenant support for future expansion

class StudyGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    subject_code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    campus_id = db.Column(db.String(20), default="iiitl")

with app.app_context():
    db.create_all()

def is_valid_college_email(email):
    if '@' not in email:
        return False
    domain = email.split('@')[-1].lower()
    return domain in [d.strip() for d in ALLOWED_DOMAINS]

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    
    if not is_valid_college_email(email):
        return jsonify({
            'error': f'Access restricted to IIIT Lucknow & campus emails (@{", @".join(ALLOWED_DOMAINS)})'
        }), 403

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            name=data.get('name', 'IIITL Student'),
            branch=data.get('branch'),
            batch_year=data.get('batch_year'),
            campus_id=data.get('campus_id', 'iiitl')
        )
        db.session.add(user)
        db.session.commit()

    return jsonify({'status': 'success', 'user': {'id': user.id, 'email': user.email, 'name': user.name}})

@app.route('/api/groups', methods=['GET'])
def get_groups():
    campus = request.args.get('campus_id', 'iiitl')
    groups = StudyGroup.query.filter_by(campus_id=campus).all()
    return jsonify([{
        'id': g.id,
        'title': g.title,
        'subject_code': g.subject_code,
        'description': g.description,
        'campus_id': g.campus_id
    } for g in groups])

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
