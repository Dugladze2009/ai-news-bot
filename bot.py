"""
AI & Tech Hub [GE] — AI News Bot
ოფიციალური AI ბლოგების RSS → ქართული შეჯამება → Discord webhook
"""
import os, re, json, html, time, calendar
import feedparser, requests

BIG = ["OpenAI", "ChatGPT", "GPT", "Anthropic", "Claude", "Google", "Gemini", "DeepMind", "Meta", "Llama",
       "Microsoft", "Copilot", "NVIDIA", "Apple", "xAI", "Grok", "Mistral", "DeepSeek", "Qwen", "Hugging Face", "Perplexity"]
AI_WORDS = ["AI", "A.I.", "LLM", "LLMs", "GPT", "Claude", "Gemini", "model", "models", "agent", "agents", "neural",
            "machine learning", "deep learning", "Copilot", "chatbot", "generative", "transformer", "reasoning"]

FEEDS = [
    # --- ოფიციალური ---
    {"name": "OpenAI",             "url": "https://openai.com/news/rss.xml",                          "color": 0x10A37F, "emoji": "🟢"},
    {"name": "Anthropic",          "url": "https://www.anthropic.com/news", "type": "html",
     "pattern": r'href="(?:https://www\.anthropic\.com)?(/news/[a-z0-9][a-z0-9\-]+)"', "base": "https://www.anthropic.com",
                                                                                                       "color": 0xD97757, "emoji": "🟠"},
    {"name": "Meta AI",            "url": "https://ai.meta.com/blog/", "type": "html",
     "pattern": r'href="(?:https://ai\.meta\.com)?(/blog/[a-z0-9][a-z0-9\-]+/?)"', "base": "https://ai.meta.com",
     "fallback": {"url": "https://about.fb.com/feed/", "type": "rss", "filter": AI_WORDS},
                                                                                                       "color": 0x0866FF, "emoji": "🟣"},
    {"name": "Mistral AI",         "url": "https://mistral.ai/news", "type": "html",
     "pattern": r'href="(?:https://mistral\.ai)?(/news/[a-z0-9][a-z0-9\-]+/?)"', "base": "https://mistral.ai",
                                                                                                       "color": 0xFA520F, "emoji": "🟧"},
    {"name": "xAI (Grok)",         "url": "https://x.ai/news", "type": "html",
     "pattern": r'href="(?:https://x\.ai)?(/news/[a-z0-9][a-z0-9\-]+/?)"', "base": "https://x.ai",
                                                                                                       "color": 0x000000, "emoji": "⚫"},
    {"name": "DeepSeek",           "url": "https://api-docs.deepseek.com/news/news", "type": "html",
     "pattern": r'href="(?:https://api-docs\.deepseek\.com)?(/news/news\d{6,}/?)"', "base": "https://api-docs.deepseek.com",
                                                                                                       "color": 0x4D6BFE, "emoji": "🐋"},
    {"name": "Google DeepMind",    "url": "https://deepmind.google/blog/rss.xml",                     "color": 0x4285F4, "emoji": "🔵"},
    {"name": "Google AI",          "url": "https://blog.google/innovation-and-ai/technology/ai/rss/", "color": 0x34A853, "emoji": "🔵"},
    {"name": "Hugging Face",       "url": "https://huggingface.co/blog/feed.xml",                     "color": 0xFFD21E, "emoji": "🤗"},
    {"name": "NVIDIA",             "url": "https://blogs.nvidia.com/feed/",                           "color": 0x76B900, "emoji": "🟩"},
    {"name": "Microsoft Research", "url": "https://www.microsoft.com/en-us/research/feed/",           "color": 0x00A4EF, "emoji": "🟦", "filter": AI_WORDS},
    {"name": "AWS Machine Learning","url": "https://aws.amazon.com/blogs/machine-learning/feed/",      "color": 0xFF9900, "emoji": "🟧"},
    # --- ახალი ამბები (ფილტრით) ---
    {"name": "TechCrunch AI",      "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "color": 0x0A9E01, "emoji": "📰", "filter": BIG},
    {"name": "MIT Technology Review","url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "color": 0xE5112E, "emoji": "📰"},
    {"name": "The Verge AI",       "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "color": 0x5200FF, "emoji": "📰", "filter": BIG},
    {"name": "Hacker News",        "url": "https://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=points%3E150&hitsPerPage=60",
     "type": "hn",                                                                                     "color": 0xFF6600, "emoji": "🟠", "filter": AI_WORDS},
]

WEBHOOK      = os.environ.get("DISCORD_WEBHOOK_URL", "")
ROLE_ID      = os.environ.get("PING_ROLE_ID", "").strip()       # optional: 🤖 AI News Ping role
ANTHROPIC_KEY= os.environ.get("ANTHROPIC_API_KEY", "").strip()
GEMINI_KEY   = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest").strip()
DRY_RUN      = os.environ.get("DRY_RUN") == "1"
FORUM        = os.environ.get("FORUM_CHANNEL") == "1"
TEST_URL     = os.environ.get("TEST_URL", "").strip()
BACKFILL_DAYS= int(os.environ.get("BACKFILL_DAYS", "0") or 0)   # ბოლო N დღის სიახლეების დაპოსტვა
BACKFILL_MAX = int(os.environ.get("BACKFILL_MAX", "40"))   # Run workflow → ერთი კონკრეტული სტატიის ტესტი   # თუ #ai-news ფორუმ-არხია: თითო სტატია = ცალკე პოსტი
MAX_POSTS    = int(os.environ.get("MAX_POSTS_PER_RUN", "5"))
STATE_FILE   = os.environ.get("STATE_FILE", "seen.json")
MAX_AGE_DAYS = 3   # ძველ სტატიებს არ ვპოსტავთ
FULL_ARTICLE = os.environ.get("FULL_ARTICLE", "0") == "1"         # 1 = მთლიანი სტატია, 0 = მოკლე შეჯამება
MAX_SOURCE_CHARS = int(os.environ.get("MAX_SOURCE_CHARS", "9000"))  # ინგლისური ტექსტის ლიმიტი
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "en-US,en;q=0.9"}
CHUNK = 3900  # Discord embed description limit is 4096

def clean(text, limit=3000):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]

# ---------- ქართული შეჯამება ----------
PROMPT = """You are the news editor of a Georgian Discord community about AI.
Write a Georgian news post about this AI announcement.
Return ONLY JSON: {{"title": "...", "text": "..."}}
- "title": natural Georgian headline, max 90 characters.
- "text": 5-7 clear Georgian sentences (600-900 characters), split into 2-3 short paragraphs with an empty line between them.
  First explain what exactly was announced and the key details (numbers, features, availability).
  End with what this means in practice — for users, developers or the AI field — woven naturally into the text (no labels like "why it matters").
- Keep product, model, company and person names in English.
- Plain, clear language. No hype, no emojis, no headings, no invented facts — only what the text says.

Source: {source}
Title: {title}
Text: {text}"""

def parse_json(s):
    m = re.search(r"\{.*\}", s, re.S)
    d = json.loads(m.group(0))
    body = (d.get("text") or d.get("summary") or "").strip()
    return d["title"].strip(), body

def via_anthropic(p):
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=60, headers={
        "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-haiku-4-5-20251001", "max_tokens": 2000, "messages": [{"role": "user", "content": p}]})
    if r.status_code >= 400: raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    return parse_json(r.json()["content"][0]["text"])

