# Subscription Manager (MVP) - Kreyòl (Render Ready)
Aplikasyon Flask pou jere abònman (Netflix, Disney+, Prime Video, Hulu, HBO Max).
- Flask + SQLAlchemy (SQLite default)
- APScheduler pou notifikasyon (Twilio WhatsApp)
- CSV import + rapò
- Login **sekirize** (password hash)
- **Route setup tanporè** pou kreye admin lè w deplwaye sou Render

## Kòmanse lokal (opsyonèl)
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # ranpli valè yo
python create_admin.py --username admin --password motdepase
python app.py
```

## Deploy sou Render
1) Mete kòd sa sou GitHub (obligatwa pou Render).
2) Sou Render → New → Web Service → chwazi repo a.
3) Build: `pip install -r requirements.txt`
   Start: `python app.py`
4) Env Vars obligatwa:
   - SECRET_KEY = yonCleSekreOu
   - TIMEZONE = America/New_York
   - (Opsyonèl pou WhatsApp) TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM
   - **SETUP_TOKEN** = yonTokenTanporePouKreyeAdmin

5) Kreye admin sou environment Render la:
   - Ale: `https://VOTRE-APP.onrender.com/setup/create-admin?token=VOTRE_SETUP_TOKEN&username=admin&password=motdepase`
   - Ou pral wè mesaj "Admin created".
   - **Imedyatman retire SETUP_TOKEN nan env** (oswa mete li vid) epi redeploy pou fè route la pa itil ankò.

## Sekirite
- Login verifye modpas ak `check_password_hash`.
- Route setup la mande `SETUP_TOKEN` **epi** li sèlman kreye admin si pa gen okenn admin deja.
- Apre w fin kreye admin nan Render, retire `SETUP_TOKEN`.
