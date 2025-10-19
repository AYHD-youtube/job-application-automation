# database.py
"""SQLite database for tracking job applications"""
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional


class JobDatabase:
    """Database for tracking job applications and preventing duplicates"""
    
    def __init__(self, db_path: str = "job_applications.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self.cursor = self.conn.cursor()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        
        # Jobs table - tracks all processed jobs
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE,
                job_url TEXT UNIQUE NOT NULL,
                company TEXT,
                title TEXT,
                location TEXT,
                description TEXT,
                applicant_count INTEGER,
                days_posted INTEGER,
                salary_min INTEGER,
                salary_max INTEGER,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_processed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Applications table - tracks all sent applications
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                relevance_score INTEGER,
                score_reasoning TEXT,
                key_matches TEXT,
                missing_skills TEXT,
                cover_letter TEXT,
                applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)
        
        # Emails table - tracks who we emailed
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL,
                recipient_email TEXT NOT NULL,
                sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT 1,
                FOREIGN KEY (application_id) REFERENCES applications(id)
            )
        """)
        
        # Skipped jobs table - tracks jobs we skipped and why
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS skipped_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                skip_reason TEXT NOT NULL,
                skip_type TEXT,
                skipped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)
        
        # Create indexes for faster lookups
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_url ON jobs(job_url)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_id ON jobs(job_id)
        """)
        
        self.conn.commit()
    
    def job_already_processed(self, job_url: str) -> bool:
        """
        Check if a job has already been processed
        
        Args:
            job_url: Job URL to check
            
        Returns:
            True if job was already processed, False otherwise
        """
        self.cursor.execute("""
            SELECT COUNT(*) as count FROM jobs WHERE job_url = ?
        """, (job_url,))
        
        result = self.cursor.fetchone()
        return result['count'] > 0
    
    def job_already_applied(self, job_url: str) -> bool:
        """
        Check if we already applied to this job
        
        Args:
            job_url: Job URL to check
            
        Returns:
            True if already applied, False otherwise
        """
        self.cursor.execute("""
            SELECT COUNT(*) as count 
            FROM jobs j
            JOIN applications a ON j.id = a.job_id
            WHERE j.job_url = ? AND a.status = 'Applied'
        """, (job_url,))
        
        result = self.cursor.fetchone()
        return result['count'] > 0
    
    def add_job(self, job_data: Dict[str, Any]) -> int:
        """
        Add a job to the database
        
        Args:
            job_data: Dictionary containing job information
            
        Returns:
            Job ID (database primary key)
        """
        self.cursor.execute("""
            INSERT OR IGNORE INTO jobs 
            (job_id, job_url, company, title, location, description, 
             applicant_count, days_posted, salary_min, salary_max)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_data.get('JobID'),
            job_data.get('job_url'),
            job_data.get('Company'),
            job_data.get('Title'),
            job_data.get('Location'),
            job_data.get('Description'),
            job_data.get('applicant_count_num'),
            job_data.get('days_posted_ago'),
            job_data.get('salary_min'),
            job_data.get('salary_max')
        ))
        
        self.conn.commit()
        
        # Get the job ID
        self.cursor.execute("SELECT id FROM jobs WHERE job_url = ?", (job_data.get('job_url'),))
        result = self.cursor.fetchone()
        return result['id']
    
    def add_application(
        self,
        job_id: int,
        status: str,
        scoring_data: Dict[str, Any],
        cover_letter: str = ""
    ) -> int:
        """
        Add an application record
        
        Args:
            job_id: Job ID from database
            status: Application status (Applied, Skipped, Failed)
            scoring_data: AI scoring data
            cover_letter: Generated cover letter
            
        Returns:
            Application ID
        """
        self.cursor.execute("""
            INSERT INTO applications 
            (job_id, status, relevance_score, score_reasoning, 
             key_matches, missing_skills, cover_letter)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            status,
            scoring_data.get('score', 0),
            scoring_data.get('reasoning', ''),
            ', '.join(scoring_data.get('key_matches', [])),
            ', '.join(scoring_data.get('missing_skills', [])),
            cover_letter
        ))
        
        self.conn.commit()
        return self.cursor.lastrowid
    
    def add_email_sent(self, application_id: int, recipient_email: str, success: bool = True):
        """
        Record an email that was sent
        
        Args:
            application_id: Application ID from database
            recipient_email: Email address
            success: Whether email was sent successfully
        """
        self.cursor.execute("""
            INSERT INTO emails_sent (application_id, recipient_email, success)
            VALUES (?, ?, ?)
        """, (application_id, recipient_email, success))
        
        self.conn.commit()
    
    def add_skipped_job(self, job_id: int, skip_reason: str, skip_type: str):
        """
        Record a skipped job
        
        Args:
            job_id: Job ID from database
            skip_reason: Reason for skipping
            skip_type: Type of skip (quality, score, no_emails, etc.)
        """
        self.cursor.execute("""
            INSERT INTO skipped_jobs (job_id, skip_reason, skip_type)
            VALUES (?, ?, ?)
        """, (job_id, skip_reason, skip_type))
        
        self.conn.commit()
    
    def get_application_stats(self) -> Dict[str, int]:
        """
        Get statistics about applications
        
        Returns:
            Dictionary with stats
        """
        stats = {}
        
        # Total jobs processed
        self.cursor.execute("SELECT COUNT(*) as count FROM jobs")
        stats['total_jobs'] = self.cursor.fetchone()['count']
        
        # Applications sent
        self.cursor.execute("""
            SELECT COUNT(*) as count FROM applications WHERE status = 'Applied'
        """)
        stats['applications_sent'] = self.cursor.fetchone()['count']
        
        # Jobs skipped
        self.cursor.execute("SELECT COUNT(*) as count FROM skipped_jobs")
        stats['jobs_skipped'] = self.cursor.fetchone()['count']
        
        # Emails sent
        self.cursor.execute("SELECT COUNT(*) as count FROM emails_sent WHERE success = 1")
        stats['emails_sent'] = self.cursor.fetchone()['count']
        
        return stats
    
    def get_recent_applications(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent applications
        
        Args:
            limit: Number of applications to return
            
        Returns:
            List of application dictionaries
        """
        self.cursor.execute("""
            SELECT 
                j.company,
                j.title,
                j.job_url,
                a.relevance_score,
                a.applied_date,
                GROUP_CONCAT(e.recipient_email) as emails
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            LEFT JOIN emails_sent e ON a.id = e.application_id
            WHERE a.status = 'Applied'
            GROUP BY a.id
            ORDER BY a.applied_date DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


if __name__ == "__main__":
    # Test the database
    with JobDatabase() as db:
        print("Database initialized successfully!")
        print("\nTables created:")
        print("  - jobs")
        print("  - applications")
        print("  - emails_sent")
        print("  - skipped_jobs")
        
        stats = db.get_application_stats()
        print(f"\nCurrent stats:")
        print(f"  Total jobs: {stats['total_jobs']}")
        print(f"  Applications sent: {stats['applications_sent']}")
        print(f"  Jobs skipped: {stats['jobs_skipped']}")
        print(f"  Emails sent: {stats['emails_sent']}")

