from app import app
from database import db
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print("Esamos lentelės:")
    for table in tables:
        print(table)
    
    if 'store' in tables:
        print("\nStore lentelė sėkmingai sukurta!")
    else:
        print("\nStore lentelės nėra.")