# Zabbix-in-Telegram

Zabbix notifications with graphs, delivered to Telegram.

Join our **Telegram group**: https://t.me/ZbxTg

Subscribe to our channel: https://t.me/Zabbix_in_Telegram

Rate us on [share.zabbix.com](https://share.zabbix.com): https://share.zabbix.com/cat-notifications/zabbix-in-telegram

### Features
- [x] Graphs based on the latest data are sent directly to your messenger
- [x] Send messages to private chats as well as group/supergroup chats
- [x] Channel support (public channels only; private channels are possible with a workaround)
- [x] Chat IDs are cached in a local file
- [x] Basic Markdown and HTML formatting
- [x] Emoji instead of severity text (see [the wiki article](https://github.com/ableev/Zabbix-in-Telegram/wiki/Trigger-severity-as-Emoji); Zabbix doesn't support utf8mb4 encoding yet)
- [x] Location map support

### TODOs
- Simple Zabbix management via bot commands -- in development (see `ZbxTgDaemon.py`, experimental)
- Ability to send a complex graph or part of a screen

### Requirements

- Python 3.9+
- Zabbix 4.0+ (this version targets Zabbix 7.0 as the primary release; see [Known issues](#known-issues) for older versions)

### Configuration / Installation

**See the wiki if you run into trouble**: https://github.com/ableev/Zabbix-in-Telegram/wiki

**First**, install the required Python packages:
```
pip install -r requirements.txt
```

* Copy `zbxtg.py` and the `zbxtg_lib/` directory into your `AlertScriptsPath` directory (the path is set in `zabbix_server.conf`). They must stay together -- `zbxtg.py` is a thin entry point that imports the rest of the code from `zbxtg_lib/`.
* Also copy `zbxtg_group.py` into the same location if you want to send messages to group chats (it's a symlink to `zbxtg.py`; Zabbix 2.x only -- on modern Zabbix just use the `group` directive/media setting instead).
* Create `zbxtg_settings.yaml` (copy it from `zbxtg_settings.example.yaml`) in the same directory as the script, and fill in your settings -- see the example file for the full, documented layout.
  * Create a bot in Telegram and get its API token: https://core.telegram.org/bots#creating-a-new-bot
  * Create a read-only user in the Zabbix web interface (used to fetch graph images -- see [Known issues](#known-issues) for why this needs a web login rather than just the API)
  * Set `zabbix.proxy` / `telegram.proxy` in `zbxtg_settings.yaml` if you're behind an internet proxy (SOCKS5 is supported too; see the comments in the example file)

  > Upgrading from an older release? A legacy `zbxtg_settings.py` next to the script is still auto-detected as a fallback, but support for it will be removed in a future release -- please migrate to the YAML format.

* Add a new Media type for Telegram in the Zabbix web interface with these settings:

<img src="https://i.imgur.com/Ytrbe4S.png" width="400px">

* Add another Media type if you also want to send messages to a group:

<img src="http://i.imgur.com/OTq4aQd.png" width="400px">

* **Zabbix 3.0 and later use different Media type settings** -- see: https://github.com/ableev/Zabbix-in-Telegram/wiki/Working-with-Zabbix-3.0
* Send a message to your bot in Telegram, e.g. `/start`
  * In a group chat, start the conversation with your bot instead: `/start@ZbxTgDevBot`
* Create a new action like this:
```
Last value: {ITEM.LASTVALUE1} ({TIME})
zbxtg;graphs
zbxtg;graphs_period=10800
zbxtg;itemid:{ITEM.ID1}
zbxtg;title:{HOST.HOST} - {TRIGGER.NAME}
```

<img src="https://i.imgur.com/ZNKtBUX.png" width="400px">

* Add the appropriate Media type to your user
  * The username is **case-sensitive**
  * If you don't have a username, you can use your chat ID directly (search online for how to find it)
  * Group chats don't have URLs, so put the group's name in the Media type instead
  * Messages to channels are configured the same way as private chats -- add the bot to your channel first, then use the channel's username as if it were a regular user

  * Private:

  <img src="https://i.imgur.com/GVDlTU5.png" width="400px">

  * Group:

  <img src="https://i.imgur.com/TgcCqDf.png" width="400px">

#### Annotations
```
zbxtg;graphs -- enables attached graphs
zbxtg;graphs_period=10800 -- sets the graph period (default: 3600 seconds)
zbxtg;graphs_width=700 -- sets the graph width (default: 900px)
zbxtg;graphs_height=300 -- sets the graph height (default: 300px)
zbxtg;itemid:{ITEM.ID1} -- attaches a graph for this itemid (from the trigger)
zbxtg;itemid:{ITEM.ID1},{ITEM.ID2},{ITEM.ID3} -- same, but for two or more graphs, use a complex trigger
zbxtg;title:{HOST.HOST} - {TRIGGER.NAME} -- sets the graph's title
zbxtg;debug -- enables debug mode; some logs and images are saved to the tmp dir
zbxtg;channel -- sends the message to a channel
zbxtg;to:username1,username2,username3 -- send to these user(s) directly, without creating dedicated Media types for them
zbxtg;to_group:Group Name One,Group Name Two -- same, but for groups
```

You can use Markdown or HTML formatting in your action: https://core.telegram.org/bots/api#markdown-style + https://core.telegram.org/bots/api#html-style.

#### Debug

* Send a message from the command line to test your setup:
```
./zbxtg.py "@username" "first part of a message" "second part of a message" --debug
```
  * For `@username`, substitute your own Telegram username (**not the bot's**, case-sensitive) or your chat ID
  * For the message parts, substitute something like `test` `test` (Telegram doesn't distinguish between subject and body)
  * You can omit the quotes if a parameter is a single word

### Development

The code is split across a few modules under `zbxtg_lib/`:

- `cli.py` -- argument parsing and orchestration (what used to be `zbxtg.py`'s `main()`)
- `directives.py` -- parsing of `zbxtg;key:value` directives from the message body
- `config.py` -- loads `zbxtg_settings.yaml` (or the legacy `.py` format) into typed config objects
- `telegram_api.py` -- Telegram Bot API client
- `zabbix_web.py` -- fetches rendered graph images from the Zabbix web frontend
- `zabbix_api.py` -- optional Zabbix JSON-RPC client (not required for the core flow, see [Known issues](#known-issues))
- `maps.py` -- Google Geocoding lookup for the `location` directive
- `utils.py` -- small shared helpers, including the flat-file chat ID cache

`zbxtg.py` and `zbxtg_group.py` are thin entry points that Zabbix calls directly by path -- their names and locations are part of the public interface and won't change.

Run the test suite with:
```
pip install -r requirements-dev.txt
pytest
```

---

![](http://i.imgur.com/1T4aHuf.png)
![](http://i.imgur.com/5ZPyvoe.png)

### Known issues

#### MEDIA_CAPTION_TOO_LONG
This means you've hit Telegram's 200-character limit for photo captions. Captions longer than that are automatically cut to 200 symbols.

#### Why graphs are fetched from the web UI instead of the API
The Zabbix JSON-RPC API (`graph.get`, `item.get`, etc.) only returns graph *configuration* -- it does not render images. Rendering is done exclusively by frontend endpoints such as `chart3.php`, which is why this script logs into the Zabbix web UI with its own read-only user to fetch graph images. This is still the case as of Zabbix 7.0.

#### Zabbix version support
Zabbix 4.0 and later are supported, with 7.0 as the primary target. If you're still on Zabbix 2.x/3.x, the classic `period=` graph URL parameter used on those versions was removed from this rewrite (current Zabbix frontends only accept a `from`/`to` time range) -- pin to a pre-3.0 release of this project if you can't upgrade Zabbix yet.

See also: https://github.com/ableev/Zabbix-in-Telegram/wiki/Working-with-Zabbix-3.0
