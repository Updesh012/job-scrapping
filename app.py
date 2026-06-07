import os
import json
import time

from flask import Flask, request, Response, render_template, jsonify
from dotenv import load_dotenv

from extractor import process_multiple_pdfs
from emailer import create_smtp_connection, send_single_email, close_connection

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload


@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum upload size is 16 MB.'}), 413


@app.errorhandler(500)
def server_error(e):
    import traceback
    tb = traceback.format_exc()
    return jsonify({
        'error': f'Internal server error: {str(e)}',
        'traceback': tb
    }), 500


@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    tb = traceback.format_exc()
    return jsonify({
        'error': f'{type(e).__name__}: {str(e)}',
        'traceback': tb
    }), 500


@app.route('/')
def index():
    """Serve the main single-page application."""
    return render_template('index.html')


@app.route('/api/extract', methods=['POST'])
def extract():
    """Accept multiple PDF uploads, extract emails, return JSON results.
    
    Expects multipart form data with field name 'pdfs' containing one or more PDF files.
    Returns JSON with per-file results and aggregated unique email list.
    """
    files = request.files.getlist('pdfs')

    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files uploaded'}), 400

    # Read all files into memory as (bytes, filename) tuples
    file_data = []
    for f in files:
        if f.filename and f.filename.lower().endswith('.pdf'):
            file_bytes = f.read()
            file_data.append((file_bytes, f.filename))

    if not file_data:
        return jsonify({'error': 'No valid PDF files found'}), 400

    results = process_multiple_pdfs(file_data)
    return jsonify(results)


@app.route('/api/send-emails', methods=['POST'])
def send_emails():
    """Send emails to extracted HR contacts with resume attachment and real-time progress.
    
    Expects multipart form data with:
        - emails: comma-separated list of recipient email addresses
        - subject: email subject line
        - body: email body text
        - sender_email: sender's Gmail address
        - app_password: Gmail app password
        - resume: PDF file to attach (required)
    
    Returns NDJSON stream with progress updates for each email sent.
    """
    emails_raw = request.form.get('emails', '')
    subject = request.form.get('subject', '').strip()
    body = request.form.get('body', '').strip()
    sender_email = request.form.get('sender_email', '').strip()
    app_password = request.form.get('app_password', '').strip()
    resume_file = request.files.get('resume')

    emails = [e.strip() for e in emails_raw.split(',') if e.strip()]

    # Validation
    if not emails:
        return jsonify({'error': 'No recipient emails provided'}), 400
    if not subject:
        return jsonify({'error': 'Email subject is required'}), 400
    if not body:
        return jsonify({'error': 'Email body is required'}), 400
    if not sender_email or not app_password:
        return jsonify({'error': 'Sender email and app password are required'}), 400
    if not resume_file or resume_file.filename == '':
        return jsonify({'error': 'Resume attachment is required'}), 400

    # Read resume bytes once
    resume_bytes = resume_file.read()
    resume_filename = resume_file.filename

    def generate():
        """Generator that yields NDJSON lines as emails are sent."""
        # Try to establish SMTP connection
        try:
            server = create_smtp_connection(sender_email, app_password)
        except Exception as e:
            yield json.dumps({
                'type': 'error',
                'message': f'Failed to connect to Gmail SMTP. Check your email and app password. Error: {str(e)}'
            }) + '\n'
            return

        sent_count = 0
        failed_count = 0

        for i, email in enumerate(emails):
            success, error = send_single_email(
                server, sender_email, email, subject, body,
                attachment_bytes=resume_bytes,
                attachment_filename=resume_filename
            )

            if success:
                sent_count += 1
            else:
                failed_count += 1

            yield json.dumps({
                'type': 'progress',
                'email': email,
                'success': success,
                'error': error,
                'index': i + 1,
                'total': len(emails),
                'sent_count': sent_count,
                'failed_count': failed_count
            }) + '\n'

            # Small delay between emails to avoid Gmail rate limiting
            if i < len(emails) - 1:
                time.sleep(1.5)

        close_connection(server)

        yield json.dumps({
            'type': 'complete',
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total': len(emails)
        }) + '\n'

    return Response(
        generate(),
        mimetype='application/x-ndjson',
        headers={
            'X-Accel-Buffering': 'no',
            'Cache-Control': 'no-cache',
        }
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)
