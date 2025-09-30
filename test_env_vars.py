#!/usr/bin/env python
"""
Test script to verify environment variables in Vercel-like environment
"""
import os
import sys
from pathlib import Path

# Add the project to the path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeser.settings')

import django
from django.conf import settings

def test_environment():
    """
    Test environment variables
    """
    print("=== Environment Variables Test ===")
    
    # Check DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    print(f"DATABASE_URL: {'SET' if database_url else 'NOT SET'}")
    if database_url:
        print(f"DATABASE_URL value: {database_url[:50]}...")
    
    # Check individual database credentials
    db_name = os.environ.get('dbname')
    db_user = os.environ.get('user')
    db_password = os.environ.get('password')
    db_host = os.environ.get('host')
    db_port = os.environ.get('port')
    
    print(f"dbname: {'SET' if db_name else 'NOT SET'}")
    print(f"user: {'SET' if db_user else 'NOT SET'}")
    print(f"password: {'SET' if db_password else 'NOT SET'}")
    print(f"host: {'SET' if db_host else 'NOT SET'}")
    print(f"port: {'SET' if db_port else 'NOT SET'}")
    
    # Print current database configuration
    print("\n=== Current Database Configuration ===")
    current_db = settings.DATABASES['default']
    print(f"Engine: {current_db['ENGINE']}")
    print(f"Name: {current_db.get('NAME', 'N/A')}")
    print(f"User: {current_db.get('USER', 'N/A')}")
    print(f"Host: {current_db.get('HOST', 'N/A')}")
    print(f"Port: {current_db.get('PORT', 'N/A')}")

if __name__ == "__main__":
    django.setup()
    test_environment()