"""
Security utilities for input sanitization and validation.
Prevents prompt injection and other security issues.
"""

import re
import logging

logger = logging.getLogger(__name__)


def sanitize_user_input(text: str, max_length: int = 5000) -> str:
    """
    Sanitize user input for safety.

    Args:
        text: User input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        return ""

    # Trim to max length
    text = text[:max_length]

    # Remove null characters
    text = text.replace('\x00', '')

    # Remove control characters except newline, tab, carriage return
    text = re.sub(r'[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

    # Normalize whitespace
    text = ' '.join(text.split())

    return text.strip()


def sanitize_for_prompt(text: str) -> str:
    """
    Sanitize text for use in LLM prompts (prevents prompt injection).

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text safe for prompt injection
    """
    text = sanitize_user_input(text)

    # Escape special prompt characters
    dangerous_patterns = [
        r'\$\{[^}]*\}',  # ${...} variable injection
        r'```.*?```',     # Code block injection
        r'<<.*?>>',       # Delimiter injection
    ]

    for pattern in dangerous_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL)

    return text


def validate_file_upload(filename: str, allowed_extensions: list = None) -> bool:
    """
    Validate uploaded file is safe.

    Args:
        filename: Name of uploaded file
        allowed_extensions: List of allowed extensions (default: pdf, docx, txt)

    Returns:
        True if file is valid, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = ['pdf', 'docx', 'txt', 'doc']

    if not filename:
        return False

    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        logger.warning(f"Path traversal attempt detected: {filename}")
        return False

    # Check file extension
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if extension not in allowed_extensions:
        logger.warning(f"Invalid file extension: {extension}")
        return False

    return True


def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        True if valid email format, False otherwise
    """
    if not email or not isinstance(email, str):
        return False

    # Simple email validation regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def validate_phone(phone: str) -> bool:
    """
    Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        True if valid phone format, False otherwise
    """
    if not phone or not isinstance(phone, str):
        return False

    # Remove common separators
    digits = re.sub(r'[\s\-\(\)\+]', '', phone)

    # Should have 7-15 digits
    return 7 <= len(digits) <= 15 and digits.isdigit()
