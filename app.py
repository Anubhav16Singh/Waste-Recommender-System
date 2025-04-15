from flask import Flask, request, render_template, jsonify
from tensorflow.keras.preprocessing import image
import numpy as np
import tensorflow as tf
import os
from werkzeug.utils import secure_filename
import requests
from bs4 import BeautifulSoup
import json
import time

# Initialize the Flask app
app = Flask(__name__)

# Load the trained model
model = tf.keras.models.load_model('waste_classification_cnn.h5')

# Define allowed file extensions for image upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Function to check if the uploaded file is an allowed image format
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Load class names (modify according to your dataset's class names)
class_names = ['trash', 'Clothes', 'biological', 'shoes', 'white-glass', 'cardboard',
               'paper', 'brown-glass', 'plastic', 'green-glass', 'metal', 'battery']

# Define the waste categories
waste_categories = {
    'organic': ['biological'],
    'inorganic': ['plastic', 'Clothes', 'shoes', 'white-glass', 'cardboard', 'paper',
                  'brown-glass', 'trash', 'green-glass', 'metal'],
    'hazardous': ['battery']
}

# Load educational content from JSON file
try:
    with open('data/educational_content.json', 'r') as f:
        educational_content = json.load(f)
except FileNotFoundError:
    educational_content = {}

# Home route that renders an upload form
@app.route('/')
def index():
    return render_template('index.html')

# Route for handling the image upload and prediction
@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join('uploads', filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(file_path)

        # Load and preprocess the image
        img = image.load_img(file_path, target_size=(128, 128))
        img_array = image.img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        # Make prediction
        predictions = model.predict(img_array)
        predicted_class_idx = np.argmax(predictions, axis=1)[0]
        predicted_class = class_names[predicted_class_idx]

        # Determine waste category
        waste_category = get_waste_category(predicted_class)

        # Get reuse/recycle ideas
        try:
            recommendations = get_recommendations(predicted_class)
        except requests.exceptions.RequestException:
            recommendations = ["Unable to fetch recommendations due to network issues."]

        # Fetch educational content
        education = educational_content.get(predicted_class, "No educational content available.")

        return jsonify({
            'predicted_class': predicted_class,
            'waste_category': waste_category,
            'recommendations': recommendations,
            'educational_content': education
        })

    return jsonify({'error': 'Invalid file format. Only png, jpg, jpeg allowed.'})

# Function to determine the waste category
def get_waste_category(predicted_class):
    for category, materials in waste_categories.items():
        if predicted_class in materials:
            return category
    return "Unknown"

# Function to get reuse/recycle recommendations
def get_recommendations(predicted_class):
    queries = {
        'Clothes': "DIY ideas for reuse or recycle clothes",
        'plastic': "DIY ideas for reuse or recycle plastic",
        'biological': "DIY ideas for reuse or recycle biological waste",
        'shoes': "DIY ideas for reuse or recycle shoes",
        'white-glass': "DIY ideas for reuse or recycle white glass",
        'cardboard': "DIY ideas for reuse or recycle cardboard",
        'paper': "DIY ideas for reuse or recycle paper",
        'brown-glass': "DIY ideas for reuse or recycle brown glass",
        'trash': "DIY ideas for reuse or recycle trash",
        'green-glass': "DIY ideas for reuse or recycle green glass",
        'metal': "DIY ideas for reuse or recycle metal",
        'battery': "DIY ideas for reuse or recycle batteries"
    }
    query = queries.get(predicted_class, "DIY ideas for waste recycling")
    return get_duckduckgo_search_results(query)

# Function to fetch search results from DuckDuckGo with retry
def get_duckduckgo_search_results(query):
    search_url = f"https://duckduckgo.com/html/?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            results = [
                {'title': result.text, 'link': result['href']}
                for result in soup.find_all('a', {'class': 'result__a'})
            ]
            return results
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise e

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
