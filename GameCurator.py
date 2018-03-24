#!/usr/bin/python3
# For game table cleanup

import cgi
import rethinkdb as r
import random
import time 
import hashlib

print ("Content-type:text/html\r\n\r\n")

conn = r.connect('localhost', 28015, db="chess")

# Delete games that have no users in them
emptygames = r.table("games").filter(
			lambda game:
			((game["white_md5uuid"]=="_") | (game["white_md5uuid"]=="F")) 
			& ((game["black_md5uuid"]=="_") | (game["black_md5uuid"]=="F"))
		).changes().run(conn)

for game in emptygames
		game.get("id").delete().run(conn)