_GEMINI_MODELS = None
GEMINI_DOWN = False   # თუ ამ გაშვებაში Gemini სრულად ჩავარდა, დანარჩენ სტატიებს შემდეგ ჯერზე ვცდით
def gemini_models():
    """ხელმისაწვდომი Gemini მოდელების სია: ჯერ არჩეული, მერე სხვა Flash მოდელები."""
    global _GEMINI_MODELS
    if _GEMINI_MODELS is not None: return _GEMINI_MODELS
    names = []
    try:
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                         timeout=20, headers={"x-goog-api-key": GEMINI_KEY})
        for m in r.json().get("models", []):
            n = m["name"].split("/", 1)[-1]
            if "generateContent" not in m.get("supportedGenerationMethods", []): continue
            if "flash" not in n or any(b in n for b in ("image", "tts", "audio", "live", "embedding", "exp", "thinking")): continue
            names.append(n)
    except Exception as e:
        print(f"  ! model list failed: {e}")
    def rank(n):   # latest-ალიასები → სტაბილური → preview; lite ბოლოს
        return ("lite" in n, "preview" in n, not n.endswith("latest"), [-int(x) for x in re.findall(r"\d+", n)])
    names = sorted(set(names), key=rank)
    _GEMINI_MODELS = [GEMINI_MODEL] + [n for n in names if n != GEMINI_MODEL]
    _GEMINI_MODELS = _GEMINI_MODELS[:4]
    print(f"  gemini models: {', '.join(_GEMINI_MODELS)}")
    return _GEMINI_MODELS

