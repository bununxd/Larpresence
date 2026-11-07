"""
Larpresence - custom Discord Rich Presence.

Install:  pip install -r requirements.txt
Run:      python larpresence.py
Needs:    Windows 10/11 (WebView2 runtime, included in Windows 11)
"""
__version__ = "1.0.0"

import base64
import io
import json
import os
import shutil
import socket
import sys
import threading
import time
import urllib.request
import uuid
import webbrowser
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import webview
from pypresence import Presence
from pypresence.types import ActivityType

# ---------------------------------------------------------------------------
# YOUR Discord Application ID.
# Either paste it here, or leave this empty and enter it in the app under
# Settings (gear icon). The value saved in Settings wins over this one.
# Create an application at https://discord.com/developers/applications
# ---------------------------------------------------------------------------
CLIENT_ID = ""

# Settings live in %APPDATA%\Larpresence\settings.json (works for the .exe and from source).
BASE_DIR = os.environ.get("APPDATA") or os.path.expanduser("~")
APP_DIR = os.path.join(BASE_DIR, "Larpresence")
OLD_APP_DIR = os.path.join(BASE_DIR, "Larpcord")      # previous name, migrated on first run
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
STARTUP_NAME = "Larpresence"
OLD_STARTUP_NAME = "Larpcord"
SINGLE_PORT = 47654          # loopback port used to keep only one Larpresence running
UPLOAD_URL = "https://catbox.moe/user/api.php"
MAX_IMAGE_BYTES = 8 * 1024 * 1024

DEFAULTS = {
    # app settings
    "client_id": "",
    "theme": "midnight",
    "glass": 50,
    "on_top": False,
    "auto_connect": False,      # resume status automatically (also after Discord restarts)
    "background": False,        # closing the window hides it to the tray
    "run_at_startup": False,    # launch with Windows
    "active": False,            # internal: was connected when last used
    "start_ts": None,           # internal: keeps the timer continuous across reconnects
    # status
    "name": "",
    "activity_type": "Playing",
    "details": "Coding in VS Code",
    "state": "Building my project",
    "large_image": "",
    "large_text": "",
    "small_image": "",
    "small_text": "",
    "use_timer": True,
    "hours_ago": "0",
    "minutes_ago": "0",
}

# All Discord work happens on ONE thread (pypresence uses an asyncio loop per thread).
POOL = ThreadPoolExecutor(max_workers=1)
STATE = {
    "rpc": None, "start_ts": None,
    "want": False,          # should the background supervisor keep us connected?
    "waiting": False,       # already told the user we're waiting for Discord
    "last_ping": 0.0,
    "notified": False,
    "bg_logs": deque(maxlen=60),
}
TRAY = {"icon": None}
QUIT = {"now": False}
STOP = threading.Event()
WINDOW = None

# 64x64 tray icon (the Larpresence logo)
ICON_PNG_B64 = "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"

TYPES = {
    "Playing": ActivityType.PLAYING,
    "Listening": ActivityType.LISTENING,
    "Watching": ActivityType.WATCHING,
    "Competing": ActivityType.COMPETING,
}


# ---------------------------------------------------------------- settings
def migrate_old_settings():
    """One time: copy settings from the old Larpcord folder so nobody loses their setup."""
    try:
        old = os.path.join(OLD_APP_DIR, "settings.json")
        if not os.path.exists(SETTINGS_FILE) and os.path.exists(old):
            os.makedirs(APP_DIR, exist_ok=True)
            shutil.copyfile(old, SETTINGS_FILE)
    except OSError:
        pass


def read_raw_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(new):
    """Merge `new` into the settings file (keys not in `new` are kept)."""
    data = read_raw_settings()
    data.update(new)
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def get_client_id():
    """Settings value first, then the CLIENT_ID constant above. Empty string if neither."""
    cid = str(read_raw_settings().get("client_id", "")).strip()
    if cid.isdigit():
        return cid
    cid = str(CLIENT_ID).strip()
    return cid if cid.isdigit() else ""


def load_settings():
    data = dict(DEFAULTS)
    data.update(read_raw_settings())
    return data


