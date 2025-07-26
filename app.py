from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import csv
import os
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_for_flash_messages'

# --- Configuration ---
PRODUCTS_FILE = 'products.csv' # This file is now purely for example/reference
LOG_FILE = 'app_log.txt'
ALLOWED_EXTENSIONS = {'csv'}

# Global variable to hold the currently active product data
current_products_data = []

# Hardcoded user profiles with their preferred PRODUCT CATEGORIES
USER_PROFILES = {
    # Tech enthusiast now prefers Electronics, Gaming, and Smart Home categories
    'tech_enthusiast': ['Electronics', 'Gaming', 'Smart Home'],
    'home_maker': ['Home & Kitchen', 'Office', 'Fitness & Lifestyle'] # Adjusted for broader categories
}

# Define required CSV columns
REQUIRED_CSV_COLUMNS = ['title', 'description', 'image_url', 'price', 'category']


def allowed_file(filename):
    """Checks if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

@app.route('/')
def index():
    log_action("Page Loaded")
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
            stream = io.StringIO(file.stream.read().decode("UTF8"))
            csv_reader = csv.DictReader(stream)

            if not all(col in csv_reader.fieldnames for col in REQUIRED_CSV_COLUMNS):
                missing_cols = [col for col in REQUIRED_CSV_COLUMNS if col not in csv_reader.fieldnames]
                flash(f'CSV format error: Missing required column(s): {", ".join(missing_cols)}. Expected {", ".join(REQUIRED_CSV_COLUMNS)}.', 'error')
                log_action("CSV Upload Failed", message=f"Missing CSV columns: {missing_cols}")
                return redirect(url_for('index'))
            
            new_products = []
            for i, row in enumerate(csv_reader):
                try:
                    row['price'] = float(row['price'])
                    if not row.get('category'):
                        flash(f'CSV data error: Missing category for product "{row.get("title", "Unknown")}" in row {i+1}.', 'error')
                        log_action("CSV Upload Failed", message=f"Missing category in row {i+1}.")
                        return redirect(url_for('index'))
                    new_products.append(row)
                except ValueError:
                    flash(f'CSV data error: Price is not a valid number in row {i+1} for product "{row.get("title", "Unknown")}".', 'error')
                    log_action("CSV Upload Failed", message=f"Price format error in row {i+1}.")
                    return redirect(url_for('index'))
            
            if not new_products:
                flash('Uploaded CSV contains no valid product data.', 'error')
                log_action("CSV Upload Failed", message="Uploaded CSV contains no valid product data.")
                return redirect(url_for('index'))

            current_products_data = new_products
            flash(f'Successfully uploaded and updated products from {file.filename}! ({len(new_products)} products loaded)', 'success')
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
    
    products = list(current_products_data)

    if selected_profile and selected_profile in USER_PROFILES:
        preferred_categories = USER_PROFILES[selected_profile]
        
        preferred_products = []
        other_products = []
        
        for product in products:
            # Check if product category is in the preferred list
            if product.get('category') in preferred_categories:
                preferred_products.append(product)
            else:
                other_products.append(product)
        
        # Sort preferred products: first by the order of their category in preferred_categories, then alphabetically by title
        def sort_key_preferred(p):
            category = p.get('category')
            # Assign a very high index if category is not in preferred_categories (shouldn't happen for preferred_products)
            category_order = preferred_categories.index(category) if category in preferred_categories else len(preferred_categories)
            return (category_order, p.get('title', ''))

        preferred_products.sort(key=sort_key_preferred)
        
        # Sort other products alphabetically by title
        other_products.sort(key=lambda p: p.get('title', ''))
        
        sorted_products = preferred_products + other_products
        
        log_action("Products reordered", profile=selected_profile, message=f"Sorted by categories: {preferred_categories}")
        return jsonify(sorted_products)
    
    # If no profile or invalid profile, return products sorted alphabetically by title (default)
    products.sort(key=lambda p: p.get('title', ''))
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
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            f.write("Application Log:\n")
    
    log_action("System Init", message="Application started. Awaiting CSV upload for products.")
    app.run(debug=True)