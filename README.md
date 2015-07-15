# Zabbix-in-Telegram
Zabbix Notifications with graphs in Telegram

### Features
- [x] graphs based on latest data are sent directly to your messenger
- [x] you can send them both in private and group chats
- [x] saves chatid as a temporary file

### Configuration
 * place `zbxtg.sh` to `AlertScriptsPath` directory
 * create `tg_vars.cfg` with your settings and save them
  * create bot in Telegram and get API key
  * create readonly user in Zabbix
  * set proxy host:port in curl exec
 * add new media for Telegram in Zabbix web interface
 * send something to your bot, e.g. "/start"
  * if you are in group chat, just mention it
 * create new action like this:

<img src="http://i.imgur.com/ZNKtBUX.png" width="300px">
#### Annotations
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

### Known issues

#### grep
If your zabbix running on FreeBSD, script might not be working due to version of `grep`.
Script uses `--perl-regexp` option from [GNU grep](http://git.sv.gnu.org/cgit/grep.git):
```
       -P, --perl-regexp
              Interpret PATTERN as a Perl regular expression.  This is highly experimental and grep -P may warn of unimplemented features.
```
`BSD grep` in FreeBSD or Mac OS doesn't support that option.
