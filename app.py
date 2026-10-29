"""
Krishi Khoj — Turn Farm PDFs into Searchable Data
Main Flask application.

Every extracted fact carries full provenance:
  document name, SHA-256 hash, version, page number, extraction timestamp.
"""
import os
import csv
import json
import io
import re
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, send_file, Response, session
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import (
    UPLOAD_FOLDER, DATABASE_PATH, MAX_CONTENT_LENGTH,
    ALLOWED_EXTENSIONS, SECRET_KEY, DEBUG,
    SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE, PERMANENT_SESSION_LIFETIME
)
from database import (
    init_db, insert_document, insert_fact, insert_page_text,
    search_facts, get_fact_by_id, get_document_by_id,
    get_all_documents, get_page_text, get_stats,
    get_distinct_values, delete_document, get_document_facts,
    get_search_autocomplete,
    create_user, get_user_by_username, get_user_by_id
)
from pdf_processor import PDFProcessor
from fact_extractor import extract_facts_from_document, get_extraction_summary
from provenance import get_timestamp

# ─── App Setup ────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE
app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
app.config['PERMANENT_SESSION_LIFETIME'] = PERMANENT_SESSION_LIFETIME

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database on startup
init_db()


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def format_file_size(size_bytes):
    """Format file size to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# ─── Template Context & Filters ───────────────────────────────────────────────

@app.context_processor
def inject_current_user():
    """Inject safe current_user into templates without exposing credentials."""
    user_id = session.get('user_id')
    username = session.get('username')
    if user_id and username:
        return {'current_user': {'id': user_id, 'username': username}}
    return {'current_user': None}


@app.template_filter('filesize')
def filesize_filter(size_bytes):
    """Jinja2 filter for file size formatting."""
    return format_file_size(size_bytes)


@app.template_filter('truncate_hash')
def truncate_hash_filter(hash_str, length=8):
    """Jinja2 filter to truncate hash for display."""
    if hash_str and len(hash_str) > length:
        return hash_str[:length] + '...'
    return hash_str


# ─── Routes: Authentication ───────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new farmer account."""
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Input validation
        if not username:
            flash('Username is required.', 'error')
            return render_template('register.html', username=username)

        if len(username) < 3 or len(username) > 30:
            flash('Username must be between 3 and 30 characters.', 'error')
            return render_template('register.html', username=username)

        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            flash('Username may only contain letters, numbers, underscores, and hyphens.', 'error')
            return render_template('register.html', username=username)

        if not password:
            flash('Password is required.', 'error')
            return render_template('register.html', username=username)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html', username=username)

        if password != confirm_password:
            flash('Passwords do not match. Please verify your password.', 'error')
            return render_template('register.html', username=username)

        # Hash password and create user safely
        password_hash = generate_password_hash(password)
        user_id = create_user(username, password_hash)

        if not user_id:
            flash('That username is already taken. Please choose another username.', 'error')
            return render_template('register.html', username=username)

        # Successful registration - establish session
        session.clear()
        session['user_id'] = user_id
        session['username'] = username
        flash('Account created successfully! Welcome to Krishi Khoj.', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Log in with an existing farmer account."""
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html', username=username)

        user = get_user_by_username(username)
        # Check credentials without leaking whether username exists
        if not user or not check_password_hash(user['password_hash'], password):
            flash('Invalid username or password. Please try again.', 'error')
            return render_template('login.html', username=username)

        # Successful login
        session.clear()
        session['user_id'] = user['id']
        session['username'] = user['username']
        flash(f'Welcome back, {user["username"]}!', 'success')

        next_url = request.args.get('next')
        if next_url and next_url.startswith('/') and not next_url.startswith('//'):
            return redirect(next_url)
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Log out the current user."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ─── Routes: Pages ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Home page with upload form and overview."""
    stats = get_stats()
    documents = get_all_documents()
    return render_template('index.html', stats=stats, documents=documents)


@app.route('/search')
def search_page():
    """Search and filter facts."""
    # Get filter parameters
    query = request.args.get('q', '').strip()
    crop_filter = request.args.get('crop', '').strip()
    category_filter = request.args.get('category', '').strip()
    season_filter = request.args.get('season', '').strip()
    page = request.args.get('page', 1, type=int)

    # Search with filters
    results = search_facts(
        query=query or None,
        crop=crop_filter or None,
        category=category_filter or None,
        season=season_filter or None,
        page=page,
        per_page=20
    )

    # Get filter options
    crops = get_distinct_values('crop_name')
    categories = get_distinct_values('category')
    seasons = get_distinct_values('season')

    return render_template(
        'search.html',
        facts=results['facts'],
        total=results['total'],
        page=results['page'],
        per_page=results['per_page'],
        total_pages=results['total_pages'],
        query=query,
        crop_filter=crop_filter,
        category_filter=category_filter,
        season_filter=season_filter,
        crops=crops,
        categories=categories,
        seasons=seasons
    )


@app.route('/document/<int:document_id>')
def document_detail(document_id):
    """Document detail with page-by-page facts view."""
    document = get_document_by_id(document_id)
    if not document:
        flash('Document not found.', 'error')
        return redirect(url_for('index'))

    # Get all facts for this document, grouped by page
    all_facts = get_document_facts(document_id)
    pages_data = []

    for page_num in range(1, document['page_count'] + 1):
        pt = get_page_text(document_id, page_num)
        page_facts = [f for f in all_facts if f['page_number'] == page_num]
        pages_data.append({
            'page_number': page_num,
            'page_text': pt if pt else '',
            'facts': page_facts
        })

    # Generate summary
    summary = {
        'total_facts': len(all_facts),
        'by_category': {},
        'crops_found': list(set(f['crop_name'] for f in all_facts if f.get('crop_name'))),
        'seasons_found': list(set(f['season'] for f in all_facts if f.get('season')))
    }
    for f in all_facts:
        cat = f['category']
        summary['by_category'][cat] = summary['by_category'].get(cat, 0) + 1

    return render_template(
        'document.html',
        document=document,
        pages=pages_data,
        summary=summary
    )


@app.route('/fact/<int:fact_id>')
def fact_detail(fact_id):
    """Single fact detail with full provenance and source context."""
    fact = get_fact_by_id(fact_id)
    if not fact:
        flash('Fact not found.', 'error')
        return redirect(url_for('search_page'))

    page_text = get_page_text(fact['document_id'], fact['page_number'])

    return render_template(
        'fact_detail.html',
        fact=fact,
        page_text=page_text or ''
    )


@app.route('/documents')
def documents_list():
    """List all uploaded documents."""
    documents = get_all_documents()
    total_facts = sum(d.get('fact_count', 0) for d in documents)
    return render_template(
        'documents.html',
        documents=documents,
        total_facts=total_facts
    )


# ─── Routes: Actions ─────────────────────────────────────────────────────────

@app.route('/upload', methods=['POST'])
def upload_pdf():
    """Upload and process a farming PDF."""
    file = request.files.get('pdf_file') or request.files.get('file')
    if not file or not file.filename or file.filename.strip() == '':
        flash('No file selected. Please choose a PDF file to upload.', 'error')
        return redirect(url_for('index'))

    if not allowed_file(file.filename):
        flash('Only PDF files are allowed.', 'error')
        return redirect(url_for('index'))

    # Save the file
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Handle duplicate filenames
    counter = 1
    base, ext = os.path.splitext(filename)
    while os.path.exists(file_path):
        filename = f"{base}_{counter}{ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        counter += 1

    file.save(file_path)

    try:
        # Process the PDF
        with PDFProcessor(file_path) as processor:
            doc_info = processor.get_document_info()
            pages = processor.extract_all_pages()

        # Insert document into database
        doc_result = insert_document(
            filename=doc_info['filename'],
            file_hash=doc_info['file_hash'],
            page_count=doc_info['page_count'],
            file_path=file_path,
            file_size=doc_info['file_size']
        )

        if doc_result['is_duplicate']:
            os.remove(file_path)  # Remove duplicate file
            flash(
                f'This document has already been uploaded (v{doc_result["version"]}). '
                f'Duplicate detected via SHA-256 hash.',
                'warning'
            )
            return redirect(url_for('document_detail',
                                    document_id=doc_result['id']))

        document_id = doc_result['id']

        # Store page texts for source viewing
        for page in pages:
            insert_page_text(document_id, page['page_number'], page['text'])

        # Extract facts
        facts = extract_facts_from_document(pages)
        extraction_date = get_timestamp()

        # Store extracted facts
        for fact in facts:
            insert_fact(
                document_id=document_id,
                crop_name=fact.get('crop_name'),
                category=fact['category'],
                fact_text=fact['fact_text'],
                value=fact.get('value'),
                unit=fact.get('unit'),
                season=fact.get('season'),
                region=fact.get('region'),
                page_number=fact['page_number'],
                original_text=fact['original_text'],
                extraction_date=extraction_date
            )

        # Get summary for flash message
        summary = get_extraction_summary(facts)
        flash(
            f'✅ Successfully extracted {summary["total_facts"]} facts from '
            f'{doc_info["page_count"]} pages! '
            f'Categories: {", ".join(f"{k} ({v})" for k, v in summary["by_category"].items())}',
            'success'
        )
        return redirect(url_for('document_detail', document_id=document_id))

    except Exception as e:
        # Clean up on error
        if os.path.exists(file_path):
            os.remove(file_path)
        flash(f'Error processing PDF: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/document/<int:document_id>/delete', methods=['POST'])
def delete_doc(document_id):
    """Delete a document and all its facts."""
    document = get_document_by_id(document_id)
    if not document:
        flash('Document not found.', 'error')
        return redirect(url_for('index'))

    # Delete file from disk
    if document.get('file_path') and os.path.exists(document['file_path']):
        os.remove(document['file_path'])

    # Delete from database
    delete_document(document_id)
    flash(f'Document "{document["filename"]}" and all its facts deleted.', 'success')
    return redirect(url_for('index'))


# ─── Routes: API ──────────────────────────────────────────────────────────────

@app.route('/api/autocomplete')
def api_autocomplete():
    """Autocomplete suggestions for search queries (single-word prefix or multi-word)."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'query': query, 'suggestions': []})

    suggestions = get_search_autocomplete(query, limit=8)
    return jsonify({'query': query, 'suggestions': suggestions})


@app.route('/api/search')
def api_search():
    """JSON API for searching facts."""
    query = request.args.get('q', '').strip() or None
    crop = request.args.get('crop', '').strip() or None
    category = request.args.get('category', '').strip() or None
    season = request.args.get('season', '').strip() or None
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    results = search_facts(query, crop, category, season, page=page, per_page=per_page)
    return jsonify(results)


@app.route('/api/stats')
def api_stats():
    """JSON API for dashboard statistics."""
    return jsonify(get_stats())


@app.route('/api/documents')
def api_documents():
    """JSON API for listing documents."""
    return jsonify(get_all_documents())


@app.route('/api/export')
def api_export():
    """Export facts as CSV or JSON with optional filters."""
    fmt = request.args.get('format', 'csv').lower()
    query = request.args.get('q', '').strip() or None
    crop = request.args.get('crop', '').strip() or None
    category = request.args.get('category', '').strip() or None
    season = request.args.get('season', '').strip() or None

    # Get all matching facts (no pagination for export)
    results = search_facts(query, crop, category, season, page=1, per_page=10000)
    facts = results['facts']

    if fmt == 'json':
        response = Response(
            json.dumps(facts, indent=2, ensure_ascii=False),
            mimetype='application/json',
            headers={'Content-Disposition': 'attachment; filename=krishi_khoj_export.json'}
        )
        return response

    # CSV export
    output = io.StringIO()
    if facts:
        fieldnames = [
            'id', 'crop_name', 'category', 'fact_text', 'value', 'unit',
            'season', 'region', 'page_number', 'original_text',
            'filename', 'file_hash', 'version', 'extraction_date'
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for fact in facts:
            writer.writerow(fact)

    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=krishi_khoj_export.csv'}
    )
    return response


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("\n🌾 Krishi Khoj — Turn Farm PDFs into Searchable Data")
    print("=" * 55)
    print(f"📂 Upload folder: {UPLOAD_FOLDER}")
    print(f"🗃️  Database: {DATABASE_PATH}")
    print(f"🌐 Server: http://127.0.0.1:5000")
    print("=" * 55)
    print()
    app.run(debug=DEBUG, host='127.0.0.1', port=5000)
