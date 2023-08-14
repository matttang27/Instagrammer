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