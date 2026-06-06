import pymupdf
import re


def extract_text_from_pdf(file_bytes):
    """Extract all text content from a PDF file given as bytes."""
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def extract_emails(text):
    """Extract unique email addresses from text using regex.
    
    Filters out common false-positive domains like example.com.
    """
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    raw_emails = re.findall(email_pattern, text)

    blacklisted_domains = {
        'example.com', 'test.com', 'email.com', 'domain.com',
        'yourcompany.com', 'company.com', 'sentry.io',
        'placeholder.com', 'sample.com',
    }

    filtered = []
    for email in raw_emails:
        email_lower = email.lower().strip()
        domain = email_lower.split('@')[1]
        if domain not in blacklisted_domains:
            filtered.append(email_lower)

    return list(set(filtered))


def process_pdf(file_bytes, filename):
    """Process a single PDF: extract text, split by job separators, extract emails.
    
    PDFs contain multiple job listings separated by lines of '=======' or more.
    Each section is parsed independently for emails.
    """
    try:
        text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        return {
            'filename': filename,
            'emails': [],
            'count': 0,
            'error': f'Failed to read PDF: {str(e)}'
        }

    # Split by separator (3 or more equal signs, possibly with whitespace)
    sections = re.split(r'={3,}', text)

    all_emails = set()
    for section in sections:
        section_text = section.strip()
        if section_text:
            emails = extract_emails(section_text)
            all_emails.update(emails)

    return {
        'filename': filename,
        'emails': sorted(list(all_emails)),
        'count': len(all_emails),
        'error': None
    }


def process_multiple_pdfs(files):
    """Process multiple uploaded PDF files and return aggregated results.
    
    Args:
        files: List of tuples (file_bytes, filename)
    
    Returns:
        Dict with per-file results and aggregated unique emails.
    """
    results = []
    all_emails = set()
    errors = []

    for file_bytes, filename in files:
        result = process_pdf(file_bytes, filename)
        results.append(result)
        if result['error']:
            errors.append({'filename': filename, 'error': result['error']})
        else:
            all_emails.update(result['emails'])

    return {
        'files': results,
        'all_emails': sorted(list(all_emails)),
        'total_count': len(all_emails),
        'errors': errors
    }
