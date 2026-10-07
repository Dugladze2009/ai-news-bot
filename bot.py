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
FORUM        = os.environ.get("FORUM_CHANNEL") == "1"
TEST_URL     = os.environ.get("TEST_URL", "").strip()   # Run workflow → ერთი კონკრეტული სტატიის ტესტი   # თუ #ai-news ფორუმ-არხია: თითო სტატია = ცალკე პოსტი
MAX_POSTS    = int(os.environ.get("MAX_POSTS_PER_RUN", "5"))
STATE_FILE   = os.environ.get("STATE_FILE", "seen.json")
MAX_AGE_DAYS = 3   # ძველ სტატიებს არ ვპოსტავთ
FULL_ARTICLE = os.environ.get("FULL_ARTICLE", "1") == "1"         # მთლიანი სტატიის თარგმნა
MAX_SOURCE_CHARS = int(os.environ.get("MAX_SOURCE_CHARS", "9000"))  # ინგლისური ტექსტის ლიმიტი
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
CHUNK = 3900  # Discord embed description limit is 4096

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
    if r.status_code >= 400: raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    return parse_json(r.json()["content"][0]["text"])

def via_gemini(p):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    r = requests.post(url, timeout=60, headers={"x-goog-api-key": GEMINI_KEY},
        json={"contents": [{"parts": [{"text": p}]}], "generationConfig": {"responseMimeType": "application/json"}})
    if r.status_code >= 400: raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
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

# ---------- მთლიანი სტატია ----------
def fetch_article(url):
    """სტატიის გვერდიდან მთავარი ტექსტის ამოღება (markdown-ის მსგავსად)."""
    try:
        import trafilatura
        r = requests.get(url, timeout=25, headers={"User-Agent": UA})
        r.raise_for_status()
        txt = trafilatura.extract(r.text, output_format="markdown", include_links=False,
                                  include_images=False, include_tables=False, favor_precision=True)
        return (txt or "").strip()
    except Exception as e:
        print(f"  ! article fetch failed: {e}")
        return ""

FULL_PROMPT = """You are the news editor of a Georgian Discord community about AI.
Translate this official AI article into natural, fluent Georgian for Discord.
Rules:
- First line: the Georgian headline only (max 90 characters). Then one empty line. Then the article body.
- Translate the WHOLE article faithfully; do not add facts or opinions. You may drop boilerplate (cookie notices, "share this", author bios, footnotes, legal text).
- Keep product, model, company and person names in English.
- Formatting: Discord markdown only. Section headings as **bold** on their own line. Lists with "• ". Short paragraphs. No # headings, no tables, no links.
- Output only the translation, nothing else.

Source: {source}
Original title: {title}

Article:
{text}"""

def split_title_body(out, fallback_title):
    out = out.strip().strip("`").strip()
    lines = out.split("\n", 1)
    title = lines[0].strip().strip("*#").strip()
    body = lines[1].strip() if len(lines) > 1 else ""
    if not body or len(title) > 150:
        return fallback_title, out
    return title, body

def full_via_anthropic(p):
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=120, headers={
        "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-haiku-4-5-20251001", "max_tokens": 16000, "messages": [{"role": "user", "content": p}]})
    if r.status_code >= 400: raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()["content"][0]["text"]

def full_via_gemini(p):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    r = requests.post(url, timeout=120, headers={"x-goog-api-key": GEMINI_KEY},
        json={"contents": [{"parts": [{"text": p}]}], "generationConfig": {"maxOutputTokens": 32000}})
    if r.status_code >= 400: raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(x.get("text", "") for x in parts if not x.get("thought"))

def full_via_translate(title, text):
    from deep_translator import GoogleTranslator
    tr = GoogleTranslator(source="auto", target="ka")
    out, buf = [], ""
    for para in text.split("\n"):
        if len(buf) + len(para) > 4000:
            out.append(tr.translate(buf) or ""); buf = ""
        buf += para + "\n"
    if buf.strip(): out.append(tr.translate(buf) or "")
    return tr.translate(title), "\n".join(out).strip()

def translate_full(source, title, article):
    text = article[:MAX_SOURCE_CHARS]
    if len(article) > MAX_SOURCE_CHARS:
        text = text.rsplit("\n", 1)[0]
    p = FULL_PROMPT.format(source=source, title=title, text=text)
    for name, fn in (("anthropic", full_via_anthropic if ANTHROPIC_KEY else None),
                     ("gemini", full_via_gemini if GEMINI_KEY else None)):
        if fn:
            try:
                out = fn(p)
                if out and len(out) > 200: return split_title_body(out, title)
            except Exception as e: print(f"  ! {name} full failed: {e}")
    try: return full_via_translate(title, text)
    except Exception as e: print(f"  ! translate full failed: {e}")
    return None

def chunks(text, size=CHUNK):
    """ტექსტის დაყოფა აბზაცების მიხედვით, თითო ნაწილი <= size."""
    parts, cur = [], ""
    for para in text.split("\n"):
        while len(para) > size:            # ძალიან გრძელი აბზაცი
            cut = para[:size].rsplit(" ", 1)[0] or para[:size]
            if cur: parts.append(cur.rstrip()); cur = ""
            parts.append(cut); para = para[len(cut):].lstrip()
        if len(cur) + len(para) + 1 > size:
            parts.append(cur.rstrip()); cur = ""
        cur += para + "\n"
    if cur.strip(): parts.append(cur.rstrip())
    return [p for p in parts if p.strip()]

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

