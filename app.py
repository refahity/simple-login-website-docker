# app.py
from flask import Flask, request, jsonify, session, redirect, url_for, make_response
import os, json
from collections import defaultdict, deque
from datetime import datetime, timedelta

app = Flask(__name__)

# --- Demo users (فقط برای لَب) ---
USERS = {
    "alice": "alice123",
    "bob": "bob123",
    "admin": "admin123",  # برای ورود به داشبورد
}

# --- Session / Config ---
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-prod")  # برای سشن
DEMO_SECRET = os.getenv("DEMO_SECRET", "changeme")  # برای شبیه‌سازی امن

# --- Rate limit ---
FAIL_BUCKET = defaultdict(list)  # ip -> [timestamps]
RATE_LIMIT_N = 1000
RATE_LIMIT_WINDOW = timedelta(minutes=1)

# --- Event buffer (برای نمایش در داشبورد) ---
EVENTS = deque(maxlen=1000)  # آخرین 1000 رو نگه می‌داریم


def log_event(event: dict):
    """Log to stdout + keep in-memory for dashboard"""
    EVENTS.append(event)
    print(json.dumps(event, ensure_ascii=False), flush=True)


def is_logged_in():
    return "user" in session


@app.get("/")
def login_page():
    """صفحه HTML لاگین (ساده و بدون Jinja)"""
    if is_logged_in():
        return redirect(url_for("dashboard"))
    html = f"""
<!doctype html>
<html lang="fa">
<head>
<meta charset="utf-8">
<title>Login</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ font-family: sans-serif; background:#0f172a; color:#e2e8f0; display:flex; align-items:center; justify-content:center; height:100vh; }}
.card {{ background:#111827; padding:24px; border-radius:16px; width: 360px; box-shadow: 0 10px 30px rgba(0,0,0,.4); }}
h1 {{ margin:0 0 12px 0; font-size:20px; }}
label {{ display:block; margin:10px 0 6px; font-size:14px; }}
input[type=text], input[type=password] {{
  width:100%; padding:10px; border-radius:10px; border:1px solid #374151; background:#0b1220; color:#e2e8f0;
}}
button {{
  width:100%; padding:10px; border:0; border-radius:10px; background:#2563eb; color:#fff; font-weight:700; margin-top:14px; cursor:pointer;
}}
.small {{ font-size:12px; opacity:.8; margin-top:10px; }}
.alert {{ background:#7f1d1d; color:#fee2e2; padding:8px 10px; border-radius:8px; margin-bottom:10px; display:none; }}
</style>
</head>
<body>
  <div class="card">
    <h1>Login</h1>
    <div id="msg" class="alert"></div>
    <form id="f">
      <label>Username</label>
      <input name="username" type="text" required>
      <label>Password</label>
      <input name="password" type="password" required>
      <button type="submit">Sign in</button>
    </form>
    <div class="small">Demo users: alice/alice123, bob/bob123, admin/admin123</div>
  </div>
<script>
const f = document.getElementById('f');
const msg = document.getElementById('msg');
f.addEventListener('submit', async (e) => {{
  e.preventDefault();
  const data = new URLSearchParams(new FormData(f));
  const r = await fetch('/login', {{ method:'POST', body:data }});
  if (r.status === 200) {{
    location.href = '/dashboard';
  }} else {{
    const j = await r.json().catch(_=>({{error:'Login failed'}}));
    msg.textContent = j.error || 'Unauthorized';
    msg.style.display = 'block';
  }}
}});
</script>
</body>
</html>
"""
    return make_response(html)


