"""
shell.py — PranshulOS
"""
import os
import sys
import threading
import time
import webview
from datetime import datetime

FLASK_URL  = "http://127.0.0.1:5000"
FLASK_HOME = "http://127.0.0.1:5000/home"
SCREEN_ASSIST_URL = "http://127.0.0.1:5000/screen-assist"

# ── Screen capture util ────────────────────────────────────────────────────────
def _take_screenshot_b64() -> str:
    """Captures the primary screen and returns a base64-encoded PNG string."""
    import mss, base64, io
    with mss.mss() as sct:
        monitor = sct.monitors[1]   # primary monitor
        img = sct.grab(monitor)
        from PIL import Image
        pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        pil.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode()


# ── API ───────────────────────────────────────────────────────────────────────
class PranshulAPI:
    def open_spotify(self):
        shortcut = r"C:\Users\Pranshul Chopra\OneDrive\Desktop\Spotify.lnk"
        if os.path.exists(shortcut):
            os.startfile(shortcut)
            return "Opened Spotify!"
        return "Spotify shortcut not found."

    def open_youtube(self):
        import webbrowser; webbrowser.open("https://youtube.com")
        return "Opened YouTube!"

    def open_linkedin(self):
        import webbrowser; webbrowser.open("https://www.linkedin.com/in/pranshul-chopra-269789371/")
        return "Opening LinkedIn..."

    def open_github(self):
        import webbrowser; webbrowser.open("https://github.com")
        return "Opening GitHub..."

    def open_whatsapp(self):
        import webbrowser; webbrowser.open("https://web.whatsapp.com")
        return "Opening WhatsApp Web..."

    def open_discord(self):
        import webbrowser; webbrowser.open("https://discord.com/app")
        return "Opening Discord..."

    def open_twitch(self):
        import webbrowser; webbrowser.open("https://twitch.tv")
        return "Opening Twitch..."

    def open_roblox(self):
        import webbrowser; webbrowser.open("https://www.roblox.com")
        return "Opening Roblox..."

    def open_steam(self):
        for path in [r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Steam\Steam.lnk"]:
            if os.path.exists(path):
                os.startfile(path)
                return "Launching Steam..."
        import webbrowser; webbrowser.open("https://store.steampowered.com")
        return "Opened Steam in browser"

    def open_warframe_market(self):
        import webbrowser; webbrowser.open("https://warframe.market/")
        return "Opening Warframe Market..."

    def chill(self):
        import webbrowser; webbrowser.open("https://youtube.com")
        return "Opened YouTube!"

    def work(self):
        spotify_shortcut = r"C:\Users\Pranshul Chopra\OneDrive\Desktop\Spotify.lnk"
        if os.path.exists(spotify_shortcut):
            os.startfile(spotify_shortcut)
        vscode_shortcut = r"C:\Users\Pranshul Chopra\OneDrive\Desktop\Visual Studio Code.lnk"
        if os.path.exists(vscode_shortcut):
            os.startfile(vscode_shortcut)
        return "Opened Spotify + VS Code!"
    def chatgpt_ai(self):
        import webbrowser
        webbrowser.open("https://chatgpt.com")
        return "Opened chatgpt"
    def open_instagram(self):
        import webbrowser
        webbrowser.open("https://instagram.com")
        return "opened instagram"
    def open_gmail(self):
        import webbrowser
        webbrowser.open("https://gmail.com")
        return "opened gmail"
    def open_slcm(self):
        import webbrowser
        webbrowser.open("https://mujslcm.jaipur.manipal.edu")
        return "opened slcm"
    def open_outlook(self):
        shortcut = r"C:\Users\Pranshul Chopra\OneDrive\Desktop\Outlook.lnk"
        if os.path.exists(shortcut):
            os.startfile(shortcut)
            return "Opened Outlook!"
        return "Outlook shortcut not found."
    def open_claude(self):
        shortcut = r"C:\Users\Pranshul Chopra\OneDrive\Desktop\Claude.lnk"
        if os.path.exists(shortcut):
            os.startfile(shortcut)
            return "Opened THE SAVIOUR , THE MESSIAH CLAUDE"
        return "Messiah left you brochacho"
    def open_muj_stella(self):
        import webbrowser
        webbrowser.open("https://www.mujstella.in")
        return "Opened Mujstella"
    def open_brave(self):
        shortcut = r"C:\Users\Pranshul Chopra\OneDrive\Desktop\Brave.lnk"
        if os.path.exists(shortcut):
            os.startfile(shortcut)
            return "Brave Opened!"
        return "Brave Aint Brave Enough for YOU"
    def start_warframe(self):
        shortcut= r"C:\Users\Pranshul Chopra\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Steam\Warframe.url"
        if os.path.exists(shortcut):
            os.startfile(shortcut)
            return "IK YOU LIKE PLAYING WISP"
        return "DONT TELL ME YOU ONLY PLAY WISP FOR HER ASSETS"
    
    def test_notification(self):
        """Fires a test toast — call from sidebar to verify notifications work."""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "fluidcb_v2"))
            from app.notifier import test_notification
            test_notification()
            return "Test notification sent!"
        except Exception as e:
            return f"Error: {e}"

    def take_screenshot_for_assist(self):
        """Called from the screen assist window to retake a screenshot."""
        try:
            b64 = _take_screenshot_b64()
            # Push to the screen assist window
            _app_ref.push_screenshot(b64)
            return "ok"
        except Exception as e:
            return f"error: {e}"

    def open_screen_assist(self):
        """Opens the screen assist window (also called from hotkey)."""
        if _app_ref:
            _app_ref.open_screen_assist_window()
        return "ok"


        h = datetime.now().hour
        if h < 12: return "Good morning, Pranshul"
        if h < 17: return "Good afternoon, Pranshul"
        return "Good evening, Pranshul"

    # ── Multi-trigger: runs ALL matching actions, returns combined message ────
    def check_trigger(self, text):
        t = text.lower().strip()

        TRIGGERS = [
            (["warframe","play warframe","start warframe"],self.start_warframe),
            (["brave open","open brave","brave"],self.open_brave),
            (["mujstella","study material"],self.open_muj_stella),
            (["help me with code","my code sucks","open claude","claude","code sucks"],self.open_claude),
            (["open outlook","outlook"],self.open_outlook),
            (["open slcm","muj slcm","check attendance","attendance","slcm"],self.open_slcm),
            (["open my mail","open mail","gmail","open gmail"],self.open_gmail),
            (["open instagram","instagram"],self.open_instagram),
            (["chatgpt","open chatgpt","open the ai","load the fucking bot"], self.chatgpt_ai),
            (["youtube", "bored", "not feeling", "too lazy", "chill"],  self.chill),
            (["start work", "stuff to do", "gotta get working", "work", "vsc"], self.work),
            (["update my profile", "update profile", "linkedin"],        self.open_linkedin),
            (["push the code", "create a repo", "add to repo", "github", "git"], self.open_github),
            (["whatsapp", "check messages", "check whatsapp"],           self.open_whatsapp),
            (["discord", "check discord"],                               self.open_discord),
            (["twitch", "watch streams", "streaming"],                   self.open_twitch),
            (["roblox", "play roblox"],                                  self.open_roblox),
            (["steam", "play games", "check games"],                     self.open_steam),
            (["warframe market", "check prices for prime",
              "check prices for mod", "check prices for mods"],          self.open_warframe_market),
            (["spotify"],                                                 self.open_spotify),
        ]

        results = []
        fired   = set()
        for keywords, fn in TRIGGERS:
            if any(kw in t for kw in keywords) and fn.__name__ not in fired:
                try:
                    msg = fn()
                    if msg:
                        results.append(msg)
                    fired.add(fn.__name__)
                except Exception as e:
                    results.append(f"Error: {e}")

        return " · ".join(results) if results else None


