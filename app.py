# app.py - Main Application File
import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
import PyPDF2
import uuid
import hashlib
import pymysql

app = Flask(__name__)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/academic_transcipts'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Database Models
class Student(db.Model):
    __tablename__ = 'student_details'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = db.Column(db.String(255), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    nationality = db.Column(db.String(100), nullable=False)

class Marksheet(db.Model):
    __tablename__ = 'marksheet_records'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(db.String(36), db.ForeignKey('student_details.id'), nullable=False)
    course_name = db.Column(db.String(255), nullable=False)
    total_marks_obtained = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)

class VerificationLog(db.Model):
    __tablename__ = 'verification_logs'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    marksheet_id = db.Column(db.String(36), db.ForeignKey('marksheet_records.id'), nullable=False)
    verification_status = db.Column(db.String(50), nullable=False)

# Utility Functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text_from_pdf(file_path):
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
    return text

def extract_text_from_image(file_path):
    return pytesseract.image_to_string(Image.open(file_path))

def generate_file_hash(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# Routes
@app.route('/', methods=['GET'])
def index():
    return render_template('upload.html')

@app.route('/verify', methods=['POST'])
def verify_marksheet():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # File hash for duplicate detection
        file_hash = generate_file_hash(filepath)
        
        # Extract text based on file type
        if filename.lower().endswith('.pdf'):
            extracted_text = extract_text_from_pdf(filepath)
        else:
            extracted_text = extract_text_from_image(filepath)
        
        # Basic text extraction and verification
        # This is a simplified example - you'd replace with actual verification logic
        try:
            # Assume text contains student name and marks
            verification_result = {
                'file_hash': file_hash,
                'extracted_text': extracted_text,
                'verification_status': 'Pending'
            }
            
            # Create verification log
            verification_log = VerificationLog(
                marksheet_id=str(uuid.uuid4()),  # Placeholder
                verification_status='Pending'
            )
            db.session.add(verification_log)
            db.session.commit()
            
            return jsonify(verification_result), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    with app.app_context():  # Ensures that we are inside Flask's application context
        db.create_all()  # Creates tables before starting the server
    app.run(debug=True)
