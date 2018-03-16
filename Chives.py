#!/usr/bin/python3

# For game creation and user management 

import cgi
import rethinkdb as r
import time
import hashlib
import random

print ("Content-type:text/html\r\n\r\n")

def convert_to_json_because_rethinkdb_sucks(response):
	return response.replace("\'","\"").replace("True","true").replace("False","false")

def find_opponent():
	return r.db("chess").table("users").filter({"online":true, "ingame" : false}).nth(0).getField("id").run(conn)

def hex_digest(player_uuid):
	m = hashlib.md5()
	m.update(player_uuid.encode('utf-8'))
	return m.hexdigest()

def find_games(player_uuid):
	uuidmd5 = hex_digest(player_uuid)
	return r.db("chess").table("games").filter((r.row["white_md5uuid"] == uuidmd5) | (r.row["black_md5uuid"] == uuidmd5)).order_by(r.desc("uts")).run(conn)

def register():
	return r.db("chess").table("users").insert({
	  "online" : False
	}).run(conn)["generated_keys"][0]

def create_game(player_one, public):
	w = random.choice([True, False])
	return r.db("chess").table('games').insert({
		"layout" : "RNBKQBNRPPPPPPPP................................pppppppprnbkqbnr",
		"uts" : int(time.time()),
		"white_md5uuid" : hex_digest(player_one) if w else "_",
		"black_md5uuid" : "_" if w else hex_digest(player_one),
		"w": True,
		"white_draw": False,
		"black_draw": False,
		"public": public,
		"moves": []
	}).run(conn)["generated_keys"][0]

def join_game(player_two, game):
	w = r.db("chess").table("games").get(game)['white_md5uuid'].run(conn) == "_"
	if w and r.db("chess").table("games").get(game)['black_md5uuid'].run(conn) == hex_digest(player_two):
		print("ERR_SELF")
		return
	if not w and r.db("chess").table("games").get(game)['white_md5uuid'].run(conn) == hex_digest(player_two):
		print("ERR_SELF")
		return
	if not w and r.db("chess").table("games").get(game)['black_md5uuid'].run(conn) != "_":
		print("ERR_GAME_FULL")
		return
	r.db("chess").table("games").get(game).update({
		"white_md5uuid" : hex_digest(player_two) if w else r.row['white_md5uuid'],
		"black_md5uuid" : r.row['black_md5uuid'] if w else hex_digest(player_two), 
		"public" : False
	}).run(conn)

def list_public(player):
	return r.db("chess").table("games").filter((r.row["public"] == True) & ((r.row["white_md5uuid"] == "_") | (r.row["black_md5uuid"] == "_")) & (r.row['white_md5uuid'] != hex_digest(player)) & (r.row['black_md5uuid'] != hex_digest(player))).order_by(r.desc("uts")).run(conn)

# switch their online status
def checkin(player):
	r.db("chess").table("users").get(player).update({
		"online" : True, 
	}).run(conn)

def checkout(player):
	r.db("chess").table("users").get(player).update({
		"online" : False, 
	}).run(conn)


##########################################################################
##########################################################################

conn = r.connect('localhost', 28015)

form = cgi.FieldStorage()
action = form["action"].value

# registers a new player
if action == 'register':
	player = register()
	print(player)

# sets user's online status to true, for instant matchmaking. 
elif action == 'checkin':
	player = form["uuid"].value
	checkin(player)

# sets user's online status to false. 
elif action == 'checkout':
	player = form["uuid"].value
	checkout(player)

# removes player from game. after both players are removed game will be deleted from database by GameCurator.py
elif (action == 'leavegame') | (action=='forfeit'):
	player = form["uuid"].value
	hash = hex_digest(player)
	game_uuid = form["game"].value
	game = r.db("chess").table("games").get(game_uuid).run(conn)
	isw = game["white_md5uuid"] == hash
	status = "F" if action == 'forfeit' else "_"
	if isw:
		r.db("chess").table("games").get(game_uuid).update({
			"white_md5uuid": status
		}).run(conn)
	else :
		r.db("chess").table("games").get(game_uuid).update({
			"black_md5uuid": status
		}).run(conn)
 
# gets game object associated with specified uuid
elif action == 'getgame':
	game_uuid = form["game"].value
	game = r.db("chess").table("games").get(game_uuid).run(conn)
	print(convert_to_json_because_rethinkdb_sucks(str(game)))

# lists all game objects associated with a player's uuid
elif action == 'retrievegames':
	player = form["uuid"].value
	cursor = find_games(player)
	print(convert_to_json_because_rethinkdb_sucks(str(cursor)))

# creates an open game for other player to join at any time
elif action == 'creategame':
	player = form['uuid'].value
	public = form['public'].value in ['true','1','True']
	print(convert_to_json_because_rethinkdb_sucks(str(r.db("chess").table("games").get(create_game(player, public)).run(conn))))

# joins game created by other player
elif action == 'joingame':
	player = form['uuid'].value
	game_id = form['game'].value
	join_game(player, game_id)
	print(convert_to_json_because_rethinkdb_sucks(str(r.db("chess").table("games").get(game_id).run(conn))))

elif action == 'listpublic':
	player = form['uuid'].value
	print(convert_to_json_because_rethinkdb_sucks(str(list_public(player))))

elif action == 'draw':
	player = form['uuid'].value
	game_id = form['game'].value
	hash = hex_digest(player)
	game = r.db("chess").table("games").get(game_id).run(conn)
	w = game["white_md5uuid"] == hash 
	r.db("chess").table("games").get(game_id).update({
		"white_draw"if w else "black_draw": True
	}).run(conn)
	game = r.db("chess").table("games").get(game_id).run(conn)
	print(convert_to_json_because_rethinkdb_sucks(str(game)))

# todo: elif action == 'unregister':
elif action == 'rejectdraw':
	player = form['uuid'].value
	game_id = form['game'].value
	hash = hex_digest(player)
	game = r.db("chess").table("games").get(game_id).run(conn)
	w = game["white_md5uuid"] == hash
	r.db("chess").table("games").get(game_id).update({
		"black_draw" if w else "white_draw" : False
	}).run(conn)
	game = r.db("chess").table("games").get(game_id).run(conn)
	print(convert_to_json_because_rethinkdb_sucks(str(game)))