# ── Sidebar JS (injected on every page load) ──────────────────────────────────
INJECT_JS = """
(function() {
  if (document.getElementById('pos-sidebar')) return;
  const style = document.createElement('style');
  style.textContent = `
    #pos-sidebar {
      position: fixed; top: 0; left: 0; width: 180px; height: 100vh;
      background: #0e0e0e; border-right: 1px solid #222;
      display: flex; flex-direction: column;
      font-family: 'IBM Plex Mono', 'Courier New', monospace;
      z-index: 99999; box-sizing: border-box;
    }
    #pos-sidebar .pos-logo {
      padding: 20px 16px 14px; font-size: 11px; font-weight: 700;
      letter-spacing: 0.15em; color: #e8a84c; border-bottom: 1px solid #222;
    }
    #pos-sidebar .pos-nav { padding: 12px 10px; flex: 1; overflow-y: auto; }
    #pos-sidebar .pos-nav-btn {
      display: block; width: 100%; padding: 9px 14px; margin-bottom: 3px;
      border-radius: 8px; border: none; background: transparent; color: #4a4845;
      font-family: inherit; font-size: 13px; text-align: left; cursor: pointer;
      transition: all 0.15s;
    }
    #pos-sidebar .pos-nav-btn:hover  { background: #1c1c1c; color: #8a8880; }
    #pos-sidebar .pos-nav-btn.active { background: #1c1c1c; color: #e8a84c; }
    #pos-sidebar .pos-section {
      padding: 14px 14px 4px; font-size: 9px; letter-spacing: 0.12em;
      color: #2e2e2e; text-transform: uppercase;
    }
    #pos-sidebar .pos-ver {
      padding: 12px 16px; font-size: 9px; color: #2e2e2e;
      border-top: 1px solid #1a1a1a;
    }
    body { margin-left: 180px !important; }
  `;
  document.head.appendChild(style);

  const sb = document.createElement('div');
  sb.id = 'pos-sidebar';
  sb.innerHTML = `
    <div class="pos-logo">FLUIDCB</div>
    <div class="pos-nav">
      <div class="pos-section">Navigate</div>
      <button class="pos-nav-btn" id="btn-home" onclick="window.location.href='/home'">🏠 Home</button>
      <button class="pos-nav-btn" id="btn-chat" onclick="window.location.href='/'">💬 Chat</button>
      <button class="pos-nav-btn" id="btn-dash" onclick="window.location.href='/dashboard'">📋 Dashboard</button>
      <button class="pos-nav-btn" id="btn-docs" onclick="window.location.href='/docs'">📝 Docs</button>
      <button class="pos-nav-btn" id="btn-screen" onclick="window.pywebview.api.open_screen_assist()">🔍 Screen Assist</button>
      <div class="pos-section">Apps</div>
      <button class="pos-nav-btn" onclick="window.pywebview.api.work()">💻 Work</button>
      <button class="pos-nav-btn" onclick="window.pywebview.api.chill()">🎬 Youtube</button>
      <button class="pos-nav-btn" onclick="window.pywebview.api.open_spotify()">🎵 Spotify</button>
      <button class="pos-nav-btn" onclick="window.pywebview.api.open_whatsapp()">💬 WhatsApp</button>
      <button class="pos-nav-btn" onclick="window.pywebview.api.open_steam()">🕹️ Steam</button>
      <button class="pos-nav-btn" onclick="window.pywebview.api.open_github()">🐙 GitHub</button>
      <button class="pos-nav-btn" onclick="window.pywebview.api.open_linkedin()">🔗 LinkedIn</button>
      <button class="pos-nav-btn" onclick="window.pywebview.api.open_slcm()">⚠️ MUJ SLCM</button>
      <button class="pos-nav-btn" onclick="window.pywebview.api.open_gmail()">✉️ GMAIL </button>
      <button class="pos-nav-btn" onclick="window.pywebview.api.open_outlook()">📨 OUTLOOK </button>
      <button class="pos-nav-btn" onclick="window.pywebview.api.open_claude()">🪽 GOD OF CODE </button>


    </div>
    <div class="pos-ver">v1.0  ·  fluidcb v2</div>
  `;

  const path = window.location.pathname;
  document.body.prepend(sb);
  document.getElementById('btn-home').className = 'pos-nav-btn' + (path === '/home' ? ' active' : '');
  document.getElementById('btn-chat').className = 'pos-nav-btn' + (path === '/' ? ' active' : '');
  document.getElementById('btn-dash').className = 'pos-nav-btn' + (path === '/dashboard' ? ' active' : '');
})();
"""

