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
    "inactive": 1434659281822679232,
    "warn_1": 1442596622013038704,
    "warn_2": 1442596750576717905,
    "warn_3": 1442623000452005948,
    "mod": 1433828741548740781
}

CHANNELS = {
    "vc": 1426972811293098015,
    "chat": 1426972811293098014,
    "availability": 1434653852367585300,
    "availability_message": 1434654321886363658,
    "availability_reaction": 1439620553572089900,
    "ps_link": 1426974154556702720,
    "best_runs": 1427066908812906526
}


EMOJI = {
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
    "birthday": "",
    "leader": "<:leader:1436531052670619791>", # ON THE SERVER
    "death": "<:death:1436531054704852993>", # ON THE SERVER
    "disconnect": "<:disconnected:1439792812165038080>", # ON THE SERVER
    "blank": "<:blank:1436531505831612456>", # ON THE SERVER
    "tcs": "<:this_challenge_sucks:1440645344252792922>", # ON THE SERVER
    "gor": "<:group_of_rushers:1443250418418188402>", # ON THE SERVER
    "pdo": "" # ON THE SERVER
}

_MESSAGES = {
    "join": [
        f"{EMOJI['join']} Is {{mention}} really ready for this? After all, not many people have the patience to wait for 8 players to join.",
        f"{EMOJI['join']} {{mention}} should now prepare to die in the backdoor a hundred times as part of join process.",
        f"{EMOJI['join']} Don't worry {{mention}}, the lights flicker only *most* of the time.",
        f"{EMOJI['join']} It's time for {{mention}} to acknowledge the possibility of pain and seizure.",
        f"{EMOJI['join']} {{mention}} just joined! Quick, everyone look like we know what we're doing!",
        f"{EMOJI['join']} Uhh, hey, {{mention}}, you have any sanity? We're running low, could we please borrow some?",
        f"{EMOJI['join']} Let's hope {{mention}} has it all Figured out."
    ],
    "join_bot": [
        f"{EMOJI['app_join']} New digital entity alert! {{mention}} has manifested.",
        f"{EMOJI['app_join']} Beep boop! {{mention}} just computed its way in.",
        f"{EMOJI['app_join']} System update detected: Bot {{mention}} has joined the network."
    ],
    "leave": [
        f"{EMOJI['leave']} {{mention}} couldn't handle the Backdoor any longer...",
        f"{EMOJI['leave']} {{mention}} disconnected. Please check your internet connection and try again. (Error Code: 277)",
        f"{EMOJI['leave']} {{mention}} ran out of crucifixes, I guess...",
        f"{EMOJI['leave']} Poof! {{mention}} is gone. Probably rage-quit after groundskeeper bugged on them or something.",
        f"{EMOJI['leave']} {{mention}} saw the light. It was outside. Outside this challenge. They're happier now.",
        f"{EMOJI['leave']} {{mention}} opened a Dupe door."
    ],
    "kick": [
        f"{EMOJI['kick']} {{mention}} got kicked. Perhaps sold too many runs...",
        f"{EMOJI['kick']} {{mention}} slipped on a nanner peel and fell out of bounds! Oh? The nanner peel was placed by an admin? Ohhhh, ok, gotcha.",
        f"{EMOJI['kick']} An admin's mighty foot sent {{mention}} flying. A reminder that you shouldn't fly during the challenge. That's cheating."
    ],
    "ban": [
        f"{EMOJI['ban']} {{mention}} got electrocuted. Not by Surge, though.",
        f"{EMOJI['ban']} {{mention}} is now trapped out of next rooms with a groundskeeper.",
        f"{EMOJI['ban']} {{mention}} got figured out. By the admin."
    ],
    "kick_bot": [
        f"{EMOJI['app_leave']} Digital termination detected: Bot {{mention}} was kicked",
        f"{EMOJI['app_leave']} Error 403: Bot {{mention}} was forcibly removed.",
        f"{EMOJI['app_leave']} {{mention}} was disconnected by administrator action."
    ],
    "available": [
        f"{EMOJI['available']} **{{name}}** is now available to participate in the challenge *({{available_count}}/8)*"
    ],
    "available_ping": [
        f"-# we have 8 people! <@&{ROLES['available']}>, go to <#{CHANNELS['ps_link']}> before someone leaves again"
    ],
    "unavailable": [
        f"{EMOJI['unavailable']} **{{name}}** is no longer available *({{available_count}}/8)*"
    ],
    "unavailable_auto": [
        f"{EMOJI['unavailable']} **{{name}}** was inactive for too long, so they're marked as unavailable *({{available_count}}/8)*"
    ],
    "join_vc": [
        f"{EMOJI['join_vc']} **{{name}}** joined the voice channel *({{count}})*"
    ],
    "leave_vc": [
        f"{EMOJI['leave_vc']} **{{name}}** left the voice channel *({{count}})*"
    ],
    "promotion": [
        f"{EMOJI['promotion']} {{mention}} was promoted to **{{role}}**"
    ],
    "demotion": [
        f"{EMOJI['demotion']} {{mention}} was demoted"
    ],
    "birthday": [
        f"{EMOJI['birthday']} happy birthday, {{mention}}!!"
    ],
    "nuh_uh": [
        "https://cdn.discordapp.com/attachments/715528165132599337/1442162843452440777/nuh-uh-3d-thumbnail-url-7g84og.png?ex=69246e4f&is=69231ccf&hm=b1bf1bb44ee89017d8404d35a1b0812eef3c6dc29a870ef3a8fefaa96fc7353e&",
        #"https://cdn.discordapp.com/attachments/715528165132599337/1442288061550563429/image.png?ex=6924e2ee&is=6923916e&hm=a8cf353e9b11473ae21a33cb7615f2f0369e2aa47bc6649b87798ccad07b5edd&",
        #"https://cdn.discordapp.com/attachments/715528165132599337/1442289370970460351/the-sybau-image-without-text-v0-uffld2n8mj1f1.png?ex=6924e426&is=692392a6&hm=857fc631938e0ed5a2b9fd79e3765f4598d9981b1c764505979bec11d200ab7c&",
        #"https://cdn.discordapp.com/attachments/715528165132599337/1442290208904183838/image.png?ex=6924e4ee&is=6923936e&hm=c3bcf903940e91605f0ed2f8bf399bdd43007de6fb2dc682693916345c7c65eb&"
    ],
    "bot_doesnt_have_perms": [
        "https://cdn.discordapp.com/attachments/715528165132599337/1442288380766457977/artworks-000519533403-ovb003-t1080x1080.png?ex=6924e33a&is=692391ba&hm=1ce891ca81be59241658390d96198e442226d78d4b4c7e708a28f5355f6ac5bb&"
    ],
    "channel_lock": [
        "🔒 channel was locked"
    ],
    "channel_unlock": [
        "🔓 channel was unlocked"
    ]
}

def message(dict_key: str, **kwargs) -> str:
    import random
    res = random.choice(_MESSAGES[dict_key])
    res = res.format(**kwargs)
    return res