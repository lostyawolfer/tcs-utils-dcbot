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




roles = {
    "admins": [
        1427016174444613804, # the man behind the challenge
        1433828741548740781  # moderator
    ],
    "new_people": [
        1445189559200776302, # cat: activity
        1442132238660796416, # not available
        1445190367006818324, # cat: common
        1433872100837425193, # newbie
        1427076669264498820, # person
        1445134463263707156, # cat: badges
        1445191573305425930, # none
        1445191426920153159, # cat: misc
        1445191748010770493, # none
    ],
    "role_check": [
        1445189559200776302, # cat: activity
        1445190367006818324, # cat: common
        1427076669264498820, # person
        1445134463263707156, # cat: badges
        1445191426920153159, # cat: misc
    ],
    "category:badges": {
        "none": 1445191573305425930,
        "other": [1443767416579559618, 1440647536397385800, 1443251279257407619, 1443251500481646784,
                  1443264316236234862, 1427674706076635169, 1445115775261081681, 1439783495248384162]
    },
    "category:misc": {
        "none":  1445191748010770493,
        "other": [1442212989351628810, 1439783181199872120, 1439831984695148544, 1429256434323034235,
                  1442596622013038704, 1442596750576717905, 1442623000452005948]
    },
    "bot": 1442086763161194597,
    "leader": 1426973394099896507,
    "available": 1434629510031999269,
    "available_leader": 1434629548347232326,
    "not_available": 1442132238660796416,
    "in_vc": 1427076261586669688,
    "in_vc_leader": 1427076452477702191,
    "available_not_in_vc": 1442132263071645779,
    "in_vc_2": 1444027810594295908,
    "in_vc_2_leader": 1444027828898238605,
    "available_not_in_vc_2": 1444027740352155688,
    "birthday": 1439339439762444552,
    "inactive": 1434659281822679232,
    "newbie": 1433872100837425193,
    "warn_1": 1442596622013038704,
    "warn_2": 1442596750576717905,
    "warn_3": 1442623000452005948,
    "mod": 1433828741548740781,

    "spoiler": 1451675068114669740,


    "completion_server_star_star": 1454594165857063004,
    "completion_server_base_star": 1453450000297365576,

    "completion_tcs+": 1454596340930838751,
    "completion_tcs": 1440647536397385800,
    "completion_has++": 1454596424120402061,
    "completion_has+": 1454596427077652671,
    "completion_has": 1454596429782847772,
    "completion_nn++": 1454595271056035861,
    "completion_nn+": 1454595144841171164,
    "completion_nn": 1443767416579559618,
    "completion_gor+": 1453876081294573729,
    "completion_gor": 1443251279257407619,
    "completion_nnd+": 1454594591360811068,
    "completion_nnd": 1454594411483758592,
    "completion_rmt": 1454812063435194490,
    "completion_pdo+": 1443264316236234862,
    "completion_pdo": 1443251500481646784,

    "completion_tbs": 1427674706076635169,
    "completion_ahp": 1445115775261081681,
    "completion_star": 1439783495248384162,
}

channels = {
    "vc": 1426972811293098015,
    "vc2": 1444027467290513448,
    "chat": 1426972811293098014,
    "availability": 1434653852367585300,
    "availability_message": 1434654321886363658,
    "availability_reaction": 1439620553572089900,
    "ps_link": 1426974154556702720,
    "best_runs": 1427066908812906526,
    "mod_chat": 1442499917728976917,
    "leader_chat": 1453699078977224876,
    "logs_channel": 1453370470584815697,
    "spoiler": 1451673464359358465
}