def gemini_call(p, json_mode, max_tokens):
    """ცდის რამდენიმე მოდელს; 503/429/timeout-ზე ელოდება და თავიდან ცდის."""
    cfg = {"maxOutputTokens": max_tokens}
    if json_mode: cfg["responseMimeType"] = "application/json"
    last = None
    for model in gemini_models():
        for attempt, wait in enumerate((0, 6)):
            if wait: time.sleep(wait)
            try:
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                  timeout=(10, 45 if max_tokens <= 4000 else 90), headers={"x-goog-api-key": GEMINI_KEY},
                                  json={"contents": [{"parts": [{"text": p}]}], "generationConfig": cfg})
            except requests.RequestException as e:
                last = f"{model}: {e}"; print(f"  ! {last}"); continue
            if r.status_code in (429, 500, 503, 504):
                last = f"{model}: HTTP {r.status_code}"; print(f"  ! {last} (ვცდი თავიდან)"); continue
            if r.status_code >= 400:
                last = f"{model}: HTTP {r.status_code}: {r.text[:200]}"; print(f"  ! {last}"); break  # სხვა მოდელზე
            try:
                parts = r.json()["candidates"][0]["content"]["parts"]
                out = "".join(x.get("text", "") for x in parts if not x.get("thought")).strip()
                if out:
                    print(f"  ✓ translated with {model}")
                    return out
                last = f"{model}: empty response"
            except Exception as e:
                last = f"{model}: bad response {e}"
            print(f"  ! {last}")
            break
    global GEMINI_DOWN
    GEMINI_DOWN = True
    raise RuntimeError(f"all Gemini models failed ({last})")

def via_gemini(p):
    return parse_json(gemini_call(p, True, 4000))

def via_translate(title, text):
    from deep_translator import GoogleTranslator
    tr = GoogleTranslator(source="auto", target="ka")
    summary = text[:800]
    if len(text) > 800:
        summary = summary.rsplit(" ", 1)[0] + "…"
    return tr.translate(title), (tr.translate(summary) if summary else "")

def to_georgian(source, title, text):
    p = PROMPT.format(source=source, title=title, text=text[:6000])
    for name, fn in (("anthropic", via_anthropic if ANTHROPIC_KEY else None),
                     ("gemini", via_gemini if GEMINI_KEY else None)):
        if fn:
            try: return fn(p)
            except Exception as e: print(f"  ! {name} failed: {e}")
    try:
        t = via_translate(title, text)
        if t and t[0] and t[0] != title: return t
    except Exception as e: print(f"  ! translate failed: {e}")
    return None

# ---------- მთლიანი სტატია ----------
ARTICLE_IMAGES = {}   # link -> [image urls]

def _good_img(u):
    lu = u.lower()
    return (u.startswith("http") and not lu.split("?")[0].endswith((".svg", ".gif"))
            and not any(b in lu for b in ("logo", "icon", "avatar", "favicon", "sprite", "badge", "emoji", "1x1", "pixel")))

def fetch_article(url):
    """სტატიის გვერდიდან მთავარი ტექსტი + ფოტოები (og:image და სტატიის შიგნით არსებული)."""
    try:
        import trafilatura
        from urllib.parse import urljoin
        r = requests.get(url, timeout=25, headers=HEADERS)
        r.raise_for_status()
        txt = trafilatura.extract(r.text, output_format="markdown", include_links=False,
                                  include_images=False, include_tables=False, favor_precision=True)
        imgs = []
        m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', r.text) or \
            re.search(r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"', r.text)
        if m: imgs.append(urljoin(url, html.unescape(m.group(1))))
        with_imgs = trafilatura.extract(r.text, output_format="markdown", include_images=True,
                                        include_links=False, favor_recall=True) or ""
        for u in re.findall(r"!\[[^\]]*\]\(([^)\s]+)", with_imgs):
            imgs.append(urljoin(url, html.unescape(u)))
        out = []
        for u in imgs:
            if _good_img(u) and u not in out: out.append(u)
        ARTICLE_IMAGES[url] = out[:4]
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
    return gemini_call(p, False, 32000)

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

