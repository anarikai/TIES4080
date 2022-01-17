from pickle import GET
from urllib import response
from flask import Flask
app = Flask(__name__)
import requests
from flask import Response
from flask import request
import json

@app.route('/vt1', methods=['GET']) #Tämä rivi kertoo osoitteen, josta tämä sovellus löytyy
def listaaJoukkueet():
	response = json.loads(requests.get("http://hazor.eu.pythonanywhere.com/2022/data2022.json").text)
	#Joukkueiden nimet merkkijonona
	teamString = ""
	teamNameList = []
	#Jäsenten nimet merkkijonona
	memberString = ""
	memberNameList = []
	uusiJoukkue = {
		"nimi": request.args.get('nimi'),
		"jasenet": request.args.getlist('jasen'),
		"id": uusiId(response),
		"leimaustapa": [],
		"rastit": []
	}
	if request.args.get('reset') != '1':
		response = lueJson()
	if request.args.get('tila') != 'delete':
		lisaaJoukkue(response, request.args.get('sarja'), uusiJoukkue)
	else:
		poistaJoukkue(response['sarjat'], request.args.get('sarja'), request.args.get('nimi'))

	#Haetaan json-tietorakenteesta joukkueiden kaikki tiedot
	for each in response['sarjat']:
		for j in each['joukkueet']:
			#Lisätään joukkueiden tiedot teamNameList-muuttujaan
			teamNameList.append(j)
			# Lisätään joukkueiden jäsenten nimet memberNameList-taulukkoon
			for member in j['jasenet']:
				memberNameList.append(member)
		#print(memberNameList)

	joukkueet = joukkueLista(response)

	#Järjestetään teamNameList-muuttujan joukkueet nimen perusteella aakkosjärjestykseen
	teamNameList = sorted(teamNameList, key=lambda k: k['nimi'].lower())
	# Järjestetään memberNameList-taulukon jäsenet nimen perusteella aakkosjärjestykseen
	#memberNameList = sorted(memberNameList, key=lambda k: k['jasenet'].lower())
	#Lisätään teamNameList-muuttujan joukkueet teamString-merkkijonoon
	for each in teamNameList:
		teamString = teamString + each['nimi'] + '\n'
	#for member in memberNameList:
		#memberString = memberString + member['jasenet'] + '\n'
	teamString = teamString + '\n' + listaaRastit(response)
	with open('data.json', 'w') as f:
		json.dump(response, f)
	return Response(teamString, mimetype="text/plain;charset=UTF-8")

@app.route('/data.json', methods=['GET']) #Tämä rivi kertoo osoitteen, josta data.json löytyy
#Tässä tehdään JSON-file, jossa on sekä uusi joukkue että jo olemassa oleva data
def readJsonAndReturnResponse():
	return Response(json.dumps(lueJson()), mimetype="application/json;charset=UTF-8") 

def lueJson():
    with open('data.json') as json_file:
       return json.load(json_file)

def lisaaJoukkue(response, sarja, joukkue):
	sarjat = response['sarjat']
	#Tässä toteutetaan avainvalidaatio eli vaa "hei onko tää avain täällä NOT", eli jos 'nimi' on -> not + True -> False, jos ei not + False -> true, eli varmistetaan, että nää avaimet (key) on täällä
	if joukkue['nimi'] is None or not 'jasenet' in joukkue or not 'id' in joukkue or not 'leimaustapa' in joukkue or not 'rastit' in joukkue:
		return
	joukkueLoydetty = False
	for each in sarjat:
		lisattavaJoukkue = {}
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

#Tässä etsitään ne rastit, joiden koodissa on numerot ja listataan ne tehtävänannon mukaisesti
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
	numeroRastitString = numeroRastitString[:-2]
	return numeroRastitString


#Tässä määritellään uudelle joukkueelle uniikki id etsimällä jo olemassa olevien joukkueiden id:stä suurin ja lisäämällä siihen 1
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

def joukkueLista(response):
	kaikkiJoukkueet = []
	sarjat = response['sarjat']
	for each in sarjat:
		for j in each['joukkueet']:
			kaikkiJoukkueet.append(j)
	print(kaikkiJoukkueet)
	return kaikkiJoukkueet
