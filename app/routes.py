from flask import Blueprint, request, jsonify
from app.models import User
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from transformers import pipeline, AutoModelForSeq2SeqLM, AutoTokenizer
import pytesseract
from pdf2image import convert_from_path
import docx
from PIL import Image
import tempfile
import os
import io
import torch


main_bp = Blueprint('main', __name__)

# Set the Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r'D:\Kaif\Hackathon\Suprem court\Application\Tesseract\tesseract.exe'

# Initialize the NER pipeline outside of the route to avoid reloading the model each time
ner_pipeline = pipeline("token-classification", model="Sidziesama/Legal_NER_Support_Model")



@main_bp.route('/')
def home():
    return "Welcome to PramanAI API!"

@main_bp.route('/hello')
def hello():
    return "working with hello :)"

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
    lang = request.form.get('lang', 'eng')

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    file_ext = file.filename.split('.')[-1].lower()

    # Temporary storage for the uploaded file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        file.save(temp_file.name)

        if file_ext == 'pdf':
            try:
                # Convert PDF to images
                images = convert_from_path(temp_file.name)
                text = ""
                for image in images:
                    text += pytesseract.image_to_string(image, lang=lang)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        elif file_ext == 'docx':
            try:
                doc = docx.Document(temp_file.name)
                text = "\n".join([para.text for para in doc.paragraphs])
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        else:
            try:
                image = Image.open(temp_file.name)
                text = pytesseract.image_to_string(image, lang=lang)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    # Clean up temporary file
    os.remove(temp_file.name)

    return jsonify({'text': text})

@main_bp.route('/api/ner', methods=['POST'])
def ner():
    # Check if 'text' is in the JSON body or if a file is uploaded
    if request.content_type == 'application/json':
        # Handle raw text input
        data = request.json
        text = data.get('text')
        if not text:
            return jsonify({"error": "No text provided"}), 400
    elif 'file' in request.files:
        # Handle file input
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        try:
            # Assume the file is a text file
            text = file.read().decode('utf-8')
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({"error": "No data provided"}), 400

    # Process the text with the NER pipeline
    result = ner_pipeline(text)
    
    # Convert float32 to float for JSON serialization
    entities = [
        {"word": entity['word'], "entity": entity['entity'], "score": float(entity['score'])}
        for entity in result
    ]

    return jsonify({"entities": entities}), 200