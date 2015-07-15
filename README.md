# Zabbix-in-Telegram
Zabbix Notifications with graphs in Telegram

Features:
- [x] graphs based on latest data are sent directly to your messenger
- [x] you can send them both in private and group chats
- [x] saves chatid as a temporary file

Settings:
 * place zbxtg.sh to AlertScriptsPath directory
 * add new media for Telegram in Zabbix web interface
 * create new action like this:

![](http://i.imgur.com/ZNKtBUX.png =500x)
```
zbxtg;graphs -- enables attached graphs
zbxth;chat -- enables sending to group chats (default - set to 1-1 private chat)
zbxtg;graphs_period=10800 -- set graphs period (default - 3600 seconds)
zbxtg;itemid:{ITEM.ID1} -- define itemid (from trigger) for attach
zbxtg;title:{HOST.HOST} - {TRIGGER.NAME} -- graph title
```

---

![](http://i.imgur.com/1T4aHuf.png)
![](http://i.imgur.com/5ZPyvoe.png)
