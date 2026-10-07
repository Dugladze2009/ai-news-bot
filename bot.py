"""
AI & Tech Hub [GE] — AI News Bot
ოფიციალური AI ბლოგების RSS → ქართული შეჯამება → Discord webhook
"""
import os, re, json, html, time, calendar
import feedparser, requests

FEEDS = [
    {"name": "OpenAI",          "url": "https://openai.com/news/rss.xml",                        "color": 0x10A37F, "emoji": "🟢"},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml",                    "color": 0x4285F4, "emoji": "🔵"},
    {"name": "Google AI",       "url": "https://blog.google/innovation-and-ai/technology/ai/rss/", "color": 0x34A853, "emoji": "🔵"},
    {"name": "Hugging Face",    "url": "https://huggingface.co/blog/feed.xml",                   "color": 0xFFD21E, "emoji": "🤗"},
]

WEBHOOK      = os.environ.get("DISCORD_WEBHOOK_URL", "")
ROLE_ID      = os.environ.get("PING_ROLE_ID", "").strip()       # optional: 🤖 AI News Ping role
ANTHROPIC_KEY= os.environ.get("ANTHROPIC_API_KEY", "").strip()
GEMINI_KEY   = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest").strip()
DRY_RUN      = os.environ.get("DRY_RUN") == "1"
MAX_POSTS    = int(os.environ.get("MAX_POSTS_PER_RUN", "5"))
STATE_FILE   = os.environ.get("STATE_FILE", "seen.json")
MAX_AGE_DAYS = 3   # ძველ სტატიებს არ ვპოსტავთ

def clean(text, limit=3000):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]

# ---------- ქართული შეჯამება ----------
PROMPT = """You are the news editor of a Georgian Discord community about AI.
Rewrite this official AI announcement for Georgian readers.
Return ONLY JSON: {{"title": "...", "summary": "..."}}
- "title": natural Georgian headline, max 90 characters. Keep product/model/company names in English.
- "summary": 2-3 short Georgian sentences: what was announced and why it matters. Max 400 characters. No hype, no invented facts — only what the text says.

Source: {source}
Title: {title}
Text: {text}"""

def parse_json(s):
    m = re.search(r"\{.*\}", s, re.S)
    d = json.loads(m.group(0))
    return d["title"].strip(), d["summary"].strip()

def via_anthropic(p):
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=60, headers={
        "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-haiku-4-5-20251001", "max_tokens": 600, "messages": [{"role": "user", "content": p}]})
    r.raise_for_status()
    return parse_json(r.json()["content"][0]["text"])

def via_gemini(p):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    r = requests.post(url, timeout=60, headers={"x-goog-api-key": GEMINI_KEY},
        json={"contents": [{"parts": [{"text": p}]}], "generationConfig": {"responseMimeType": "application/json"}})
    r.raise_for_status()
    return parse_json(r.json()["candidates"][0]["content"]["parts"][0]["text"])

def via_translate(title, text):
    from deep_translator import GoogleTranslator
    tr = GoogleTranslator(source="auto", target="ka")
    summary = text[:450]
    if len(text) > 450:
        summary = summary.rsplit(" ", 1)[0] + "…"
    return tr.translate(title), (tr.translate(summary) if summary else "")

def to_georgian(source, title, text):
    p = PROMPT.format(source=source, title=title, text=text[:2500])
    for name, fn in (("anthropic", via_anthropic if ANTHROPIC_KEY else None),
                     ("gemini", via_gemini if GEMINI_KEY else None)):
        if fn:
            try: return fn(p)
            except Exception as e: print(f"  ! {name} failed: {e}")
    try: return via_translate(title, text)
    except Exception as e: print(f"  ! translate failed: {e}")
    return title, text[:400]

# ---------- Discord ----------
def image_of(entry):
    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key, []) or []:
            if m.get("url"): return m["url"]
    for l in entry.get("links", []):
        if l.get("rel") == "enclosure" and str(l.get("type", "")).startswith("image"):
            return l.get("href")
    m = re.search(r'<img[^>]+src="([^"]+)"', entry.get("summary", "") or "")
    return m.group(1) if m else None

def post(feed, entry, ka_title, ka_summary):
    ts = entry.get("published_parsed") or entry.get("updated_parsed")
    embed = {
        "author": {"name": f"{feed['emoji']} {feed['name']} · ოფიციალური განცხადება"},
        "title": ka_title[:256],
        "url": entry.link,
        "description": f"{ka_summary}\n\n🔗 **[წაიკითხე სრულად]({entry.link})**"[:4000],
        "color": feed["color"],
        "footer": {"text": f"AI & Tech Hub [GE] • ორიგინალი: {clean(entry.get('title',''), 150)}"},
    }
    if ts: embed["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", ts)
    img = image_of(entry)
    if img: embed["image"] = {"url": img}
    payload = {"username": "AI News 🇬🇪", "embeds": [embed], "allowed_mentions": {"parse": []}}
    if ROLE_ID:
        payload["content"] = f"<@&{ROLE_ID}>"
        payload["allowed_mentions"] = {"roles": [ROLE_ID]}
    if DRY_RUN or not WEBHOOK:
        print(json.dumps(payload, ensure_ascii=False, indent=2)); return True
    for _ in range(3):
        r = requests.post(WEBHOOK, json=payload, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.json().get("retry_after", 2))); continue
        r.raise_for_status(); return True
    return False

# ---------- main ----------
def main():
    try: seen = json.load(open(STATE_FILE, encoding="utf-8"))
    except FileNotFoundError: seen = {}
    first_run = not seen
    new_items = []
    for feed in FEEDS:
        try:
            d = feedparser.parse(feed["url"], agent="Mozilla/5.0 (AI-Tech-Hub-GE news bot)")
        except Exception as e:
            print(f"! {feed['name']}: {e}"); continue
        print(f"{feed['name']}: {len(d.entries)} entries")
        known = set(seen.get(feed["name"], []))
        entries = [e for e in d.entries if e.get("link")]
        if first_run:
            # პირველ გაშვებაზე: თითო ფიდიდან მხოლოდ ბოლო სტატია, დანარჩენი "ნანახად" ინიშნება
            seen[feed["name"]] = [e.link for e in entries]
            if entries: new_items.append((feed, entries[0]))
            continue
        for e in entries:
            if e.link in known: continue
            ts = e.get("published_parsed") or e.get("updated_parsed")
            if ts and time.time() - calendar.timegm(ts) > MAX_AGE_DAYS * 86400:
                known.add(e.link); continue
            new_items.append((feed, e))
        seen[feed["name"]] = list(known)
    # ძველიდან ახლისკენ
    new_items.sort(key=lambda x: calendar.timegm(x[1].get("published_parsed") or time.gmtime(0)))
    posted = 0
    for feed, e in new_items:
        if posted >= MAX_POSTS: break   # დანარჩენი შემდეგ გაშვებაზე
        title, text = clean(e.get("title", ""), 300), clean(e.get("summary", "") or e.get("description", ""))
        print(f"→ {feed['name']}: {title}")
        ka_title, ka_summary = to_georgian(feed["name"], title, text or title)
        try:
            ok = post(feed, e, ka_title, ka_summary)
        except Exception as ex:
            print(f"  ! post failed: {ex}"); ok = False
        if ok:
            posted += 1
            lst = seen.setdefault(feed["name"], [])
            if e.link not in lst: lst.append(e.link)
            time.sleep(1.5)
    for k in seen: seen[k] = seen[k][-300:]
    json.dump(seen, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"done: {posted} posted")

if __name__ == "__main__":
    main()
