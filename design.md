# Instragrammer

## Goals

- Follow accounts with lots of mutuals
- Unfollow accounts that don't follow back after a period of time
    - Store what time an account is followed, then check if they have followed back after a period of time (e.g. 1 week)
    - Keep a list of accounts unfollowed this way - following an account again would be awkward and suspicious
    - Keep a list of accounts that are pending follow back - don't start timer until they have accepted the follow request. If they don't accept, unfollow them after a period of time (e.g. 1 week)
- Take into account Matthew's actions - e.g. if Matthew follows an account, the bot should not unfollow it, and make sure that the bot does not follow accounts that Matthew has unfollowed
    - This is done by periodically checking Matthew's followers and following lists, and updating the bot's lists accordingly
- Keep track of stats - e.g. how many accounts followed, how many unfollowed, how many pending, how many mutuals, etc.


## Settings

- Follow accounts with at least X mutuals
- Unfollow accounts that don't follow back after X days
- Check every X minutes
- Username and password

## Implementation

Every X minutes:
- Get followers and following lists using this answer: https://stackoverflow.com/a/63056537 - requires selenium to use browser console
- Check following - unfollow accounts that haven't followed back after X days, and update unfollowed list
- Check followers - follow accounts with at least X mutuals that aren't in the pending or unfollowed list, and update followed list


## Actual Step by Step implementation

On start:

- Sign-in to Instagram, Load database, Check followers and following lists of personal account.

Repeatable:
- Get a random mutual, by choosing a random person from accountData['mutuals']
- Go through the follower list of the mutual, adding / updating the database.
    - Make sure to stop earlier if the mutual has too many followers.
    - If matthew is already following them, set matthewinteract to true.
- Go through the database, checking accounts that haven't been updated in the past X days.
    - Skip if matthewinteract is true.
    - If they follow us, but we don't follow them, set matthewinteract to true.
    - If the status is different from the status in database, set matthewinteract to true.
    - If status is "Follow", and the number of mutuals is above the threshold, and not blacklisted, follow them.
        - Then set the followrequest timestamp to now.
    - If status is "Following", and they haven't followed back, and the followrequest timestamp is more than X days ago, unfollow them.
        - Then set blacklisted to true.

BONUS: detect people who have unfollowed us.