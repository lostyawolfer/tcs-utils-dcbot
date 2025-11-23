TARGET_GUILD = 1426972810332340406

def check_guild(guild_id: int) -> bool:
    if guild_id == TARGET_GUILD:
        return True
    return False



from dotenv import dotenv_values
TOKEN = dotenv_values('.env').get('TOKEN')
if not TOKEN:
    print('there\'s no token\n'
          'create a .env file in this directory and put in "TOKEN=..." and replace the "..." with ur bot token')




ROLES = {
    "admins": [
        1427016174444613804, # the man behind the challenge
        1433828741548740781  # moderator
    ],
    "new_people": [
        1427076669264498820, # person
        1433872100837425193  # newbie
    ],
    "bot": 1442086763161194597,
    "leader": 1426973394099896507,
    "available": 1434629510031999269,
    "available_leader": 1434629548347232326,
    "not_available": 1442132238660796416,
    "in_vc": 1427076261586669688,
    "in_vc_leader": 1427076452477702191,
    "not_in_vc": 1442132263071645779,
    "birthday": 1439339439762444552,
    "inactive": 1434659281822679232
}

CHANNELS = {
    "vc": 1426972811293098015,
    "chat": 1426972811293098014,
    "availability": 1434653852367585300,
    "availability_message": 1434654321886363658,
    "availability_reaction": 1439620553572089900,
    "ps_link": 1426974154556702720
}


_EMOJI = {
    "join": "<:join:1436503008924926052>",
    "leave": "<:leave:1436503027937841173>",
    "ban": "<:ban:1438882547588141118>",
    "kick": "<:kick:1439803052826689537>",
    "app_join": "<:newapp:1438882548829913209>",
    "app_leave": "<:removedapp:1438882550075621538>",
    "available": "<:available:1436525036281532449>",
    "unavailable": "<:notavailable:1436528517956374578>",
    "join_vc": "<:join_vc:1436503046107566181>",
    "leave_vc": "<:leave_vc:1436528566174220289>",
    "promotion": "<:promotion:1442087863347974294>",
    "demotion": "<:demotion:1442087886391607376>",
    "birthday": ""
}

_MESSAGES = {
    "join": [
        f"{_EMOJI['join']} Is {{mention}} really ready for this? After all, not many people have the patience to wait for 8 players to join.",
        f"{_EMOJI['join']} {{mention}} should now prepare to die in the backdoor a hundred times as part of join process.",
        f"{_EMOJI['join']} Don't worry {{mention}}, the lights flicker only *most* of the time.",
        f"{_EMOJI['join']} It's time for {{mention}} to acknowledge the possibility of pain and seizure.",
        f"{_EMOJI['join']} {{mention}} just joined! Quick, everyone look like we know what we're doing!",
        f"{_EMOJI['join']} Uhh, hey, {{mention}}, you have any sanity? We're running low, could we please borrow some?",
        f"{_EMOJI['join']} Let's hope {{mention}} has it all Figured out."
    ],
    "join_bot": [
        f"{_EMOJI['app_join']} New digital entity alert! {{mention}} has manifested.",
        f"{_EMOJI['app_join']} Beep boop! {{mention}} just computed its way in.",
        f"{_EMOJI['app_join']} System update detected: Bot {{mention}} has joined the network."
    ],
    "leave": [
        f"{_EMOJI['leave']} {{mention}} couldn't handle the Backdoor any longer...",
        f"{_EMOJI['leave']} {{mention}} disconnected. Please check your internet connection and try again. (Error Code: 277)",
        f"{_EMOJI['leave']} {{mention}} ran out of crucifixes, I guess...",
        f"{_EMOJI['leave']} Poof! {{mention}} is gone. Probably rage-quit after groundskeeper bugged on them or something.",
        f"{_EMOJI['leave']} {{mention}} saw the light. It was outside. Outside this challenge. They're happier now.",
        f"{_EMOJI['leave']} {{mention}} opened a Dupe door."
    ],
    "kick": [
        f"{_EMOJI['kick']} {{mention}} got kicked. Perhaps sold too many runs...",
        f"{_EMOJI['kick']} {{mention}} slipped on a nanner peel and fell out of bounds! Oh? The nanner peel was placed by an admin? Ohhhh, ok, gotcha.",
        f"{_EMOJI['kick']} An admin's mighty foot sent {{mention}} flying. A reminder that you shouldn't fly during the challenge. That's cheating."
    ],
    "ban": [
        f"{_EMOJI['ban']} {{mention}} got electrocuted. Not by Surge, though.",
        f"{_EMOJI['ban']} {{mention}} is now trapped out of next rooms with a groundskeeper.",
        f"{_EMOJI['ban']} {{mention}} got figured out. By the admin."
    ],
    "kick_bot": [
        f"{_EMOJI['app_leave']} Digital termination detected: Bot {{mention}} was kicked",
        f"{_EMOJI['app_leave']} Error 403: Bot {{mention}} was forcibly removed.",
        f"{_EMOJI['app_leave']} {{mention}} was disconnected by administrator action."
    ],
    "available": [
        f"{_EMOJI['available']} **{{name}}** is now available to participate in the challenge *({{available_count}}/8)*"
    ],
    "available_ping": [
        f"-# we have 8 people! <@&{ROLES['available']}>, go to <#{CHANNELS['ps_link']}> before someone leaves again"
    ],
    "unavailable": [
        f"{_EMOJI['unavailable']} **{{name}}** is no longer available *({{available_count}}/8)*"
    ],
    "unavailable_auto": [
        f"{_EMOJI['unavailable']} **{{name}}** was inactive for too long, so they're marked as unavailable *({{available_count}}/8)*"
    ],
    "join_vc": [
        f"{_EMOJI['join_vc']} **{{name}}** has joined the voice channel"
    ],
    "leave_vc": [
        f"{_EMOJI['leave_vc']} **{{name}}** has left the voice channel"
    ],
    "promotion": [
        f"{_EMOJI['promotion']} {{mention}} was promoted to **{{role}}**"
    ],
    "demotion": [
        f"{_EMOJI['demotion']} {{mention}} was demoted"
    ],
    "birthday": [
        f"{_EMOJI['birthday']} happy birthday, {{mention}}!!"
    ],
    "nuh_uh": [
        "https://cdn.discordapp.com/attachments/715528165132599337/1442162843452440777/nuh-uh-3d-thumbnail-url-7g84og.png?ex=69246e4f&is=69231ccf&hm=b1bf1bb44ee89017d8404d35a1b0812eef3c6dc29a870ef3a8fefaa96fc7353e&"
    ]
}

def message(dict_key: str, **kwargs) -> str:
    import random
    res = random.choice(_MESSAGES[dict_key])
    res = res.format(**kwargs)
    return res