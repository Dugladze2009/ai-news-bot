# 🤖 AI News Bot — AI & Tech Hub [GE]

AI წყაროებიდან (OpenAI, Anthropic, Meta AI, Mistral, xAI, DeepSeek, Google DeepMind, Google AI, Hugging Face, NVIDIA, Microsoft Research, AWS ML, TechCrunch AI, MIT Technology Review, The Verge AI, Hacker News) ახალ სტატიებს
ყოველ 30 წუთში ამოწმებს, **ქართულად აჯამებს** (მოკლედ + რატომ არის მნიშვნელოვანი) და Discord-ის #ai-news არხში პოსტავს.
მუშაობს უფასოდ, GitHub Actions-ზე — კომპიუტერი ჩართული არ უნდა იყოს.

## დაყენება (10 წუთი)

### 1. Discord Webhook
#ai-news → ⚙️ Edit Channel → Integrations → Webhooks → **New Webhook** → **Copy Webhook URL**

### 2. Gemini API გასაღები (უფასო, ქართული თარგმანისთვის)
https://aistudio.google.com/apikey → **Create API key** → დააკოპირე.
(გასაღების გარეშეც იმუშავებს Google Translate-ით, მაგრამ თარგმანი უფრო სუსტი იქნება.)

### 3. GitHub რეპო
1. github.com → **New repository** → სახელი მაგ. `ai-news-bot` → **Public** → Create
2. **Add file → Upload files** → ატვირთე ყველა ფაილი ამ საქაღალდიდან
   (`.github` საქაღალდეც! თუ ვერ ტვირთავს, შექმენი ხელით: Add file → Create new file →
   სახელში ჩაწერე `.github/workflows/ai-news.yml` და ჩასვი შიგთავსი)

### 4. Secrets
რეპოში: **Settings → Secrets and variables → Actions → New repository secret**
- `DISCORD_WEBHOOK_URL` — ნაბიჯი 1-ის ლინკი
- `GEMINI_API_KEY` — ნაბიჯი 2-ის გასაღები

(არასავალდებულო) **Variables** ტაბში:
- `FORUM_CHANNEL` = `1` — თუ #ai-news ფორუმ-არხია, თითო სტატია ცალკე პოსტად გაიხსნება
- `FULL_ARTICLE` = `1` — თუ მოკლე შეჯამების ნაცვლად მთლიანი სტატიის თარგმანი გინდა
- `PING_ROLE_ID` — 🤖 AI News Ping როლის ID, თუ გინდა რომ ყოველ სიახლეზე ეს როლი დაიპინგოს.

### 5. გაშვება
**Actions** ტაბი → თუ ითხოვს, ჩართე workflows → **AI News → Discord** → **Run workflow**.
პირველ გაშვებაზე თითო წყაროდან ბოლო სტატიას დაპოსტავს (სატესტოდ), შემდეგ კი მხოლოდ ახლებს.

## წყაროს დამატება
ახალი წყარო პირველ გაშვებაზე ჩუმად აღირიცხება (ძველ სტატიებს არ დაპოსტავს), მერე მხოლოდ ახლებს.
`"filter": BIG` — მხოლოდ დიდ კომპანიებზე სიახლეები, `"filter": AI_WORDS` — მხოლოდ AI თემები.
`bot.py`-ში `FEEDS` სიაში დაამატე ხაზი:
```python
{"name": "სახელი", "url": "https://.../rss.xml", "color": 0xFF0000, "emoji": "🔴"},
```