emoji = {
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
    "join_vc_2": "<:join_vc_2:1444102928880242709>",
    "leave_vc_2": "<:leave_vc_2:1444327229210497237>",
    "promotion": "<:promotion:1442087863347974294>",
    "demotion": "<:demotion:1442087886391607376>",
    "birthday": "",
    "leader": "<:leader:1436531052670619791>", # ON THE SERVER
    "death": "<:death:1436531054704852993>", # ON THE SERVER
    "disconnect": "<:disconnected:1439792812165038080>", # ON THE SERVER
    "blank": "<:blank:1436531505831612456>", # ON THE SERVER
    "tcs": "<:this_challenge_sucks:1440645344252792922>", # ON THE SERVER
    "gor": "<:group_of_rushers:1443250418418188402>", # ON THE SERVER
    "pdo": "<:professional_door_opener:1443719522908504215>", # ON THE SERVER
    "nn": "<:neverending_night:1443768885097529394>", # ON THE SERVER
    "edit": "<:edit:1444529076516688064>",
    "newbie": "<:upvote:1434612815062237195>", # ON THE SERVER
    "inactive": "🛌",
    "inactive_revoke": "🏆",

    "knife": "🔪",
    "hug": "🤗",
    "kiss": "💋",
    "high_five": "✋",
    "handshake": "🤝",
    "fire": "🔥",
    "punch": "👊",
    "slap": "👋",
    "pat": "🫳",
    "touch": "👉",

    '0': '<:0_:1444462399632445473>',
    '1': '<:1_:1444462401075548353>',
    '2': '<:2_:1444462402312736962>',
    '3': '<:3_:1444462403902505134>',
    '4': '<:4_:1444462405286629618>',
    '5': '<:5_:1444462406779801734>',
    '6': '<:6_:1444462407962329088>',
    '7': '<:7_:1444462409342255204>',
    '8': '<:8_:1444462410584035388>',
    '9': '<:9_:1444462412559290492>',

    '0b': '<:0b:1448879492884861040>',
    '0g': '<:0g:1448879494063587509>',
    '0p': '<:0p:1448879495393054891>',
    '1b': '<:1b:1448879496374779945>',
    '1g': '<:1g:1448879497838334122>',
    '1p': '<:1p:1448879499184705679>',
    '2b': '<:2b:1448879500711690512>',
    '2g': '<:2g:1448879502422835452>',
    '2p': '<:2p:1448879504490762390>',
    '3b': '<:3b:1448879506612813926>',
    '3g': '<:3g:1448879507753668638>',
    '3p': '<:3p:1448879508827672656>',
    '4b': '<:4b:1448879509934964942>',
    '4g': '<:4g:1448879511205707796>',
    '4p': '<:4p:1448879512350887996>',
    '5b': '<:5b:1448879513755979848>',
    '5g': '<:5g:1448879515206942771>',
    '5p': '<:5p:1448879516561702913>',
    '6b': '<:6b:1448879517950017616>',
    '6g': '<:6g:1448879519942316132>',
    '6p': '<:6p:1448879521708376237>',
    '7b': '<:7b:1448879523016872042>',
    '7g': '<:7g:1448879524350787775>',
    '7p': '<:7p:1448879526485426336>',
    '8b': '<:8b:1448879527634931843>',
    '8g': '<:8g:1448879528825847951>',
    '8p': '<:8p:1448879529878618213>',
    '9b': '<:9b:1448879531162210413>',
    '9g': '<:9g:1448879532508451019>',
    '9p': '<:9p:1448879535033421935>'
}

