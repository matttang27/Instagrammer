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

from database_functions import (create_table, databaseLogin, deleteTable,
                                load_table, resetLastUpdated, saveDataToJSON)

# import a env file with the following variables: USERNAME, PASSWORD

load_dotenv()
account = {}

account["USERNAME"] = os.getenv("USERNAME")
account["PASSWORD"] = os.getenv("PASSWORD")

# Create a new instance of the Chrome driver
from selenium.webdriver.chrome.options import Options

# enable browser logging
o = Options()
#o.add_argument("--headless")
o.set_capability("goog:loggingPrefs", {"browser": "ALL"})
driver = webdriver.Chrome(options=o)

MUTUAL_REQUIREMENTS = 20
DAY_LIMIT = 7

STATUS_BUTTON_CLASS = "_ap30"


# Function to log in to Instagram
def login():
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5)

    try:

        username_input = driver.find_element(By.NAME, "username")
    except:
        print("requires captcha, waiting 1 minute")

        time.sleep(60)
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
    follow_button = None
    try:
        try:
            follow_button = driver.find_elements(By.XPATH,"//*[contains(text(), 'Follow')]")
            
        except:
            follow_button = driver.find_elements(By.XPATH,"//*[contains(text(), 'Follow Back')]")

        follow_button[0].click()
    except:
        print("Already followed!")
    
    time.sleep(2)


# Function to unfollow an account by username
def unfollow_account(username):
    log("to unfollow: " + username)

    """
    driver.get(f"https://www.instagram.com/{username}/")
    time.sleep(4)

    Disabling the unfollow, for now, just in case something bad happens.
    try:
        unfollow_button = driver.find_element(By.CLASS_NAME, "_acat")
        print(unfollow_button.find_elements(By.CSS_SELECTOR,"*")[0].text)
        unfollow_button.click()
        time.sleep(2)

        second_button = driver.find_elements(By.XPATH,"//*[contains(text(), 'Unfollow')]")[-1]
        second_button.click()
        time.sleep(2)
    except:
        print("Not following")"""




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

        foundAccount["followers"] = []
        foundAccount["following"] = []
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


def getRandomMutual(conn,db,accountData):
    dictData = {user["username"]:user for user in db}
    # get a random mutual account
    randomMutual = random.choice(accountData["mutuals"])
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


    # if there are too many accounts that you don't follow, the people on the bottom probably don't have a lot of mutuals.
    follow_counter = 0


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

            if (data[-1] == "Follow"):
                follow_counter += 1
            
            if dictData.get(data[0]):
                user = dictData.get(data[0])
                dataToAdd.append((data[0], data[-1], user["followrequest"], user["mutualcount"], user["followercount"], user["followingcount"], user["matthewinteract"], user["lastupdated"], user["blacklisted"]))
            
            else:
                #If matthew is already following them, set matthewinteract to true.
                dataToAdd.append((data[0], data[-1], None, 0, 0, 0, (data[-1] == "Following"), None, False))
                
            
            profile_counter += 1

        if follow_counter >= 50:
            break

        if profile_counter == past_counter:
            same_value_counter += 1
        else:
            same_value_counter = 0

        if same_value_counter == 4:
            break
    
    #add dataToAdd to database
    with conn.cursor() as cur:
        execute_values(cur, "UPSERT INTO accounts (username, status, followRequest, mutualCount, followerCount, followingCount, matthewInteract, lastUpdated, blacklisted) VALUES %s", dataToAdd)
    conn.commit()


def getProfileData(username):
    

    #get status
    status = ""
    while True:
        try:
            driver.get(f"https://www.instagram.com/{username}/")
            time.sleep(10)
            status = driver.find_elements(By.CLASS_NAME, STATUS_BUTTON_CLASS)[0].text
            break
        except IndexError:
            #check if the page is unavailable, or if it's ratelimited.


            unavailable = driver.find_elements(By.XPATH,"//*[contains(text(), 'Sorry, this page')]")
            
            if (len(unavailable) > 0):
                print("Page unavailable, blacklisting")
                log(username + " page unavailable, blacklisting")
                return {"status":"Unavailable","followers":0,"following":0,"mutuals":0,"followback":False}
            else:
                print("Did not work, waiting 5 minutes")
                #if the status button isn't found, it's probably because Instagram put us on cooldown. Wait 30 minutes and try again.
                time.sleep(5*60)
                print("Retrying...")
    #get the follower, following, and mutual counts
    elements = driver.find_elements(By.CLASS_NAME, "_ac2a")
    followers = int(elements[1].text.replace(",",""))
    following = int(elements[2].text.replace(",",""))
    num_mutuals = 0
    try:
        mutuals = driver.find_elements(By.CLASS_NAME, "_aaaj")[0]
        num_mutuals = int(mutuals.text.split(" ")[-2].replace(",",""))
    except Exception as e:
        pass

    follow_back = False

    try:

        driver.get(f"https://www.instagram.com/{username}/following/")
        time.sleep(5)

        
        # scroll down
        element = driver.find_element(By.CLASS_NAME, "_aano")
        time.sleep(5)

        verical_ordinate = 100
        profileList = driver.find_elements(By.CLASS_NAME, "x1dm5mii")

        driver.execute_script(
            "arguments[0].scrollTop = arguments[1]", element, verical_ordinate
        )

        profileList = driver.find_elements(By.CLASS_NAME, "x1dm5mii")

        profile = profileList[0]
        data = profile.find_element(By.CLASS_NAME, "x9f619").text.split("\n")
        if (data[0] == account["USERNAME"]):
            follow_back = True
    
    except:
        pass



    print(username,status,followers,following,num_mutuals,follow_back)
    return {"status":status,"followers":followers,"following":following,"mutuals":num_mutuals,"followback":follow_back}

