from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import csv
import os
import io
from datetime import datetime
from urllib.parse import quote, unquote

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_for_flash_messages'

# --- Configuration ---
PRODUCTS_FILE = 'products.csv'
LOG_FILE = 'app_log.txt'
ALLOWED_EXTENSIONS = {'csv'}

# Global variable to hold the currently active product data
current_products_data = []

# Hardcoded user profiles with their preferred PRODUCT CATEGORIES
USER_PROFILES = {
    'tech_enthusiast': ['Electronics', 'Gaming', 'Smart Home'],
    'home_maker': ['Home & Kitchen', 'Office', 'Fitness & Lifestyle']
}

# Define required CSV columns
REQUIRED_CSV_COLUMNS = ['title', 'description', 'image_url', 'price', 'category']

# Pre-defined demo CSV content
DEMO_CSV_CONTENT = """title,description,image_url,price,category
Smart Watch,Track your fitness and receive notifications,https://via.placeholder.com/150/FF8C00/000000?text=Smart+Watch,199.99,Electronics
Bluetooth Speaker,Portable speaker with rich bass,https://via.placeholder.com/150/8A2BE2/FFFFFF?text=Bluetooth+Speaker,79.00,Electronics
Coffee Maker,Programmable drip coffee machine,https://via.placeholder.com/150/00CED1/000000?text=Coffee+Maker,65.50,Home & Kitchen
Air Fryer,Healthy cooking with less oil,https://via.placeholder.com/150/FF1493/FFFFFF?text=Air+Fryer,110.00,Home & Kitchen
Robot Vacuum,Automatic floor cleaner with smart mapping,https://via.placeholder.com/150/50C878/000000?text=Robot+Vacuum,299.00,Smart Home
Desk Lamp,LED desk lamp with adjustable brightness,https://via.placeholder.com/150/DAA520/FFFFFF?text=Desk+Lamp,35.99,Home & Kitchen
Yoga Mat,Non-slip mat for yoga and pilates,https://via.placeholder.com/150/6A5ACD/FFFFFF?text=Yoga+Mat,20.00,Fitness & Lifestyle
Water Bottle,Insulated stainless steel bottle,https://via.placeholder.com/150/4682B4/FFFFFF?text=Water+Bottle,18.50,Fitness & Lifestyle
Gaming Headset,Immersive audio with noise-cancelling mic,https://via.placeholder.com/150/DC143C/FFFFFF?text=Gaming+Headset,85.00,Gaming
E-Reader,Lightweight device for digital books,https://via.placeholder.com/150/20B2AA/000000?text=E-Reader,130.00,Electronics
Portable Monitor,15.6-inch portable display for laptops,https://via.placeholder.com/150/4169E1/FFFFFF?text=Portable+Monitor,220.00,Electronics
Wireless Charger,Fast charging pad for smartphones,https://via.placeholder.com/150/9370DB/FFFFFF?text=Wireless+Charger,29.99,Electronics
"""

