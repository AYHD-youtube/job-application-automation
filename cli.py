#!/usr/bin/env python3
# cli.py
"""
Command Line Interface for Job Application Automation
Allows users to register, login, and run automation from the terminal.
"""
import argparse
import getpass
import os
import sys
import sqlite3
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash

from database import JobDatabase

# Database directory
DATABASE_DIR = 'databases'


@contextmanager
def get_user_db():
    """Get user database connection as a context manager"""
    db_path = os.path.join(DATABASE_DIR, 'users.db')
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        print("Please run the Flask app first to initialize the database: python app.py")
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def authenticate_user(email, password):
    """
    Authenticate a user with email and password.
    
    Args:
        email: User's email address
        password: User's password
        
    Returns:
        tuple: (user_data, settings) if successful, exits on failure
    """
    with get_user_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user_data = cursor.fetchone()
        
        if not user_data:
            print(f"Error: User with email '{email}' not found")
            sys.exit(1)
        
        if not check_password_hash(user_data['password_hash'], password):
            print("Error: Invalid password")
            sys.exit(1)
        
        # Get user settings
        cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_data['id'],))
        settings = cursor.fetchone()
        
        # Convert to dict to use outside context manager
        user_dict = dict(user_data)
        settings_dict = dict(settings) if settings else None
        
        return user_dict, settings_dict


def register(args):
    """Register a new user"""
    email = args.email or input("Email: ")
    name = args.name or input("Name: ")
    password = args.password or getpass.getpass("Password: ")
    
    if not email or not name or not password:
        print("Error: Email, name, and password are required")
        sys.exit(1)
    
    with get_user_db() as conn:
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            print(f"Error: Email '{email}' is already registered")
            sys.exit(1)
        
        # Create user
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            (email, password_hash, name)
        )
        user_id = cursor.lastrowid
        
        # Create default settings
        cursor.execute(
            "INSERT INTO user_settings (user_id) VALUES (?)",
            (user_id,)
        )
        
        conn.commit()
    
    print(f"✓ Registration successful!")
    print(f"  User ID: {user_id}")
    print(f"  Email: {email}")
    print(f"  Name: {name}")
    print("\nYou can now login with: python cli.py login --email your@email.com")


def login(args):
    """Login and verify credentials"""
    email = args.email or input("Email: ")
    password = args.password or getpass.getpass("Password: ")
    
    user_data, settings = authenticate_user(email, password)
    
    print(f"✓ Login successful!")
    print(f"  User ID: {user_data['id']}")
    print(f"  Email: {user_data['email']}")
    print(f"  Name: {user_data['name']}")
    
    # Show settings status
    print("\nSettings Status:")
    if settings:
        print(f"  Google API Key: {'✓ Set' if settings['google_api_key'] else '✗ Not set'}")
        print(f"  Hunter API Key: {'✓ Set' if settings['hunter_api_key'] else '✗ Not set'}")
        print(f"  Gmail Auth: {'✓ Authorized' if settings['gmail_authenticated'] else '✗ Not authorized'}")
        print(f"  Resume: {'✓ Uploaded' if settings['resume_filename'] else '✗ Not uploaded'}")
        print(f"  LinkedIn URL: {'✓ Set' if settings['linkedin_search_url'] else '✗ Not set'}")
    else:
        print("  No settings configured yet")
    
    print("\nTo configure settings, visit the web interface at http://localhost:5000")
    
    return user_data['id']


