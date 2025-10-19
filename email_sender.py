# email_sender.py
"""Send emails via Gmail API"""
import base64
import email.message
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from typing import List, Dict


def send_application_email(
    to_email: str,
    subject: str,
    body_html: str,
    sender_name: str,
    sender_email: str,
    token_path: str = "token.json"
) -> bool:
    """
    Send application email via Gmail API
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body_html: Email body in HTML format
        sender_name: Sender's name
        sender_email: Sender's email address
        token_path: Path to Gmail OAuth token
        
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        creds = Credentials.from_authorized_user_file(token_path)
        service = build('gmail', 'v1', credentials=creds)
        
        # Create message
        msg = email.message.EmailMessage()
        msg['To'] = to_email
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['Subject'] = subject
        
        # Set HTML content
        msg.set_content(body_html, subtype='html')
        
        # Encode message
        encoded_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        
        # Send
        service.users().messages().send(
            userId='me',
            body={'raw': encoded_msg}
        ).execute()
        
        print(f"✓ Email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"✗ Error sending email to {to_email}: {e}")
        return False


def send_to_multiple_recipients(
    recipients: List[str],
    subject: str,
    body_html: str,
    sender_name: str,
    sender_email: str,
    token_path: str = "token.json"
) -> Dict[str, bool]:
    """
    Send email to multiple recipients
    
    Args:
        recipients: List of recipient email addresses
        subject: Email subject
        body_html: Email body in HTML format
        sender_name: Sender's name
        sender_email: Sender's email address
        token_path: Path to Gmail OAuth token
        
    Returns:
        Dictionary mapping email addresses to success status
    """
    results = {}
    
    for recipient in recipients:
        success = send_application_email(
            to_email=recipient,
            subject=subject,
            body_html=body_html,
            sender_name=sender_name,
            sender_email=sender_email,
            token_path=token_path
        )
        results[recipient] = success
    
    return results

