"""
LUMA Backend Application
Flask REST API Server for Distributed AI Image Generation
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Import database and blueprints
from models import db
from routes.auth import auth_bp
from routes.generate import generate_bp

# Load environment variables from .env file
load_dotenv()

def create_app():
    """Application factory for LUMA Flask Backend"""
    app = Flask(__name__)

    # 1. Base Configuration
    base_dir = os.path.abspath(os.path.dirname(__file__))
    logs_dir = os.path.join(base_dir, 'logs')
    outputs_dir = os.path.join(base_dir, 'outputs')
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(outputs_dir, exist_ok=True)

    db_path = os.environ.get('DATABASE_URI', f"sqlite:///{os.path.join(base_dir, 'luma.db')}")
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'luma-session-secret-key-dev')
    app.config['JWT_SECRET'] = os.environ.get('JWT_SECRET', 'luma-jwt-super-secret-key-2026')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['OUTPUT_FOLDER'] = outputs_dir
    app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 # Max 20MB payload

    # 2. CORS Setup (Allow frontend at 192.168.1.10 and localhost)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # 3. Logging Setup
    configure_logging(app, logs_dir)

    # 4. Database Setup
    db.init_app(app)
    with app.app_context():
        db.create_all()
        app.logger.info("Database initialized successfully.")

    # 5. Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(generate_bp, url_prefix='/api')

    # 6. Global Routes & Error Handlers
    @app.route('/api/health', methods=['GET'])
    def health_check():
        from services.ai_client import ai_client
        ai_healthy = ai_client.is_healthy()
        return jsonify({
            'status': 'healthy',
            'service': 'luma-backend',
            'database': 'connected',
            'ai_server': {
                'url': ai_client.server_url,
                'status': 'online' if ai_healthy else 'offline/mock',
                'mock_mode': ai_client.mock_mode
            }
        }), 200

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not Found', 'message': 'Requested API endpoint does not exist'}), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"Internal Server Error: {e}")
        return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected server error occurred'}), 500

    return app


def configure_logging(app, logs_dir):
    """Configure rotating file handler and console logging"""
    log_file = os.path.join(logs_dir, 'luma_backend.log')
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s in %(filename)s:%(lineno)d]: %(message)s'
    )

    # Rotating file handler (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    # Also route root logger to catch logs from services
    root_logger = logging.getLogger('luma')
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    app.logger.info("LUMA Backend logging system configured.")


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    app.logger.info(f"Starting LUMA Flask Server on http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
