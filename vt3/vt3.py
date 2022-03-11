#!/usr/bin/python
# -*- coding: utf-8 -*-
from email.policy import default
from random import choices
from flask import Flask, session, redirect, url_for, escape, request, Response, render_template
from flask_wtf import FlaskForm
from wtforms import StringField, validators, PasswordField, SelectField, RadioField
import mysql.connector
import mysql.connector.pooling
from mysql.connector import errorcode
import json
import io
import hashlib
import werkzeug.exceptions
from functools import wraps

app = Flask(__name__)

app.secret_key = '"\xf9$T\x88\xefT8[\xf1\xc4Y-r@\t\xec!5d\xf9\xcc\xa2\xaa'

# Tietokantayhteyteen tarvittavat tiedot luetaan erillisestä tiedostosta
tiedosto = io.open("dbconfig.json", encoding="UTF-8")
dbconfig = json.load(tiedosto)

def auth(f):
    ''' Tämä decorator hoitaa kirjautumisen tarkistamisen ja ohjaa tarvittaessa kirjautumissivulle
    '''
    @wraps(f)
    def decorated(*args, **kwargs):
        if not 'kirjautunut' in session:
            return redirect(url_for('lomake'))
        return f(*args, **kwargs)
    return decorated

# Connection-pool
pool=mysql.connector.pooling.MySQLConnectionPool(pool_name="tietokantayhteydet",
        pool_size=2, #PythonAnywheren ilmaisen tunnuksen maksimi on kolme
        **dbconfig)

# @app.route määrää mille osoitteille tämä funktio suoritetaan
# Kirjautumissivu
@app.route('/kirjaudu', methods=['POST','GET'])
def lomake():
    sql1 = '''SELECT j.id AS jid, j.joukkuenimi, j.salasana, j.sarja, s.id AS sid, s.kilpailu, k.id AS kid, k.kisanimi FROM joukkueet j, sarjat s, kilpailut k
    WHERE j.sarja = s.id AND s.kilpailu = k.id AND j.joukkuenimi = %s
    '''
    sql2 = '''SELECT id, kisanimi FROM kilpailut
    '''
    try:
        con = pool.get_connection()
        cur2 = con.cursor(buffered=True, dictionary=True)
        cur2.execute(sql2)
        kilpailut = cur2.fetchall()

        kilpailuLista = []
        for element in kilpailut:
            kilpailuLista.append((str(element["id"]), element["kisanimi"] ))

        class kirjautumislomake(FlaskForm):
            kilpailu = SelectField('Kilpailu', choices=kilpailuLista, validators = [validators.InputRequired()])
            tunnus = StringField('Joukkueen nimi', validators=[validators.InputRequired(),validators.Length(min=2, message="Syöttämäsi arvo ei kelpaa")], default='')
            salasana = PasswordField('Salasana', validators=[validators.InputRequired(),validators.Length(min=1, message="Syöttämäsi arvo ei kelpaa")], default='')
        form = kirjautumislomake()
        # Tarkistetaan salasana ja että kyseinen joukkue löytyy valitusta kilpailusta
        if request.method == 'POST':
            kilpailu = form.kilpailu.data
            joukkueen_nimi = form.tunnus.data.strip().lower()
            cur = con.cursor(buffered=True, dictionary=True)
            cur.execute(sql1, (form.tunnus.data,))
            joukkue = cur.fetchone()
            joukkue_nimi_kannassa = joukkue['joukkuenimi'].strip().lower()

            m = hashlib.sha512()
            m.update(str(joukkue['jid']).encode("UTF-8"))
            m.update(form.salasana.data.encode("UTF-8"))
            salasana = m.hexdigest()
            if joukkue_nimi_kannassa == joukkueen_nimi and joukkue['salasana'] == salasana and int(joukkue['kid']) == int(kilpailu):
                session['kirjautunut'] = "ok"
                session['kilpailu'] = int(joukkue['kid'])
                session['joukkue'] = int(joukkue['jid'])
                return redirect(url_for('sivu'))
            if joukkue == None or salasana != joukkue['salasana']:
                return render_template('pohja.html', form=form, kilpailut=kilpailut, kilpailu=kilpailu)

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Tunnus tai salasana on väärin")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Tietokantaa ei löydy")
        else:
            print(err)
    finally:
        con.close()
    return Response (render_template('pohja.html', form=form, kilpailut=kilpailut), mimetype="text/html")

