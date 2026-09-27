#!/usr/bin/env python3
"""Extra! Extra!'s watcher (every 15 minutes): prints a special edition when a Garden machine has been dark for 30+ minutes
(and an all-clear when it's back), or when an agent's night shift crashes. State lives in private/watch.json."""
import datetime as dt, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import pubkit as pk   # noqa: E402

MACHINES = {"thebak3ry": "theBAK3RY", "hack-safe": "Hack-Safe", "mappi3": "MapPI3", "nukebox": "NukeBox", "cak3d-oracle-vm": "the X VM"}
DARK_AFTER = dt.timedelta(minutes=30)
STATE = os.path.join(ROOT, "private", "watch.json")
RELAY_LOG = os.path.join(pk.HERMES, "logs", "relay.log")


def extra(**kw):
    args = [sys.executable, os.path.join(ROOT, "extra.py"), "publish"]
    for k, v in kw.items():
        args += ["--" + k, str(v)]
    subprocess.run(args, check=False, timeout=180)


def main():
    st = pk.load(STATE, {"machines": {}, "relay_pos": 0})
    now = dt.datetime.now().astimezone()
    try:
        peers = json.loads(subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=30).stdout).get("Peer") or {}
    except Exception:
        peers = {}
    seen = {}
    for p in peers.values():
        host = str(p.get("DNSName", "")).split(".")[0]
        if host in MACHINES:
            seen[host] = bool(p.get("Online"))
    for host, name in MACHINES.items():
        if host not in seen:
            continue
        m = st["machines"].setdefault(host, {"online": True, "since": now.isoformat(), "extra": False})
        if seen[host] != m["online"]:
            m.update(online=seen[host], since=now.isoformat())
            if seen[host] and m.get("extra"):
                down = now - dt.datetime.fromisoformat(m.get("went_dark", now.isoformat()))
                extra(kind="all-clear", headline="%s is back online" % name, agent="The Gardiner", key="back-%s-%s" % (host, now.strftime("%H")),
                      body="%s answered the Garden again after about %d minutes in the dark." % (name, max(1, down.total_seconds() // 60)))
                m["extra"] = False
            if not seen[host]:
                m["went_dark"] = now.isoformat()
        elif not m["online"] and not m.get("extra") and now - dt.datetime.fromisoformat(m["since"]) >= DARK_AFTER:
            extra(kind="outage", headline="%s goes dark" % name, agent="The Gardiner", key="dark-%s" % host,
                  body="%s has been offline on the tailnet for more than 30 minutes. The agents can't reach it until it's back." % name,
                  todo="Check its power and network. If it's a Pi, look for the red/green lights and give it a gentle power cycle.")
            m["extra"] = True
    try:   # crashed night shifts from the relay log (only lines written since the last check)
        size = os.path.getsize(RELAY_LOG)
        pos = st.get("relay_pos", 0) if st.get("relay_pos", 0) <= size else 0
        with open(RELAY_LOG, errors="ignore") as f:
            f.seek(pos)
            for line in f:
                m = re.search(r"\[([\w-]+)\] finished '([^']+)' status=error.*?err=(.*)", line)
                if m:
                    extra(kind="alert", headline="%s's shift crashed" % m.group(2).replace("Relay: ", ""), agent="The Gardiner",
                          key="crash-%s" % re.sub(r"\W+", "-", m.group(2).lower()),
                          body="The job '%s' ended with an error: %s" % (m.group(2), m.group(3).strip()[:200] or "no details"),
                          todo="Look at the Relay review in the morning paper, or ask The Gardiner in Discord.")
            st["relay_pos"] = f.tell()
    except FileNotFoundError:
        pass
    pk.save(STATE, st)


if __name__ == "__main__":
    main()
