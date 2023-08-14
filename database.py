#!/usr/bin/env python3
"""
Test psycopg with CockroachDB.
"""

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

load_dotenv()
def create_table(conn):
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS accounts (username TEXT PRIMARY KEY, status TEXT, followRequest TIMESTAMP, mutualCount INT, followerCount INT, followingCount INT, matthewInteract BOOLEAN, lastUpdated TIMESTAMP)"
        )
        logging.debug("create_accounts(): status message: %s",
                      cur.statusmessage)
        conn.commit()

def load_table(conn):
    #load table into a 2d array
    rows = None
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM accounts")
        logging.debug("load_accounts(): status message: %s",
                      cur.statusmessage)
        rows = cur.fetchall()
        conn.commit()
    return rows

def deleteTable(conn):
    with conn.cursor() as cur:
        cur.execute("DROP TABLE accounts")
        logging.debug("delete_accounts(): status message: %s",
                      cur.statusmessage)
        conn.commit()
def main():

    try:
        
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url, 
                                application_name="Instagrammer", 
                                cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception as e:
        logging.fatal(e)
        return
    data = load_table(conn)
    print(data)
    # Close communication with the database.
    conn.close()

if __name__ == "__main__":
    main()