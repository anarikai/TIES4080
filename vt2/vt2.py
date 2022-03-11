#!/wwwhome/home/anarikai/public_html/cgi-bin/ties4080//venv/bin/python
# edellisellä shebang-rivillä ei ole merkitystä nyt muuten kuin komentorivillä 
# suoritettaessa eikä oikeastaan silloinkaan, koska Flask-sovellusta ei voi kunnolla
# suorittaa komentoriviltä halava/jalava-koneissa
# -*- coding: utf-8 -*-
from flask import Flask, session, redirect, url_for, escape, request, Response, render_template
from markupsafe import Markup
from polyglot import PolyglotForm
from flask_wtf import FlaskForm
from wtforms import StringField, validators, IntegerField
from contextlib import closing
import os
import json

app = Flask(__name__)

# set the secret key.  keep this really secret:
app.secret_key = '"\xf9$T\x88\xefT8[\xf1\xc4Y-r@\t\xec!5d\xf9\xcc\xa2\xaa'

# @app.route määrää mille osoitteille tämä funktio suoritetaan
@app.route('/', methods=['POST','GET']) 
def lomake():
    class Pelilaskuri(PolyglotForm):
        koko         = IntegerField('Laudan koko ', [validators.NumberRange(min=8, max=16, message="Syöttämäsi arvo ei kelpaa")], default=8)
        pelaaja1     = StringField('Pelaaja 1 ', validators=[validators.InputRequired(),validators.Length(min=2, message="Syöttämäsi arvo ei kelpaa")], default='Pelaaja1')
        pelaaja2        = StringField('Pelaaja 2 ', [validators.InputRequired(),validators.Length(min=2, message="Syöttämäsi arvo ei kelpaa")], default='Pelaaja2')
        laudankoko   = 8
    form = Pelilaskuri()

    if request.method == 'GET':
        lauta = {
            "koko": request.args.get("koko"),
            "pelaaja1": request.args.get("pelaaja1"),
            "pelaaja2": request.args.get("pelaaja2")
        }
        if not lauta['koko'] is None and lauta['koko'].isdigit() and not int(lauta['koko']) < 8 and not int(lauta['koko']) > 16 and not lauta['pelaaja1'] is None and len(lauta['pelaaja1']) > 2 and not lauta['pelaaja2'] is None and len(lauta['pelaaja2']) > 2 :
            form.koko.data = int(lauta['koko'])
            form.laudankoko = int(lauta['koko'])
            form.pelaaja1.data = lauta['pelaaja1']
            form.pelaaja2.data = lauta['pelaaja2']
        else:
            aiemmat_arvot = lue_json()
            if 'pelaaja1' in aiemmat_arvot['pelilauta'] and 'pelaaja2' in aiemmat_arvot['pelilauta'] and 'koko' in aiemmat_arvot['pelilauta']:
                form.pelaaja1.data = aiemmat_arvot['pelilauta']['pelaaja1']
                form.pelaaja2.data = aiemmat_arvot['pelilauta']['pelaaja2']
                form.koko.data = aiemmat_arvot['pelilauta']['koko']
                form.laudankoko = aiemmat_arvot['pelilauta']['koko']
    # Lähetetään lomake ja validoidaan se. 
    if request.method == 'POST':
        form.validate()
        if len(form.koko.errors) == 0 and len(form.pelaaja1.errors) == 0 and len(form.pelaaja2.errors) == 0:
            form.laudankoko = form.koko.data
            form.nimi1 = form.pelaaja1.data
            form.nimi2 = form.pelaaja2.data

    # Kirjataan viimeksi annetut tiedot json-tiedostoon.
    # http://users.jyu.fi/~anarikai/cgi-bin/ties4080/vt2/vt2.cgi/data.json
    data = {
        'pelilauta' : {
            'pelaaja1': form.pelaaja1.data,
            'pelaaja2': form.pelaaja2.data,
            'koko': form.koko.data
        }
    }

    luo_json(data)
    return Response (render_template('pohja.xhtml', form=form), mimetype="application/xhtml+xml")
    
# Tässä tehdään json-tiedosto, johon on kirjattu muistiin sovellukseen viimeksi syötetyt arvot
def luo_json(data):
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f)
# Luetaan json-tiedosto
@app.route('/data.json', methods=['GET']) # Tämä rivi kertoo osoitteen, josta data.json löytyy
def lue_json():
    with open('data.json') as json_file:
       return json.load(json_file)