from app import app
from models import db, User, RideResult, Store

with app.app_context():
    db.create_all()
    print("Duomenų bazė sukurta sėkmingai!")

    # Patikrinkime, ar visos lentelės buvo sukurtos
    tables = ['user', 'ride_result', 'store']
    for table in tables:
        if table in db.engine.table_names():
            print(f"{table.capitalize()} lentelė sėkmingai sukurta!")
        else:
            print(f"{table.capitalize()} lentelės nėra. Kažkas nepavyko.")