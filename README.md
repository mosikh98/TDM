# Twitch Drops Miner

> Automatically mine timed Twitch Drops without streaming video or audio.

![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python)
![License MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)

A low-bandwidth, headless Twitch Drops miner: it finds eligible campaigns, picks a
live channel, and tracks drop progress from a web dashboard — without downloading
the stream.

![Web dashboard](./screenshot.png)

## Features

- Low-bandwidth mining — no video/audio downloads
- Automatic campaign discovery and smart channel selection
- Web dashboard: campaigns, channels, inventory, settings, history
- Optional dashboard password (protects UI, API and live connections)
- Drop history with stats and CSV export
- Telegram notifications on every claimed drop
- Persistent Twitch login sessions
- Docker / headless deployment

## Quick start

### Docker Compose

```bash
git clone https://github.com/mostafajr445-stack/tdm
cd tdm
docker compose up -d --build
```

### From source

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/):

```bash
uv sync
uv run main.py
```

Open <http://localhost:8080> and log in with Twitch.

## Usage

1. Log in via the Smart TV device flow (`twitch.tv/activate`) — the session is saved.
2. Wait for campaigns to load, then add your games in **Games to Watch**
   (priority `1` = highest).
3. Leave it running — channel selection and progress tracking are automatic.

> [!WARNING]
> Don't watch Twitch on the same account while the miner runs — it can desync drop progress.
> Your Twitch account must be linked to your game accounts:
> [twitch.tv/drops/campaigns](https://www.twitch.tv/drops/campaigns)

## Telegram notifications

**Settings → Telegram Notifications** → bot token from [@BotFather](https://t.me/BotFather)
+ your chat ID → **Test Connection**.

## Dashboard password (optional)

**Settings → Dashboard password** (8–1024 characters). Forgot it? Stop the miner,
delete `data/web_auth.json`, restart, and set a new one.

## Data & logs

- Docker persists data in `./data` (mounted at `/app/data`)
- Source installs keep data in `./data`
- Logs: mount `./logs:/app/logs`

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). Coding agents must follow [AGENTS.md](./AGENTS.md).

## License

MIT — see [LICENSE](./LICENSE).

## Credits

Based on **[DevilXD/TwitchDropsMiner](https://github.com/DevilXD/TwitchDropsMiner)**
(MIT license), via the [rangermix/TwitchDropsMiner](https://github.com/rangermix/TwitchDropsMiner)
fork. Big thanks to the original author [@DevilXD](https://github.com/DevilXD) and all
contributors and translators.
