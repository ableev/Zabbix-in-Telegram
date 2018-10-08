# Zabbix-in-Telegram
Zabbix Notifications with graphs in Telegram

Join us in our **Telegram group** via this link: https://t.me/ZbxTg

Subscribe to our channel: https://t.me/Zabbix_in_Telegram

Rate on [share.zabbix.com](https://share.zabbix.com): https://share.zabbix.com/cat-notifications/zabbix-in-telegram

### Features
- [x] Graphs based on latest data are sent directly to your messenger
- [x] You can send messages both in private and group/supergroup chats
- [x] Channels support (only public, but you can do it for private as well with dirty hack)
- [x] Saves chatid as a temporary file
- [x] Simple markdown and HTML are supported
- [x] Emoji (you can use emoji instead of severity, see [the wiki article](https://github.com/ableev/Zabbix-in-Telegram/wiki/Trigger-severity-as-Emoji)) (zabbix doesn't support utf8mb4 encoding yet)
- [x] Location map

### TODOs
- Simple zabbix's management via bot's commands – in dev state
- Ability to send complex graph or part of screen


### Configuration / Installation

**READ WIKI IF YOU HAVE PROBLEM WITH SOMETHING**: https://github.com/ableev/Zabbix-in-Telegram/wiki

**First of all**: You need to install the appropriate modules for python, this is required for operation! </br>
                  To do so, enter `pip install -r requirements.txt` in your commandline!

 * Put `zbxtg.py` in your `AlertScriptsPath` directory, the path is set inside your `zabbix_server.conf`
 * Put `zbxtg_group.py` in the same location if you want to send messages to the group chat (if you are using Zabbix 2.x version)
 * Create `zbxtg_settings.py` (copy it from `zbxtg_settings.example.py`) with your settings and save them in the same directory as the script, see example for layout
  * Create a bot in Telegram and get API key: https://core.telegram.org/bots#creating-a-new-bot
  * Create readonly user in Zabbix web interface (for getting graphs from zabbix)
  * Set proxy host:port in `zbxtg_settings.py` if you need an internet proxy (socks5 supported as well, the wiki will help you)
 * Add new media for Telegram in Zabbix web interface with these settings:
 
<img src="https://i.imgur.com/Ytrbe4S.png" width="400px">

 * Add another one if you want to send messages to the group
 
<img src="http://i.imgur.com/OTq4aQd.png" width="400px">

 * **Note that Zabbix 3.0 has different settings for that step, see it there**: https://github.com/ableev/Zabbix-in-Telegram/wiki/Working-with-Zabbix-3.0
 * Send a message to your bot via Telegram, e.g. "/start"
  * If you are in a group chat, start a conversation with your bot: `/start@ZbxTgDevBot`
 * Create a new action like this:
```
Last value: {ITEM.LASTVALUE1} ({TIME})
zbxtg;graphs
zbxtg;graphs_period=10800
zbxtg;itemid:{ITEM.ID1}
zbxtg;title:{HOST.HOST} - {TRIGGER.NAME}
```

<img src="https://i.imgur.com/ZNKtBUX.png" width="400px">

 * Add the appropriate Media Type to your user
  * The username is **CASE-SENSITIVE**
  * If you don't have a username, you can use your chatid directly (and you need to google how to get it)
  * Group chats don't have URLs, so you need to put group's name in media type
  * Messages for channels should be sent as for private chats (simply add bot to your channel first and use channel's username as if it was a real user)

  * Private:

  <img src="https://i.imgur.com/GVDlTU5.png" width="400px">

  * Group:

  <img src="https://i.imgur.com/TgcCqDf.png" width="400px">

#### Annotations
```
zbxtg;graphs -- enables attached graphs
zbxtg;graphs_period=10800 -- set graphs period (default - 3600 seconds)
zbxtg;graphs_width=700 -- set graphs width (default - 900px)
zbxtg;graphs_height=300 -- set graphs height (default - 300px)
zbxtg;itemid:{ITEM.ID1} -- define itemid (from trigger) for attach
zbxtg;itemid:{ITEM.ID1},{ITEM.ID2},{ITEM.ID3} -- same, but if you want to send two or more graphs, use complex trigger
zbxtg;title:{HOST.HOST} - {TRIGGER.NAME} -- graph's title
zbxtg;debug -- enables debug mode, some logs and images will be saved in the tmp dir (temporary doesn't affect python version)
zbxtg;channel -- enables sending to channels
zbxtg;to:username1,username2,username3 -- now you don't need to create dedicated profiles and add media for them, use this option in action to send messages to those user(s)
zbxtg;to_group:Group Name One,Group Name Two -- the same but for groups
```

You can use markdown or html formatting in your action: https://core.telegram.org/bots/api#markdown-style + https://core.telegram.org/bots/api#html-style. 

#### Debug

* You can use the following command to send a message from your command line: </br>
`./zbxtg.py "@username" "first part of a message" "second part of a message" --debug`
 * For `@username` substitute your Telegram username, **NOT that of your bot** (case-sensitive) OR chatid
 * For `first part of a message` and `second part of a message` just substitute something like "test" "test" (for Telegram it's doesn't matter between subject and body)
 * You can skip the `"` if it's one word for every parameter, these are optional

---

![](http://i.imgur.com/1T4aHuf.png)
![](http://i.imgur.com/5ZPyvoe.png)

### Known issues

#### MEDIA_CAPTION_TOO_LONG
If you see this error, it means that you rich the limit of caption with 200 symbols in it (Telegram API's limitaion).
Such captions will be automatically cut to 200 symbols.

#### Zabbix 3.0 
https://github.com/ableev/Zabbix-in-Telegram/wiki/Working-with-Zabbix-3.0
