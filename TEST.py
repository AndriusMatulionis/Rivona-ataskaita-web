from database import db, Base, User, RideResult, Store
from app import app
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    if 'store' in inspector.get_table_names():
        print("Store lentelė sėkmingai sukurta!")
    else:
        print("Store lentelės nėra.")