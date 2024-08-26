from flask import Blueprint, request, jsonify  # Added jsonify here
from app.models import User
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
import pytesseract
from PIL import Image
import io

main_bp = Blueprint('main', __name__)

# Set the Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r'D:\Kaif\Hackathon\Suprem court\Application\Tesseract\tesseract.exe'

@main_bp.route('/')
def home():
    return "Welcome to PramanAI API!"

@main_bp.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data['username']
    password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully!'})

@main_bp.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Login successful!'})
    return jsonify({'message': 'Invalid credentials!'}), 401

@main_bp.route('/api/ocr', methods=['POST'])
def ocr():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    lang = request.form.get('lang', 'eng')  # Default to English if no language is specified

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        img = Image.open(io.BytesIO(file.read()))
        text = pytesseract.image_to_string(img, lang=lang)
        return jsonify({'text': text}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500