# Global app reference so API methods can reach the window manager
_app_ref = None

# ── App ────────────────────────────────────────────────────────────────────────
class PranshulOS:
    def __init__(self):
        global _app_ref
        _app_ref = self
        self.api    = PranshulAPI()
        self.window = webview.create_window(
            "FLUIDCB",
            url=FLASK_HOME,
            js_api=self.api,
            width=1100, height=720,
            min_size=(860, 560),
            background_color="#0c0c0c",
        )
        self.window.events.loaded += self._on_load
        self._assist_window = None   # second window, created on demand

    def _on_load(self):
        self.window.evaluate_js(INJECT_JS)

    # ── Screen assist window ────────────────────────────────────────────────
    def open_screen_assist_window(self):
        """
        Takes screenshot FIRST, then opens the window, then pushes the image in.
        This avoids the window appearing in its own screenshot.
        """
        if self._assist_window is not None:
            # Window already open — just retake
            threading.Thread(target=self._shoot_and_push, daemon=True).start()
            return

        # Step 1: capture first (window not open yet, so it can't appear in shot)
        def _capture_then_open():
            try:
                b64 = _take_screenshot_b64()
            except Exception as e:
                print(f"[screen assist] screenshot error: {e}")
                b64 = None

            # Step 2: open the window
            self._assist_window = webview.create_window(
                "Screen Assist — FLUIDCB",
                url=SCREEN_ASSIST_URL,
                js_api=self.api,
                width=1200, height=750,
                min_size=(900, 600),
                background_color="#0c0c0c",
            )
            self._assist_window.events.closed += self._on_assist_closed

            # Step 3: push image once window has loaded
            if b64:
                def _push_when_ready():
                    # Wait for JS runtime to be ready
                    time.sleep(0.8)
                    self.push_screenshot(b64)
                self._assist_window.events.loaded += lambda: threading.Thread(
                    target=_push_when_ready, daemon=True
                ).start()

        threading.Thread(target=_capture_then_open, daemon=True).start()

    def _on_assist_closed(self):
        self._assist_window = None

    def _shoot_and_push(self):
        """Takes a screenshot and pushes the base64 PNG to the assist window."""
        try:
            b64 = _take_screenshot_b64()
            self.push_screenshot(b64)
        except Exception as e:
            print(f"[screen assist] screenshot error: {e}")

    def push_screenshot(self, b64: str):
        if self._assist_window:
            # Escape backticks in the b64 string (shouldn't happen but be safe)
            safe = b64.replace('`', '')
            self._assist_window.evaluate_js(f"window.loadScreenshot(`{safe}`)")

    # ── Hotkey listener (runs in background thread) ─────────────────────────
    def _start_hotkey_listener(self):
        """
        Listens for Ctrl+Alt+S globally.
        Requires the `keyboard` package (pip install keyboard).
        """
        try:
            import keyboard
            keyboard.add_hotkey('ctrl+alt+v', self.open_screen_assist_window, suppress=False)
            keyboard.wait()   # blocks thread forever
        except ImportError:
            print("[screen assist] `keyboard` package not installed — hotkey disabled.")
            print("  Install with: pip install keyboard")
        except Exception as e:
            print(f"[screen assist] hotkey listener error: {e}")

    def run(self):
        # Start global hotkey listener in background
        threading.Thread(target=self._start_hotkey_listener, daemon=True).start()
        webview.start(debug=False)

def launch():
    app = PranshulOS()
    app.run()
