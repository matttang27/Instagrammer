import datetime
import json
import logging
import os
import random
import time
import traceback
import uuid
from argparse import ArgumentParser, RawTextHelpFormatter

import psycopg2
import requests
# Import environment variables
from dotenv import load_dotenv
from psycopg2.errors import SerializationFailure
from psycopg2.extras import execute_values
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# import a env file with the following variables: USERNAME, PASSWORD

load_dotenv()
account = {}

account["USERNAME"] = os.getenv("USERNAME")
account["PASSWORD"] = os.getenv("PASSWORD")

# Create a new instance of the Chrome driver
from selenium.webdriver.chrome.options import Options

# enable browser logging
o = Options()
o.set_capability("goog:loggingPrefs", {"browser": "ALL"})
driver = webdriver.Chrome(options=o)


# Function to log in to Instagram
def login():
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(2)

    username_input = driver.find_element(By.NAME, "username")
    password_input = driver.find_element(By.NAME, "password")

    username_input.send_keys(account["USERNAME"])
    time.sleep(1)
    password_input.send_keys(account["PASSWORD"])
    time.sleep(1)
    login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    login_button.click()
    time.sleep(5)


# Function to follow an account by username
def follow_account(username):
    driver.get(f"https://www.instagram.com/{username}/")
    time.sleep(2)

    follow_button = driver.find_element_by_css_selector("button:not([disabled])")
    follow_button.click()
    time.sleep(2)


# Function to unfollow an account by username
def unfollow_account(username):
    driver.get(f"https://www.instagram.com/{username}/")
    time.sleep(2)

    follow_button = driver.find_element_by_css_selector(
        "button[aria-label='Following']"
    )
    follow_button.click()
    time.sleep(2)

    unfollow_button = driver.find_element_by_xpath("//button[text()='Unfollow']")
    unfollow_button.click()
    time.sleep(2)


def findMutualAccounts():
    driver.get("https://www.instagram.com/accounts/access_tool/current_follow_requests")


def getUserId(username):
    try:
        driver.get(
            f"https://www.instagram.com/web/search/topsearch/?query=${account['USERNAME']}"
        )
        x = driver.find_element(By.TAG_NAME, "pre").text

        x = json.loads(x)["users"]
        acc = None
        # find a user with the username USERNAME
        for user in x:
            print(user["user"]["username"])
            if user["user"]["username"] == username:
                acc = user["user"]
                break
        if acc == None:
            # if no user is found, raise an error
            raise Exception("No user found")

        userId = acc["pk"]
        return userId
    except Exception as e:
        print(traceback.format_exc())
        return None


def getFollowersAndFollowing(username):
    try:
        driver.get("https://www.instagram.com")
        time.sleep(3)
        driver.execute_script(
            f"""
                              const username = "{username}";"""
            + """

/**
 * Initialized like this so typescript can infer the type
 */
let followers = [{ username: "", full_name: "" }];
let followings = [{ username: "", full_name: "" }];
let dontFollowMeBack = [{ username: "", full_name: "" }];
let iDontFollowBack = [{ username: "", full_name: "" }];

followers = [];
followings = [];
dontFollowMeBack = [];
iDontFollowBack = [];

(async () => {
  try {
    console.log(`Process started! Give it a couple of seconds`);

    const userQueryRes = await fetch(
      `https://www.instagram.com/web/search/topsearch/?query=${username}`
    );

    const userQueryJson = await userQueryRes.json();

    const userId = userQueryJson.users[0].user.pk;

    let after = null;
    let has_next = true;

    while (has_next) {
      await fetch(
        `https://www.instagram.com/graphql/query/?query_hash=c76146de99bb02f6415203be841dd25a&variables=` +
          encodeURIComponent(
            JSON.stringify({
              id: userId,
              include_reel: true,
              fetch_mutual: true,
              first: 50,
              after: after,
            })
          )
      )
        .then((res) => res.json())
        .then((res) => {
          has_next = res.data.user.edge_followed_by.page_info.has_next_page;
          after = res.data.user.edge_followed_by.page_info.end_cursor;
          followers = followers.concat(
            res.data.user.edge_followed_by.edges.map(({ node }) => {
              return {
                username: node.username,
                full_name: node.full_name,
              };
            })
          );
        });
    }

    console.log("followers " + followers.map(x => x.username).toString() );

    after = null;
    has_next = true;

    while (has_next) {
      await fetch(
        `https://www.instagram.com/graphql/query/?query_hash=d04b0a864b4b54837c0d870b0e77e076&variables=` +
          encodeURIComponent(
            JSON.stringify({
              id: userId,
              include_reel: true,
              fetch_mutual: true,
              first: 50,
              after: after,
            })
          )
      )
        .then((res) => res.json())
        .then((res) => {
          has_next = res.data.user.edge_follow.page_info.has_next_page;
          after = res.data.user.edge_follow.page_info.end_cursor;
          followings = followings.concat(
            res.data.user.edge_follow.edges.map(({ node }) => {
              return {
                username: node.username,
                full_name: node.full_name,
              };
            })
          );
        });
    }

    console.log("following "+ followings.map(x => x.username).toString() );
  } catch (err) {
    console.log({ err });
  }
})();"""
        )

        time.sleep(10)
        # get the logs from the browser
        logs = driver.get_log("browser")
        print(logs)
        foundAccount = {}
        for log in logs:
            if log["message"].split(" ")[2] == '"followers':
                foundAccount["followers"] = log["message"].split(" ")[3][:-1].split(",")
            elif log["message"].split(" ")[2] == '"following':
                foundAccount["following"] = log["message"].split(" ")[3][:-1].split(",")
        foundAccount["mutuals"] = []
        foundAccount["iDontFollowBack"] = []
        foundAccount["dontFollowMeBack"] = []
        for follower in foundAccount["followers"]:
            if follower not in foundAccount["following"]:
                foundAccount["dontFollowMeBack"].append(follower)

            elif follower in foundAccount["following"]:
                foundAccount["mutuals"].append(follower)

        for following in foundAccount["following"]:
            if following not in foundAccount["followers"]:
                foundAccount["iDontFollowBack"].append(following)

        return foundAccount

    except Exception as e:
        print(traceback.format_exc())