# Joukkuelistaussivu
@app.route('/kirjautunut', methods=['POST','GET'])
@auth
def sivu():
    kilpailu = session['kilpailu']
    joukkue = session['joukkue']
    kilpailu_sql = '''SELECT k.id AS kid, k.kisanimi, s.id AS sid, s.sarjanimi, s.kilpailu, j.id AS jid, j.joukkuenimi, j.sarja, j.jasenet FROM kilpailut k, sarjat s, joukkueet j 
    WHERE k.id = s.kilpailu AND s.id = j.sarja AND k.id = %s ORDER BY s.sarjanimi, j.joukkuenimi, j.jasenet
    '''
    joukkue_sql = '''SELECT id, joukkuenimi FROM joukkueet WHERE id = %s
    '''
    try:
        con = pool.get_connection()
        cur = con.cursor(buffered=True, dictionary=True)
        cur2 = con.cursor(buffered=True, dictionary=True)
        cur.execute(kilpailu_sql, (kilpailu,))
        joukkueet = cur.fetchall()
        kilpailu_nimi = joukkueet[0]['kisanimi']
        cur2.execute(joukkue_sql, (joukkue,))
        joukkue = cur2.fetchone()
        joukkue_nimi = joukkue['joukkuenimi']
        kaikki_sarjat = set([])

        for joukkue in joukkueet:
            joukkue['jasenet'] = joukkue['jasenet'].replace('[', '').replace(']', '').replace('"', '').split(',')
            kaikki_sarjat.add(joukkue['sarjanimi'])
        sortatut_sarjat = sorted(kaikki_sarjat)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Tunnus tai salasana on väärin")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Tietokantaa ei löydy")
        else:
            print(err)
    # Suljetaan yhteys kantaan
    finally:
        con.close()
    return Response (render_template('kirjautunut.html', kilpailu_nimi=kilpailu_nimi, joukkue_nimi=joukkue_nimi, joukkueet=joukkueet, kaikki_sarjat=sortatut_sarjat), mimetype="text/html")

