from app import app, db, User

with app.app_context():
    admin = User.query.filter_by(username='Andrius1989').first()
    if admin:
        admin.set_password('xenpub-figBeq-gefcu0')
        db.session.commit()
        print(f"Administratoriaus slaptažodis atnaujintas")
        print(f"Naujas slaptažodžio hash: {admin.password_hash[:20]}...")
    else:
        print("Administratorius nerastas")