import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_mail import Mail, Message
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import json
from itsdangerous import URLSafeTimedSerializer
from flask_migrate import Migrate
import calendar
from functools import wraps
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from store_routes import store_bp
from models import db, User, RideResult, Store, init_app
from sqlalchemy import inspect

load_dotenv()

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'xopwim-2xugpe-vEgsaz'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'duomenu_baze.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
app.config['SESSION_TYPE'] = 'filesystem'

init_app(app)
mail = Mail(app)
migrate = Migrate(app, db)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

login_manager = LoginManager(app)
login_manager.login_view = 'login'

app.register_blueprint(store_bp)

# Unique and sorted list of car numbers
CAR_NUMBERS = sorted(list(set([
    "FFH433", "FGB047", "GJM253", "GJM332", "GUN418", 
    "JEH745", "JEH746", "KTT023", "KTT029", "KUL631", 
    "KUL633", "KUL637", "KUM239", "KZL604", "LCS347", 
    "LCS352", "LCS353", "LCS360", "LCS358"
])))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Tik administratorius gali pasiekti šį puslapį.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    user_id = current_user.id
    selected_month = request.args.get('month', date.today().strftime('%Y-%m'))
    visi_irasai = RideResult.query.filter(RideResult.user_id == user_id, RideResult.menesis == selected_month).all()
    print(f"Index: Vartotojas prisijungęs: {current_user.is_authenticated}")
    
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.json
            else:
                data = request.form.to_dict()
            
            if not data:
                return jsonify({"success": False, "message": "Nėra duomenų"})
            
            print("Gauti duomenys:", data)  # Pridėta debuginimui
            
            data['data'] = datetime.strptime(data['data'], '%Y-%m-%d').date()
            data['savaitgalis'] = data.get('savaitgalis') == 'true'
            
            eur_uz_reisa = (
                float(data['km_kiekis']) * 0.1 +
                float(data['tasku_kiekis']) * 1.7 +
                float(data['pakrautos_paletes']) * 0.64 +
                float(data['tara']) * 0.5 +
                float(data['atgalines_paletes']) * 0.64
            )

            if data['savaitgalis']:
                eur_uz_reisa_be_taros = eur_uz_reisa - (float(data['tara']) * 0.5)
                eur_uz_reisa = eur_uz_reisa_be_taros * 1.2 + (float(data['tara']) * 0.5)

            menesis = data['data'].strftime('%Y-%m')
            naujas_irasas = RideResult(
                user_id=user_id, 
                data=data['data'], 
                auto_nr=data['auto_nr'], 
                tasku_kiekis=float(data['tasku_kiekis']),
                km_kiekis=float(data['km_kiekis']), 
                pakrautos_paletes=float(data['pakrautos_paletes']),
                tara=float(data['tara']), 
                atgalines_paletes=float(data['atgalines_paletes']),
                eur_uz_reisa=eur_uz_reisa, 
                menesis=menesis, 
                savaitgalis=data['savaitgalis']
            )

            db.session.add(naujas_irasas)
            db.session.commit()

            # Konvertuojame naują įrašą į žodyną
            new_record = {
                'id': naujas_irasas.id,
                'data': naujas_irasas.data.strftime('%Y-%m-%d'),
                'auto_nr': naujas_irasas.auto_nr,
                'tasku_kiekis': float(naujas_irasas.tasku_kiekis),
                'km_kiekis': float(naujas_irasas.km_kiekis),
                'pakrautos_paletes': float(naujas_irasas.pakrautos_paletes),
                'tara': float(naujas_irasas.tara),
                'atgalines_paletes': float(naujas_irasas.atgalines_paletes),
                'eur_uz_reisa': float(naujas_irasas.eur_uz_reisa),
                'savaitgalis': naujas_irasas.savaitgalis
            }

            # Atnaujinamas bendros sumos skaičiavimas
            bendra_suma = {
                'tasku_kiekis': sum(irasas.tasku_kiekis or 0 for irasas in visi_irasai) + float(data['tasku_kiekis']),
                'km_kiekis': sum(irasas.km_kiekis or 0 for irasas in visi_irasai) + float(data['km_kiekis']),
                'pakrautos_paletes': sum(irasas.pakrautos_paletes or 0 for irasas in visi_irasai) + float(data['pakrautos_paletes']),
                'tara': sum(irasas.tara or 0 for irasas in visi_irasai) + float(data['tara']),
                'atgalines_paletes': sum(irasas.atgalines_paletes or 0 for irasas in visi_irasai) + float(data['atgalines_paletes']),
                'eur_uz_reisa': sum(irasas.eur_uz_reisa or 0 for irasas in visi_irasai) + eur_uz_reisa
            }

            return jsonify({
                "success": True,
                "message": "Įrašas sėkmingai pridėtas!",
                "newRecord": new_record,
                "newTotal": bendra_suma
            })
        except Exception as e:
            db.session.rollback()
            print("Klaida:", str(e))  # Pridėta debuginimui
            return jsonify({"success": False, "message": f"Klaida pridedant įrašą: {str(e)}"})

    bendra_suma = {
        'tasku_kiekis': sum(irasas.tasku_kiekis or 0 for irasas in visi_irasai),
        'km_kiekis': sum(irasas.km_kiekis or 0 for irasas in visi_irasai),
        'pakrautos_paletes': sum(irasas.pakrautos_paletes or 0 for irasas in visi_irasai),
        'tara': sum(irasas.tara or 0 for irasas in visi_irasai),
        'atgalines_paletes': sum(irasas.atgalines_paletes or 0 for irasas in visi_irasai),
        'eur_uz_reisa': sum(irasas.eur_uz_reisa or 0 for irasas in visi_irasai)
    }

    visi_irasai_list = [{
        'id': irasas.id,
        'data': irasas.data.strftime('%Y-%m-%d'),
        'auto_nr': irasas.auto_nr,
        'tasku_kiekis': float(irasas.tasku_kiekis or 0),
        'km_kiekis': float(irasas.km_kiekis or 0),
        'pakrautos_paletes': float(irasas.pakrautos_paletes or 0),
        'tara': float(irasas.tara or 0),
        'atgalines_paletes': float(irasas.atgalines_paletes or 0),
        'eur_uz_reisa': float(irasas.eur_uz_reisa or 0),
        'savaitgalis': bool(irasas.savaitgalis)
    } for irasas in visi_irasai]

    user_info = {
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'is_admin': current_user.is_admin
    }

    current_date = date.today()
    available_months = []
    for i in range(12):
        month_date = current_date - timedelta(days=current_date.day - 1) - timedelta(days=30*i)
        month_value = month_date.strftime('%Y-%m')
        month_label = f"{calendar.month_name[month_date.month]} {month_date.year}"
        available_months.append({'value': month_value, 'label': month_label})

    return render_template('index.html', 
                           visi_irasai=json.dumps(visi_irasai_list),
                           bendra_suma=json.dumps(bendra_suma), 
                           selected_month=selected_month,
                           car_numbers=json.dumps(CAR_NUMBERS),
                           user=json.dumps(user_info),
                           available_months=json.dumps(available_months))

