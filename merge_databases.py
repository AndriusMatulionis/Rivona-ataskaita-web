import os
import shutil
from app import app, db, User, RideResult, Store

# Kelias į pagrindinę duomenų bazę
main_db_path = 'duomenu_baze.db'

# Kelias į virtualios aplinkos duomenų bazę
venv_db_path = 'instance/duomenu_baze.db'

# Sukuriame atsarginę kopiją abiejų duomenų bazių
shutil.copy2(main_db_path, 'main_db_backup.db')
shutil.copy2(venv_db_path, 'venv_db_backup.db')

# Pašaliname seną virtualios aplinkos duomenų bazę
os.remove(venv_db_path)

# Kopijuojame pagrindinę duomenų bazę į virtualios aplinkos vietą
shutil.copy2(main_db_path, venv_db_path)

# Atnaujiname duomenų bazę
with app.app_context():
    db.create_all()

    # Perkopijuojame vartotojus iš virtualios aplinkos duomenų bazės
    venv_users = User.query.all()
    for user in venv_users:
        existing_user = User.query.filter_by(username=user.username).first()
        if not existing_user:
            db.session.add(user)

    db.session.commit()

    print("Duomenų bazės sujungtos ir atnaujintos.")
    
    # Atspausdiname visus vartotojus
    users = User.query.all()
    print("Vartotojai duomenų bazėje:")
    for user in users:
        print(f"- {user.username} (Admin: {user.is_admin})")