def status(args):
    """Show user status and statistics"""
    email = args.email or input("Email: ")
    password = args.password or getpass.getpass("Password: ")
    
    user_data, settings = authenticate_user(email, password)
    user_id = user_data['id']
    
    # Get recent job runs
    with get_user_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM job_runs 
            WHERE user_id = ? 
            ORDER BY started_at DESC 
            LIMIT 5
        """, (user_id,))
        recent_runs = [dict(row) for row in cursor.fetchall()]
    
    print(f"\n{'='*50}")
    print(f"User Status: {user_data['name']} ({user_data['email']})")
    print(f"{'='*50}")
    
    # Configuration status
    print("\n📋 Configuration:")
    if settings:
        print(f"  • Google API Key: {'✓' if settings['google_api_key'] else '✗'}")
        print(f"  • Hunter API Key: {'✓' if settings['hunter_api_key'] else '✗'}")
        print(f"  • Gmail Authorized: {'✓' if settings['gmail_authenticated'] else '✗'}")
        print(f"  • Resume Uploaded: {'✓' if settings['resume_filename'] else '✗'}")
        print(f"  • LinkedIn URL: {'✓' if settings['linkedin_search_url'] else '✗'}")
    else:
        print("  No settings configured")
    
    # Get stats from user's job database
    user_db_path = os.path.join(DATABASE_DIR, f"user_{user_id}_jobs.db")
    if os.path.exists(user_db_path):
        try:
            with JobDatabase(user_db_path) as db:
                stats = db.get_application_stats()
            print("\n📊 Statistics:")
            print(f"  • Total Jobs Processed: {stats['total_jobs']}")
            print(f"  • Applications Sent: {stats['applications_sent']}")
            print(f"  • Jobs Skipped: {stats['jobs_skipped']}")
            print(f"  • Emails Sent: {stats['emails_sent']}")
        except Exception as e:
            print(f"\n📊 Statistics: Error reading database - {e}")
    else:
        print("\n📊 Statistics: No automation runs yet")
    
    # Recent runs
    if recent_runs:
        print("\n🕐 Recent Automation Runs:")
        for run in recent_runs:
            status_icon = {'completed': '✓', 'failed': '✗', 'running': '⏳', 'stopped': '⏹'}.get(run['status'], '?')
            print(f"  {status_icon} {run['started_at']} - {run['status']} "
                  f"(processed: {run['jobs_processed']}, sent: {run['applications_sent']})")
    else:
        print("\n🕐 Recent Runs: No automation runs yet")
    
    print(f"\n{'='*50}")


def list_users(args):
    """List all registered users (admin function)"""
    with get_user_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, name, created_at FROM users ORDER BY id")
        users = [dict(row) for row in cursor.fetchall()]
    
    if not users:
        print("No users registered yet")
        return
    
    print(f"\n{'='*60}")
    print(f"{'ID':<5} {'Email':<30} {'Name':<15} {'Created'}")
    print(f"{'='*60}")
    
    for user in users:
        print(f"{user['id']:<5} {user['email']:<30} {user['name']:<15} {user['created_at']}")
    
    print(f"{'='*60}")
    print(f"Total users: {len(users)}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Job Application Automation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Register a new user:
    python cli.py register --email user@example.com --name "John Doe"
    
  Login (verify credentials):
    python cli.py login --email user@example.com
    
  Check status and statistics:
    python cli.py status --email user@example.com
    
  List all users:
    python cli.py list-users

Note: For full functionality including Gmail authorization and running automation,
      use the web interface at http://localhost:5000
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Register command
    register_parser = subparsers.add_parser('register', help='Register a new user')
    register_parser.add_argument('--email', '-e', help='Email address')
    register_parser.add_argument('--name', '-n', help='Full name')
    register_parser.add_argument('--password', '-p', help='Password (will prompt if not provided)')
    
    # Login command
    login_parser = subparsers.add_parser('login', help='Login and verify credentials')
    login_parser.add_argument('--email', '-e', help='Email address')
    login_parser.add_argument('--password', '-p', help='Password (will prompt if not provided)')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show user status and statistics')
    status_parser.add_argument('--email', '-e', help='Email address')
    status_parser.add_argument('--password', '-p', help='Password (will prompt if not provided)')
    
    # List users command
    subparsers.add_parser('list-users', help='List all registered users')
    
    args = parser.parse_args()
    
    if args.command == 'register':
        register(args)
    elif args.command == 'login':
        login(args)
    elif args.command == 'status':
        status(args)
    elif args.command == 'list-users':
        list_users(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