def getRandomMutual(conn,db):
    # get a random mutual account
    # randomMutual = random.choice(account["mutuals"])
    randomMutual = "a_blimp_in_the_night"
    # go to account
    driver.get(f"https://www.instagram.com/{randomMutual}/followers/")
    time.sleep(5)
    # scroll down
    element = driver.find_element(By.CLASS_NAME, "_aano")
    time.sleep(5)

    verical_ordinate = 100

    # Skip first profile (me)
    profile_counter = 1

    # if the length of profileList doesn't change 4 times in a row, break
    same_value_counter = 0
    past_counter = 1

    dataToAdd = []
    while True:
        profileList = driver.find_elements(By.CLASS_NAME, "x1dm5mii")
        past_counter = profile_counter

        print(verical_ordinate)
        driver.execute_script(
            "arguments[0].scrollTop = arguments[1]", element, verical_ordinate
        )
        verical_ordinate += 500
        time.sleep(3)

        while profile_counter < len(profileList):
            profile = profileList[profile_counter]

            # idk why this works...but it does
            data = profile.find_element(By.CLASS_NAME, "x9f619").text.split("\n")
            print(data)

            if db[data[0]] == None:
              dataToAdd.append((data[0], data[-1], None, 0, 0, 0, False, None))
            
            else:
                user = db[data[0]]
                dataToAdd.append((data[0], data[-1], user["followrequest"], user["mutualcount"], user["followercount"], user["followingcount"], user["matthewinteract"], user["lastupdated"]))
            
            profile_counter += 1

        if profile_counter == past_counter:
            same_value_counter += 1
        else:
            same_value_counter = 0

        if same_value_counter == 4:
            break
    
    #add dataToAdd to database
    with conn.cursor() as cur:
        execute_values(cur, "UPSERT INTO accounts (username, status, followRequest, mutualCount, followerCount, followingCount, matthewInteract, lastUpdated) VALUES %s", dataToAdd)
    conn.commit()


def getProfileData(username):
    driver.get(f"https://www.instagram.com/{username}/")
    time.sleep(5)

    #get status
    status = driver.find_elements(By.CLASS_NAME, "_aacl")[0].text
    #get the follower, following, and mutual counts
    elements = driver.find_elements(By.CLASS_NAME, "_ac2a")
    num_mutuals = 0
    try:
        mutuals = driver.find_elements(By.CLASS_NAME, "_aaaj")[0]
        num_mutuals = mutuals.text.split(" ")[-2]
    except Exception as e:
        print(traceback.format_exc())
    print(int(elements[1].text), int(elements[2].text), int(num_mutuals))
    return [status,int(elements[1].text), int(elements[2].text), int(num_mutuals)]

def updateAccounts(conn,db):
    for i in db.keys():
        if (db[i]["lastupdated"] == None) or ((datetime.datetime.now() - db[i]["lastupdated"]).days > 7):
            #update the account
            data = getProfileData(i)
            with conn.cursor() as cur:
                cur.execute("UPDATE accounts SET status = %s, mutualCount = %s, followerCount = %s, followingCount = %s, lastUpdated = %s WHERE username = %s", (data[0], data[3], data[1], data[2], datetime.datetime.now(), i))
            conn.commit()
        

def create_table(conn):
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS accounts (username TEXT PRIMARY KEY, status TEXT, followRequest TIMESTAMP, mutualCount INT, followerCount INT, followingCount INT, matthewInteract BOOLEAN, lastUpdated TIMESTAMP)"
        )
        logging.debug("create_accounts(): status message: %s",
                      cur.statusmessage)
        conn.commit()

def load_table(conn):
    #load table into an ordereddict
    rows = None

    data = {}
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM accounts")
        logging.debug("load_accounts(): status message: %s",
                      cur.statusmessage)
        rows = cur.fetchall()
        conn.commit()
    for i in range(len(rows)):
        data[rows[i]['username']] = rows[i]
    return data


def databaseLogin():

    try:
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url, application_name="Instagrammer", cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception as e:
        logging.fatal(e)
        return
    return conn

# Main function to execute the bot actions
def main():
    try:
        
        conn = databaseLogin()

        create_table(conn)

        

        login()

            #getProfileData("matttang27")

        getRandomMutual(conn,load_table(conn))

        updateAccounts(conn,load_table(conn))

        # Implement the main bot logic here
        # - Fetch accounts with mutuals
        # - Follow accounts
        # - Check for accounts that haven't followed back
        # - Unfollow accounts if necessary
        # - Monitor Matthew's actions
        # - Implement settings check every X minutes

    except Exception as e:
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
