"""
HashInsight Enterprise - Test Configuration
测试配置

Provides pytest fixtures for Flask integration testing with in-memory SQLite.
"""

import os
import sys
import pytest

# Set test environment before any app imports
os.environ['SESSION_SECRET'] = 'test-secret-key-for-testing-only'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['TESTING'] = 'true'


@pytest.fixture(scope='session')
def app():
    """Create Flask application for testing with SQLite"""
    # Patch SQLAlchemy config to use SQLite without pool settings
    original_db_url = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    # Import after setting env vars
    from flask import Flask
    from db import db, Base
    
    # Create minimal test app
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['WTF_CSRF_ENABLED'] = False
    test_app.config['SECRET_KEY'] = 'test-secret-key'
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
    
    # Initialize database
    db.init_app(test_app)
    
    with test_app.app_context():
        db.create_all()
    
    yield test_app
    
    # Restore original
    if original_db_url:
        os.environ['DATABASE_URL'] = original_db_url


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()
