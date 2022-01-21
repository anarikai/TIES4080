from math import trunc
from urllib import response
from flask import Flask
app = Flask(__name__)
import requests
from flask import Response
from flask import request
import json


@app.route('/vt1', methods=['GET']) # Tämä rivi kertoo osoitteen, josta tämä sovellus löytyy
def listaaJoukkueet():
	response = json.loads(requests.get("http://hazor.eu.pythonanywhere.com/2022/data2022.json").text)
	# Joukkueiden nimet merkkijonona
	teamString = ""

	joukkueJaPisteetString = ""
	# Taulukko joukkueen tiedoille
	teamNameList = []
	# Taulukko joukkueille ja pisteille
	joukkueJaPisteetList = []

	# Uusi joukkue -olio
	uusiJoukkue = {
		"nimi": request.args.get('nimi'),
		"jasenet": request.args.getlist('jasen'),
		"id": uusiId(response),
		"leimaustapa": [],
		'leimaukset': [],
		"rastit": []
	}

	leimaustavat = request.args.getlist('leimaustapa')
	# Jos reset-attribuutti on jotain muuta kuin 1, ladataan oma tietorakenne. Muuten ladataan alkuperäinen
	if request.args.get('reset') != '1':
		response = lueJson()
	# Jos tila-attribuutti on jotain muuta kuin delete, niin lisätään uusi joukkue. Muuten joukkue poistetaan nimen ja sarjan perusteella
	if request.args.get('tila') != 'delete':
		lisaaJoukkue(response, request.args.get('sarja'), uusiJoukkue)
	else:
		poistaJoukkue(response['sarjat'], request.args.get('sarja'), request.args.get('nimi'))

	# Käydään leimaustavat läpi ja asetetaan niitä vastaavat id:t
	for each in leimaustavat:
		if each == 'GPS':
			uusiJoukkue['leimaustapa'].append(0)
		if each == 'NFC':
			uusiJoukkue['leimaustapa'].append(1)
		if each == 'QR':
			uusiJoukkue['leimaustapa'].append(2)
		if each == 'Lomake':
			uusiJoukkue['leimaustapa'].append(3)

	#Haetaan json-tietorakenteesta joukkueiden kaikki tiedot
	for each in response['sarjat']:
		for j in each['joukkueet']:
			#Lisätään joukkueiden tiedot teamNameList-muuttujaan
			teamNameList.append(j)

	#Järjestetään teamNameList-muuttujan joukkueet nimen perusteella aakkosjärjestykseen
	teamNameList = sorted(teamNameList, key=lambda k: k['nimi'].lower())
	# Asetetaan kayRastitLapi-funktion palauttaman vastauksen joukkueJaPisteetList-taulukkoon
	joukkueJaPisteetList = kayRastitLapi(response)
	#Lisätään teamNameList-muuttujan joukkueet teamString-merkkijonoon
	for each in teamNameList:
		teamString = teamString + each['nimi'] + '\n'
	# Muodostetaan merkkijono, jossa on joukkueiden nimet ja pisteet sekä jäsenet
	for each in joukkueJaPisteetList:
		joukkueJaPisteetString = joukkueJaPisteetString + each['nimi'] + ' ' + '(' + str(each['pisteet']) + ' ' + 'p' + ')' + '\n'
		for jasen in each['jasenet']:
			joukkueJaPisteetString = joukkueJaPisteetString + '  ' + str(jasen) + '\n'
	# Lisätään kaikki yhteiseen merkkijonoon, joka palauetaan rivillä 78
	teamString = teamString + '\n' + listaaRastit(response) + '\n' + joukkueJaPisteetString

	with open('data.json', 'w') as f:
		json.dump(response, f)
	return Response(teamString, mimetype="text/plain;charset=UTF-8")

@app.route('/data.json', methods=['GET']) # Tämä rivi kertoo osoitteen, josta data.json löytyy
# Tässä tehdään JSON-file, jossa on sekä uusi joukkue että jo olemassa oleva data
def readJsonAndReturnResponse():
	return Response(json.dumps(lueJson()), mimetype="application/json;charset=UTF-8") 

# Luetaan json-tiedosto
def lueJson():
    with open('data.json') as json_file:
       return json.load(json_file)

# Lisätään uusi joukkue
def lisaaJoukkue(response, sarja, joukkue):
	sarjat = response['sarjat']
	# Tässä toteutetaan avainvalidaatio eli vaa "hei onko tää avain täällä NOT", eli jos 'nimi' on -> not + True -> False, jos ei not + False -> true, eli varmistetaan, että nää avaimet (key) on täällä
	if joukkue['nimi'] is None or not 'jasenet' in joukkue or not 'id' in joukkue or not 'leimaustapa' in joukkue or not 'rastit' in joukkue:
		return
	joukkueLoydetty = False
	for each in sarjat:
		for j in each['joukkueet']:
			if j.get('nimi') and j['nimi'].strip().lower() == joukkue['nimi'].strip().lower():
				joukkueLoydetty = True
				print('Samanniminen joukkue on jo olemassa')
				break
	if not joukkueLoydetty:
		for each in sarjat:
			if each['nimi'] == sarja:
				each['joukkueet'].append(joukkue)
				break