@app.route('/admin')
@admin_required
def admin_panel():
    users = User.query.all()
    return render_template('admin_panel.html', users=users)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Negalima ištrinti administratoriaus paskyros.', 'danger')
    else:
        try:
            RideResult.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()
            flash(f'Vartotojas {user.username} ir visi jo įrašai sėkmingai ištrinti.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Klaida trinant vartotoją: {str(e)}', 'danger')
    return redirect(url_for('admin_panel'))

@app.route('/grafikai')
@login_required
def grafikai():
    user_id = current_user.id
    visi_irasai = RideResult.query.filter_by(user_id=user_id).all()
    visi_irasai_json = json.dumps([{
        'id': irasas.id,
        'data': irasas.data.strftime('%Y-%m-%d'),
        'auto_nr': irasas.auto_nr,
        'tasku_kiekis': float(irasas.tasku_kiekis),
        'km_kiekis': float(irasas.km_kiekis),
        'pakrautos_paletes': float(irasas.pakrautos_paletes),
        'tara': float(irasas.tara),
        'atgalines_paletes': float(irasas.atgalines_paletes),
        'eur_uz_reisa': float(irasas.eur_uz_reisa),
        'savaitgalis': irasas.savaitgalis,
        'menesis': irasas.data.strftime('%Y-%m')
    } for irasas in visi_irasai])
    return render_template('grafikai.html', visi_irasai=visi_irasai_json)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Patikrinkite, ar vartotojo vardas jau egzistuoja
        if User.query.filter_by(username=username).first():
            flash('Vartotojo vardas jau užimtas.', 'danger')
            return redirect(url_for('register'))
        
        # Patikrinkite, ar el. paštas jau užregistruotas
        if User.query.filter_by(email=email).first():
            flash('El. paštas jau užregistruotas.', 'danger')
            return redirect(url_for('register'))
        
        # Sukurkite naują vartotoją
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        # Išsaugokite naują vartotoją duomenų bazėje
        db.session.add(new_user)
        db.session.commit()
        
        
        
        flash('Registracija sėkminga! Galite prisijungti.', 'success')
        return redirect(url_for('login'))
    
    # Jei tai GET užklausa, tiesiog parodykite registracijos formą
    return render_template('register.html')
    

