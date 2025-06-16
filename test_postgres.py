#!/usr/bin/env python3
"""
Test PostgreSQL connection for SOI Hub project
"""

import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append('/home/itsupport/projects/soi-hub')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

def test_postgres_connection():
    """Test PostgreSQL database connection"""
    try:
        from django.db import connection
        
        print("🔍 Testing PostgreSQL connection...")
        print(f"Database settings:")
        print(f"  - Engine: {settings.DATABASES['default']['ENGINE']}")
        print(f"  - Name: {settings.DATABASES['default']['NAME']}")
        print(f"  - Host: {settings.DATABASES['default']['HOST']}")
        print(f"  - Port: {settings.DATABASES['default']['PORT']}")
        print(f"  - User: {settings.DATABASES['default']['USER']}")
        
        # Test connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"\n✅ PostgreSQL connection successful!")
            print(f"PostgreSQL version: {version}")
            
            # Test basic query
            cursor.execute("SELECT current_database(), current_user;")
            db_info = cursor.fetchone()
            print(f"Connected to database: {db_info[0]}")
            print(f"Connected as user: {db_info[1]}")
            
            # Test table existence
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%event%'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            if tables:
                print(f"\nFound event-related tables:")
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print(f"\nNo event-related tables found (migrations may need to be run)")
                
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL connection failed!")
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Check if it's a connection error
        if "connection" in str(e).lower() or "refused" in str(e).lower():
            print("\n🔧 Possible solutions:")
            print("1. Start PostgreSQL service: sudo systemctl start postgresql")
            print("2. Check if PostgreSQL is installed: sudo systemctl status postgresql")
            print("3. Verify database exists: sudo -u postgres psql -l")
            print("4. Check connection settings in soi_hub/settings.py")
            
        return False

def test_django_models():
    """Test Django models can be imported"""
    try:
        print("\n🔍 Testing Django models...")
        
        from events.models import Event, Venue
        from accounts.models import User
        
        print("✅ Django models imported successfully!")
        print(f"  - Event model: {Event}")
        print(f"  - Venue model: {Venue}")
        print(f"  - User model: {User}")
        
        # Test model counts (if database is accessible)
        try:
            event_count = Event.objects.count()
            venue_count = Venue.objects.count()
            user_count = User.objects.count()
            
            print(f"\nCurrent database counts:")
            print(f"  - Events: {event_count}")
            print(f"  - Venues: {venue_count}")
            print(f"  - Users: {user_count}")
            
        except Exception as e:
            print(f"\nCould not query model counts: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Django models test failed!")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("SOI Hub PostgreSQL Connection Test")
    print("=" * 60)
    
    # Test PostgreSQL connection
    postgres_ok = test_postgres_connection()
    
    # Test Django models
    models_ok = test_django_models()
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"PostgreSQL Connection: {'✅ PASS' if postgres_ok else '❌ FAIL'}")
    print(f"Django Models: {'✅ PASS' if models_ok else '❌ FAIL'}")
    
    if postgres_ok and models_ok:
        print("\n🎉 All tests passed! Ready to proceed with development.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please resolve issues before proceeding.")
        sys.exit(1) 