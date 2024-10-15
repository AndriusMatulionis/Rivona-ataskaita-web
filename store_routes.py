from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Store
from sqlalchemy import or_

store_bp = Blueprint('store', __name__)

@store_bp.route('/store_catalog')
@login_required
def store_catalog():
    return render_template('store_catalog.html')

@store_bp.route('/get_store_list')
@login_required
def get_store_list():
    stores = Store.query.all()
    store_list = [f"{store.pavadinimas} - {store.adresas}" for store in stores]
    return jsonify(store_list)

@store_bp.route('/store/search')
@login_required
def store_search():
    query = request.args.get('query', '')
    stores = Store.query.filter(or_(
        Store.pavadinimas.ilike(f'%{query}%'),
        Store.adresas.ilike(f'%{query}%'),
        Store.apskritis.ilike(f'%{query}%')
    )).all()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('store_search_results.html', stores=stores, query=query)
    return render_template('store_catalog.html', stores=stores, query=query)

@store_bp.route('/store/<int:store_id>')
@login_required
def store_detail(store_id):
    store = Store.query.get_or_404(store_id)
    return render_template('store_detail.html', store=store)

@store_bp.route('/store/add', methods=['GET', 'POST'])
@login_required
def add_store():
    if not current_user.is_admin:
        flash('Tik administratoriai gali pridėti naujas parduotuves.', 'danger')
        return redirect(url_for('store.store_catalog'))
    
    if request.method == 'POST':
        new_store = Store(
            pavadinimas=request.form['pavadinimas'],
            adresas=request.form['adresas'],
            apskritis=request.form['apskritis'],
            darbo_laikas=request.form['darbo_laikas'],
            darbuotoju_darbo_laikas=request.form['darbuotoju_darbo_laikas'],
            sestadienio_darbo_laikas=request.form['sestadienio_darbo_laikas'],
            sekmadienio_darbo_laikas=request.form['sekmadienio_darbo_laikas'],
            google_maps_nuoroda=request.form['google_maps_nuoroda']
        )
        db.session.add(new_store)
        db.session.commit()
        flash('Nauja parduotuvė sėkmingai pridėta!', 'success')
        return redirect(url_for('store.store_catalog'))
    return render_template('add_store.html')

@store_bp.route('/store/edit/<int:store_id>', methods=['GET', 'POST'])
@login_required
def edit_store(store_id):
    if not current_user.is_admin:
        flash('Tik administratoriai gali redaguoti parduotuves.', 'danger')
        return redirect(url_for('store.store_catalog'))
    
    store = Store.query.get_or_404(store_id)
    if request.method == 'POST':
        store.pavadinimas = request.form['pavadinimas']
        store.adresas = request.form['adresas']
        store.apskritis = request.form['apskritis']
        store.darbo_laikas = request.form['darbo_laikas']
        store.darbuotoju_darbo_laikas = request.form['darbuotoju_darbo_laikas']
        store.sestadienio_darbo_laikas = request.form['sestadienio_darbo_laikas']
        store.sekmadienio_darbo_laikas = request.form['sekmadienio_darbo_laikas']
        store.google_maps_nuoroda = request.form['google_maps_nuoroda']
        db.session.commit()
        flash('Parduotuvės informacija atnaujinta!', 'success')
        return redirect(url_for('store.store_detail', store_id=store.id))
    return render_template('edit_store.html', store=store)

@store_bp.route('/store/delete/<int:store_id>', methods=['POST'])
@login_required
def delete_store(store_id):
    if not current_user.is_admin:
        flash('Tik administratoriai gali trinti parduotuves.', 'danger')
        return redirect(url_for('store.store_catalog'))
    
    store = Store.query.get_or_404(store_id)
    db.session.delete(store)
    db.session.commit()
    flash('Parduotuvė ištrinta!', 'success')
    return redirect(url_for('store.store_catalog'))