@app.before_request
def before_request():
    print("Duomenų bazės sesija:", db.session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        print(f"Bandoma prisijungti su vartotoju: {username}")
        
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"Vartotojas rastas: {user.username}")
            print(f"Vartotojo tipas: {'Administratorius' if user.is_admin else 'Paprastas vartotojas'}")
            print(f"Slaptažodžio hash: {user.password_hash[:20]}...")
            if user.check_password(password):
                print("Slaptažodis teisingas")
                login_user(user)
                print(f"Vartotojas prisijungęs: {current_user.is_authenticated}")
                return redirect(url_for('index'))
            else:
                print("Neteisingas slaptažodis")
        else:
            print("Vartotojas nerastas")
        
        flash('Neteisingas vartotojo vardas arba slaptažodis.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sėkmingai atsijungėte!', 'success')
    return redirect(url_for('login'))

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            send_password_reset_email(user)
            flash('Patikrinkite savo el. paštą dėl instrukcijų, kaip atstatyti slaptažodį.', 'info')
        else:
            flash('Nerastas vartotojas su šiuo el. paštu.', 'warning')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        flash('Netinkama arba pasibaigusi nuoroda', 'warning')
        return redirect(url_for('reset_password_request'))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Vartotojas nerastas', 'warning')
        return redirect(url_for('reset_password_request'))
    
    if request.method == 'POST':
        password = request.form['password']
        user.set_password(password)
        db.session.commit()
        flash('Jūsų slaptažodis buvo atnaujintas!', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

def send_password_reset_email(user):
    token = s.dumps(user.email, salt='password-reset-salt')
    reset_url = url_for('reset_password', token=token, _external=True)
    subject = 'Slaptažodžio Atstatymas'
    body = f'''
    Norėdami atstatyti slaptažodį, spauskite šią nuorodą:
    {reset_url}

    Jei neprašėte atstatyti slaptažodžio, ignoruokite šį laišką.
    '''
    msg = Message(subject,
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[user.email],
                  body=body)
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Klaida siunčiant el. laišką: {str(e)}")
        raise

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    irasas = RideResult.query.get_or_404(id)
    if irasas.user_id != current_user.id:
        flash('Jūs neturite teisės redaguoti šio įrašo.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            irasas.data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()
            irasas.auto_nr = request.form['auto_nr']
            irasas.km_kiekis = float(request.form['km_kiekis'])
            irasas.tasku_kiekis = float(request.form['tasku_kiekis'])
            irasas.pakrautos_paletes = float(request.form['pakrautos_paletes'])
            irasas.atgalines_paletes = float(request.form['atgalines_paletes'])
            irasas.tara = float(request.form['tara'])
            irasas.savaitgalis = request.form.get('savaitgalis') == 'true'

            eur_uz_reisa = (
                irasas.km_kiekis * 0.1 +
                irasas.tasku_kiekis * 1.7 +
                irasas.pakrautos_paletes * 0.64 +
                irasas.tara * 0.5 +
                irasas.atgalines_paletes * 0.64
            )

            if irasas.savaitgalis:
                eur_uz_reisa_be_taros = eur_uz_reisa - (irasas.tara * 0.5)
                irasas.eur_uz_reisa = eur_uz_reisa_be_taros * 1.2 + (irasas.tara * 0.5)
            else:
                irasas.eur_uz_reisa = eur_uz_reisa

            irasas.menesis = irasas.data.strftime('%Y-%m')

            db.session.commit()
            flash('Įrašas sėkmingai atnaujintas!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Klaida atnaujinant įrašą: {str(e)}', 'danger')
    return render_template('edit.html', irasas=irasas, car_numbers=json.dumps(CAR_NUMBERS))

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    irasas = RideResult.query.get_or_404(id)
    if irasas.user_id != current_user.id:
        return jsonify({"success": False, "message": 'Jūs neturite teisės ištrinti šio įrašo.'})
    
    try:
        # Išsaugome įrašo duomenis prieš jį ištrindami
        deleted_record = {
            'tasku_kiekis': irasas.tasku_kiekis,
            'km_kiekis': irasas.km_kiekis,
            'pakrautos_paletes': irasas.pakrautos_paletes,
            'tara': irasas.tara,
            'atgalines_paletes': irasas.atgalines_paletes,
            'eur_uz_reisa': irasas.eur_uz_reisa
        }
        
        db.session.delete(irasas)
        db.session.commit()
        
        # Apskaičiuojame naują bendrą sumą
        visi_irasai = RideResult.query.filter_by(user_id=current_user.id).all()
        new_total = {
            'tasku_kiekis': sum(irasas.tasku_kiekis or 0 for irasas in visi_irasai),
            'km_kiekis': sum(irasas.km_kiekis or 0 for irasas in visi_irasai),
            'pakrautos_paletes': sum(irasas.pakrautos_paletes or 0 for irasas in visi_irasai),
            'tara': sum(irasas.tara or 0 for irasas in visi_irasai),
            'atgalines_paletes': sum(irasas.atgalines_paletes or 0 for irasas in visi_irasai),
            'eur_uz_reisa': sum(irasas.eur_uz_reisa or 0 for irasas in visi_irasai)
        }
        
        return jsonify({
            "success": True, 
            "message": 'Įrašas sėkmingai ištrintas!',
            "deletedRecord": deleted_record,
            "newTotal": new_total
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f'Klaida trinant įrašą: {str(e)}'})

@app.template_filter('date_format')
def date_format(value, format='%Y-%m-%d'):
    if isinstance(value, str):
        return datetime.strptime(value, '%Y-%m-%d').strftime(format)
    return value.strftime(format)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.route('/reset_admin', methods=['GET', 'POST'])
def reset_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = User.query.filter_by(is_admin=True).first()
        if admin:
            admin.username = username
            admin.set_password(password)
        else:
            admin = User(username=username, email='admin@example.com', is_admin=True)
            admin.set_password(password)
            db.session.add(admin)
        
        db.session.commit()
        flash('Administratoriaus paskyra atnaujinta arba sukurta!', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_admin.html')

def create_admin_if_not_exists():
    with app.app_context():
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            new_admin = User(username='admin', email='admin@example.com', is_admin=True)
            new_admin.set_password('admin123')  # Pakeiskite į saugesnį slaptažodį
            db.session.add(new_admin)
            db.session.commit()
            print("Administratoriaus paskyra sukurta!")
        else:
            print("Administratoriaus paskyra jau egzistuoja.")
            
            
with app.app_context():
    inspector = inspect(db.engine)
    print("Lentelės duomenų bazėje:", inspector.get_table_names())
    users = User.query.all()
    print("Vartotojai duomenų bazėje:", [u.username for u in users])            

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin_if_not_exists()
    app.run(debug=True)