# Zabbix-in-Telegram
Zabbix Notifications with graphs in Telegram

Join us on **Telegram group**: https://telegram.me/joinchat/AGnFigJ_NW75IGNnpOyjig

### Features
- [x] graphs based on latest data are sent directly to your messenger
- [x] you can send them both in private and group chats
- [x] saves chatid as a temporary file

### Configuration

**First of all**: you need to install `requests` module for python: `pip install requests`

 * Place `zbxtg.py` in your `AlertScriptsPath` directory, the path is set inside your zabbix_server.conf
 * Create `zbxtg_settings.py` with your settings and save them in the same directory as the script, see example for layout
  * Create a bot in Telegram and get API key
  * Create readonly user in Zabbix
  * Set proxy host:port in `zbxtg_settings.py` if you need an internet proxy
 * Add new media for Telegram in Zabbix web interface with these settings:
 
![](http://i.imgur.com/ajQtVAq.png) 
 
 * Send a message to your bot via Telegram, e.g. "/start"
  * If you are in group chat, just mention your bot, e.g. `@ZbxTgDevBot ping`
 * Create new action like this:

<img src="http://i.imgur.com/ZNKtBUX.png" width="300px">
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

---

![](http://i.imgur.com/1T4aHuf.png)
![](http://i.imgur.com/5ZPyvoe.png)

### Known issues

#### MEDIA_CAPTION_TOO_LONG
If you see this error, it means that you rich the limit of caption with 200 symbols in it (Telegram API's limitaion).
Such captions will be automatically cut to 200 symbols.

-