def post(feed, entry, ka_title, ka_text):
    ts = entry.get("published_parsed") or entry.get("updated_parsed")
    desc = f"{ka_text}\n\n🔗 **წყარო:** [{feed['name']} — ორიგინალი სტატია]({entry.link})"
    embed = {
        "author": {"name": f"🤖 AI NEWS · {feed['emoji']} {feed['name']}"},
        "title": ("📰 " + ka_title)[:256],
        "url": entry.link,
        "description": desc[:4000],
        "color": feed["color"],
        "footer": {"text": "AI & Tech Hub [GE] • AI-ის სიახლეები ქართულად"},
    }
    if ts: embed["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", ts)
    imgs = list(ARTICLE_IMAGES.get(entry.link, []))
    feed_img = image_of(entry)
    if feed_img and feed_img not in imgs: imgs.insert(0, feed_img)
    imgs = imgs[:4]
    embeds = [embed]
    if imgs:
        embed["image"] = {"url": imgs[0]}
        # Discord აჩვენებს გალერეად, თუ embed-ებს ერთი და იგივე url აქვთ (მაქს. 4 ფოტო)
        for u in imgs[1:]:
            embeds.append({"url": entry.link, "image": {"url": u}})
    print(f"  images: {len(imgs)}")
    payload = {"username": "AI News 🇬🇪", "embeds": embeds, "allowed_mentions": {"parse": []}}
    if ROLE_ID:
        payload["content"] = f"<@&{ROLE_ID}>"
        payload["allowed_mentions"] = {"roles": [ROLE_ID]}
    if FORUM:
        payload["thread_name"] = ka_title[:100]
    send(payload)
    return True

# ---------- წყაროები ----------
class Entry(dict):
    """feedparser-ის entry-ს მსგავსი ობიექტი HTML წყაროებისთვის."""
    def __getattr__(self, k):
        try: return self[k]
        except KeyError: raise AttributeError(k)

def fetch_entries(feed):
    """აბრუნებს (entries, filter). fallback-ის შემთხვევაში მისი ფილტრი გამოიყენება."""
    try:
        return _fetch(feed), feed.get("filter")
    except Exception as e:
        fb = feed.get("fallback")
        if not fb: raise
        print(f"  ! {feed['name']}: {e} → ვცდი სათადარიგო წყაროს")
        return _fetch({**feed, **fb}), fb.get("filter", feed.get("filter"))

def _fetch(feed):
    r = requests.get(feed["url"], timeout=40, headers=HEADERS)
    r.raise_for_status()
    if feed.get("type") == "hn":
        out = []
        for h in r.json().get("hits", []):
            url = h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}"
            out.append(Entry(link=url, title=h.get("title") or "", summary=clean(h.get("story_text") or "", 1000),
                             published_parsed=time.gmtime(h.get("created_at_i") or time.time())))
        return out
    if feed.get("type") == "html":
        links = []
        for path in re.findall(feed["pattern"], r.text):
            url = feed["base"] + path
            if url not in links: links.append(url)
        return [Entry(link=u, title="", summary="") for u in links]
    return [e for e in feedparser.parse(r.content).entries if e.get("link")]

def fill_from_page(e):
    """HTML წყაროს სტატიისთვის: სათაური და სურათი თავად გვერდიდან."""
    if e.get("title"): return
    try:
        h = requests.get(e.link, timeout=25, headers=HEADERS).text
        m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', h) or re.search(r"<title[^>]*>(.*?)</title>", h, re.S | re.I)
        e["title"] = clean(m.group(1), 200) if m else e.link
        m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', h)
        if m: e["media_content"] = [{"url": html.unescape(m.group(1))}]
        m = re.search(r'<meta[^>]+(?:name|property)="(?:og:)?description"[^>]+content="([^"]+)"', h)
        if m: e["summary"] = html.unescape(m.group(1))
        m = (re.search(r'<meta[^>]+property="article:published_time"[^>]+content="([^"]+)"', h)
             or re.search(r'"datePublished"\s*:\s*"([^"]+)"', h)
             or re.search(r'<time[^>]+datetime="([^"]+)"', h))
        if m:
            from datetime import datetime, timezone
            try:
                dt = datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
                if not dt.tzinfo: dt = dt.replace(tzinfo=timezone.utc)
                e["published_parsed"] = dt.astimezone(timezone.utc).timetuple()
            except ValueError:
                pass
    except Exception as ex:
        print(f"  ! page meta failed: {ex}"); e["title"] = e.link

