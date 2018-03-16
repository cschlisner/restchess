#!/usr/bin/python3
# For game creation and user management 

import cgi
import rethinkdb as r
import random
import time 
import hashlib

print ("Content-type:text/html\r\n\r\n")

def hex_digest(player_uuid):
	m = hashlib.md5()
	m.update(player_uuid.encode('utf-8'))
	return m.hexdigest()

def find_opponent():
	return r.db("chess").table("users").filter({
				"online": True, 
			}).nth(0).getField("id").run(conn)

def create_game(player_one, player_two):
	w = random.choice([True, False])
	return r.db("chess").table('games').insert({
		"layout" : "RNBKQBNRPPPPPPPP................................pppppppprnbkqbnr",
		"uts" : int(time.time()),
		"white_md5uuid" : hex_digest(player_one) if w else hex_digest(player_two),
		"black_md5uuid" : hex_digest(player_two) if w else hex_digest(player_one),
		"w": True,
		"public":False,
		"white_draw":False,
		"black_draw":False,
		"moves": []
	}).run(conn)["generated_keys"][0]
	
conn = r.connect('localhost', 28015).repl()

while (True):
	# Create games from users in lobby
	online = r.db("chess").table("users").filter({
		"online":True 
	}).run(conn)
	try:
		player_one = online.next()
		player_two = online.next()	
	except:
		# Delete games that have no users in them
		emptyGames = r.db("chess").table("games").filter(
			lambda game:
			((game["white_md5uuid"]=="_") | (game["white_md5uuid"]=="F")) 
			& ((game["black_md5uuid"]=="_") | (game["black_md5uuid"]=="F"))
		).run(conn)
		
		
		try: 
			emptygame = emptyGames.next()
		except:
			continue;

		r.db("chess").table("games").get(emptygame.get("id")).delete().run(conn)


		print("deleted game: " + emptygame.get("id"))
		continue;		
		
	r.db("chess").table("users").get(player_one["id"]).update({
		"online": False
	}).run(conn)
	r.db("chess").table("users").get(player_two["id"]).update({
		"online": False
	}).run(conn)
	print("created game: " + create_game(player_one["id"], player_two["id"])+ " : "+ player_one["id"]+","+player_two["id"]);

