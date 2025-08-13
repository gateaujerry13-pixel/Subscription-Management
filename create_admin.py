import argparse
from werkzeug.security import generate_password_hash
from app import create_app
from models import db, Admin

parser = argparse.ArgumentParser()
parser.add_argument('--username', required=True)
parser.add_argument('--password', required=True)
args = parser.parse_args()

app = create_app()
with app.app_context():
    if Admin.query.filter_by(username=args.username).first():
        print("Admin deja egziste.")
    else:
        admin = Admin(username=args.username, password_hash=generate_password_hash(args.password))
        db.session.add(admin)
        db.session.commit()
        print("Admin created:", args.username)
