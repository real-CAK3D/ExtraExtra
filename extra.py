#!/usr/bin/env python3
"""EXTRA! EXTRA! — the Garden's one-page special editions, printed only when something big happens.

  extra.py publish --headline "..." --body "..." [--kind outage|all-clear|alert|win] [--agent NAME] [--todo "what to do"] [--key dedupe-key]
  extra.py build           (reprint the home page, back issues and the rack's latest.json)

Any agent can publish one (the watcher does it for machines going dark and crashed shifts). Each extra rings CAK3D's phone
through The Corner Chronicle. The same --key is never published twice in a day.
"""
import argparse, datetime as dt, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
sys.path.insert(0, ROOT)
import pubkit as pk   # noqa: E402
from pubkit import e   # noqa: E402

CSS = os.path.join(ROOT, "extra-extra.css")
KINDS = {"outage": ("🚨", "BREAKING"), "all-clear": ("✅", "ALL CLEAR"), "alert": ("⚠️", "ALERT"), "win": ("🎉", "GOOD NEWS")}


def sheet(x, up="../"):
    icon, word = KINDS.get(x.get("kind"), KINDS["alert"])
    when = dt.datetime.fromisoformat(x["at"])
    body = "".join("<p>%s</p>" % e(p) for p in re.split(r"\n\s*\n", x.get("body") or "") if p.strip())
    return ('<div class="xx-sheet xx-%s"><div class="xx-mast"><a class="xx-seal" href="/" aria-label="The Corner Chronicle"><svg viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" stroke-width="5"/><path d="M24 78h72v-22l-36-18-36 18z" fill="none" stroke="currentColor" stroke-width="6" stroke-linejoin="round"/><rect x="36" y="60" width="14" height="18" fill="currentColor"/><rect x="62" y="60" width="20" height="10" fill="currentColor"/><path d="M74 38c4-8 12-8 10-16M82 36c6-6 12-4 12-12" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/></svg></a>'
            '<div class="xx-cry">EXTRA! EXTRA!</div><div class="xx-edition">SPECIAL EDITION · %s · %s</div></div>'
            '<div class="xx-flag">%s %s</div><h1 class="xx-head">%s</h1>%s<div class="xx-body">%s</div>%s'
            '<div class="xx-foot"><a href="%sarchive.html">Every Extra ›</a> · printed %s</div></div>'
            % (e(x.get("kind")), e(when.strftime("%A, %B %-d, %Y")), e(when.strftime("%-I:%M %p")), icon, word, e(x.get("headline")),
               ('<div class="xx-by">Reported by %s</div>' % e(x["agent"])) if x.get("agent") else "", body,
               ('<div class="xx-todo"><b>What to do</b><p>%s</p></div>' % e(x["todo"])) if x.get("todo") else "", up, e(when.strftime("%-I:%M %p"))))


def all_extras():
    d = os.path.join(ROOT, "data")
    return sorted((pk.load(os.path.join(d, f)) for f in os.listdir(d) if f.endswith(".json")), key=lambda x: x.get("at", ""), reverse=True) if os.path.isdir(d) else []


def build():
    xs = [x for x in all_extras() if x.get("id")]
    os.makedirs(os.path.join(SITE, "issues"), exist_ok=True)
    for x in xs:
        out = os.path.join(SITE, "issues", x["id"] + ".html")
        open(out, "w").write(pk.shell("EXTRA! " + x.get("headline", ""), sheet(x), CSS, "xx-page", "#b3261e"))   # reprint every time so style fixes reach old extras
    now = dt.datetime.now().astimezone()
    fresh = [x for x in xs if now - dt.datetime.fromisoformat(x["at"]) < dt.timedelta(hours=48)]
    if xs:
        home = sheet(xs[0], up="")
    else:
        home = ('<div class="xx-sheet xx-quiet"><div class="xx-mast"><a class="xx-seal" href="/" aria-label="The Corner Chronicle"><svg viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" stroke-width="5"/><path d="M24 78h72v-22l-36-18-36 18z" fill="none" stroke="currentColor" stroke-width="6" stroke-linejoin="round"/><rect x="36" y="60" width="14" height="18" fill="currentColor"/><rect x="62" y="60" width="20" height="10" fill="currentColor"/><path d="M74 38c4-8 12-8 10-16M82 36c6-6 12-4 12-12" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/></svg></a>'
                '<div class="xx-cry">EXTRA! EXTRA!</div><div class="xx-edition">NO SPECIAL EDITIONS</div></div>'
                '<h1 class="xx-head">All quiet in the Garden</h1><div class="xx-body"><p>Extras only print when something big happens — a machine goes dark, '
                'a night shift crashes, or there\'s news that can\'t wait for tomorrow\'s Double Wide. You\'ll get a notice the moment one hits.</p></div></div>')
    open(os.path.join(SITE, "index.html"), "w").write(pk.shell("EXTRA! EXTRA!", home, CSS, "xx-page", "#b3261e"))
    items = "".join('<li><a href="issues/%s.html">%s %s</a> <span class="small">%s</span></li>'
                    % (e(x["id"]), KINDS.get(x.get("kind"), KINDS["alert"])[0], e(x.get("headline")), e(dt.datetime.fromisoformat(x["at"]).strftime("%b %-d, %-I:%M %p"))) for x in xs)
    pk.archive_page(SITE, CSS, "xx-arch", "Extra! Extra!", "every special edition", items, "🚨")
    pk.latest(SITE, "Extra! Extra!", (xs[0]["at"][:10] if xs else now.date().isoformat()),
              (xs[0]["headline"] if xs else "All quiet — no special editions"), ("issues/%s.html" % xs[0]["id"]) if xs else "",
              [x["id"] for x in fresh], active=bool(fresh))


def publish(a):
    now = dt.datetime.now().astimezone()
    key = a.key or re.sub(r"[^a-z0-9]+", "-", a.headline.lower())[:40]
    log = pk.load(os.path.join(ROOT, "private", "keys.json"), {})
    if log.get(key) == now.date().isoformat():
        print("extra: already published today (%s)" % key)
        return
    x = {"id": now.strftime("%Y-%m-%dT%H%M"), "at": now.isoformat(timespec="seconds"), "kind": a.kind, "headline": a.headline,
         "body": a.body, "agent": a.agent, "todo": a.todo, "key": key}
    pk.save(os.path.join(ROOT, "data", x["id"] + ".json"), x)
    log[key] = now.date().isoformat()
    pk.save(os.path.join(ROOT, "private", "keys.json"), log)
    build()
    pk.notify("%s EXTRA! %s" % (KINDS.get(a.kind, KINDS["alert"])[0], a.headline), (a.body or "")[:140], "/extra-extra/")
    print("extra published:", x["id"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("publish")
    p.add_argument("--headline", required=True)
    p.add_argument("--body", default="")
    p.add_argument("--kind", default="alert", choices=list(KINDS))
    p.add_argument("--agent", default="")
    p.add_argument("--todo", default="")
    p.add_argument("--key", default="")
    sub.add_parser("build")
    a = ap.parse_args()
    publish(a) if a.cmd == "publish" else build()
