from app import app, User

with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print(f"Tikrinamas slaptažodis administratoriui")
        print(f"Teisingas slaptažodis: {admin.check_password('naujas_admin_slaptazodis')}")
        print(f"Neteisingas slaptažodis: {admin.check_password('neteisingas_slaptazodis')}")
    else:
        print("Administratorius nerastas")