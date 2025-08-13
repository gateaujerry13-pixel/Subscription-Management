from twilio.rest import Client
from datetime import date, timedelta
import csv, os
from models import Client as ClientModel
from flask import current_app

def get_twilio_client():
    sid = current_app.config.get('TWILIO_ACCOUNT_SID')
    token = current_app.config.get('TWILIO_AUTH_TOKEN')
    if not sid or not token:
        return None
    return Client(sid, token)

def send_whatsapp(to_number, message):
    tw = get_twilio_client()
    from_wh = current_app.config.get('TWILIO_WHATSAPP_FROM')
    if not tw or not from_wh:
        current_app.logger.warning("Twilio pa konfigire, pa voye mesaj la.")
        return None
    msg = tw.messages.create(body=message, from_=from_wh, to=f"whatsapp:{to_number}")
    return msg.sid

def format_client_message(name, service, exp_date):
    return f"Bonjou {name}! 🎬\nAbònman ou pou *{service}* ap ekspire {exp_date.strftime('%d/%m/%Y')}. Tanpri renouvle. Mèsi!"

def check_and_notify(days_before_list=[3,1,0]):
    today = date.today()
    for days_before in days_before_list:
        target = today + timedelta(days=days_before)
        clients = ClientModel.query.filter_by(active=True).filter(ClientModel.expiration_date == target).all()
        for c in clients:
            try:
                msg = format_client_message(c.name, c.service, c.expiration_date)
                send_whatsapp(c.phone, msg)
            except Exception as e:
                current_app.logger.error(f"Erè voye WhatsApp pou {c.phone}: {e}")

def generate_daily_csv():
    today = date.today()
    rows = ClientModel.query.filter(ClientModel.active==True).all()
    out_dir = os.path.join(current_app.root_path, 'data')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'daily_report_{today.isoformat()}.csv')
    with open(out_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['id','name','phone','service','expiration_date','active'])
        for r in rows:
            writer.writerow([r.id, r.name, r.phone, r.service, r.expiration_date.isoformat(), r.active])
    return out_path

def generate_weekly_csv():
    today = date.today()
    out_dir = os.path.join(current_app.root_path, 'data')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'weekly_report_{today.isoformat()}.csv')
    rows = ClientModel.query.filter(ClientModel.active==True).all()
    with open(out_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['id','name','phone','service','expiration_date','active'])
        for r in rows:
            writer.writerow([r.id, r.name, r.phone, r.service, r.expiration_date.isoformat(), r.active])
    return out_path
