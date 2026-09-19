"""
Authentication Routes & JWT Middleware
Endpoints:
- POST /api/register
- POST /api/login
- GET  /api/me
"""

import jwt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError
from models import db, User

logger = logging.getLogger('luma.auth')
auth_bp = Blueprint('auth', __name__)

def token_required(f):
    """
    JWT Authentication Decorator
    Validates Bearer token in the 'Authorization' header and injects current_user.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')

        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]

        if not token:
            return jsonify({'error': 'Unauthorized', 'message': 'Missing authentication token'}), 401

        try:
            payload = jwt.decode(
                token, 
                current_app.config['JWT_SECRET'], 
                algorithms=['HS256']
            )
            user_id = payload.get('user_id')
            current_user = User.query.get(user_id)
            if not current_user:
                return jsonify({'error': 'Unauthorized', 'message': 'User no longer exists'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Unauthorized', 'message': 'Token has expired, please log in again'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'error': 'Unauthorized', 'message': f'Invalid token: {str(e)}'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register new user account"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Bad Request', 'message': 'Username and password are required'}), 400

    if len(username) < 3:
        return jsonify({'error': 'Bad Request', 'message': 'Username must be at least 3 characters'}), 400

    if len(password) < 4:
        return jsonify({'error': 'Bad Request', 'message': 'Password must be at least 4 characters'}), 400

    # Check for existing user
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Conflict', 'message': f"Username '{username}' is already taken"}), 409

    try:
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        logger.info(f"Registered new user: {username} (ID: {user.id})")
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict()
        }), 201
    except IntegrityError:
        db.session.rollback()
        logger.warning(f"Registration conflict for username '{username}' (IntegrityError)")
        return jsonify({'error': 'Conflict', 'message': f"Username '{username}' is already taken"}), 409
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error for {username}: {e}")
        return jsonify({'error': 'Internal Server Error', 'message': 'Failed to create user'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Bad Request', 'message': 'Username and password are required'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        logger.warning(f"Failed login attempt for username: {username}")
        return jsonify({'error': 'Unauthorized', 'message': 'Invalid username or password'}), 401

    # Issue JWT Token (Valid for 7 days)
    token_payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow()
    }

    token = jwt.encode(token_payload, current_app.config['JWT_SECRET'], algorithm='HS256')
    logger.info(f"User {username} logged in successfully")

    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """Retrieve logged-in user details"""
    return jsonify({'user': current_user.to_dict()}), 200