_messages = {
    "join": [
        f"{emoji['join']} {{mention}}, are you ready for the pain?",
        f"{emoji['join']} {{mention}} should now prepare to die in the backdoor a hundred times",
        f"{emoji['join']} heya, {{mention}}, welcome! mind you, this entire server is a safespot",
        f"{emoji['join']} it's time for {{mention}} to acknowledge the possibility of pain and seizure",
        f"{emoji['join']} {{mention}} just joined! quick, everyone look like we know what we're doing!",
        f"{emoji['join']} uhh, hey, {{mention}}, you have any sanity? We're running low, could we please borrow some?",
        f"{emoji['join']} let's hope {{mention}} has it all Figured out"
    ],
    "join_bot": [
        f"{emoji['app_join']} someone added a clanker who's called {{mention}}",
        f"{emoji['app_join']} i think {{mention}} just hacked us",
        f"{emoji['app_join']} {{mention}} computed its way in"
    ],
    "leave": [
        f"{emoji['leave']} {{mention}} couldn't handle The Backdoor any longer...",
        f"{emoji['leave']} {{mention}} disconnected. Please check your internet connection and try again. (Error Code: 277)",
        f"{emoji['leave']} {{mention}} ran out of crucifixes, I guess...",
        f"{emoji['leave']} {{mention}} decided to ragequit",
        f"{emoji['leave']} {{mention}} saw the light. it was outside. Outside this challenge. they're happier now"
    ],
    "kick": [
        f"{emoji['kick']} {{mention}} was kicked from this experience (Error Code: 267)",
        f"{emoji['kick']} {{mention}} slipped on a nanner peel and fell out of bounds! what? the nanner peel was placed by an admin? ohhhh, ok, gotcha",
        f"{emoji['kick']} an admin's mighty foot sent {{mention}} flying. a reminder that you shouldn't fly during the challenge, that's cheating"
    ],
    "ban": [
        f"{emoji['ban']} {{mention}} got electrocuted. not by surge, though",
        f"{emoji['ban']} {{mention}} was kicked from this experience: You have been permanently blacklisted from This Challenge Sucks (Error Code: 267)",
        f"{emoji['ban']} {{mention}} got figured out. by an admin."
    ],
    "kick_bot": [
        f"{emoji['app_leave']} digital termination detected: Bot {{mention}} was kicked",
        f"{emoji['app_leave']} error 403: bot {{mention}} was forcibly removed",
        f"{emoji['app_leave']} {{mention}} was disconnected by administrator action"
    ],
    "spoiler_add": [f"{emoji['join']} {{mention}} joined the spoilers channel"],
    "spoiler_remove": [f"{emoji['kick']} {{mention}} is no longer in the spoilers channel"],
    "available": [
        f"{emoji['available']} **{{name}}** is now available {{available_count}}"
    ],
    "available_ping": [
        f"{emoji['available']} **{{name}}** is now available {{available_count}} *<@&{roles['available']}>*"
    ],
    "unavailable": [
        f"{emoji['unavailable']} **{{name}}** is no longer available {{available_count}}"
    ],
    "unavailable_ping": [
        f"{emoji['unavailable']} **{{name}}** is no longer available {{available_count}} *(we still have 8 tho)*"
    ],
    "unavailable_auto": [
        f"{emoji['unavailable']} **{{name}}** seemed inactive, so they were marked unavailable by mods {{available_count}}"
    ],
    "join_vc": [
        f"{emoji['join_vc']} **{{name}}** joined the voice channel {{count}}"
    ],
    "leave_vc": [
        f"{emoji['leave_vc']} **{{name}}** left the voice channel {{count}}"
    ],
    "join_vc_2": [
        f"{emoji['join_vc_2']} **{{name}}** joined the second voice channel {{count}}"
    ],
    "leave_vc_2": [
        f"{emoji['leave_vc']} **{{name}}** left the second voice channel {{count}}"
    ],
    "promotion": [
        f"{emoji['promotion']} {{mention}} is now a moderator!"
    ],
    "demotion": [
        f"{emoji['demotion']} {{mention}} was demoted..."
    ],
    "new_leader": [
        f"{emoji['promotion']} {{mention}} is now a leader!"
    ],
    "leader_removed": [
        f"{emoji['demotion']} {{mention}} is no longer a leader..."
    ],
    "promotion_welcome": [
        f"{emoji['promotion']} welcome, {{mention}}. hope this chat is cozy!"
    ],
    "demotion_goodbye": [
        f"{emoji['demotion']} {{mention}} wasn't worthy of being a mod, it seems. well, off you go"
    ],
    "name_change": [
        f"{emoji['edit']} {{mention}}'s name was changed from **{{old_name}}** to **{{new_name}}**"
    ],
    "birthday": [
        f"{emoji['birthday']} happy birthday, {{mention}}!!"
    ],
    "newbie": [
        f"{emoji['newbie']} {{mention}} is not a newbie anymore!! please applaud!!"
    ],
    "inactive": [
        f"{emoji['inactive']} {{mention}} seemed to be inactive... hey, if you have reasons, tell us! just, if you keep the silence going without reason, you might as well leave..."
    ],
    "inactive_revoke": [
        f"{emoji['inactive_revoke']} {{mention}} is no longer considered inactive!"
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
    "wip": [
        "https://media.discordapp.net/attachments/715528165132599337/1450116115190513795/pug-dog-constructor-safety-helmet-yellow-black-work-progress-sign-wooden-pole-isolated-white-background-92995840.png?ex=69415d5f&is=69400bdf&hm=95a383c0b59ff99f483df65c5ab5d0b44e8628c786b847e75246b557447eb0fb&=&format=webp&quality=lossless"
    ],
    "channel_lock": [
        "🔒 channel was locked"
    ],
    "channel_unlock": [
        "🔓 channel was unlocked"
    ],

    "completion_tbs": [f"🏅 {{mention}} got **this badge sucks**"],
    "completion_ahp": [f"🏅 {{mention}} got **a hard place**"],
    "completion_star": [f"🏅 {{mention}} got **the completionist star**"],
    "completion_dv": [f"⭐ {{mention}} beat **doorsverse**"],
    "completion_ch_tcs": [f"🏆 {{mention}} beat **this challenge sucks**"],
    "completion_ch_gor": [f"🏆 {{mention}} beat **group of rushers**"],
    "completion_ch_pdo": [f"🏆 {{mention}} beat **professional doors opener**"],
    "completion_ch_nn": [f"🏆 {{mention}} beat **neverending night**"],

    "rp_kill": [f"{emoji['knife']} {{author}} brutally murdered {{target}}"],
    "rp_hug": [f"{emoji['hug']} {{author}} hugged {{target}}"],
    "rp_kiss": [f"{emoji['kiss']} {{author}} kissed {{target}}"],
    "rp_high_five": [f"{emoji['high_five']} {{author}} gave a high five to {{target}}"],
    "rp_handshake": [f"{emoji['handshake']} {{author}} shook hands with {{target}}"],
    "rp_burn": [f"{emoji['fire']} {{author}} set {{target}} on fire"],
    "rp_punch": [f"{emoji['punch']} {{author}} punched {{target}}"],
    "rp_slap": [f"{emoji['slap']} {{author}} slapped {{target}}"],
    "rp_pat": [f"{emoji['pat']} {{author}} patted {{target}} on the head"],
    "rp_touch": [f"{emoji['touch']} {{author}} touched {{target}}"],
}

def message(dict_key: str, **kwargs) -> str:
    import random
    res = random.choice(_messages[dict_key])
    res = res.format(**kwargs)
    return res