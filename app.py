import os
import secrets
from datetime import datetime
from functools import wraps

import qrcode
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Event, Registration


# Load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-me')

# SQLite database used by this project
db_path = os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', '').strip().lower()

print(f'--- DATABASE READY: {db_path}')


db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(f):
    """Allow only the configured organizer/admin account."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def save_qr_image(data, filename):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    qr_dir = os.path.join(basedir, 'static', 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)
    full_path = os.path.join(qr_dir, filename)
    img.save(full_path)
    return f'static/qrcodes/{filename}'


def create_secure_token():
    """Create a cryptographically random, hard-to-guess registration token."""
    return secrets.token_urlsafe(32)


def migrate_existing_sqlite():
    """Safely add new columns/indexes to an existing SQLite database."""
    if not os.path.exists(db_path):
        return

    connection = db.engine.raw_connection()
    try:
        cursor = connection.cursor()
        cursor.execute('PRAGMA table_info(users)')
        user_columns = {row[1] for row in cursor.fetchall()}
        if 'is_admin' not in user_columns:
            cursor.execute('ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0')

        cursor.execute('PRAGMA table_info(registrations)')
        registration_columns = {row[1] for row in cursor.fetchall()}
        if 'qr_token' not in registration_columns:
            cursor.execute('ALTER TABLE registrations ADD COLUMN qr_token VARCHAR(100)')

        # Unique registration per user/event. Existing data in this project has no duplicates.
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS uq_registration_user_event ON registrations(user_id, event_id)')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_registrations_qr_token ON registrations(qr_token)')

        # Configure the admin account from .env.
        if ADMIN_EMAIL:
            cursor.execute('UPDATE users SET is_admin = 0')
            cursor.execute('UPDATE users SET is_admin = 1 WHERE lower(email) = ?', (ADMIN_EMAIL,))

        connection.commit()
    finally:
        connection.close()


def migrate_registration_qrs():
    """Give existing registrations secure tokens and regenerate their QR codes."""
    registrations = Registration.query.all()
    changed = False

    for reg in registrations:
        if not reg.qr_token:
            reg.qr_token = create_secure_token()
            changed = True

        # Regenerate old QR codes so old, editable ID-based QR data is no longer used.
        qr_filename = f'qr_{reg.id}.png'
        qr_path = os.path.join(basedir, 'static', 'qrcodes', qr_filename)
        qr_data = f'EVENTHUB:{reg.qr_token}'
        save_qr_image(qr_data, qr_filename)
        if reg.qr_code_path != f'static/qrcodes/{qr_filename}':
            reg.qr_code_path = f'static/qrcodes/{qr_filename}'
            changed = True

    if changed:
        db.session.commit()


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not name or not email or not password:
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('signup'))

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email already registered.', 'error')
            return redirect(url_for('signup'))

        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            is_admin=(email == ADMIN_EMAIL)
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('dashboard'))

    return render_template('auth.html', mode='signup')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user:
            valid_password = False
            try:
                valid_password = check_password_hash(user.password, password)
            except (ValueError, TypeError):
                valid_password = False

            # Backward compatibility for existing demo accounts that were stored
            # in plain text by the old version. Upgrade the password after login.
            if not valid_password and user.password == password:
                valid_password = True
                user.password = generate_password_hash(password)

            if valid_password:
                # Keep admin status in sync with the configured admin email.
                user.is_admin = (user.email.lower() == ADMIN_EMAIL)
                db.session.commit()
                login_user(user)
                return redirect(url_for('dashboard'))

        flash('Invalid email or password.', 'error')

    return render_template('auth.html', mode='login')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    events = Event.query.order_by(Event.date.asc(), Event.time.asc()).all()
    return render_template('dashboard.html', events=events)


@app.route('/event/<int:event_id>')
@login_required
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    registered = Registration.query.filter_by(
        user_id=current_user.id,
        event_id=event_id
    ).first()
    return render_template('event_detail.html', event=event, registered=registered)


@app.route('/register/<int:event_id>', methods=['POST'])
@login_required
def register_event(event_id):
    event = Event.query.get_or_404(event_id)
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()

    if not name or not email or not phone:
        flash('Please fill in all registration fields.', 'error')
        return redirect(url_for('event_detail', event_id=event_id))

    existing = Registration.query.filter_by(
        user_id=current_user.id,
        event_id=event_id
    ).first()
    if existing:
        flash('You are already registered for this event.', 'info')
        return redirect(url_for('event_detail', event_id=event_id))

    new_reg = Registration(
        user_id=current_user.id,
        event_id=event_id,
        name=name,
        email=email,
        phone=phone,
        qr_token=create_secure_token(),
        status='confirmed'
    )
    db.session.add(new_reg)
    db.session.commit()

    qr_filename = f'qr_{new_reg.id}.png'
    qr_data = f'EVENTHUB:{new_reg.qr_token}'
    new_reg.qr_code_path = save_qr_image(qr_data, qr_filename)
    db.session.commit()

    flash('Successfully registered! Your secure event pass is ready.', 'success')
    return redirect(url_for('event_detail', event_id=event_id))


@app.route('/scan')
@admin_required
def scan():
    return render_template('scanner.html')


@app.route('/my-registrations')
@login_required
def my_registrations():
    registrations = Registration.query.filter_by(user_id=current_user.id).order_by(Registration.registered_at.desc()).all()
    return render_template('my_registrations.html', registrations=registrations)


@app.route('/admin')
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.created_at.desc()).all()
    registrations = Registration.query.order_by(Registration.registered_at.desc()).all()
    events = Event.query.order_by(Event.date.asc(), Event.time.asc()).all()
    total_attended = Registration.query.filter_by(status='attended').count()
    total_confirmed = Registration.query.filter_by(status='confirmed').count()
    return render_template(
        'admin.html',
        users=users,
        registrations=registrations,
        events=events,
        total_attended=total_attended,
        total_confirmed=total_confirmed
    )


@app.route('/api/scan-result', methods=['POST'])
@admin_required
def scan_result():
    data = request.get_json(silent=True) or {}
    decoded_text = data.get('decodedText', '').strip()

    if not decoded_text.startswith('EVENTHUB:'):
        return jsonify({
            'status': 'error',
            'message': 'Invalid EventHub QR code.'
        }), 400

    token = decoded_text[len('EVENTHUB:'):].strip()
    if not token:
        return jsonify({
            'status': 'error',
            'message': 'QR code does not contain a valid registration token.'
        }), 400

    reg = Registration.query.filter_by(qr_token=token).first()
    if not reg:
        return jsonify({
            'status': 'error',
            'message': 'Registration not found. The QR code may be invalid or tampered with.'
        }), 404

    if reg.status == 'attended':
        return jsonify({
            'status': 'error',
            'message': f'Attendance already marked for {reg.name}.'
        }), 409

    reg.status = 'attended'
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': f'Verified! Attendance marked for {reg.name}.',
        'event': reg.event.name,
        'time': datetime.now().strftime('%I:%M %p')
    })


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        migrate_existing_sqlite()
        migrate_registration_qrs()

    app.run(debug=True)
