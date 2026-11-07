<p align="center"><img src="logo.png" width="110" alt="Larpresence logo"></p>

# Larpresence

Set a fully custom Discord status: your own name, text, images and an elapsed timer that can start hours in the past.

Larpresence uses Discord's official Rich Presence. It talks to your running Discord desktop app over a local connection. It never asks for your Discord login or token, and it is not a self-bot.

## Features

- Custom name and activity type (Playing, Listening, Watching, Competing)
- Two text lines (details and state)
- Large image and small corner badge: click to pick a file or drag one in
- Elapsed timer with a "started X hours ago" offset
- Live preview, and connect / update / disconnect without restarting
- Resumes your status automatically, even after Discord restarts
- Optional: keep running in the system tray and start with Windows
- Themes, adjustable glass strength, always on top
- Remembers everything between launches

## Setup (one time)

Larpresence needs a **Discord Application ID** of your own. It's free and takes a minute.

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications) and click **New Application**.
2. Give it a name. This name is the fallback Discord can show for your status (see [Custom name](#custom-name)). Discord rejects names containing "discord".
3. Copy the **Application ID** from the General Information page. It's a public identifier, not a secret.
4. Click the gear icon in Larpresence and paste it into *Application ID*. Larpresence opens Settings for you on first launch.

## Download or run from source

**Exe:** grab `Larpresence.exe` from the [Releases](../../releases) page and run it. Windows only.

**From source:** requires Windows 10/11 and Python 3.9+.

```
pip install -r requirements.txt
python larpresence.py
```

## Build the exe yourself

Double-click `build.bat`. The result is `dist\Larpresence.exe`.

To make it work without setup for your friends, set `CLIENT_ID` near the top of `larpresence.py` to your own Application ID before building.

## How to use

1. Open the **Discord desktop app** (the browser version doesn't work).
2. Start Larpresence and fill in the name, text and images.
3. Click **Connect**. Use **Update** any time to apply changes live.
4. Click **Disconnect** to clear the status.

Your status only shows while Larpresence is running and connected. Closing the app removes it, unless you turned on background mode.

In Discord, make sure **Settings > Activity Privacy > Share my activity** is on. Your own profile can look different from what others see, so check from another account if unsure.

## Settings

Click the gear icon in the title bar.

| Section | Option | What it does |
|---|---|---|
| Discord | Application ID | Your app's ID (required). Changing it while connected takes effect after you reconnect. |
| Appearance | Theme | Midnight, Graphite, Forest or Rose. |
| Appearance | Glass strength | How frosted the panels look. |
| Behavior | Resume status automatically | Reconnects whenever Discord opens or restarts. |
| Behavior | Keep running in the background | Closing the window hides Larpresence in the system tray. |
| Behavior | Start with Windows | Launches hidden at login. Adds an entry under the current user's Windows startup list (`HKCU\...\Run`); turning it off removes it. |
| Behavior | Keep window on top | Stays above other windows. |
| Data | Open settings folder | Opens `%APPDATA%\Larpresence`. |
| Data | Reset all settings | Disconnects, then wipes saved settings, including the Application ID (click twice to confirm). |

Changes save automatically. If you used the earlier "Larpcord" version, your settings are copied over on first launch.

## Custom name

Discord normally shows the name of your Developer Portal application. Larpresence also sends your custom name, and Discord displays it in many places, but Discord decides where the override is honored. Where it isn't, your Developer Portal app name is shown instead, so give your application a name you're happy with.

## About images

Discord can only display images that are hosted at a web address, so when you pick a local image Larpresence uploads it to [catbox.moe](https://catbox.moe), a free host that needs no account. **The uploaded image is publicly reachable by anyone with the link. Don't use private images.** Images are limited to 8 MB.

## Where settings are stored

`%APPDATA%\Larpresence\settings.json`

## Troubleshooting

- **"No Application ID set"**: add yours in Settings (gear icon) or in `CLIENT_ID` in the code. See [Setup](#setup-one-time).
- **"Connection failed"**: Discord desktop isn't running, or Discord and Larpresence are running at different privilege levels (one as administrator, one not). Run both normally.
- **Status doesn't appear**: check Activity Privacy (above) and that the log shows a successful connect.
- **Custom name not shown everywhere**: see [Custom name](#custom-name).
- **Blank window**: install the [WebView2 runtime](https://developer.microsoft.com/microsoft-edge/webview2/) (already included in Windows 11).
- **Image upload failed**: the free host may be down or blocked on your network. Try again later.
- **Windows SmartScreen or antivirus warns about the exe**: the exe is not code-signed, which commonly triggers this for small tools built with PyInstaller. You can build it yourself from source instead.

## Disclaimer

Larpresence is an independent project and is not affiliated with Discord. It lets you display any status you like, so please don't use it to impersonate others or mislead people in ways that violate Discord's terms.

## License

MIT. See [LICENSE](LICENSE).