def send(payload, thread_id=None):
    if DRY_RUN or not WEBHOOK:
        print(json.dumps(payload, ensure_ascii=False, indent=2)[:1500]); return {"channel_id": "dry"}
    url = WEBHOOK + "?wait=true" + (f"&thread_id={thread_id}" if thread_id else "")
    for _ in range(4):
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.json().get("retry_after", 2)) + 0.5); continue
        r.raise_for_status(); return r.json()
    raise RuntimeError("rate limited")

def post_full(feed, entry, ka_title, body):
    """სრული სტატია: პირველი embed სათაურით და სურათით, შემდეგ გაგრძელება."""
    ts = entry.get("published_parsed") or entry.get("updated_parsed")
    parts = chunks(body)
    n = len(parts)
    img = image_of(entry)
    thread_id = None
    for i, part in enumerate(parts):
        last = i == n - 1
        embed = {"description": part + (f"\n\n🔗 **[ორიგინალი სტატია]({entry.link})**" if last else ""),
                 "color": feed["color"]}
        if i == 0:
            embed.update({"author": {"name": f"{feed['emoji']} {feed['name']} · ოფიციალური განცხადება"},
                          "title": ka_title[:256], "url": entry.link})
            if img: embed["image"] = {"url": img}
        if n > 1:
            embed["footer"] = {"text": f"ნაწილი {i+1}/{n} • AI & Tech Hub [GE]"}
        else:
            embed["footer"] = {"text": "AI & Tech Hub [GE]"}
        if last and ts: embed["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", ts)
        payload = {"username": "AI News 🇬🇪", "embeds": [embed], "allowed_mentions": {"parse": []}}
        if i == 0:
            if ROLE_ID:
                payload["content"] = f"<@&{ROLE_ID}>"
                payload["allowed_mentions"] = {"roles": [ROLE_ID]}
            if FORUM:
                payload["thread_name"] = ka_title[:100]
        res = send(payload, thread_id)
        if i == 0 and FORUM:
            thread_id = res.get("channel_id")
        time.sleep(1.2)
    return True

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
    send(payload)
    return True

# ---------- main ----------
def process(feed, e):
    title, text = clean(e.get("title", ""), 300), clean(e.get("summary", "") or e.get("description", ""))
    print(f"→ {feed['name']}: {title}")
    print(f"  translators: anthropic={'yes' if ANTHROPIC_KEY else 'no'} gemini={'yes' if GEMINI_KEY else 'NO KEY'} ({GEMINI_MODEL})")
    ok = False
    if FULL_ARTICLE:
        article = fetch_article(e.link)
        print(f"  page text: {len(article)} chars, rss text: {len(text)} chars")
        if len(article) < 300 and len(text) > len(article):
            article = text
        res = translate_full(feed["name"], title, article) if len(article) >= 200 else None
        if res:
            ok = post_full(feed, e, res[0], res[1])
    if not ok:
        ka_title, ka_summary = to_georgian(feed["name"], title, text or title)
        ok = post(feed, e, ka_title, ka_summary)
    return ok

def run_test(url):
    from types import SimpleNamespace
    host = re.sub(r"^www\.", "", url.split("/")[2])
    feed = next((f for f in FEEDS if host in f["url"]), {"name": host, "color": 0x5B6CFF, "emoji": "🧪"})
    title = ""
    try:
        r = requests.get(url, timeout=25, headers={"User-Agent": UA})
        m = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.S | re.I)
        title = clean(m.group(1), 200) if m else url
    except Exception as ex:
        print(f"! test page fetch failed: {ex}"); title = url
    e = SimpleNamespace(link=url, title=title)
    e.get = lambda k, d=None: {"title": title, "link": url}.get(k, d)
    process(feed, e)

def main():
    if TEST_URL:
        run_test(TEST_URL); return
    try: seen = json.load(open(STATE_FILE, encoding="utf-8"))
    except FileNotFoundError: seen = {}
    first_run = not seen
    new_items, feed_links = [], {}
    for feed in FEEDS:
        try:
            r = requests.get(feed["url"], timeout=25, headers={"User-Agent": UA})
            r.raise_for_status()
            d = feedparser.parse(r.content)
        except Exception as e:
            print(f"! {feed['name']}: {e}"); continue
        print(f"{feed['name']}: {len(d.entries)} entries")
        known = set(seen.get(feed["name"], []))
        entries = [e for e in d.entries if e.get("link")]
        feed_links[feed["name"]] = [e.link for e in entries]
        if first_run:
            # პირველ გაშვებაზე ყველაფერი "ნანახად" ინიშნება და არაფერი იპოსტება
            seen[feed["name"]] = [e.link for e in entries]
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
        try:
            ok = process(feed, e)
        except Exception as ex:
            print(f"  ! failed: {ex}"); ok = False
        if ok:
            posted += 1
            lst = seen.setdefault(feed["name"], [])
            if e.link not in lst: lst.append(e.link)
            time.sleep(1.5)
    for k in seen:   # ფიდში არსებული ბმულები არასოდეს იშლება; ძველები 1000-მდე
        cur = feed_links.get(k, [])
        posted_or_old = [x for x in seen[k] if x not in set(cur)]
        keep_cur = [x for x in cur if x in set(seen[k])]
        seen[k] = keep_cur + posted_or_old[-1000:]
    json.dump(seen, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"done: {posted} posted")

if __name__ == "__main__":
    main()