def updateAccounts(conn,db):
    tableData = load_table(conn)
    
    dictData = {user["username"]:user for user in tableData}

    for i in dictData.keys():

        if (dictData[i]["lastupdated"] == None) or ((dictData[i]["followrequest"] != None) and ((datetime.datetime.now() - dictData[i]["lastupdated"]).days > DAY_LIMIT)):
            #update the account
            data = getProfileData(i)

            with conn.cursor() as cur:
                cur.execute("UPDATE accounts SET status = %s, followerCount = %s, followingCount = %s, mutualCount = %s, followBack = %s, lastUpdated = %s WHERE username = %s", (data["status"], data["followers"], data["following"], data["mutuals"], data["followback"], datetime.datetime.now(), i))
            conn.commit()

            if (data["status"] == "Follow"):
                user = dictData.get(i)
                #If user blocked request, don't try to follow again
                if (user["followrequest"] != None):
                    print(i, "rejected follow request, blacklisted.")
                    log(i + " rejected follow request, blacklisted.")
                    with conn.cursor() as cur:
                        cur.execute("UPDATE accounts SET followrequest = %s, blacklisted = %s WHERE username = %s", (None, True, i))
                    conn.commit()
                elif ((not (user["matthewinteract"] or user["blacklisted"])) and (data["mutuals"] > MUTUAL_REQUIREMENTS)):
                    print("requested follow for", i)
                    log("requested follow for " + i)
                    follow_account(i)
                    with conn.cursor() as cur:
                        cur.execute("UPDATE accounts SET followrequest = %s WHERE username = %s", (datetime.datetime.now(), i))
                    conn.commit()

def log(message):
    #open log.json, and add message with a timestamp

    with open('log.json') as json_file:
        data = json.load(json_file)
        data.append({"time":datetime.datetime.now(),"message":message})
        with open('log.json', 'w') as outfile:
            json.dump(data, outfile, indent=4, sort_keys=True, default=str)

def checkToUnfollow(conn,accountData):

    #Unfollow if:

    #Unfollowed us
    #Removed us from following
    #Did not follow back after request

    tableData = load_table(conn)
    
    dictData = {user["username"]:user for user in tableData}

    org_followers, org_following = [],[]
    #open followerfollowing.json
    with open('followerfollowing.json') as json_file:
        data = json.load(json_file)
        #get the list of followers and following
        org_followers = data["followers"]
        org_following = data["following"]
    unfollowed = list(set(org_followers) - set(accountData["followers"]))
    removed = list((set(org_following) - set(accountData["following"])) - set(unfollowed))

    for i in dictData.keys():
        if ((dictData[i]["followrequest"] != None) and ((datetime.datetime.now() - dictData[i]["lastupdated"]).days > DAY_LIMIT)):
            if (i in accountData["following"]):
                with conn.cursor() as cur:
                    cur.execute("UPDATE accounts SET followrequest = %s WHERE username = %s", (None, i))
                conn.commit()
                if (not (i in accountData["followers"])):
                    unfollow_account(i)
                    print("unfollowed and blacklisted", i)
                    log(i + " did not follow back: unfollowed and blacklisted")
                    with conn.cursor() as cur:
                        cur.execute("UPDATE accounts SET followrequest = %s, blacklisted = %s WHERE username = %s", (None, True, i))
                    conn.commit()

    for i in unfollowed:
        #blacklist and unfollow them

        if (dictData.get(i)):
            with conn.cursor() as cur:
                cur.execute("UPDATE accounts SET blacklisted = %s WHERE username = %s", (True, i))
            conn.commit()
        else:
            data = getProfileData(i)

            with conn.cursor() as cur:
                cur.execute("UPDATE accounts SET status = %s, followerCount = %s, followingCount = %s, mutualCount = %s, followBack = %s, lastUpdated = %s, blacklisted = %s WHERE username = %s", (data["status"], data["followers"], data["following"], data["mutuals"], data["followback"], datetime.datetime.now(), True, i))
            conn.commit()

        unfollow_account(i)
        print("unfollowed and blacklisted", i)
        log(i + " unfollowed us: unfollowed and blacklisted")

    for i in removed:
        #blacklist them

        if (dictData.get(i)):
            with conn.cursor() as cur:
                cur.execute("UPDATE accounts SET blacklisted = %s WHERE username = %s", (True, i))
            conn.commit()
        else:
            data = getProfileData(i)

            with conn.cursor() as cur:
                cur.execute("UPDATE accounts SET status = %s, followerCount = %s, followingCount = %s, mutualCount = %s, followBack = %s, lastUpdated = %s, blacklisted = %s WHERE username = %s", (data["status"], data["followers"], data["following"], data["mutuals"], data["followback"], datetime.datetime.now(), True, i))
            conn.commit()
        print("removed us: blacklisted", i)
        log(i + " removed us: blacklisted")
    
    with open('followerfollowing.json', 'w') as outfile:
        json.dump(accountData, outfile, indent=4, sort_keys=True, default=str)



# Main function to execute the bot actions
def main():
    
    try:

        log("bot starting...")
        
        conn = databaseLogin()  

        login()

        while (True):

            accountData = getFollowersAndFollowing(account["USERNAME"])

            

            checkToUnfollow(conn,accountData)

            updateAccounts(conn,load_table(conn))

            saveDataToJSON(conn)

            getRandomMutual(conn,load_table(conn),accountData)

            saveDataToJSON(conn)

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
