#!/usr/bin/env python
"""
Test script to verify Supabase PostgreSQL connection
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
from django.db import connection

def test_supabase_connection():
    """
    Test the Supabase PostgreSQL connection using credentials from the environment
    """
    # Check if we have all PostgreSQL credentials
    db_config = settings.DATABASES['default']
    
    print(f"Current database engine: {db_config['ENGINE']}")
    
    if 'postgresql' in db_config['ENGINE']:
        print("Attempting to connect to PostgreSQL...")
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                print(f"Connection successful! Result: {result}")
                return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    else:
        print("Current database is not PostgreSQL. Checking if PostgreSQL credentials are available...")
        
        # Check if individual database credentials are available
        from dotenv import dotenv_values
        config = dotenv_values(BASE_DIR / ".env")
        
        db_credentials = {
            'NAME': config.get("dbname"),
            'USER': config.get("user"),
            'PASSWORD': config.get("password"),
            'HOST': config.get("host"),
            'PORT': config.get("port")
        }
        
        # Print which credentials are available
        for key, value in db_credentials.items():
            status = "SET" if value and value.strip() != "" else "NOT SET"
            print(f"{key}: {status}")
        
        all_set = all(cred is not None and cred.strip() != "" for cred in db_credentials.values())
        if all_set:
            print("All PostgreSQL credentials are available!")
            
            # Try to connect using the credentials
            import psycopg2
            try:
                conn = psycopg2.connect(
                    dbname=db_credentials['NAME'],
                    user=db_credentials['USER'],
                    password=db_credentials['PASSWORD'],
                    host=db_credentials['HOST'],
                    port=db_credentials['PORT']
                )
                print("Successfully connected to PostgreSQL!")
                conn.close()
                return True
            except Exception as e:
                print(f"Failed to connect to PostgreSQL: {e}")
                return False
        else:
            print("Not all PostgreSQL credentials are set in .env file")
            return False

if __name__ == "__main__":
    django.setup()
    success = test_supabase_connection()
    if success:
        print("\n✅ PostgreSQL connection test completed successfully")
        sys.exit(0)
    else:
        print("\n❌ PostgreSQL connection test failed")
        sys.exit(1)