# Kirjautuneen joukkueen tietojen muokkaus
@app.route('/update', methods=['POST','GET'])
@auth
def muunnos_lomake():
    kilpailu = session['kilpailu']
    joukkue = session['joukkue']

    sql_kaikki_sarjat = '''SELECT id, sarjanimi FROM sarjat
    '''
    sql_joukkueen_sarja = '''SELECT sarja FROM joukkueet WHERE id = %s
    '''
    sql_kilpailu_nimi = '''SELECT id, kisanimi FROM kilpailut WHERE id = %s
    '''
    sql_joukkuenimi = '''SELECT joukkuenimi, jasenet, sarja FROM joukkueet WHERE id = %s
    '''
    joukkue_nimi = ''
    kilpailu_nimi = ''

    class muutoslomake(FlaskForm):
            sarja = RadioField('Sarja', choices=[], validators = [validators.InputRequired()])
    form = muutoslomake()

    try:
        con = pool.get_connection()
        cur = con.cursor(buffered=True, dictionary=True)
        cur.execute(sql_kaikki_sarjat)
        kaikki_sarjat = cur.fetchall()

        cur2 = con.cursor(buffered=True, dictionary=True)
        cur2.execute(sql_joukkueen_sarja, (joukkue,))
        joukkue_sarja = cur2.fetchone()
        cur3 = con.cursor(buffered=True, dictionary=True)
        cur3.execute(sql_kilpailu_nimi, (kilpailu,))
        yksi_kilpailu = cur3.fetchone()
        kilpailu_nimi = yksi_kilpailu['kisanimi']
        cur4 = con.cursor(buffered=True, dictionary=True)
        cur4.execute(sql_joukkuenimi, (joukkue,))
        yksi_joukkue = cur4.fetchone()
        joukkue_nimi = yksi_joukkue['joukkuenimi']
        joukkueen_jasenet = yksi_joukkue['jasenet'].replace('[', '').replace(']', '').replace('"', '').split(',')

        sarjaLista = []
        for element in kaikki_sarjat:
            sarjaLista.append((str(element["id"]), element["sarjanimi"] ))
        class muutoslomake(FlaskForm):
            sarja = RadioField('Sarja', choices=sarjaLista, validators = [validators.InputRequired()], default=yksi_joukkue["sarja"])
            joukkue = StringField('Joukkueen nimi', validators=[validators.InputRequired(),validators.Length(min=2, message="Syöttämäsi arvo ei kelpaa")], default=joukkue_nimi)
            jasen1 = StringField('Jäsen 1', validators=[validators.InputRequired(),validators.Length(min=2, message="Syöttämäsi arvo ei kelpaa")], default=joukkueen_jasenet[0] if len(joukkueen_jasenet) >= 1 else '')
            jasen2 = StringField('Jäsen 2', validators=[validators.InputRequired(),validators.Length(min=2, message="Syöttämäsi arvo ei kelpaa")], default=joukkueen_jasenet[1] if len(joukkueen_jasenet) >= 2 else '')
            jasen3 = StringField('Jäsen 3', default=joukkueen_jasenet[2] if len(joukkueen_jasenet) >= 3 else '')
            jasen4 = StringField('Jäsen 4', default=joukkueen_jasenet[3] if len(joukkueen_jasenet) >= 4 else '')
            jasen5 = StringField('Jäsen 5', default=joukkueen_jasenet[4] if len(joukkueen_jasenet) >= 5 else '')
        form = muutoslomake()

        # Päivitetään joukkueen tiedot.
        if request.method == 'POST':
            sql_update = '''UPDATE joukkueet SET sarja = %s, joukkuenimi = %s, jasenet = %s WHERE id = %s
            '''
            # sql-kysely kilpailun kaikista joukkueista
            sql_haejoukkueet = '''SELECT j.id AS jid, j.joukkuenimi, j.sarja, s.id AS sid FROM joukkueet j, sarjat s
            WHERE j.sarja = s.id AND s.kilpailu = %s
            '''
            members = []
            members.append(form.jasen1.data.strip().lower())
            members.append(form.jasen2.data.strip().lower())
            members.append(form.jasen3.data.strip().lower())
            members.append(form.jasen4.data.strip().lower())
            members.append(form.jasen5.data.strip().lower())
                

            # Tehdään jäsenistä JSON-taulukko.
            jasenet = '['
            jasenet = jasenet + '"' + str(form.jasen1.data) + '"'
            jasenet = jasenet + ', "' + str(form.jasen2.data) + '"'
            if form.jasen3.data != '':
                jasenet = jasenet + ', "' + str(form.jasen3.data) + '"'
            if form.jasen4.data != '':
                jasenet = jasenet + ', "' + str(form.jasen4.data) + '"'
            if form.jasen5.data != '':
                jasenet = jasenet + ', "' + str(form.jasen5.data) + '"'
            jasenet = jasenet + ']'

            cur6 = con.cursor(buffered=True, dictionary=True)
            # haetaan kaikki kilpailun joukkueet
            cur6.execute(sql_haejoukkueet, (kilpailu,))
            kilpailun_joukkueet = cur6.fetchall()
            cur5 = con.cursor(buffered=True, dictionary=True)
            update_ok = True
            # Tarkistetaan, onko jäsenten nimet uniikkia ja onko samassa kilpailussa toinen samanniminen joukkue
            for j in kilpailun_joukkueet:
                if str(form.joukkue.data).strip().lower() == str(j['joukkuenimi']).strip().lower() and str(j['jid']) != str(joukkue):
                    update_ok = False
                    break
            # jos kaikki on on ok suoritetaan tietojen päivitys kantaan
            if update_ok:
                try:
                    cur5.execute(sql_update, (form.sarja.data, form.joukkue.data, jasenet, joukkue))
                    con.commit()
                    return Response (render_template('muutatietoja.html', form=form, kilpailu_nimi=kilpailu_nimi, joukkue_nimi=joukkue_nimi, joukkue_sarja=joukkue_sarja, joukkueen_jasenet= joukkueen_jasenet, joukkue=joukkue))
                except mysql.connector.Error as err:
                    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                        print("Tunnus tai salasana on väärin")
                    elif err.errno == errorcode.ER_BAD_DB_ERROR:
                        print("Tietokantaa ei löydy")
                    else:
                        print(err)
            else:
                virhe = 'Tämä nimi on jo käytössä kilpailun toisella joukkueella!'
                return Response (render_template('muutatietoja.html', form=form, kilpailu_nimi=kilpailu_nimi, joukkue_nimi=joukkue_nimi, joukkue_sarja=joukkue_sarja, joukkueen_jasenet= joukkueen_jasenet, virhe=virhe, joukkue=joukkue))

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Tunnus tai salasana on väärin")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Tietokantaa ei löydy")
        else:
            print(err)
    # suljetaan yhteys kantaan
    finally:
        con.close()
    return Response (render_template('muutatietoja.html', form=form, kilpailu_nimi=kilpailu_nimi, joukkue_nimi = joukkue_nimi, joukkue_sarja=joukkue_sarja, joukkueen_jasenet= joukkueen_jasenet, joukkue=joukkue), mimetype="text/html")