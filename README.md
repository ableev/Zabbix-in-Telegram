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

 * Put `zbxtg.py` in your `AlertScriptsPath` directory, the path is set inside your zabbix_server.conf
 * Put `zbxtg_group.py` in the same location if you want to send messages to the group chat
 * Create `zbxtg_settings.py` with your settings and save them in the same directory as the script, see example for layout
  * Create a bot in Telegram and get API key
  * Create readonly user in Zabbix (for getting graphs images from zabbix)
  * Set proxy host:port in `zbxtg_settings.py` if you need an internet proxy
 * Add new media for Telegram in Zabbix web interface with these settings:
 
<img src="https://i.imgur.com/Ytrbe4S.png" width="400px">
 * If you use Zabbix 3.0, add following script parameters:
```
{ALERT.SENDTO}
{ALERT.SUBJECT}
{ALERT.MESSAGE}
```
<img src="http://i.imgur.com/pugmk6w.png" width="400px">
 * Add another one if you want to send messages to the group
 
<img src="http://i.imgur.com/OTq4aQd.png" width="400px">
 
 * Send a message to your bot via Telegram, e.g. "/start"
  * If you are in group chat, just mention your bot, e.g. `@ZbxTgDevBot ping`
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
  * Group chats don't have URLs, so you need to put group's name in media type

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
zbxtg;title:{HOST.HOST} - {TRIGGER.NAME} -- graph title
zbxtg;debug -- enable debug mode, some logs and images will be saved in the tmp dir (temporary doesn't affect python version)
```

You can use markdown in your action: https://core.telegram.org/bots/api#using-markdown

#### Debug

* You can use the following command to send a message from your command line: </br>
`./zbxtg.py "<username>" "<message_subject>" "<message_body>"`
 * For `<username>` substitute your Telegram username, NOT that of your bot (case-sensitive)
 * For `<message_subject>` and `<message_body>` just substitute something like "test" "test" (for Telegram it's doesn't matter between subject and body
 * You can omit the `"`, these are optional

---

![](http://i.imgur.com/1T4aHuf.png)
![](http://i.imgur.com/5ZPyvoe.png)

### Known issues

#### MEDIA_CAPTION_TOO_LONG
If you see this error, it means that you rich the limit of caption with 200 symbols in it (Telegram API's limitaion).
Such captions will be automatically cut to 200 symbols.

#### Zabbix don't send messages
If you successfully sent messages form console directly, you may need to check user rights to /tmp/zbxtg folder. User zabbix need to write access here:

```chown -R zabbix:zabbix /tmp/zbxtg```

Or just delete this folder, zabbix will create this folder with first alert.

-
