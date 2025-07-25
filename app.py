from flask import Flask, render_template, request, jsonify
import csv
import os
import json

app = Flask(__name__)

# --- Configuration ---
PRODUCTS_FILE = 'products.csv'
LOG_FILE = 'app_log.txt'

# Hardcoded user profiles with their preferred product titles
USER_PROFILES = {
    'tech_enthusiast': ['Laptop', 'External SSD', 'Monitor', 'Keyboard'],
    'casual_user': ['Headphones', 'Mouse', 'USB Drive', 'Webcam']
}

def load_products():
    """Loads products from the CSV file."""
    products = []
    try:
        with open(PRODUCTS_FILE, mode='r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                # Ensure price is a float for sorting
                row['price'] = float(row['price'])
                products.append(row)
    except FileNotFoundError:
        print(f"Error: {PRODUCTS_FILE} not found.")
    return products

def log_action(action_type, product_title=None, profile=None):
    """Logs user actions to a file."""
    timestamp = os.system('date +"%Y-%m-%d %H:%M:%S"') # This won't work correctly, using a Python method instead.
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = f"[{timestamp}] Action: {action_type}"
    if product_title:
        log_entry += f", Product: {product_title}"
    if profile:
        log_entry += f", Profile: {profile}"
    
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + '\n')
    print(f"Logged: {log_entry}") # For debugging purposes

@app.route('/')
def index():
    products = load_products()
    log_action("Page Loaded")
    return render_template('index.html', products=products, profiles=USER_PROFILES.keys())

@app.route('/get_products', methods=['POST'])
def get_products():
    data = request.json
    selected_profile = data.get('profile')
    
    products = load_products()

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
    app.run(debug=True) # debug=True is good for development, disable for production