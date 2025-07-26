from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import csv
import os
import io # Import io module for in-memory file handling
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_for_flash_messages' # Required for flash messages

# --- Configuration ---
PRODUCTS_FILE = 'products.csv'
LOG_FILE = 'app_log.txt'
ALLOWED_EXTENSIONS = {'csv'}

# Global variable to hold the currently active product data
# This will be updated when a new CSV is uploaded.
# NOTE: For a production app, this data would ideally be stored in a database
# (like Firestore, as discussed in the initial instructions) for persistence
# across server restarts and scalability. For this demo, in-memory is fine.
current_products_data = []

# Hardcoded user profiles with their preferred product titles
USER_PROFILES = {
    'tech_enthusiast': ['Laptop', 'External SSD', 'Monitor', 'Keyboard'],
    'casual_user': ['Headphones', 'Mouse', 'USB Drive', 'Webcam']
}

def allowed_file(filename):
    """Checks if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_initial_products():
    """Loads products from the static CSV file at startup."""
    products = []
    try:
        with open(PRODUCTS_FILE, mode='r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                try:
                    row['price'] = float(row['price'])
                    products.append(row)
                except ValueError:
                    print(f"Warning: Could not convert price to float for row: {row}")
    except FileNotFoundError:
        print(f"Error: Initial {PRODUCTS_FILE} not found. Starting with empty product list.")
    return products

def log_action(action_type, product_title=None, profile=None, message=None):
    """Logs user actions or system events to a file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = f"[{timestamp}] Action: {action_type}"
    if product_title:
        log_entry += f", Product: {product_title}"
    if profile:
        log_entry += f", Profile: {profile}"
    if message:
        log_entry += f", Message: {message}"
    
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + '\n')
    print(f"Logged: {log_entry}") # For debugging purposes

@app.before_request
def initialize_products_if_empty():
    """Initializes product data if it's empty (e.g., on first run or server restart)."""
    global current_products_data
    if not current_products_data:
        current_products_data = load_initial_products()
        if current_products_data:
            log_action("System Init", message=f"Loaded {len(current_products_data)} products from {PRODUCTS_FILE}")
        else:
            log_action("System Init", message="No initial products loaded.")

@app.route('/')
def index():
    log_action("Page Loaded")
    # The products passed here are just for initial rendering if no JS loads them
    # The JS on the frontend will immediately call /get_products
    return render_template('index.html', products=current_products_data, profiles=USER_PROFILES.keys())

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    global current_products_data
    if 'csv_file' not in request.files:
        flash('No file part', 'error')
        log_action("CSV Upload Failed", message="No file part in request.")
        return redirect(url_for('index'))
    
    file = request.files['csv_file']
    
    if file.filename == '':
        flash('No selected file', 'error')
        log_action("CSV Upload Failed", message="No file selected.")
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        try:
            # Read the file content into a string
            stream = io.StringIO(file.stream.read().decode("UTF8"))
            csv_reader = csv.DictReader(stream)
            
            new_products = []
            for i, row in enumerate(csv_reader):
                # Basic validation for required fields
                if not all(k in row for k in ['title', 'description', 'image_url', 'price']):
                    flash(f'CSV format error: Missing required column in row {i+1}. Expected title, description, image_url, price.', 'error')
                    log_action("CSV Upload Failed", message=f"CSV format error: Missing column in row {i+1}.")
                    return redirect(url_for('index'))
                
                try:
                    row['price'] = float(row['price'])
                    new_products.append(row)
                except ValueError:
                    flash(f'CSV data error: Price is not a valid number in row {i+1}.', 'error')
                    log_action("CSV Upload Failed", message=f"Price format error in row {i+1}.")
                    return redirect(url_for('index'))
            
            if not new_products:
                flash('Uploaded CSV contains no valid product data.', 'error')
                log_action("CSV Upload Failed", message="Uploaded CSV contains no valid product data.")
                return redirect(url_for('index'))

            current_products_data = new_products
            flash(f'Successfully uploaded and updated products from {file.filename}!', 'success')
            log_action("CSV Upload Success", message=f"Uploaded {len(new_products)} products from {file.filename}")
            return redirect(url_for('index'))
            
        except Exception as e:
            flash(f'Error processing CSV file: {str(e)}', 'error')
            log_action("CSV Upload Failed", message=f"Error processing CSV: {str(e)}")
            return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload a CSV file.', 'error')
        log_action("CSV Upload Failed", message="Invalid file type.")
        return redirect(url_for('index'))


@app.route('/get_products', methods=['POST'])
def get_products():
    data = request.json
    selected_profile = data.get('profile')
    
    # Use the globally stored current_products_data
    products = list(current_products_data) # Create a copy to avoid modifying the global list during sorting

    if selected_profile and selected_profile in USER_PROFILES:
        preferred_products_titles = USER_PROFILES[selected_profile]
        
        # Separate preferred and non-preferred products
        preferred_products = []
        other_products = []
        for product in products:
            if product['title'] in preferred_products_titles:
                preferred_products.append(product)
            else:
                other_products.append(product)
        
        # Sort preferred products (e.g., by their order in the profile list)
        # This is a simple sorting; for more complex ordering, you'd need a more robust algorithm.
        preferred_products.sort(key=lambda p: preferred_products_titles.index(p['title']))
        
        # Combine them: preferred products first, then others (optionally sorted, e.g., by title)
        other_products.sort(key=lambda p: p['title'])
        sorted_products = preferred_products + other_products
        
        log_action("Products reordered", profile=selected_profile)
        return jsonify(sorted_products)
    
    # If no profile or invalid profile, return products as is (or with default sort)
    products.sort(key=lambda p: p['title']) # Default sort by title
    return jsonify(products)


@app.route('/log_click', methods=['POST'])
def log_click():
    data = request.json
    product_title = data.get('productTitle')
    profile = data.get('profile')
    if product_title:
        log_action("Product Clicked", product_title=product_title, profile=profile)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Product title missing"}), 400

@app.route('/log_add_to_cart', methods=['POST'])
def log_add_to_cart():
    data = request.json
    product_title = data.get('productTitle')
    profile = data.get('profile')
    if product_title:
        log_action("Added to Cart", product_title=product_title, profile=profile)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Product title missing"}), 400

if __name__ == '__main__':
    # Create an empty log file if it doesn't exist
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            f.write("Application Log:\n")
    
    # Initial load of products when the app starts
    current_products_data = load_initial_products()
    if current_products_data:
        log_action("System Init", message=f"Loaded {len(current_products_data)} products from {PRODUCTS_FILE}")
    else:
        log_action("System Init", message="No initial products loaded.")

    app.run(debug=True) # debug=True is good for development, disable for production