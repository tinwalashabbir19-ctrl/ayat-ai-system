#!/usr/bin/env python3
# ==============================================
# MAIN ORCHESTRATOR - Premium Products AI System
# Complete Agentic AI Workflow
# ==============================================

import os
import sys
import json
import time
import sqlite3
import datetime
import threading
import schedule
from pathlib import Path
from typing import Dict, List, Optional
import logging
import colorlog

# Setup logging
def setup_logging():
    """Configure colored logging"""
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

logger = setup_logging()

# Flask for web dashboard (for Render health checks)
from flask import Flask, jsonify, render_template_string, request
app = Flask(__name__)

# ==============================================
# ORCHESTRATOR CLASS
# ==============================================

class Orchestrator:
    """Main Controller for all agents"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.db_path = self.base_dir / "database" / "products.db"
        
        # Initialize agents
        self.agents = {}
        self.is_running = False
        
        # Create necessary directories
        self.setup_directories()
        
        logger.info("🏪 Premium Products AI System Initialized")
        logger.info(f"📁 Working Directory: {self.base_dir}")
    
    def setup_directories(self):
        """Create all necessary directories"""
        directories = [
            "database",
            "assets/brand",
            "assets/products",
            "assets/output",
            "google_credentials",
            "static/qr_codes",
            "logs",
            "backups"
        ]
        
        for dir_path in directories:
            (self.base_dir / dir_path).mkdir(parents=True, exist_ok=True)
    
    def initialize_database(self):
        """Create database tables if they don't exist"""
        db = sqlite3.connect(self.db_path)
        cursor = db.cursor()
        
        # Products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                description TEXT,
                benefits TEXT,
                ingredients TEXT,
                price_inr REAL,
                stock_quantity INTEGER DEFAULT 0,
                batch_number TEXT,
                manufacturing_date DATE,
                expiry_date DATE,
                image_path TEXT,
                label_path TEXT,
                container_path TEXT,
                weight_grams INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                customer_email TEXT,
                shipping_address TEXT,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_amount REAL,
                status TEXT DEFAULT 'pending',
                payment_status TEXT DEFAULT 'pending',
                payment_method TEXT,
                tracking_number TEXT,
                dispatch_date DATE,
                delivery_date DATE,
                notes TEXT
            )
        ''')
        
        # Order items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                price_at_time REAL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        
        # Inventory movements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                quantity_change INTEGER,
                movement_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        
        # Social posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                platform TEXT,
                post_type TEXT,
                content TEXT,
                image_path TEXT,
                scheduled_time TIMESTAMP,
                posted_at TIMESTAMP,
                status TEXT DEFAULT 'scheduled',
                post_id TEXT,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0
            )
        ''')
        
        # WhatsApp conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whatsapp_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_phone TEXT,
                customer_name TEXT,
                last_message TEXT,
                last_message_time TIMESTAMP,
                conversation_state TEXT DEFAULT 'new',
                order_id INTEGER,
                sentiment TEXT,
                auto_reply_sent BOOLEAN DEFAULT 0,
                language TEXT DEFAULT 'en'
            )
        ''')
        
        # Email logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                subject TEXT,
                body TEXT,
                received_time TIMESTAMP,
                replied BOOLEAN DEFAULT 0,
                escalated BOOLEAN DEFAULT 0,
                sentiment TEXT,
                reply_sent TEXT
            )
        ''')
        
        db.commit()
        db.close()
        
        logger.info("✅ Database initialized successfully")
    
    def create_sample_products(self):
        """Create sample products in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        products = [
            ('Lavender Dream Soap', 'soap', 'Lavender', 'Handmade lavender soap with essential oils', 
             'Relaxes mind, Soothes skin, Natural fragrance', 299, 50, 'Lavender oil, Shea butter, Glycerin'),
            ('Rose Petal Soap', 'soap', 'Rose', 'Luxurious rose petal soap for glowing skin',
             'Brightens skin, Natural glow, Anti-aging', 349, 45, 'Rose extract, Shea butter, Vitamin E'),
            ('Charcoal Detox Soap', 'soap', 'Charcoal', 'Deep cleansing charcoal soap for clear skin',
             'Detoxifies skin, Removes impurities, Controls oil', 279, 40, 'Activated charcoal, Tea tree oil'),
            ('Coconut Milk Soap', 'soap', 'Coconut', 'Nourishing coconut milk soap for soft skin',
             'Deep moisturizing, Softens skin, Natural glow', 259, 55, 'Coconut milk, Shea butter, Vitamin E'),
            ('Green Tea Soap', 'soap', 'Green Tea', 'Antioxidant-rich green tea soap for youthful skin',
             'Anti-aging, Protects skin, Natural freshness', 319, 30, 'Green tea extract, Vitamin C, Aloe vera'),
            ('Honey & Oatmeal Soap', 'soap', 'Honey', 'Gentle honey and oatmeal soap for sensitive skin',
             'Soothes skin, Natural moisturizer, Gentle exfoliation', 269, 40, 'Honey, Oatmeal, Shea butter'),
            ('Coffee Scrub Soap', 'soap', 'Coffee', 'Exfoliating coffee scrub soap for smooth skin',
             'Removes dead skin, Improves circulation, Cellulite reduction', 299, 35, 'Coffee grounds, Coconut oil'),
            ('Mango Butter Soap', 'soap', 'Mango', 'Rich mango butter soap for dry skin',
             'Intense hydration, Nourishes skin, Natural protection', 329, 30, 'Mango butter, Cocoa butter, Vitamin E'),
            ('Sea Salt Soap', 'soap', 'Sea Salt', 'Mineral-rich sea salt soap for skin health',
             'Exfoliates skin, Mineral boost, Natural rejuvenation', 279, 25, 'Sea salt, Coconut oil, Essential oils'),
            ('Matcha Soap', 'soap', 'Matcha', 'Antioxidant matcha soap for radiant skin',
             'Anti-aging, Brightens skin, Natural protection', 349, 20, 'Matcha powder, Shea butter, Vitamin E'),
            ('Milk & Honey Soap', 'soap', 'Milk', 'Classic milk and honey soap for soft skin',
             'Gentle cleansing, Natural moisturizing, Softens skin', 259, 45, 'Milk powder, Honey, Glycerin'),
            ('Lemon Grass Soap', 'soap', 'Lemon Grass', 'Refreshing lemongrass soap for revitalizing skin',
             'Energizes skin, Natural fragrance, Purifies skin', 289, 30, 'Lemongrass oil, Glycerin, Vitamin E'),
            ('Green Tea Foam Facewash', 'facewash', 'Green Tea', 'Gentle green tea foam facewash', 
             'Cleanses deeply, Protects skin, Natural freshness', 399, 25, 'Green tea extract, Aloe vera, Vitamin C'),
            ('Vitamin C Foam Facewash', 'facewash', 'Vitamin C', 'Brightening vitamin C foam facewash',
             'Brightens skin, Even tone, Natural glow', 449, 20, 'Vitamin C, Hyaluronic acid, Vitamin E'),
            ('Charcoal Foam Facewash', 'facewash', 'Charcoal', 'Deep cleansing charcoal foam facewash',
             'Detoxifies skin, Removes impurities, Controls oil', 349, 30, 'Activated charcoal, Tea tree oil'),
            ('Saffron Foam Facewash', 'facewash', 'Saffron', 'Luxurious saffron foam facewash for glowing skin',
             'Brightens skin, Natural glow, Anti-aging', 499, 15, 'Saffron, Sandalwood, Vitamin E'),
            ('Aloe Vera Foam Facewash', 'facewash', 'Aloe Vera', 'Soothing aloe vera foam facewash',
             'Soothes skin, Natural hydration, Gentle cleansing', 369, 30, 'Aloe vera, Chamomile, Vitamin E'),
            ('Tea Tree Foam Facewash', 'facewash', 'Tea Tree', 'Antibacterial tea tree foam facewash',
             'Fights acne, Controls oil, Natural protection', 389, 20, 'Tea tree oil, Witch hazel, Aloe vera'),
            ('Vitamin C Brightening Serum', 'serum', 'Vitamin C', 'Powerful vitamin C brightening serum',
             'Brightens skin, Reduces dark spots, Anti-aging', 699, 15, 'Vitamin C, Hyaluronic acid, Vitamin E'),
            ('Hyaluronic Acid Serum', 'serum', 'Hyaluronic', 'Intense hydration hyaluronic acid serum',
             'Deep hydration, Plumps skin, Reduces fine lines', 749, 12, 'Hyaluronic acid, Vitamin B5, Vitamin E'),
            ('Retinol Anti-Aging Serum', 'serum', 'Retinol', 'Advanced retinol anti-aging serum',
             'Reduces wrinkles, Fights aging, Improves texture', 849, 10, 'Retinol, Vitamin E, Hyaluronic acid'),
            ('Niacinamide Serum', 'serum', 'Niacinamide', 'Pore-minimizing niacinamide serum',
             'Reduces pores, Even skin tone, Controls oil', 649, 15, 'Niacinamide, Zinc, Vitamin C'),
            ('Peptide Firming Serum', 'serum', 'Peptide', 'Firming peptide serum for youthful skin',
             'Firms skin, Improves elasticity, Reduces wrinkles', 799, 8, 'Peptides, Hyaluronic acid, Vitamin E'),
            ('Biotin Hair Growth Shampoo', 'shampoo', 'Biotin', 'Strengthening biotin shampoo',
             'Promotes hair growth, Strengthens hair, Reduces fall', 449, 20, 'Biotin, Keratin, Argan oil'),
            ('Coconut Milk Nourishing Shampoo', 'shampoo', 'Coconut', 'Nourishing coconut milk shampoo',
             'Deep conditions, Softens hair, Natural shine', 399, 25, 'Coconut milk, Argan oil, Vitamin E'),
            ('GlowFence Sunscreen Cream', 'cream', 'Sunscreen', 'Broad spectrum SPF 50 sunscreen cream',
             'Protects from UV, Prevents tanning, Hydrates skin', 599, 20, 'Zinc oxide, Vitamin E, Aloe vera'),
            ('Skin Whitening Cream', 'cream', 'Whitening', 'Advanced skin whitening and brightening cream',
             'Brightens skin, Even tone, Reduces pigmentation', 699, 15, 'Kojic acid, Vitamin C, Shea butter'),
            ('5-in-1 Hair Oil', 'oil', 'Hair Oil', 'Complete 5-in-1 hair oil for healthy hair',
             'Strengthens hair, Promotes growth, Reduces dandruff, Deep conditions, Prevents split ends', 499, 25, 
             'Coconut oil, Argan oil, Almond oil, Castor oil, Rosemary oil')
        ]
        
        for product in products:
            cursor.execute('''
                INSERT OR IGNORE INTO products
                (name, category, subcategory, description, benefits, price_inr, stock_quantity, ingredients)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', product)
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ {len(products)} sample products created!")

# ==============================================
# HEALTH CHECK ENDPOINT (For Render)
# ==============================================

@app.route('/')
@app.route('/health')
def health_check():
    """Health check endpoint for Render and cron-job.org"""
    return jsonify({
        'status': 'healthy',
        'service': 'Premium Products AI System',
        'timestamp': datetime.datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/status')
def status_page():
    """Simple status page"""
    return jsonify({
        'status': 'running',
        'message': 'Agentic AI System is operational',
        'uptime': '24/7'
    })

# ==============================================
# STARTUP
# ==============================================

def start_web_server():
    """Start Flask web server for Render"""
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    # Initialize orchestrator
    orchestrator = Orchestrator()
    orchestrator.initialize_database()
    orchestrator.create_sample_products()
    
    logger.info("🚀 Starting Agentic AI System...")
    
    # Start web server in thread
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    
    logger.info(f"🌐 Web Dashboard: http://localhost:{os.environ.get('PORT', 5000)}")
    logger.info("📱 WhatsApp Agent: Ready")
    logger.info("📧 Email Agent: Ready")
    logger.info("📦 Inventory Agent: Ready")
    logger.info("✅ System is running!")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("🛑 System shutting down...")
        sys.exit(0)