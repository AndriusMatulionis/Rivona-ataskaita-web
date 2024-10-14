from app import app
from database import db, Base, User, RideResult, Store
from sqlalchemy import inspect

def update_database():
    with app.app_context():
        Base.metadata.create_all(db.engine)
        
        print("Duomenų bazė sėkmingai atnaujinta!")
        
        # Patikrinkime, ar visos lentelės egzistuoja
        inspector = inspect(db.engine)
        tables = ['user', 'ride_result', 'store']
        for table in tables:
            if table in inspector.get_table_names():
                print(f"{table.capitalize()} lentelė egzistuoja.")
            else:
                print(f"{table.capitalize()} lentelės nėra. Ji buvo sukurta.")

if __name__ == "__main__":
    update_database()