@app.post("/login")
def login():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent", "-")
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    now = datetime.utcnow()

    # Rate-limit (ساده)
    FAIL_BUCKET[ip] = [t for t in FAIL_BUCKET[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(FAIL_BUCKET[ip]) >= RATE_LIMIT_N:
        log_event({
            "t": now.isoformat(), "ip": ip, "ua": ua, "user": username,
            "event": "login_rate_limited", "n_fail": len(FAIL_BUCKET[ip])
        })
        return jsonify(error="Too many attempts"), 429

    ok = USERS.get(username) == password
    log_event({
        "t": now.isoformat(), "ip": ip, "ua": ua, "user": username,
        "event": "login_success" if ok else "login_failure"
    })

    if ok:
        session["user"] = username
        return jsonify(status="ok"), 200
    else:
        FAIL_BUCKET[ip].append(now)
        return jsonify(error="Invalid credentials", status="fail"), 401


@app.get("/dashboard")
def dashboard():
    """داشبورد ساده: خوش‌آمد + نمایش زنده لاگ‌ها + شبیه‌ساز دمو"""
    if not is_logged_in():
        return redirect(url_for("login_page"))
    user = session["user"]
    html = f"""
<!doctype html>
<html lang="fa">
<head>
<meta charset="utf-8">
<title>Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ font-family: ui-sans-serif, system-ui; background:#0f172a; color:#e2e8f0; margin:0; }}
.topbar {{ display:flex; justify-content:space-between; align-items:center; padding:12px 16px; background:#111827; position:sticky; top:0; }}
.btn {{ background:#2563eb; color:#fff; border:none; border-radius:10px; padding:8px 12px; cursor:pointer; }}
.wrap {{ display:grid; grid-template-columns: 1fr 360px; gap:16px; padding:16px; }}
.card {{ background:#111827; padding:16px; border-radius:16px; box-shadow:0 8px 24px rgba(0,0,0,.35); }}
h2 {{ margin:0 0 12px; font-size:18px; }}
pre {{ white-space: pre-wrap; word-break: break-word; }}
label, input {{ display:block; width:100%; }}
input[type=text], input[type=number] {{
  background:#0b1220; color:#e2e8f0; border:1px solid #374151; border-radius:8px; padding:8px; margin-top:6px; margin-bottom:10px;
}}
.small {{ font-size:12px; opacity:.8; }}
.logline {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:12px; padding:2px 0; border-bottom:1px dashed #334155; }}
.success {{ color:#86efac; }}
.fail {{ color:#fda4af; }}
.rate {{ color:#fde68a; }}
</style>
</head>
<body>
  <div class="topbar">
    <div>Hi, <b>{user}</b></div>
    <div>
      <a class="btn" href="/logout">Logout</a>
    </div>
  </div>

  <div class="wrap">
    <div class="card">
      <h2>Login Events (live)</h2>
      <div id="logs"></div>
      <div class="small">Auto-refresh every 2s</div>
    </div>

    <div class="card">
      <h2>Demo Generator</h2>
      <label>DEMO_SECRET</label>
      <input id="secret" type="text" placeholder="changeme">
      <label>IP</label>
      <input id="ip" type="text" value="203.0.113.55">
      <label>Count</label>
      <input id="count" type="number" value="20" min="1" max="500">
      <button class="btn" id="btnSim">Generate Failures</button>
      <div id="msg" class="small" style="margin-top:10px;"></div>
    </div>
  </div>

<script>
let lastLen = 0;

async function fetchEvents() {{
  const r = await fetch('/api/events');
  const data = await r.json();
  if (!Array.isArray(data)) return;
  const logs = document.getElementById('logs');
  logs.innerHTML = '';
  data.slice(-200).reverse().forEach(ev => {{
    const div = document.createElement('div');
    div.className = 'logline ' + (ev.event==='login_success' ? 'success' : (ev.event==='login_rate_limited' ? 'rate' : 'fail'));
    div.textContent = `[${{ev.t}}] ${{ev.ip}} ${{ev.user}} → ${{ev.event}} (UA=${{ev.ua||'-'}})`;
    logs.appendChild(div);
  }});
}}
setInterval(fetchEvents, 2000);
fetchEvents();

document.getElementById('btnSim').addEventListener('click', async () => {{
  const s = document.getElementById('secret').value || 'changeme';
  const ip = document.getElementById('ip').value || '10.10.10.10';
  const count = document.getElementById('count').value || 20;
  const r = await fetch(`/simulate?count=${{count}}&ip=${{encodeURIComponent(ip)}}`, {{
    method: 'POST',
    headers: {{ 'X-Demo-Secret': s }}
  }});
  const j = await r.json().catch(_=>({{error:'err'}}));
  const msg = document.getElementById('msg');
  msg.textContent = r.ok ? `Generated: ${{j.generated}}` : (j.error || 'forbidden');
}});
</script>
</body>
</html>
"""
    return make_response(html)


@app.get("/api/events")
def api_events():
    """آخرین رویدادها به‌صورت JSON برای داشبورد"""
    return jsonify(list(EVENTS))


@app.get("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login_page"))


@app.post("/simulate")
def simulate():
    """شبیه‌سازی «الگوی حمله» (ایمن، بدون حمله واقعی)"""
    if request.headers.get("X-Demo-Secret") != DEMO_SECRET:
        return jsonify(error="forbidden"), 403
    count = int(request.args.get("count", "50"))
    ip = request.args.get("ip", "10.10.10.10")
    ua = "DemoAttack/1.0"
    now = datetime.utcnow()
    for i in range(count):
        log_event({
            "t": (now + timedelta(seconds=i)).isoformat(),
            "ip": ip, "ua": ua, "user": "alice", "event": "login_failure"
        })
    return jsonify(ok=True, generated=count)


if __name__ == "__main__":
    # در لَب: 0.0.0.0 برای دسترسی شبکه‌ای
    app.run(host="0.0.0.0", port=5000, debug=True)