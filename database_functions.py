#!/usr/bin/env python3
"""
Test psycopg with CockroachDB.
"""

import json
import logging
import os
import random
import time
import uuid
from argparse import ArgumentParser, RawTextHelpFormatter

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from psycopg2.errors import SerializationFailure

# import a env file with the following variables: USERNAME, PASSWORD

load_dotenv()
account = {}

account["USERNAME"] = os.getenv("USERNAME")
account["PASSWORD"] = os.getenv("PASSWORD")

ACCOUNT_SCHEMA = "(username TEXT PRIMARY KEY, status TEXT, followRequest TIMESTAMP, mutualCount INT, followerCount INT, followingCount INT, followBack BOOLEAN, matthewInteract BOOLEAN, lastUpdated TIMESTAMP, blacklisted BOOLEAN)"
LOG_SCHEMA = "(time TIMESTAMP, message TEXT)"
FOLLOWERFOLLOWING_SCHEMA = "(type TEXT PRIMARY KEY, list TEXT[])"
ACTIONS_SCHEMA = "(action TEXT, time TIMESTAMP, username TEXT, details TEXT)"


ACCOUNT_PATH = account["USERNAME"] + ".accounts"
LOG_PATH = account["USERNAME"] + ".log"
FOLLOWERFOLLOWING_PATH = account["USERNAME"] + ".followerfollowing"
ACTIONS_PATH = account["USERNAME"] + ".actions"

load_dotenv()
def create_table(conn,table_name, table_schema):
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS {} {}".format(table_name,table_schema))
        
        logging.debug("create_accounts(): status message: %s",
                      cur.statusmessage)
        conn.commit()

def load_table(conn,table_name):
    #load table into a 2d array
    rows = None
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM " + table_name)
        logging.debug("load_accounts(): status message: %s",
                      cur.statusmessage)
        rows = cur.fetchall()
        conn.commit()
    return rows

def deleteTable(conn, table_name):
    with conn.cursor() as cur:
        cur.execute("DROP TABLE " + table_name)
        logging.debug("delete_accounts(): status message: %s",
                      cur.statusmessage)
        conn.commit()

def resetLastUpdated(conn, table_name):
    with conn.cursor() as cur:
        cur.execute("UPDATE " + table_name + "  SET lastUpdated = NULL")
        logging.debug("resetLastUpdated(): status message: %s",
                      cur.statusmessage)
        conn.commit()

def JSONtoTable(conn, table_name):
    with open("followerfollowing.json") as json_file:
        data = json.load(json_file)

        for i in data.keys():
            with conn.cursor() as cur:
                #upsert into table, using i as text and data[i] as list
                cur.execute("UPSERT INTO " + table_name + " (type, list) VALUES (%s, %s)", (i, data[i]))

                
            conn.commit()

    
        
def databaseLogin():

    try:
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url, application_name="Instagrammer", cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception as e:
        logging.fatal(e)
        return
    return conn

def saveDataToJSON(conn, table_name):
    data = load_table(conn, table_name)
    print(data)
    data = [dict(row) for row in data]

    #save it to a json file
    
    with open('data.json', 'w') as outfile:
        json.dump(data, outfile, indent=4, sort_keys=True, default=str)

def updateAccountValue(conn):
    with conn.cursor() as cur:
        cur.execute("UPDATE accounts_" + account["USERNAME"] + "  SET status = %s WHERE username = %s", (value, username))
        logging.debug("updateAccountValue(): status message: %s",
                      cur.statusmessage)
        conn.commit()
import datetime


def main():

    

    conn = databaseLogin()

    #load log table
    logData = load_table(conn, LOG_PATH)

    #for each log entry, convert and add it to the actions table
    for i in logData:   
        action,username,details = None,None,None
        if (i["message"] == "bot starting..."):
            action = "startup"
        #if message starts with: "requested follow for"
        elif (i["message"].startswith("requested follow for")):
            action = "follow request"
            username = i["message"].split(" ")[3]
        #if message's second and third word is "unfollowed us"
        elif (i["message"].split(" ")[1] == "unfollowed" and i["message"].split(" ")[2] == "us:"):
            #add two actions: unfollow and blacklisted
            action = "unfollow"
            details = "reason: unfollowed us"
            username = i["message"].split(" ")[0]
            with conn.cursor() as cur:
                cur.execute("INSERT INTO " + ACTIONS_PATH + " (action, time, username, details) VALUES (%s, %s, %s, %s)", ("blacklist", i["timestamp"], username, details))
            conn.commit()
        #if "removed us"
        elif (i["message"].split(" ")[1] == "removed" and i["message"].split(" ")[2] == "us:"):
            action = "blacklist"
            details = "reason: removed us"
            username = i["message"].split(" ")[0]
        #if "did not follow back"
        elif (i["message"].split(" ")[1] == "did" and i["message"].split(" ")[2] == "not" and i["message"].split(" ")[3] == "follow" and i["message"].split(" ")[4] == "back:"):
            action = "unfollow"
            details = "reason: did not follow back"
            username = i["message"].split(" ")[0]
            with conn.cursor() as cur:
                cur.execute("INSERT INTO " + ACTIONS_PATH + " (action, time, username, details) VALUES (%s, %s, %s, %s)", ("blacklist", i["timestamp"], username, details))
            conn.commit()
        #if "rejected follow request"
        elif (i["message"].split(" ")[1] == "rejected" and i["message"].split(" ")[2] == "follow" and i["message"].split(" ")[3] == "request,"):
            action = "blacklist"
            details = "reason: rejected follow request"
            username = i["message"].split(" ")[0]
        #if "page unavailable,"
        elif (i["message"].split(" ")[1] == "page" and i["message"].split(" ")[2] == "unavailable,"):
            action = "blacklist"
            details = "reason: page unavailable"
            username = i["message"].split(" ")[0]




        with conn.cursor() as cur:
            cur.execute("INSERT INTO " + ACTIONS_PATH + " (action, time, username, details) VALUES (%s, %s, %s, %s)", (action, i["timestamp"], username, details))
            logging.debug("main(): status message: %s",
                    cur.statusmessage)
        conn.commit()

    



    # Close communication with the database.
    conn.close()

if __name__ == "__main__":
    main()
    