import os
import urllib.parse
import pymysql
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "dynamic_price_db")


def get_database_uri():
    """
    Strict MySQL connection handler.
    Ensures MySQL database exists and connects using SQLAlchemy.
    Properly URL-encodes passwords with special characters (like '@').
    Raises a clear RuntimeError if MySQL is unreachable (no silent fallback).
    """
    try:
        # 1. Connect to MySQL server directly to ensure DB exists
        connection = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            charset="utf8mb4",
            connect_timeout=5
        )
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        connection.commit()
        connection.close()

        # 2. Safely URL-encode the password to handle special characters like '@'
        encoded_password = urllib.parse.quote_plus(MYSQL_PASSWORD)

        print(f"[DATABASE] Connected successfully to MySQL database: '{MYSQL_DB}' at {MYSQL_HOST}:{MYSQL_PORT}")
        if encoded_password:
            return f"mysql+pymysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
        else:
            return f"mysql+pymysql://{MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

    except Exception as e:
        error_msg = (
            f"\n{'='*70}\n"
            f"[DATABASE ERROR] STRICT MYSQL REQUIREMENT FAILED!\n"
            f"Could not connect to MySQL database '{MYSQL_DB}' on {MYSQL_HOST}:{MYSQL_PORT} with user '{MYSQL_USER}'.\n"
            f"Reason: {e}\n"
            f"Please verify:\n"
            f"  1. MySQL Service is running ('MySQL80').\n"
            f"  2. Credentials in '.env' are correct (MYSQL_USER, MYSQL_PASSWORD).\n"
            f"{'='*70}\n"
        )
        print(error_msg)
        raise RuntimeError(f"Database connection error: {e}")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "academic-dynamic-pricing-multiuser-2026")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = get_database_uri()
