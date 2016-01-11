# Zabbix-in-Telegram
Zabbix Notifications with graphs in Telegram

Join us in our **Telegram group** via this link: https://telegram.me/joinchat/AGnFigJ_NW75IGNnpOyjig

Rate on [share.zabbix.com](https://share.zabbix.com): https://share.zabbix.com/cat-notifications/zabbix-in-telegram

### Features
- [x] Graphs based on latest data are sent directly to your messenger
- [x] You can send them both in private and group chats
- [x] Saves chatid as a temporary file

### Configuration / Installation

**First of all**: You need to install the `requests` module for python, this is required for operation! </br>
                  To do so, enter `pip install requests` in your commandline!

 * Place `zbxtg.py` in your `AlertScriptsPath` directory, the path is set inside your zabbix_server.conf
 * Create `zbxtg_settings.py` with your settings and save them in the same directory as the script, see example for layout
  * Create a bot in Telegram and get API key
  * Create readonly user in Zabbix
  * Set proxy host:port in `zbxtg_settings.py` if you need an internet proxy
 * Add new media for Telegram in Zabbix web interface with these settings:
 
![](http://i.imgur.com/sjGjwo5.png) 
 
 * Send a message to your bot via Telegram, e.g. "/start"
  * If you are in group chat, just mention your bot, e.g. `@ZbxTgDevBot ping`
 * Create a new action like this:

<img src="http://i.imgur.com/ZNKtBUX.png" width="400px" height="340px">

 * Add the appropriate Media Type to your user
  * The username is CASE-SENSITIVE
  
![](http://i.imgur.com/doHpeOP.png)

#### Annotations
```
zbxtg;graphs -- enables attached graphs
zbxth;chat -- enables sending to group chats (default - set to 1-1 private chat)
zbxtg;graphs_period=10800 -- set graphs period (default - 3600 seconds)
zbxtg;itemid:{ITEM.ID1} -- define itemid (from trigger) for attach
zbxtg;title:{HOST.HOST} - {TRIGGER.NAME} -- graph title
zbxtg;debug -- enable debug mode, some logs and images will be saved in the tmp dir
```

You can use markdown in your action: https://core.telegram.org/bots/api#using-markdown

#### Debug

* You can use the following command to send a message from your command line: </br>
`./zbxtg.py "<username>" "<message>" "<message>"`
 * For `<username>` substitute your Telegram username, NOT that of your bot (case-sensitive)
 * For `<message>` just substitute something like "test"
 * You can omit the `"`, these are optional

---

![](http://i.imgur.com/1T4aHuf.png)
![](http://i.imgur.com/5ZPyvoe.png)

### Known issues

#### MEDIA_CAPTION_TOO_LONG
If you see this error, it means that you rich the limit of caption with 200 symbols in it (Telegram API's limitaion).
Such captions will be automatically cut to 200 symbols.

-