def allowed_file(filename):
    """Checks if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_and_load_csv_data(csv_stream_content, filename):
    """Helper function to parse CSV content and update products."""
    global current_products_data
    try:
        stream = io.StringIO(csv_stream_content)
        csv_reader = csv.DictReader(stream)

        if not all(col in csv_reader.fieldnames for col in REQUIRED_CSV_COLUMNS):
            missing_cols = [col for col in REQUIRED_CSV_COLUMNS if col not in csv_reader.fieldnames]
            flash(f'CSV format error: Missing required column(s): {", ".join(missing_cols)}. Expected {", ".join(REQUIRED_CSV_COLUMNS)}.', 'error')
            log_action("CSV Upload Failed", message=f"Missing CSV columns: {missing_cols} in {filename}")
            return False
        
        new_products = []
        for i, row in enumerate(csv_reader):
            try:
                row['url_encoded_title'] = quote(row['title'])
                
                row['price'] = float(row['price'])
                if not row.get('category'):
                    flash(f'CSV data error: Missing category for product "{row.get("title", "Unknown")}" in row {i+1} of {filename}.', 'error')
                    log_action("CSV Upload Failed", message=f"Missing category in row {i+1} of {filename}.")
                    return False
                new_products.append(row)
            except ValueError:
                flash(f'CSV data error: Price is not a valid number in row {i+1} for product "{row.get("title", "Unknown")}" in {filename}.', 'error')
                log_action("CSV Upload Failed", message=f"Price format error in row {i+1} of {filename}.")
                return False
        
        if not new_products:
            flash('Uploaded CSV contains no valid product data.', 'error')
            log_action("CSV Upload Failed", message=f"Uploaded CSV contains no valid product data from {filename}.")
            return False

        current_products_data = new_products
        flash(f'Successfully loaded products from {filename}! ({len(new_products)} products loaded)', 'success')
        log_action("CSV Loaded Success", message=f"Loaded {len(new_products)} products from {filename}")
        return True
            
    except Exception as e:
        flash(f'Error processing CSV file {filename}: {str(e)}', 'error')
        log_action("CSV Load Failed", message=f"Error processing CSV {filename}: {str(e)}")
        return False


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
        csv_content = file.stream.read().decode("UTF8")
        if parse_and_load_csv_data(csv_content, file.filename):
            return redirect(url_for('index'))
        else:
            return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload a CSV file.', 'error')
        log_action("CSV Upload Failed", message="Invalid file type.")
        return redirect(url_for('index'))

@app.route('/load_demo_store', methods=['POST'])
def load_demo_store():
    """Route to load a predefined demo store."""
    if parse_and_load_csv_data(DEMO_CSV_CONTENT, "demo_products.csv"):
        pass
    return redirect(url_for('index'))

@app.route('/get_products', methods=['POST'])
def get_products():
    data = request.json
    selected_profile = data.get('profile')
    search_query = data.get('search_query', '').strip().lower() # NEW: Get search query
    
    products = list(current_products_data)

    # NEW: Filter products by search query first
    if search_query:
        products = [
            p for p in products 
            if search_query in p.get('title', '').lower() or 
               search_query in p.get('description', '').lower()
        ]
        log_action("Search Performed", message=f"Query: '{search_query}', Results: {len(products)}")

    if selected_profile and selected_profile in USER_PROFILES:
        preferred_categories = USER_PROFILES[selected_profile]
        
        preferred_products = []
        other_products = []
        
        for product in products:
            if product.get('category') in preferred_categories:
                preferred_products.append(product)
            else:
                other_products.append(product)
        
        def sort_key_preferred(p):
            category = p.get('category')
            category_order = preferred_categories.index(category) if category in preferred_categories else len(preferred_categories)
            return (category_order, p.get('title', ''))

        preferred_products.sort(key=sort_key_preferred)
        
        other_products.sort(key=lambda p: p.get('title', ''))
        
        sorted_products = preferred_products + other_products
        
        log_action("Products reordered", profile=selected_profile, message=f"Sorted by categories: {preferred_categories}")
        return jsonify(sorted_products)
    
    products.sort(key=lambda p: p.get('title', ''))
    return jsonify(products)

@app.route('/product/<product_title_encoded>')
def product_detail(product_title_encoded):
    product_title = unquote(product_title_encoded)
    main_product = None
    similar_products = []

    for p in current_products_data:
        if p['title'] == product_title:
            main_product = p
            break

    if not main_product:
        flash(f"Product '{product_title}' not found.", 'error')
        log_action("Product Viewed Failed", message=f"Product '{product_title}' not found.")
        return redirect(url_for('index'))

    log_action("Product Viewed", product_title=main_product['title'])

    if 'category' in main_product:
        for p in current_products_data:
            if p.get('category') == main_product['category'] and p['title'] != main_product['title']:
                similar_products.append(p)
        similar_products = similar_products[:4]

    return render_template('product_detail.html', main_product=main_product, similar_products=similar_products, profiles=USER_PROFILES.keys())


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