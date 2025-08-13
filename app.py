import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
from flask_migrate import Migrate
from werkzeug.security import check_password_hash
from datetime import datetime
from models import db, Admin, Client, Account
from tasks import check_and_notify, generate_daily_csv, generate_weekly_csv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()
def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///data/subscriptions.db')
    app.config['TWILIO_ACCOUNT_SID'] = os.getenv('TWILIO_ACCOUNT_SID')
    app.config['TWILIO_AUTH_TOKEN'] = os.getenv('TWILIO_AUTH_TOKEN')
    app.config['TWILIO_WHATSAPP_FROM'] = os.getenv('TWILIO_WHATSAPP_FROM')
    app.config['SETUP_TOKEN'] = os.getenv('SETUP_TOKEN')
    db.init_app(app)
    Migrate(app, db)
    # Ensure DB tables and data folder exist on boot
    with app.app_context():
        db.create_all()
    os.makedirs(os.path.join(app.root_path, 'data'), exist_ok=True)

    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(app)

    class AdminUser(UserMixin):
        pass

    @login_manager.user_loader
    def load_user(user_id):
        admin = Admin.query.get(int(user_id))
        if not admin:
            return None
        user = AdminUser()
        user.id = admin.id
        return user

    # ---------- One-time setup route (create admin on Render) ----------
    @app.route('/setup/create-admin')
    def setup_create_admin():
        # Only allowed if SETUP_TOKEN is set and matches query token
        token_env = app.config.get('SETUP_TOKEN')
        token = request.args.get('token', None)
        if not token_env or not token or token != token_env:
            return jsonify({"ok": False, "error": "Unauthorized"}), 401

        # Only create if no admin exists
        if Admin.query.first():
            return jsonify({"ok": False, "error": "Admin already exists"}), 400

        username = request.args.get('username', 'admin')
        password = request.args.get('password', None)
        if not password:
            return jsonify({"ok": False, "error": "Password required"}), 400

        from werkzeug.security import generate_password_hash
        admin = Admin(username=username, password_hash=generate_password_hash(password))
        db.session.add(admin)
        db.session.commit()
        return jsonify({"ok": True, "message": "Admin created", "username": username})

    # ---------- Auth routes ----------
    @app.route('/login', methods=['GET','POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            admin = Admin.query.filter_by(username=username).first()
            if admin and check_password_hash(admin.password_hash, password):
                user = AdminUser()
                user.id = admin.id
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Login echwe')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    # ---------- Views ----------
    @app.route('/')
    @login_required
    def dashboard():
        accounts = Account.query.all()
        clients = Client.query.all()
        return render_template('dashboard.html', accounts=accounts, clients=clients)

    @app.route('/clients')
    @login_required
    def clients_view():
        clients = Client.query.order_by(Client.expiration_date).all()
        return render_template('clients.html', clients=clients)

    @app.route('/clients/add', methods=['POST'])
    @login_required
    def add_client():
        name = request.form['name']
        phone = request.form['phone']
        service = request.form['service']
        exp = datetime.strptime(request.form['expiration_date'], '%Y-%m-%d').date()
        c = Client(name=name, phone=phone, service=service, expiration_date=exp)
        db.session.add(c)
        db.session.commit()
        flash('Kliyan ajoute.')
        return redirect(url_for('clients_view'))

    @app.route('/accounts')
    @login_required
    def accounts_view():
        accounts = Account.query.all()
        return render_template('accounts.html', accounts=accounts)

    @app.route('/accounts/add', methods=['POST'])
    @login_required
    def add_account():
        srv = request.form['service']
        a_type = request.form.get('account_type')
        status = request.form.get('status','available')
        exp = None
        if request.form.get('expiration_date'):
            exp = datetime.strptime(request.form['expiration_date'],'%Y-%m-%d').date()
        acc = Account(service=srv, account_type=a_type, status=status, expiration_date=exp)
        db.session.add(acc)
        db.session.commit()
        flash('Kont ajoute.')
        return redirect(url_for('accounts_view'))

    @app.route('/import', methods=['GET','POST'])
    @login_required
    def import_csv():
        if request.method == 'POST':
            f = request.files['file']
            import csv, io
            stream = io.StringIO(f.stream.read().decode('utf-8'))
            reader = csv.DictReader(stream)
            count = 0
            for row in reader:
                try:
                    exp = datetime.strptime(row['expiration_date'],'%Y-%m-%d').date()
                    c = Client(name=row['name'], phone=row['phone'], service=row['service'], expiration_date=exp)
                    db.session.add(c)
                    count += 1
                except Exception as e:
                    app.logger.error(f"Import error: {e}")
            db.session.commit()
            flash(f'Import fini: {count} kliyan ajoute.')
            return redirect(url_for('clients_view'))
        return render_template('import.html')

    @app.route('/reports')
    @login_required
    def reports():
        return render_template('reports.html')

    @app.route('/reports/daily')
    @login_required
    def download_daily():
        path = generate_daily_csv()
        return send_file(path, as_attachment=True)

    @app.route('/reports/weekly')
    @login_required
    def download_weekly():
        path = generate_weekly_csv()
        return send_file(path, as_attachment=True)

    # ---------- Scheduler ----------
    @app.before_first_request
    def init_scheduler():
        sched = BackgroundScheduler(timezone=os.getenv('TIMEZONE','America/New_York'))
        sched.add_job(lambda: check_and_notify([3,1,0]), trigger=CronTrigger(hour=9, minute=0))
        sched.add_job(lambda: generate_daily_csv(), trigger=CronTrigger(hour=20, minute=0))
        sched.start()

    return app

if __name__ == '__main__':
    app = create_app()
    # For local dev; Render uses gunicorn via Procfile
    app.run(host='0.0.0.0', port=5000, debug=True)