# Poistetaan joukkue nimen ja sarjan perusteella
def poistaJoukkue(data, sarja, joukkue):
	for each in data:
		sarjaLoydetty = False
		joukkueLoydetty = False
		if each.get('nimi') and each['nimi'].strip().lower() == sarja.strip().lower():
			sarjaLoydetty = True
			for j in each['joukkueet']:
				if j.get('nimi') and j['nimi'].strip().lower() == joukkue.strip().lower():
					each['joukkueet'].remove(j)
					joukkueLoydetty = True
					break
			if joukkueLoydetty:
				break
		if sarjaLoydetty:
			break

# Tässä etsitään ne rastit, joiden koodissa on numerot ja listataan ne tehtävänannon mukaisesti
def listaaRastit(response):
	numeroRastitString = ""
	numeroRastit = []
	rastit = response['rastit']
	#Tarkistetaan, löytyyko koodista numeroa
	for each in rastit:
		onko = each['koodi'][0].isdigit()
		if onko == True:
			numeroRastit.append(each['koodi'])
	#Asetetaan taulukon alkiot suuruusjärjestykseen
	numeroRastit.sort()
	for each in numeroRastit:
		numeroRastitString = numeroRastitString + each + '; '
	#Poistetaan viimeinen puolipiste
	numeroRastitString = numeroRastitString[:-2] + '\n'
	return numeroRastitString


# Tässä määritellään uudelle joukkueelle uniikki id etsimällä jo olemassa olevien joukkueiden id:stä suurin ja lisäämällä siihen 1
def uusiId(response):
	suurinId = 0
	kaikkiIdt = []
	sarjat = response['sarjat']
	for each in sarjat:
		for j in each['joukkueet']:
			joukkueId = j['id']
			kaikkiIdt.append(joukkueId)
	for i in range(0, len(kaikkiIdt)):
		for j in range(i+1, len(kaikkiIdt)):
			if kaikkiIdt[i] < kaikkiIdt[j]:
				suurinId = kaikkiIdt[j]
			if kaikkiIdt[i] > kaikkiIdt[j]:
				suurinId = kaikkiIdt[i]
			if kaikkiIdt[i] == kaikkiIdt[j]:
				suurinId = kaikkiIdt[i]
	return suurinId + 1

# Otetaan talteen koko joukkueet-olio
def joukkueLista(response):
	kaikkiJoukkueet = []
	sarjat = response['sarjat']
	for sarja in sarjat:
		for joukkue in sarja['joukkueet']:
			kaikkiJoukkueet.append(joukkue)
	#print(kaikkiJoukkueet)
	return kaikkiJoukkueet

# Käydään läpi rastit ja joukkueiden leimaukset sekä lasketaan pisteet
def kayRastitLapi(data):
	joukkueet = joukkueLista(data)
	rastit = data['rastit']
	joukkueTaulukko = []

	for joukkue in joukkueet:
		joukkuePisteDict = {
			"nimi": '',
			"pisteet": '',
			"jasenet": []
		}
		lahto = []
		maali = []
		pisteet = 0
		for leimaus in joukkue['leimaukset']:
			for rasti in rastit:
				if str(leimaus['rasti']) == str(rasti['id']):
					if str(rasti['koodi']) == 'LAHTO':
						lahto.append(leimaus['aika'])
					if str(rasti['koodi']) == 'MAALI':
						maali.append(leimaus['aika'])
		# Jos on useampi lähtö- tai maali-rasti niin järjestetään ajan mukaan 
		lahto.sort()
		maali.sort()
		
		eiPisteita = False
		if (len(lahto) == 0 or len(maali) == 0):
			eiPisteita = True
		if not eiPisteita:
			lahtoAika = lahto[-1]
			for finish in maali:
				if finish > lahtoAika:
					maaliAika = finish
			leimauksetKertaalleen = set()
			for leimaus in joukkue['leimaukset']:
				for rasti in rastit:
					# Muunnettu stringeiksi, koska data.json ei ole tasalaatuista ja pisteiden lasku menee muuten väärin
					if str(leimaus['rasti']) == str(rasti['id']) and str(rasti['id']) not in leimauksetKertaalleen:
						if str(lahtoAika) <= str(leimaus['aika']) and str(maaliAika) >= str(leimaus['aika']) and rasti['koodi'][0].isdigit():
							pisteet = pisteet + int(rasti['koodi'][0])
							leimauksetKertaalleen.add(str(rasti['id']))
		joukkuePisteDict['nimi'] = joukkue['nimi']
		joukkuePisteDict['pisteet'] = pisteet
		# Laitetaan joukkueiden jäsenet aakkosjärjestykseen
		joukkuePisteDict['jasenet'] = sorted(joukkue['jasenet'])
		joukkueTaulukko.append(joukkuePisteDict)
		# Järjestetään taulukko ensisijaisesti pisteiden perusteella ja toissijaisesti aakkosjärjestyksen mukaan.
		sortattuTaulukko = sorted(sorted(joukkueTaulukko, key = lambda i: i['nimi'].lower()), key = lambda i : i['pisteet'], reverse = True)
	#print(joukkueTaulukko)

	return sortattuTaulukko