# ---------------------------------------------------------------- image upload
def upload_image(b64, filename):
    """Upload an image to catbox.moe (no account needed) and return its public URL.
    Discord can only show images that live at a URL, so local files have to be hosted somewhere."""
    try:
        data = base64.b64decode(b64)
        if len(data) > MAX_IMAGE_BYTES:
            return {"ok": False, "error": "Image is larger than 8 MB."}
        ext = os.path.splitext(filename)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            ext = ".png"
        boundary = "----larpresence" + uuid.uuid4().hex
        name = "larp" + uuid.uuid4().hex[:10] + ext
        parts = [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"reqtype\"\r\n\r\nfileupload\r\n".encode(),
            (f"--{boundary}\r\nContent-Disposition: form-data; name=\"fileToUpload\"; filename=\"{name}\"\r\n"
             "Content-Type: application/octet-stream\r\n\r\n").encode(),
            data,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
        req = urllib.request.Request(
            UPLOAD_URL,
            data=b"".join(parts),
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "Mozilla/5.0 Larpresence",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = resp.read().decode("utf-8", "replace").strip()
        if out.startswith("http"):
            return {"ok": True, "url": out}
        return {"ok": False, "error": f"Upload host said: {out[:120]}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------- presence
def compute_start(s, logs):
    if not s.get("use_timer"):
        return None
    try:
        h = float(s.get("hours_ago") or 0)
        m = float(s.get("minutes_ago") or 0)
    except ValueError:
        logs.append("✕ Hours/minutes must be numbers. Timer skipped.")
        return None
    if h < 0 or m < 0:
        logs.append("✕ Hours/minutes can't be negative. Using 0 instead.")
        h, m = max(h, 0), max(m, 0)
    return int(time.time() - (h * 3600 + m * 60))


def build_kwargs(s, logs):
    kw = {"activity_type": TYPES.get(s.get("activity_type"), ActivityType.PLAYING)}
    for key in ("name", "details", "state", "large_image", "large_text", "small_image", "small_text"):
        val = (s.get(key) or "").strip()
        if val:
            kw[key] = val
    for k in ("details", "state"):
        if k in kw and len(kw[k]) < 2:
            logs.append(f"✕ '{k}' needs at least 2 characters, skipped.")
            del kw[k]
    if STATE["start_ts"]:
        kw["start"] = STATE["start_ts"]
    return kw


def push(s, logs):
    kw = build_kwargs(s, logs)
    if len(kw) <= 1:
        logs.append("✕ Nothing to send. Fill in at least one field.")
        return
    try:
        STATE["rpc"].update(**kw)
        shown = ", ".join(
            "start=<timestamp>" if k == "start" else f"{k}={str(v)[:40]!r}"
            for k, v in kw.items() if k != "activity_type"
        )
        logs.append("✓ Updated: " + shown)
    except Exception as e:  # noqa: BLE001
        logs.append(f"✕ Update failed: {e}")


def bg_log(msg):
    STATE["bg_logs"].append(msg)


def discard(rpc):
    """Release a Presence object that never connected (avoids leaking its event loop)."""
    if rpc is None:
        return
    try:
        rpc.loop.close()
    except Exception:  # noqa: BLE001
        pass


def do_start(s):
    logs = []
    cid = get_client_id()
    if not cid:
        logs.append("✕ No Application ID set. Open Settings (gear icon) and add yours.")
        return {"connected": False, "logs": logs, "needs_id": True}
    save_settings(s)
    rpc = None
    try:
        logs.append("Connecting to Discord…")
        rpc = Presence(cid)
        rpc.connect()
        STATE["rpc"] = rpc
    except Exception as e:  # noqa: BLE001
        discard(rpc)
        STATE["rpc"] = None
        logs.append(f"✕ Connection failed: {e}")
        if load_settings().get("auto_connect"):
            STATE["want"] = True
            STATE["waiting"] = True
            save_settings({"active": True})
            logs.append("Larpresence will keep trying in the background.")
        else:
            STATE["want"] = False
            logs.append("Make sure the Discord desktop app is running.")
        return {"connected": False, "logs": logs}
    STATE["want"] = True
    STATE["waiting"] = False
    STATE["last_ping"] = time.time()
    logs.append("✓ Connected.")
    STATE["start_ts"] = compute_start(s, logs)
    save_settings({"active": True, "start_ts": STATE["start_ts"]})
    push(s, logs)
    return {"connected": True, "logs": logs}


def do_update(s):
    logs = []
    if not STATE["rpc"]:
        return {"connected": False, "logs": ["✕ Not connected."]}
    save_settings(s)
    STATE["start_ts"] = compute_start(s, logs)
    save_settings({"start_ts": STATE["start_ts"]})
    STATE["last_ping"] = time.time()
    push(s, logs)
    return {"connected": True, "logs": logs}


def do_stop():
    logs = []
    STATE["want"] = False
    STATE["waiting"] = False
    save_settings({"active": False, "start_ts": None})
    rpc = STATE["rpc"]
    if rpc:
        try:
            rpc.clear()
            rpc.close()
        except Exception as e:  # noqa: BLE001
            logs.append(f"✕ Error while disconnecting: {e}")
    STATE["rpc"] = None
    STATE["start_ts"] = None
    logs.append("Disconnected. Status cleared.")
    return {"connected": False, "logs": logs}


def close_rpc():
    rpc = STATE["rpc"]
    STATE["rpc"] = None
    if rpc:
        try:
            rpc.close()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------- background supervisor
def supervise_once():
    """Runs on the Discord thread every few seconds: keeps the status alive.
    Reconnects when Discord starts (or restarts) and re-sends the status as a heartbeat."""
    s = load_settings()
    if not (STATE["want"] and s.get("auto_connect")):
        return
    now = time.time()

    if STATE["rpc"]:
        if now - STATE["last_ping"] < 30:
            return
        STATE["last_ping"] = now
        try:
            STATE["rpc"].update(**build_kwargs(s, []))
        except Exception:  # noqa: BLE001
            try:
                STATE["rpc"].close()
            except Exception:  # noqa: BLE001
                pass
            STATE["rpc"] = None
            STATE["waiting"] = True
            bg_log("Lost the connection to Discord. Reconnecting automatically…")
        return

    cid = get_client_id()
    if not cid:
        return
    rpc = None
    try:
        rpc = Presence(cid)
        rpc.connect()
    except Exception:  # noqa: BLE001
        discard(rpc)
        if not STATE["waiting"]:
            STATE["waiting"] = True
            bg_log("Waiting for Discord…")
        return
    STATE["rpc"] = rpc
    STATE["waiting"] = False
    STATE["last_ping"] = now
    logs = []
    saved = s.get("start_ts") if s.get("use_timer") else None
    STATE["start_ts"] = saved or compute_start(s, logs)
    push(s, logs)
    for line in logs:
        bg_log(line)
    bg_log("✓ Connected automatically.")


def supervisor_loop():
    while not STOP.is_set():
        try:
            POOL.submit(supervise_once).result(timeout=30)
        except Exception:  # noqa: BLE001
            pass
        STOP.wait(5)


# ---------------------------------------------------------------- startup with Windows
def startup_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --background'
    py = sys.executable
    pyw = os.path.join(os.path.dirname(py), "pythonw.exe")
    if os.path.exists(pyw):
        py = pyw
    return f'"{py}" "{os.path.abspath(__file__)}" --background'


def set_startup(enabled):
    """Add/remove the Windows login entry. Returns False if it couldn't be done.
    Also removes the entry the old "Larpcord" version created."""
    try:
        import winreg
    except ImportError:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        try:
            try:
                winreg.DeleteValue(key, OLD_STARTUP_NAME)
            except FileNotFoundError:
                pass
            if enabled:
                winreg.SetValueEx(key, STARTUP_NAME, 0, winreg.REG_SZ, startup_command())
            else:
                try:
                    winreg.DeleteValue(key, STARTUP_NAME)
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------- window, tray, single instance
def show_window():
    for fn in ("show", "restore"):
        try:
            getattr(WINDOW, fn)()
        except Exception:  # noqa: BLE001
            pass


def tray_available():
    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def do_quit():
    QUIT["now"] = True
    icon = TRAY["icon"]
    TRAY["icon"] = None
    if icon:
        try:
            icon.stop()
        except Exception:  # noqa: BLE001
            pass
    try:
        WINDOW.destroy()
    except Exception:  # noqa: BLE001
        pass


def ensure_tray():
    """Create or remove the tray icon to match the 'background' setting. True if a tray icon exists."""
    want = bool(load_settings().get("background")) and tray_available()
    if want and not TRAY["icon"]:
        try:
            import pystray
            from PIL import Image
            img = Image.open(io.BytesIO(base64.b64decode(ICON_PNG_B64)))
            menu = pystray.Menu(
                pystray.MenuItem("Open Larpresence", lambda icon, item: show_window(), default=True),
                pystray.MenuItem("Quit", lambda icon, item: do_quit()),
            )
            icon = pystray.Icon("Larpresence", img, "Larpresence", menu)
            icon.run_detached()
            TRAY["icon"] = icon
        except Exception:  # noqa: BLE001
            TRAY["icon"] = None
    elif not want and TRAY["icon"]:
        try:
            TRAY["icon"].stop()
        except Exception:  # noqa: BLE001
            pass
        TRAY["icon"] = None
    return TRAY["icon"] is not None


def hide_to_tray():
    WINDOW.hide()
    if not STATE["notified"]:
        STATE["notified"] = True
        try:
            TRAY["icon"].notify("Larpresence is still running. Right-click the tray icon to quit.", "Larpresence")
        except Exception:  # noqa: BLE001
            pass


def on_closing():
    """Alt+F4 etc.: hide to the tray instead of quitting when background mode is on."""
    if QUIT["now"]:
        return True
    if load_settings().get("background") and TRAY["icon"]:
        hide_to_tray()
        return False
    return True


def claim_single_instance():
    """Only one Larpresence at a time. A second launch just asks the first one to show its window."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        srv.bind(("127.0.0.1", SINGLE_PORT))
    except OSError:
        srv.close()
        try:
            c = socket.create_connection(("127.0.0.1", SINGLE_PORT), timeout=2)
            c.sendall(b"noop" if "--background" in sys.argv else b"show")
            c.close()
            return False
        except OSError:
            return True  # the port belongs to something else; just run

    srv.listen(2)

    def loop():
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                return
            try:
                if conn.recv(16).startswith(b"show"):
                    show_window()
            except OSError:
                pass
            finally:
                conn.close()

    threading.Thread(target=loop, daemon=True).start()
    return True


class Api:
    """Methods exposed to the page as window.pywebview.api.*"""

    def get_settings(self):
        d = load_settings()
        d["has_id"] = bool(get_client_id())
        return d

    def save_app_settings(self, a):
        cid = str(a.get("client_id") or "").strip()
        if cid and not cid.isdigit():
            return {"ok": False, "error": "The Application ID should be numbers only."}
        old = get_client_id()
        try:
            glass = max(0, min(100, int(a.get("glass", 50))))
        except (TypeError, ValueError):
            glass = 50
        clean = {
            "background": bool(a.get("background")),
            "run_at_startup": bool(a.get("run_at_startup")),
            "client_id": cid,
            "theme": a.get("theme") if a.get("theme") in ("midnight", "graphite", "forest", "rose") else "midnight",
            "glass": glass,
            "on_top": bool(a.get("on_top")),
            "auto_connect": bool(a.get("auto_connect")),
        }
        save_settings(clean)
        try:
            WINDOW.on_top = clean["on_top"]
        except Exception:  # noqa: BLE001
            pass
        if clean["auto_connect"] and STATE["rpc"]:
            STATE["want"] = True
        startup_ok = set_startup(clean["run_at_startup"]) or not clean["run_at_startup"]
        tray_ok = ensure_tray() or not clean["background"]
        return {"ok": True, "id_changed": get_client_id() != old, "startup_ok": startup_ok, "tray_ok": tray_ok}

    def open_url(self, url):
        if str(url).startswith("https://discord.com/developers/applications"):
            webbrowser.open(url)

    def open_folder(self):
        try:
            os.makedirs(APP_DIR, exist_ok=True)
            os.startfile(APP_DIR)  # Windows only
        except Exception:  # noqa: BLE001
            pass

    def reset_settings(self):
        try:
            POOL.submit(do_stop).result(timeout=10)   # clear the live status first
        except Exception:  # noqa: BLE001
            STATE["want"] = False
        try:
            os.remove(SETTINGS_FILE)
        except OSError:
            pass
        set_startup(False)
        ensure_tray()
        return self.get_settings()

    def get_status(self):
        logs = []
        while STATE["bg_logs"]:
            try:
                logs.append(STATE["bg_logs"].popleft())
            except IndexError:
                break
        return {"connected": STATE["rpc"] is not None, "logs": logs}

    def quit_app(self):
        do_quit()

    def upload(self, b64, filename):
        return upload_image(b64, filename)

    def start(self, s):
        return POOL.submit(do_start, s).result()

    def update(self, s):
        return POOL.submit(do_update, s).result()

    def stop(self):
        return POOL.submit(do_stop).result()

    def minimize(self):
        WINDOW.minimize()

    def close(self):
        if load_settings().get("background") and TRAY["icon"]:
            hide_to_tray()
        else:
            do_quit()


HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Larpresence</title>
<style>
  :root{
    --text:#eceef2; --dim:rgba(236,238,242,.55); --faint:rgba(236,238,242,.32);
    --edge:rgba(255,255,255,.10); --panel:rgba(255,255,255,.045); --field:rgba(0,0,0,.28);
    --accent:#9db4ff; --accent2:#5b7fe0; --ok:#6fcf97; --bad:#ef7b7b;
    --bga:rgba(70,92,150,.55); --bgb:rgba(110,76,98,.42); --blur:26px;
  }
  *{box-sizing:border-box;margin:0}
  html,body{height:100%}
  body{
    font:13px/1.4 "Segoe UI Variable Text","Segoe UI",system-ui,sans-serif;
    color:var(--text);background:#0d0e11;overflow:hidden;user-select:none;
  }
  .bg{position:fixed;inset:0;background:
      radial-gradient(700px 480px at 8% 0%,var(--bga),transparent 70%),
      radial-gradient(640px 460px at 100% 100%,var(--bgb),transparent 70%),
      #0d0e11}
  .win{position:relative;height:100%;display:flex;flex-direction:column;border:1px solid rgba(255,255,255,.13)}
  main{flex:1;min-height:0;padding:4px 20px 20px;display:flex;flex-direction:column;gap:14px}

  .glass{background:var(--panel);border:1px solid var(--edge);border-radius:14px;
         -webkit-backdrop-filter:blur(var(--blur)) saturate(150%);backdrop-filter:blur(var(--blur)) saturate(150%);
         box-shadow:inset 0 1px 0 rgba(255,255,255,.06)}

  .titlebar{position:relative;z-index:30;height:40px;flex:none;display:flex;align-items:center}
  .logo{width:18px;height:18px;margin-right:9px;flex:none;pointer-events:none}
  .drag{flex:1;height:100%;display:flex;align-items:center;padding-left:20px;font-size:13px;font-weight:600;letter-spacing:.2px}
  .status{font-size:12px;color:var(--dim);margin-right:10px;pointer-events:none}
  .status.on{color:var(--ok)}
  .wb{width:46px;height:100%;border:0;background:none;color:var(--dim);display:grid;place-items:center;cursor:pointer;transition:background .12s,color .12s}
  .wb:hover{background:rgba(255,255,255,.08);color:var(--text)}
  .wb.close:hover{background:#c42b1c;color:#fff}
  .wb svg{width:10px;height:10px;stroke:currentColor;stroke-width:1.2;fill:none}

  .grid{flex:1;min-height:0;display:grid;grid-template-columns:1.15fr 1fr;gap:14px}
  .left{min-height:0;overflow-y:auto;display:flex;flex-direction:column;gap:12px;padding-right:2px}
  .left::-webkit-scrollbar,#log::-webkit-scrollbar{width:6px}
  .left::-webkit-scrollbar-thumb,#log::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15);border-radius:6px}
  .right{min-height:0;display:flex;flex-direction:column;gap:12px}

  .sec{padding:14px 15px}
  .sec>.t{font-size:13px;font-weight:600;margin-bottom:10px}
  .f+.f{margin-top:9px}
  label.l{display:block;font-size:12px;color:var(--dim);margin-bottom:4px}
  .two{display:grid;grid-template-columns:1fr 1fr;gap:10px}

  input[type=text]{width:100%;padding:8px 10px;font:inherit;color:var(--text);user-select:text;
    background:var(--field);border:1px solid var(--edge);border-radius:9px;outline:none;transition:border-color .15s}
  input[type=text]::placeholder{color:var(--faint)}
  input[type=text]:focus{border-color:var(--accent)}

  .seg{display:flex;gap:2px;padding:3px;background:var(--field);border:1px solid var(--edge);border-radius:10px}
  .seg button{flex:1;padding:6px 0;border:0;border-radius:7px;background:none;color:var(--dim);font:inherit;cursor:pointer}
  .seg button:hover{color:var(--text)}
  .seg button.on{background:rgba(255,255,255,.12);color:var(--text)}

  /* image slots */
  .imgrow{display:flex;gap:12px;align-items:flex-start}
  .imgrow+.imgrow{margin-top:12px}
  .imgrow .meta{flex:1;min-width:0}
  .slot{position:relative;width:100%;height:92px;border:1px dashed rgba(255,255,255,.22);border-radius:12px;
        background:var(--field);display:grid;place-items:center;text-align:center;color:var(--dim);font-size:11.5px;
        cursor:pointer;overflow:hidden;transition:border-color .15s,background .15s}
  .slot:hover,.slot.over{border-color:var(--accent);background:rgba(157,180,255,.08)}
  .slot img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:none}
  .slot.has{border-style:solid}
  .slot.has img{display:block}
  .slot.has .ph{display:none}
  .slot .x{position:absolute;top:4px;right:4px;width:20px;height:20px;border:0;border-radius:50%;
           background:rgba(0,0,0,.65);color:#fff;font-size:13px;line-height:20px;cursor:pointer;display:none}
  .slot.has .x{display:block}
  .slot .busy{position:absolute;inset:0;background:rgba(10,11,14,.75);display:none;place-items:center;color:var(--text)}
  .slot.loading .busy{display:grid}

  /* timer */
  .trow{display:flex;align-items:center;gap:10px}
  .sw{position:relative;width:38px;height:22px;flex:none}
  .sw input{display:none}
  .sw span{position:absolute;inset:0;border-radius:99px;background:rgba(255,255,255,.14);cursor:pointer;transition:.15s}
  .sw span::after{content:"";position:absolute;left:3px;top:3px;width:16px;height:16px;border-radius:50%;background:#fff;transition:.15s}
  .sw input:checked+span{background:var(--accent2)}
  .sw input:checked+span::after{transform:translateX(16px)}
  .ago{margin-left:auto;display:flex;align-items:center;gap:6px;color:var(--dim)}
  .ago input{width:48px;text-align:center;padding:6px 4px}

  /* preview */
  .preview{padding:14px 15px}
  .preview .cap{font-size:12px;color:var(--dim);margin-bottom:10px}
  .act{display:flex;gap:12px;align-items:center}
  .art{position:relative;width:72px;height:72px;flex:none;border-radius:10px;background:#2a2e3b center/cover;
       display:grid;place-items:center;font-size:26px;font-weight:600;color:var(--dim)}
  .badge{position:absolute;right:-6px;bottom:-6px;width:26px;height:26px;border-radius:50%;border:3px solid #15171d;
         background:#2a2e3b center/cover;display:none}
  .lines{min-width:0}
  .lines div{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .verb{font-size:11.5px;color:var(--dim)}
  .pname{font-weight:600;font-size:14px}
  .pl{font-size:12.5px;color:rgba(236,238,242,.8)}
  .ptime{font-size:12.5px;color:var(--ok);font-variant-numeric:tabular-nums}

  /* buttons */
  .btns{display:flex;gap:8px}
  .btn{flex:1;padding:10px 0;border-radius:10px;border:1px solid var(--edge);background:var(--panel);color:var(--text);
       font:inherit;font-weight:500;cursor:pointer;transition:background .15s}
  .btn:hover:not(:disabled){background:rgba(255,255,255,.1)}
  .btn:disabled{opacity:.35;cursor:default}
  .btn.main{background:#e9ebf1;border-color:#e9ebf1;color:#14161c;font-weight:600}
  .btn.main:hover:not(:disabled){background:#fff}
  .btn.danger{color:var(--bad)}

  /* settings sheet */
  #b_gear svg{width:15px;height:15px;stroke-width:1.6}
  .overlay{position:absolute;inset:0;z-index:20;display:none;justify-content:center;align-items:flex-start;
           padding:48px 40px 22px;background:rgba(6,7,10,.55);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px)}
  .overlay.open{display:flex}
  .sheet{width:100%;max-width:540px;max-height:100%;overflow-y:auto;background:rgba(24,26,33,.9)}
  .sheet::-webkit-scrollbar{width:6px}
  .sheet::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15);border-radius:6px}
  .shead{display:flex;align-items:center;justify-content:space-between;padding:14px 18px}
  .shead b{font-size:15px;font-weight:600}
  .shead button{border:0;background:none;color:var(--dim);font-size:20px;line-height:1;cursor:pointer;padding:0 4px}
  .shead button:hover{color:var(--text)}
  .ss{padding:14px 18px 16px;border-top:1px solid var(--edge)}
  .ss>.t{font-size:12px;font-weight:600;color:var(--dim);margin-bottom:8px}
  .srow{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:7px 0}
  .srow .sl{font-size:13px}
  .shint{font-size:11.5px;color:var(--faint);margin-top:2px}
  .err{color:var(--bad);font-size:11.5px;margin-top:4px;min-height:14px}
  .themes{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
  .chip{height:46px;border-radius:10px;border:1px solid var(--edge);color:var(--text);font:inherit;font-size:11.5px;
        text-align:left;padding:0 9px;cursor:pointer;display:flex;align-items:flex-end;padding-bottom:6px}
  .chip.on{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
  input[type=range]{width:190px;accent-color:var(--accent)}
  .rangewrap{display:flex;align-items:center;gap:10px;color:var(--dim);font-size:12px}
  .btn.sm{flex:none;padding:7px 12px;font-size:12.5px}
  .btnrow{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}
  .about{font-size:11.5px;color:var(--faint);padding:12px 18px 16px;border-top:1px solid var(--edge)}

  .logbox{flex:1;min-height:80px;padding:11px 13px;display:flex;flex-direction:column}
  .logbox .cap{font-size:12px;color:var(--dim);margin-bottom:6px}
  #log{flex:1;overflow-y:auto;font:11.5px/1.55 Consolas,"Cascadia Mono",monospace;color:var(--dim);user-select:text}
  #log .ok{color:var(--ok)} #log .err{color:var(--bad)} #log .tm{color:var(--faint)}
</style>
</head>
<body>
<div class="bg"></div>
<div class="win">
<div class="titlebar">
  <div class="drag pywebview-drag-region"><svg class="logo" viewBox="0 0 1024 1024"><rect x="12" y="12" width="1000" height="1000" rx="224" fill="#0a0a0a" stroke="#ffffff" stroke-opacity=".35" stroke-width="24"/><rect x="262" y="190" width="160" height="610" rx="70" fill="#fff"/><rect x="262" y="640" width="458" height="160" rx="70" fill="#fff"/><circle cx="742" cy="742" r="178" fill="#0a0a0a"/><circle cx="742" cy="742" r="124" fill="#fff"/></svg>Larpresence</div>
  <span class="status" id="status">Not connected</span>
  <button class="wb" id="b_gear" title="Settings"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg></button>
  <button class="wb" id="b_min" title="Minimize"><svg viewBox="0 0 10 10"><path d="M0 5h10"/></svg></button>
  <button class="wb close" id="b_close" title="Close"><svg viewBox="0 0 10 10"><path d="M0 0l10 10M10 0L0 10"/></svg></button>
</div>
<main>
  <div class="grid">
    <section class="left">
      <div class="sec glass">
        <div class="t">Name</div>
        <div class="f">
          <label class="l" for="name">What shows after “Playing”</label>
          <input type="text" id="name" placeholder="Any name you want">
        </div>
        <div class="f">
          <div class="seg" id="seg">
            <button data-t="Playing">Playing</button>
            <button data-t="Listening">Listening</button>
            <button data-t="Watching">Watching</button>
            <button data-t="Competing">Competing</button>
          </div>
        </div>
      </div>

      <div class="sec glass">
        <div class="t">Text</div>
        <div class="two">
          <div><label class="l" for="details">First line</label><input type="text" id="details"></div>
          <div><label class="l" for="state">Second line</label><input type="text" id="state"></div>
        </div>
      </div>

      <div class="sec glass">
        <div class="t">Images</div>
        <div class="two">
          <div>
            <label class="l">Large image <span style="opacity:.6">· main artwork</span></label>
            <div class="slot" id="slot_large" data-key="large_image">
              <input type="file" accept="image/*" hidden>
              <div class="ph">Drop image or click</div>
              <img alt=""><button class="x" title="Remove">×</button><div class="busy">Uploading…</div>
            </div>
            <input type="text" id="large_text" placeholder="Hover text" style="margin-top:8px">
          </div>
          <div>
            <label class="l">Small image <span style="opacity:.6">· corner badge</span></label>
            <div class="slot" id="slot_small" data-key="small_image">
              <input type="file" accept="image/*" hidden>
              <div class="ph">Drop image or click</div>
              <img alt=""><button class="x" title="Remove">×</button><div class="busy">Uploading…</div>
            </div>
            <input type="text" id="small_text" placeholder="Hover text" style="margin-top:8px">
          </div>
        </div>
      </div>

      <div class="sec glass">
        <div class="t">Timer</div>
        <div class="trow">
          <label class="sw"><input type="checkbox" id="use_timer"><span></span></label>
          <span>Show elapsed time</span>
          <div class="ago">started
            <input type="text" id="hours_ago"> h
            <input type="text" id="minutes_ago"> min ago
          </div>
        </div>
      </div>
    </section>

    <section class="right">
      <div class="preview glass">
        <div class="cap">Preview</div>
        <div class="act">
          <div class="art" id="p_art"><span id="p_letter">L</span><div class="badge" id="p_badge"></div></div>
          <div class="lines">
            <div class="verb" id="p_verb">Playing</div>
            <div class="pname" id="p_name">Your name</div>
            <div class="pl" id="p_det"></div>
            <div class="pl" id="p_st"></div>
            <div class="ptime" id="p_time"></div>
          </div>
        </div>
      </div>

      <div class="btns">
        <button class="btn main" id="b_start">Connect</button>
        <button class="btn" id="b_update" disabled>Update</button>
        <button class="btn danger" id="b_stop" disabled>Disconnect</button>
      </div>

      <div class="logbox glass">
        <div class="cap">Log</div>
        <div id="log"></div>
      </div>
    </section>
  </div>
</main>

<div class="overlay" id="overlay">
  <div class="sheet glass">
    <div class="shead"><b>Settings</b><button id="s_close" title="Close">×</button></div>

    <div class="ss">
      <div class="t">Discord</div>
      <label class="l" for="s_id">Application ID</label>
      <input type="text" id="s_id" placeholder="Paste your Application ID">
      <div class="err" id="id_err"></div>
      <div class="shint">Required. Create an application in the Discord Developer Portal and copy its Application ID. The application's name is the fallback name Discord can show.</div>
      <div class="btnrow"><button class="btn sm" id="s_dev">Open Developer Portal</button></div>
    </div>

    <div class="ss">
      <div class="t">Appearance</div>
      <label class="l">Theme</label>
      <div class="themes" id="themes"></div>
      <div class="srow" style="margin-top:8px">
        <div><div class="sl">Glass strength</div><div class="shint">How frosted the panels look</div></div>
        <div class="rangewrap"><input type="range" id="s_glass" min="0" max="100" step="1"><span id="glass_val">50%</span></div>
      </div>
    </div>

    <div class="ss">
      <div class="t">Behavior</div>
      <div class="srow">
        <div><div class="sl">Resume status automatically</div><div class="shint">Reconnects whenever Discord opens or restarts</div></div>
        <label class="sw"><input type="checkbox" id="s_auto"><span></span></label>
      </div>
      <div class="srow">
        <div><div class="sl">Keep running in the background</div><div class="shint">Closing the window hides Larpresence in the system tray</div></div>
        <label class="sw"><input type="checkbox" id="s_bg"><span></span></label>
      </div>
      <div class="srow">
        <div><div class="sl">Start with Windows</div><div class="shint">Launches hidden at login and resumes your status. Also turns on the two options above</div></div>
        <label class="sw"><input type="checkbox" id="s_start"><span></span></label>
      </div>
      <div class="srow">
        <div><div class="sl">Keep window on top</div><div class="shint">Stays above other windows</div></div>
        <label class="sw"><input type="checkbox" id="s_top"><span></span></label>
      </div>
    </div>

    <div class="ss">
      <div class="t">Data</div>
      <div class="btnrow">
        <button class="btn sm" id="s_folder">Open settings folder</button>
        <button class="btn sm danger" id="s_reset">Reset all settings</button>
        <button class="btn sm" id="s_quit">Quit Larpresence</button>
      </div>
    </div>

    <div class="about">Larpresence v__VERSION__ · Not affiliated with Discord · Your status only shows while Larpresence is running and connected.</div>
  </div>
</div>
</div>

<script>
const TEXT_IDS = ["name","details","state","large_text","small_text","hours_ago","minutes_ago"];
const $ = id => document.getElementById(id);
const images = {large_image:"", small_image:""};
let type = "Playing";
let t0 = Date.now();

function gather(){
  const s = {activity_type:type, use_timer:$("use_timer").checked, large_image:images.large_image, small_image:images.small_image};
  TEXT_IDS.forEach(i => s[i] = $(i).value);
  return s;
}
function fill(s){
  TEXT_IDS.forEach(i => $(i).value = s[i] ?? "");
  $("use_timer").checked = !!s.use_timer;
  images.large_image = s.large_image || ""; images.small_image = s.small_image || "";
  refreshSlot("large_image"); refreshSlot("small_image");
  setType(s.activity_type || "Playing");
}
function setType(t){
  type = t;
  document.querySelectorAll("#seg button").forEach(b => b.classList.toggle("on", b.dataset.t === t));
  renderPreview();
}
function log(msg){
  const el = $("log"), d = document.createElement("div");
  const tm = document.createElement("span"); tm.className = "tm";
  tm.textContent = new Date().toTimeString().slice(0,8) + "  ";
  const m = document.createElement("span"); m.textContent = msg;
  if (msg.startsWith("✕")) m.className = "err"; else if (msg.startsWith("✓")) m.className = "ok";
  d.append(tm, m); el.append(d); el.scrollTop = el.scrollHeight;
}
let isConnected = false;
function setConnected(c){
  isConnected = c;
  $("b_start").disabled = c; $("b_update").disabled = !c; $("b_stop").disabled = !c;
  $("status").textContent = c ? "Connected" : "Not connected";
  $("status").classList.toggle("on", c);
}
const pad = n => String(n).padStart(2,"0");
const cssUrl = u => `url("${u.replace(/"/g,"%22")}")`;

function renderPreview(){
  const s = gather();
  $("p_verb").textContent = {Playing:"Playing", Listening:"Listening to", Watching:"Watching", Competing:"Competing in"}[type];
  $("p_name").textContent = s.name.trim() || "Your name";
  $("p_det").textContent = s.details; $("p_st").textContent = s.state;
  const art = $("p_art"), letter = $("p_letter"), badge = $("p_badge");
  if (s.large_image){ art.style.backgroundImage = cssUrl(s.large_image); letter.style.display = "none"; }
  else { art.style.backgroundImage = ""; letter.style.display = ""; letter.textContent = ((s.name.trim()||"L")[0]).toUpperCase(); }
  if (s.small_image){ badge.style.display = "block"; badge.style.backgroundImage = cssUrl(s.small_image); }
  else badge.style.display = "none";
  tick();
}
function tick(){
  const s = gather();
  if (!s.use_timer){ $("p_time").textContent = ""; return; }
  const off = (parseFloat(s.hours_ago)||0)*3600 + (parseFloat(s.minutes_ago)||0)*60;
  const sec = Math.max(0, Math.floor(off + (Date.now()-t0)/1000));
  $("p_time").textContent = `${pad(Math.floor(sec/3600))}:${pad(Math.floor(sec%3600/60))}:${pad(sec%60)} elapsed`;
}

/* ---------- image slots: click to browse, or drag a file in ---------- */
function refreshSlot(key){
  const slot = document.querySelector(`.slot[data-key="${key}"]`);
  const url = images[key];
  slot.classList.toggle("has", !!url);
  slot.querySelector("img").src = url || "";
}
async function handleFile(key, file){
  if (!file) return;
  if (!file.type.startsWith("image/")){ log("✕ That isn't an image file."); return; }
  if (file.size > 8*1024*1024){ log("✕ Image is larger than 8 MB."); return; }
  const slot = document.querySelector(`.slot[data-key="${key}"]`);
  slot.classList.add("loading");
  try {
    const dataUrl = await new Promise((res, rej) => {
      const r = new FileReader(); r.onload = () => res(r.result); r.onerror = () => rej(r.error); r.readAsDataURL(file);
    });
    const out = await window.pywebview.api.upload(dataUrl.split(",")[1], file.name);
    if (out.ok){ images[key] = out.url; refreshSlot(key); renderPreview(); log("✓ Image uploaded."); }
    else log("✕ Upload failed: " + out.error);
  } catch (e) { log("✕ " + e); }
  slot.classList.remove("loading");
}
document.querySelectorAll(".slot").forEach(slot => {
  const key = slot.dataset.key, input = slot.querySelector("input");
  slot.addEventListener("click", e => { if (e.target.classList.contains("x")) return; input.click(); });
  input.addEventListener("change", () => { handleFile(key, input.files[0]); input.value = ""; });
  slot.querySelector(".x").addEventListener("click", e => {
    e.stopPropagation(); images[key] = ""; refreshSlot(key); renderPreview();
  });
  ["dragenter","dragover"].forEach(ev => slot.addEventListener(ev, e => { e.preventDefault(); slot.classList.add("over"); }));
  ["dragleave","drop"].forEach(ev => slot.addEventListener(ev, e => { e.preventDefault(); slot.classList.remove("over"); }));
  slot.addEventListener("drop", e => handleFile(key, e.dataTransfer.files[0]));
});
// don't let a missed drop navigate the window to the image
["dragover","drop"].forEach(ev => window.addEventListener(ev, e => e.preventDefault()));

async function call(fn, ...args){
  try {
    const r = await window.pywebview.api[fn](...args);
    r.logs.forEach(log); setConnected(r.connected);
    if (r.needs_id) openSettings();
  } catch (e) { log("✕ " + e); }
}
document.querySelectorAll("#seg button").forEach(b => b.onclick = () => setType(b.dataset.t));
TEXT_IDS.concat(["use_timer"]).forEach(i => $(i).addEventListener("input", () => {
  if (i==="hours_ago" || i==="minutes_ago" || i==="use_timer") t0 = Date.now();
  renderPreview();
}));
$("b_start").onclick  = () => call("start", gather());
$("b_update").onclick = () => call("update", gather());
$("b_stop").onclick   = () => call("stop");
$("b_min").onclick   = () => window.pywebview.api.minimize();
$("b_close").onclick = () => window.pywebview.api.close();
setInterval(tick, 1000);

/* ---------- settings ---------- */
const THEMES = {
  midnight:{label:"Midnight", a:"rgba(70,92,150,.55)",  b:"rgba(110,76,98,.42)", accent:"#9db4ff", accent2:"#5b7fe0"},
  graphite:{label:"Graphite", a:"rgba(125,130,142,.30)", b:"rgba(85,90,100,.26)", accent:"#c9ced8", accent2:"#7c8493"},
  forest:  {label:"Forest",   a:"rgba(48,122,98,.45)",   b:"rgba(66,108,150,.30)", accent:"#7fd8b5", accent2:"#3f9f7d"},
  rose:    {label:"Rose",     a:"rgba(156,72,96,.45)",   b:"rgba(130,96,52,.32)",  accent:"#f4a3b5", accent2:"#c8587a"},
};
const app = {client_id:"", theme:"midnight", glass:50, on_top:false, auto_connect:false, background:false, run_at_startup:false};

Object.entries(THEMES).forEach(([key, t]) => {
  const c = document.createElement("button");
  c.className = "chip"; c.dataset.theme = key; c.textContent = t.label;
  c.style.background = `linear-gradient(135deg, ${t.a}, ${t.b}), #15171c`;
  c.onclick = () => { app.theme = key; applyTheme(); saveApp(); };
  $("themes").append(c);
});

function applyTheme(){
  const t = THEMES[app.theme] || THEMES.midnight, r = document.documentElement.style, g = app.glass;
  r.setProperty("--bga", t.a); r.setProperty("--bgb", t.b);
  r.setProperty("--accent", t.accent); r.setProperty("--accent2", t.accent2);
  r.setProperty("--blur", (6 + g * 0.4) + "px");
  r.setProperty("--panel", `rgba(255,255,255,${(0.02 + g * 0.0005).toFixed(3)})`);
  document.querySelectorAll(".chip").forEach(c => c.classList.toggle("on", c.dataset.theme === app.theme));
  $("glass_val").textContent = g + "%";
}
function fillApp(s){
  app.client_id = s.client_id || "";
  app.theme = (s.theme in THEMES) ? s.theme : "midnight";
  app.glass = Number.isFinite(+s.glass) ? +s.glass : 50;
  app.on_top = !!s.on_top; app.auto_connect = !!s.auto_connect;
  app.background = !!s.background; app.run_at_startup = !!s.run_at_startup;
  $("s_id").value = app.client_id; $("s_glass").value = app.glass;
  $("s_top").checked = app.on_top; $("s_auto").checked = app.auto_connect;
  $("s_bg").checked = app.background; $("s_start").checked = app.run_at_startup;
  applyTheme();
}
async function saveApp(){
  app.client_id = $("s_id").value.trim(); app.glass = +$("s_glass").value;
  app.on_top = $("s_top").checked; app.auto_connect = $("s_auto").checked;
  app.background = $("s_bg").checked; app.run_at_startup = $("s_start").checked;
  try {
    const r = await window.pywebview.api.save_app_settings(app);
    $("id_err").textContent = r.ok ? "" : r.error;
    if (r.ok && r.id_changed)
      log(isConnected ? "Application ID changed. Disconnect and connect again to use it." : "✓ Application ID saved.");
    if (r.ok && !r.startup_ok) log("✕ Couldn't set up start with Windows (Windows only).");
    if (r.ok && !r.tray_ok) log("✕ Tray icon unavailable. Run: pip install -r requirements.txt");
  } catch (e) { log("✕ " + e); }
}
function openSettings(){ $("overlay").classList.add("open"); }
function closeSettings(){ $("overlay").classList.remove("open"); }

$("b_gear").onclick = () => $("overlay").classList.contains("open") ? closeSettings() : openSettings();
$("s_close").onclick = closeSettings;
$("overlay").addEventListener("mousedown", e => { if (e.target.id === "overlay") closeSettings(); });
window.addEventListener("keydown", e => { if (e.key === "Escape") closeSettings(); });
$("s_id").addEventListener("change", saveApp);
["s_top","s_auto","s_bg"].forEach(id => $(id).addEventListener("change", saveApp));
$("s_start").addEventListener("change", () => {
  if ($("s_start").checked){ $("s_bg").checked = true; $("s_auto").checked = true; }
  saveApp();
});
$("s_quit").onclick = () => window.pywebview.api.quit_app();
$("s_glass").addEventListener("input", () => { app.glass = +$("s_glass").value; applyTheme(); });
$("s_glass").addEventListener("change", saveApp);
$("s_dev").onclick = () => window.pywebview.api.open_url("https://discord.com/developers/applications");
$("s_folder").onclick = () => window.pywebview.api.open_folder();
let resetArmed = false;
$("s_reset").onclick = async () => {
  if (!resetArmed){
    resetArmed = true; $("s_reset").textContent = "Click again to confirm";
    setTimeout(() => { resetArmed = false; $("s_reset").textContent = "Reset all settings"; }, 3000);
    return;
  }
  resetArmed = false; $("s_reset").textContent = "Reset all settings";
  const s = await window.pywebview.api.reset_settings();
  fill(s); fillApp(s); setConnected(false); $("id_err").textContent = ""; log("Settings reset.");
};

window.addEventListener("pywebviewready", async () => {
  const s = await window.pywebview.api.get_settings();
  fill(s); fillApp(s);
  if (!s.has_id){
    log("Welcome! Add your Discord Application ID in Settings to get started.");
    openSettings();
  } else if (s.auto_connect && s.active) {
    log("Resuming your status automatically…");
  } else {
    log("Open the Discord desktop app, then press Connect.");
  }
  poll();
  setInterval(poll, 2000);
});
async function poll(){
  try {
    const r = await window.pywebview.api.get_status();
    r.logs.forEach(log);
    if (r.connected !== isConnected) setConnected(r.connected);
  } catch (e) {}
}
renderPreview();
</script>
</body>
</html>
'''


def startup_tasks(hidden):
    """Runs once the window system is up (on its own thread)."""
    st = load_settings()
    STATE["want"] = bool(st.get("auto_connect") and st.get("active"))
    if st.get("run_at_startup"):
        set_startup(True)  # refreshes the path if the exe was moved (and drops the old Larpcord entry)
    ok = ensure_tray()
    if hidden and not ok:
        show_window()  # never leave the user with an invisible app
    threading.Thread(target=supervisor_loop, daemon=True).start()


def main():
    global WINDOW
    if not claim_single_instance():
        return
    migrate_old_settings()
    st = load_settings()
    hidden = "--background" in sys.argv and bool(st.get("background")) and tray_available()
    WINDOW = webview.create_window(
        "Larpresence",
        html=HTML.replace("__VERSION__", __version__),
        on_top=bool(st.get("on_top")),
        hidden=hidden,
        js_api=Api(),
        width=980,
        height=700,
        resizable=False,   # fixed size
        frameless=True,    # custom title bar in the page
        easy_drag=False,   # only the title bar drags the window
        background_color="#0d0e11",
    )
    WINDOW.events.closing += on_closing
    webview.start(startup_tasks, hidden)
    STOP.set()
    try:
        POOL.submit(close_rpc).result(timeout=5)
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
