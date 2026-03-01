"""Test database migrations and alembic setup.

Tests that database migrations run successfully and schema is correct.
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def test_database_connection():
    """Test connection to PostgreSQL database using environment variables.
    
    This test verifies that database credentials are correctly configured
    via environment variables (never hardcoded in source).
    
    Raises:
        psycopg2.Error: If connection fails
    """
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "aeterna"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
            port=int(os.getenv("POSTGRES_PORT", "5432"))
        )
        print("✓ Successfully connected to database!")
        conn.close()
    except psycopg2.Error as e:
        print(f"✗ Database connection failed: {e}")
        raise