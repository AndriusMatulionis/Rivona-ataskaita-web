from app import app, db, User

with app.app_context():
    try:
        users = User.query.all()
        print(f"Sėkmingai prisijungta prie duomenų bazės. Rasta vartotojų: {len(users)}")
        for user in users:
            print(f"- {user.username} (Admin: {user.is_admin})")
    except Exception as e:
        print(f"Klaida prisijungiant prie duomenų bazės: {str(e)}")