from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, date
import os
from dotenv import load_dotenv

# Įkeliame aplinkos kintamuosius iš .env failo
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///duomenu_baze.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# El. pašto konfigūracija
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

# Inicializuojame plėtinius
db = SQLAlchemy(app)
mail = Mail(app)

# Vartotojų klasė
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_token(self, expires_sec=1800):
        s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

# RideResult klasė
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

# Sukuriame duomenų bazės lenteles
with app.app_context():
    db.create_all()

# Pagrindinis puslapis
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

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

            eur_uz_reisa = (
                km_kiekis * 0.1 +
                tasku_kiekis * 1.7 +
                pakrautos_paletes * 0.64 +
                tara * 0.5 +
                atgalines_paletes * 0.64
            )

            menesis = data.strftime('%Y-%m')
            naujas_irasas = RideResult(
                data=data,
                auto_nr=auto_nr,
                tasku_kiekis=tasku_kiekis,
                km_kiekis=km_kiekis,
                pakrautos_paletes=pakrautos_paletes,
                tara=tara,
                atgalines_paletes=atgalines_paletes,
                eur_uz_reisa=eur_uz_reisa,
                menesis=menesis
            )

            db.session.add(naujas_irasas)
            db.session.commit()
            flash('Įrašas sėkmingai pridėtas!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Klaida pridedant įrašą: {str(e)}', 'error')
            return redirect(url_for('index'))

    bendra_suma = {
        'tasku_kiekis': sum(irasas.tasku_kiekis for irasas in visi_irasai),
        'km_kiekis': sum(irasas.km_kiekis for irasas in visi_irasai),
        'pakrautos_paletes': sum(irasas.pakrautos_paletes for irasas in visi_irasai),
        'tara': sum(irasas.tara for irasas in visi_irasai),
        'atgalines_paletes': sum(irasas.atgalines_paletes for irasas in visi_irasai),
        'eur_uz_reisa': sum(irasas.eur_uz_reisa for irasas in visi_irasai)
    }

    return render_template('index.html', visi_irasai=visi_irasai, bendra_suma=bendra_suma, selected_month=selected_month)

# Registracija
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Vartotojas su tokiu vardu jau egzistuoja.', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Vartotojas su tokiu el. paštu jau egzistuoja.', 'error')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registracija sėkminga! Galite prisijungti.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Prisijungimas
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
        flash('Neteisingas prisijungimo vardas arba slaptažodis.', 'error')

    return render_template('login.html')

# Atsijungimas
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Sėkmingai atsijungėte!', 'success')
    return redirect(url_for('login'))

# Slaptažodžio atstatymo užklausa
@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            send_reset_email(user)
        flash('Jei toks el. paštas egzistuoja, slaptažodžio atstatymo instrukcijos buvo išsiųstos.')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html')

# Slaptažodžio keitimas
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash('Netinkama arba pasibaigusi nuoroda', 'danger')
        return redirect(url_for('reset_password_request'))

    if request.method == 'POST':
        password = request.form['password']
        user.set_password(password)
        db.session.commit()
        flash('Jūsų slaptažodis buvo atnaujintas! Galite prisijungti.')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

# Funkcija slaptažodžio atstatymo el. laiško siuntimui
def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Slaptažodžio atstatymas',
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[user.email])
    msg.body = f'''Norėdami atstatyti slaptažodį, paspauskite šią nuorodą:
{url_for('reset_password', token=token, _external=True)}

Jei to neprašėte, tiesiog ignoruokite šį el. laišką.
'''
    mail.send(msg)

# Redagavimas
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    irasas = RideResult.query.get_or_404(id)
    if request.method == 'POST':
        try:
            irasas.data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()
            irasas.auto_nr = request.form['auto_nr']
            irasas.tasku_kiekis = float(request.form['tasku_kiekis'])
            irasas.km_kiekis = float(request.form['km_kiekis'])
            irasas.pakrautos_paletes = float(request.form['pakrautos_paletes'])
            irasas.tara = float(request.form['tara'])
            irasas.atgalines_paletes = float(request.form['atgalines_paletes'])

            irasas.eur_uz_reisa = (
                irasas.km_kiekis * 0.1 +
                irasas.tasku_kiekis * 1.7 +
                irasas.pakrautos_paletes * 0.64 +
                irasas.tara * 0.5 +
                irasas.atgalines_paletes * 0.64
            )

            irasas.menesis = irasas.data.strftime('%Y-%m')
            db.session.commit()
            flash('Įrašas sėkmingai atnaujintas!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Klaida atnaujinant įrašą: {str(e)}', 'error')
            return redirect(url_for('edit', id=id))
    
    return render_template('edit.html', irasas=irasas)

# Įrašo šalinimas
@app.route('/delete/<int:id>')
def delete(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    irasas = RideResult.query.get_or_404(id)
    try:
        db.session.delete(irasas)
        db.session.commit()
        flash('Įrašas sėkmingai ištrintas!', 'success')
    except Exception as e:
        flash(f'Klaida trinant įrašą: {str(e)}', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)