def passes_filter(feed, e, words=None):
    words = words if words is not None else feed.get("filter")
    if not words: return True
    hay = f"{e.get('title','')} {clean(e.get('summary','') or '', 1000)}"
    return any(re.search(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", hay, re.I if w != "AI" else 0) for w in words)

# ---------- main ----------
def process(feed, e):
    if GEMINI_DOWN and not ANTHROPIC_KEY:
        return False
    title, text = clean(e.get("title", ""), 300), clean(e.get("summary", "") or e.get("description", ""))
    print(f"→ {feed['name']}: {title}")
    print(f"  translators: anthropic={'yes' if ANTHROPIC_KEY else 'no'} gemini={'yes' if GEMINI_KEY else 'NO KEY'} ({GEMINI_MODEL})")
    ok = False
    article = fetch_article(e.link)
    print(f"  page text: {len(article)} chars, rss text: {len(text)} chars")
    if len(article) < 300 and len(text) > len(article):
        article = text
    if FULL_ARTICLE:
        res = translate_full(feed["name"], title, article) if len(article) >= 200 else None
        if res:
            ok = post_full(feed, e, res[0], res[1])
        elif len(article) >= 200:
            print("  ✗ სრული თარგმნა ვერ მოხერხდა — არ ვპოსტავ, შემდეგ გაშვებაზე თავიდან ვცდი")
            return False
    if not ok:
        res = to_georgian(feed["name"], title, article or text or title)
        if not res:
            print("  ✗ თარგმნა ვერ მოხერხდა — არ ვპოსტავ, შემდეგ გაშვებაზე თავიდან ვცდი")
            return False
        ok = post(feed, e, *res)
    return ok

def run_test(url):
    from types import SimpleNamespace
    host = re.sub(r"^www\.", "", url.split("/")[2])
    feed = next((f for f in FEEDS if host in f["url"]), {"name": host, "color": 0x5B6CFF, "emoji": "🧪"})
    title = ""
    try:
        r = requests.get(url, timeout=25, headers=HEADERS)
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
            entries, flt = fetch_entries(feed)
        except Exception as e:
            print(f"! {feed['name']}: {e}"); continue
        print(f"{feed['name']}: {len(entries)} entries")
        known = set(seen.get(feed["name"], []))
        feed_links[feed["name"]] = [e.link for e in entries]
        reseed = known and entries and not any(e.link in known for e in entries)
        if BACKFILL_DAYS:
            if feed.get("type") == "html":
                entries = entries[:8]
            for e in entries:
                if feed.get("type") == "html": fill_from_page(e)
                ts = e.get("published_parsed") or e.get("updated_parsed")
                if not ts or time.time() - calendar.timegm(ts) > BACKFILL_DAYS * 86400: continue
                if not passes_filter(feed, e, flt): continue
                new_items.append((feed, e))
            seen[feed["name"]] = list(dict.fromkeys(seen.get(feed["name"], []) + [e.link for e in entries]))
            continue
        if first_run or feed["name"] not in seen or reseed:
            # ახალი წყარო: ყველაფერი "ნანახად" ინიშნება და არაფერი იპოსტება
            seen[feed["name"]] = [e.link for e in entries]
            print(f"  (ახალი წყარო — {len(entries)} სტატია მოინიშნა ნანახად)")
            continue
        for e in entries:
            if e.link in known: continue
            ts = e.get("published_parsed") or e.get("updated_parsed")
            if ts and time.time() - calendar.timegm(ts) > MAX_AGE_DAYS * 86400:
                known.add(e.link); continue
            if feed.get("type") == "html":
                fill_from_page(e)
            if not passes_filter(feed, e, flt):
                known.add(e.link); continue
            new_items.append((feed, e))
        seen[feed["name"]] = list(known)
    # ძველიდან ახლისკენ
    new_items.sort(key=lambda x: calendar.timegm(x[1].get("published_parsed") or time.gmtime(0)))
    posted = 0
    limit = BACKFILL_MAX if BACKFILL_DAYS else MAX_POSTS
    if BACKFILL_DAYS:
        print(f"backfill: {len(new_items)} სიახლე ბოლო {BACKFILL_DAYS} დღეში, ვპოსტავ მაქს. {limit}")
        new_items = new_items[-limit:]   # ყველაზე ახლები, ძველიდან ახლისკენ
    for feed, e in new_items:
        if posted >= limit: break   # დანარჩენი შემდეგ გაშვებაზე
        try:
            ok = process(feed, e)
        except Exception as ex:
            print(f"  ! failed: {ex}"); ok = False
        if ok:
            posted += 1
            lst = seen.setdefault(feed["name"], [])
            if e.link not in lst: lst.append(e.link)
            time.sleep(4 if BACKFILL_DAYS else 1.5)
    for k in seen:   # ფიდში არსებული ბმულები არასოდეს იშლება; ძველები 1000-მდე
        cur = feed_links.get(k, [])
        posted_or_old = [x for x in seen[k] if x not in set(cur)]
        keep_cur = [x for x in cur if x in set(seen[k])]
        seen[k] = keep_cur + posted_or_old[-1000:]
    json.dump(seen, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"done: {posted} posted")

if __name__ == "__main__":
    main()
