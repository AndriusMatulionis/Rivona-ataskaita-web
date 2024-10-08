import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from functools import wraps
from flask_mail import Mail, Message
from dotenv import load_dotenv
import json
from itsdangerous import URLSafeTimedSerializer
from flask_migrate import Migrate

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'xopwim-2xugpe-vEgsaz'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///duomenu_baze.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

db = SQLAlchemy(app)
mail = Mail(app)
migrate = Migrate(app, db)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class RideResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    auto_nr = db.Column(db.String(20), nullable=False)
    tasku_kiekis = db.Column(db.Float, nullable=False)
    km_kiekis = db.Column(db.Float, nullable=False)
    pakrautos_paletes = db.Column(db.Float, nullable=False)
    tara = db.Column(db.Float, nullable=False)
    atgalines_paletes = db.Column(db.Float, nullable=False)
    eur_uz_reisa = db.Column(db.Float, nullable=False)
    menesis = db.Column(db.String(7), nullable=False)
    savaitgalis = db.Column(db.Boolean, default=False)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Prašome prisijungti.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    selected_month = request.args.get('month', date.today().strftime('%Y-%m'))
    visi_irasai = RideResult.query.filter(RideResult.menesis == selected_month).all()

    if request.method == 'POST':
        try:
            data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()
            auto_nr = request.form['auto_nr']
            tasku_kiekis = float(request.form['tasku_kiekis'])
            km_kiekis = float(request.form['km_kiekis'])
            pakrautos_paletes = float(request.form['pakrautos_paletes'])
            tara = float(request.form['tara'])
            atgalines_paletes = float(request.form['atgalines_paletes'])
            savaitgalis = request.form.get('savaitgalis') == 'true'

            # Bazinis skaičiavimas
            eur_uz_reisa = (
                km_kiekis * 0.1 +
                tasku_kiekis * 1.7 +
                pakrautos_paletes * 0.64 +
                tara * 0.5 +
                atgalines_paletes * 0.64
            )

            # Jei savaitgalis, pridedame 20% prie visų, išskyrus tara
            if savaitgalis:
                eur_uz_reisa_be_taros = eur_uz_reisa - (tara * 0.5)
                eur_uz_reisa = eur_uz_reisa_be_taros * 1.2 + (tara * 0.5)

            menesis = data.strftime('%Y-%m')
            naujas_irasas = RideResult(
                data=data, auto_nr=auto_nr, tasku_kiekis=tasku_kiekis,
                km_kiekis=km_kiekis, pakrautos_paletes=pakrautos_paletes,
                tara=tara, atgalines_paletes=atgalines_paletes,
                eur_uz_reisa=eur_uz_reisa, menesis=menesis, savaitgalis=savaitgalis
            )

            db.session.add(naujas_irasas)
            db.session.commit()
            flash('Įrašas sėkmingai pridėtas!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Klaida pridedant įrašą: {str(e)}', 'danger')
        return redirect(url_for('index'))

    bendra_suma = {
        'tasku_kiekis': sum(irasas.tasku_kiekis for irasas in visi_irasai),
        'km_kiekis': sum(irasas.km_kiekis for irasas in visi_irasai),
        'pakrautos_paletes': sum(irasas.pakrautos_paletes for irasas in visi_irasai),
        'tara': sum(irasas.tara for irasas in visi_irasai),
        'atgalines_paletes': sum(irasas.atgalines_paletes for irasas in visi_irasai),
        'eur_uz_reisa': sum(irasas.eur_uz_reisa for irasas in visi_irasai)
    }

    visi_irasai_json = json.dumps([{
        'id': irasas.id,
        'data': irasas.data.strftime('%Y-%m-%d'),
        'auto_nr': irasas.auto_nr,
        'tasku_kiekis': irasas.tasku_kiekis,
        'km_kiekis': irasas.km_kiekis,
        'pakrautos_paletes': irasas.pakrautos_paletes,
        'tara': irasas.tara,
        'atgalines_paletes': irasas.atgalines_paletes,
        'eur_uz_reisa': irasas.eur_uz_reisa,
        'savaitgalis': irasas.savaitgalis
    } for irasas in visi_irasai])

    return render_template('index.html', 
                           visi_irasai=visi_irasai_json, 
                           bendra_suma=json.dumps(bendra_suma), 
                           selected_month=selected_month)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Vartotojo vardas jau užimtas.', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('El. paštas jau užregistruotas.', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registracija sėkminga! Galite prisijungti.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Sėkmingai prisijungėte!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Neteisingas vartotojo vardas arba slaptažodis.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
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
    msg = Message('Slaptažodžio Atstatymas',
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[user.email])
    msg.body = f'''Norėdami atstatyti slaptažodį, spauskite šią nuorodą:
{url_for('reset_password', token=token, _external=True)}

Jei neprašėte atstatyti slaptažodžio, ignoruokite šį laišką.
'''
    mail.send(msg)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    irasas = RideResult.query.get_or_404(id)
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

            # Perskaičiuojame eur_uz_reisa
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

            db.session.commit()
            flash('Įrašas sėkmingai atnaujintas!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Klaida atnaujinant įrašą: {str(e)}', 'danger')
    return render_template('edit.html', irasas=irasas)

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    irasas = RideResult.query.get_or_404(id)
    try:
        db.session.delete(irasas)
        db.session.commit()
        flash('Įrašas sėkmingai ištrintas!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Klaida trinant įrašą: {str(e)}', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)