# resume_handler.py
"""Handle resume download and text extraction"""
import os
import io
import requests
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
import PyPDF2


def download_resume_from_drive(file_id: str, token_path: str = "token.json") -> bytes:
    """
    Download resume PDF from Google Drive
    
    Args:
        file_id: Google Drive file ID
        token_path: Path to Google OAuth token
        
    Returns:
        PDF file content as bytes
    """
    try:
        creds = Credentials.from_authorized_user_file(token_path)
        service = build('drive', 'v3', credentials=creds)
        
        request = service.files().get_media(fileId=file_id)
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        file_buffer.seek(0)
        return file_buffer.read()
        
    except Exception as e:
        print(f"Error downloading resume from Drive: {e}")
        raise


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extract text from PDF content
    
    Args:
        pdf_content: PDF file as bytes
        
    Returns:
        Extracted text
    """
    try:
        pdf_buffer = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_buffer)
        
        text_parts = []
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        
        return "\n".join(text_parts)
        
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""


def get_resume_text(file_id: str, cache_path: str = "resume_cache.txt", local_pdf: str = "resume.pdf") -> str:
    """
    Get resume text, using cache if available
    
    Priority order:
    1. Check cache file (resume_cache.txt)
    2. Check local PDF file (resume.pdf)
    3. Download from Google Drive
    
    Args:
        file_id: Google Drive file ID
        cache_path: Path to cache file
        local_pdf: Path to local PDF file
        
    Returns:
        Resume text
    """
    # Check cache first (fastest)
    if os.path.exists(cache_path):
        print(f"  Using cached resume text from {cache_path}")
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # Check for local PDF file (no API needed)
    if os.path.exists(local_pdf):
        print(f"  Found local resume file: {local_pdf}")
        try:
            with open(local_pdf, 'rb') as f:
                pdf_content = f.read()
            resume_text = extract_text_from_pdf(pdf_content)
            
            # Cache for future use
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(resume_text)
            
            print(f"  ✓ Extracted text from local PDF and cached")
            return resume_text
        except Exception as e:
            print(f"  ⚠ Error reading local PDF: {e}")
            print(f"  Falling back to Google Drive download...")
    
    # Fallback: Download from Google Drive
    print(f"  Downloading resume from Google Drive...")
    pdf_content = download_resume_from_drive(file_id)
    resume_text = extract_text_from_pdf(pdf_content)
    
    # Cache for future use
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(resume_text)
    
    return resume_text

