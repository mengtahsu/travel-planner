#!/usr/bin/env python3
"""Travel Planner Generator — scheduled runs, generates index.html from AI + Google Images."""

import base64
import json
import hashlib
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from jinja2 import Environment, FileSystemLoader

# Fix console encoding to avoid cp1252 crashes with Chinese output
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except (OSError, AttributeError):
    pass

def safe_print(*args, **kwargs):
    """Print that never crashes on encoding errors."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        print(*(str(a).encode('ascii', errors='replace').decode() for a in args), **kwargs)

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config" / "settings.json"
CHAT_DIR = ROOT / "data" / "chat"
PLANS_DIR = ROOT / "data" / "plans"
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_HTML = ROOT / "index.html"

def _load_key(filename: str, env_name: str) -> str:
    """Load API key from file, then env var, in that order."""
    key_file = ROOT / filename
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    return os.environ.get(env_name, "")

GEMINI_API_KEY = _load_key("gemini_api_key.txt", "GEMINI_API_KEY")
SERPER_API_KEY = _load_key("serper_api_key.txt", "SERPER_API_KEY")


# ═══════════════════════════════════════════════════════════════
# Task 5: Config, chat reading, hash checking
# ═══════════════════════════════════════════════════════════════

def load_config() -> dict[str, Any]:
    """Load settings from GitHub API first (so web changes take effect), fall back to local file."""
    token = _get_github_token()

    if token:
        try:
            resp = requests.get(
                "https://api.github.com/repos/mengtahsu/travel-planner/contents/config/settings.json",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                timeout=10
            )
            if resp.status_code == 200:
                content = resp.json().get("content", "")
                return json.loads(base64.b64decode(content).decode("utf-8"))
            else:
                print(f"        GitHub GET config/settings.json: HTTP {resp.status_code}")
        except (requests.RequestException, KeyError, json.JSONDecodeError, ValueError) as e:
            print(f"Failed to fetch config from GitHub: {e}")

    # Fall back to local file
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_today_key() -> str:
    return date.today().isoformat()


def _get_github_token() -> str:
    token_file = ROOT / "github_token.txt"
    if token_file.exists():
        return token_file.read_text(encoding="utf-8").strip()
    return os.environ.get("GITHUB_TOKEN", "")


def _github_api_get(path: str) -> str | None:
    """Fetch file content (UTF-8 text) from GitHub API. Returns None on failure."""
    token = _get_github_token()
    if not token:
        print(f"        GitHub GET {path}: no token")
        return None
    try:
        resp = requests.get(
            f"https://api.github.com/repos/mengtahsu/travel-planner/contents/{path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=10
        )
        if resp.status_code == 200:
            return base64.b64decode(resp.json()["content"]).decode("utf-8")
        else:
            print(f"        GitHub GET {path}: HTTP {resp.status_code}")
    except (requests.RequestException, KeyError, json.JSONDecodeError, ValueError) as e:
        print(f"        GitHub GET {path} failed: {e}")
    return None


def get_chat_text(today_key: str) -> str:
    """Get chat text for today, falling back to most recent non-empty chat file."""
    # Try GitHub API first (reflects web saves) for today
    content = _github_api_get(f"data/chat/{today_key}.txt")
    if content is not None:
        text = content.strip()
        if text:
            return text

    # Fall back to local file for today
    chat_file = CHAT_DIR / f"{today_key}.txt"
    if chat_file.exists():
        text = chat_file.read_text(encoding="utf-8").strip()
        if text:
            return text

    # If today has no chat, check recent days (midnight gap fix)
    for days_back in range(1, 8):
        day = (date.fromisoformat(today_key) - timedelta(days=days_back)).isoformat()
        content = _github_api_get(f"data/chat/{day}.txt")
        if content is not None:
            text = content.strip()
            if text:
                return text
        chat_file = CHAT_DIR / f"{day}.txt"
        if chat_file.exists():
            text = chat_file.read_text(encoding="utf-8").strip()
            if text:
                return text

    return ""


def get_chat_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest() if text else ""


def get_config_hash(config: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def get_last_hashes(today_key: str) -> tuple[str, str]:
    plan_file = PLANS_DIR / f"{today_key}.json"
    if plan_file.exists():
        plan = json.loads(plan_file.read_text(encoding="utf-8"))
        return plan.get("chat_hash", ""), plan.get("config_hash", "")
    return "", ""


def save_plan_json(today_key: str, plan_data: dict[str, Any], chat_hash: str, config_hash: str) -> None:
    plan_data["chat_hash"] = chat_hash
    plan_data["config_hash"] = config_hash
    plan_data["generated_at"] = datetime.now().isoformat()
    plan_file = PLANS_DIR / f"{today_key}.json"
    plan_file.write_text(json.dumps(plan_data, ensure_ascii=False, indent=2), encoding="utf-8")


def has_changes() -> tuple[bool, str, str, str]:
    """Check if chat text or settings have changed since last generation."""
    today = get_today_key()
    chat_text = get_chat_text(today)
    current_chat_hash = get_chat_hash(chat_text)
    config = load_config()
    current_config_hash = get_config_hash(config)
    last_chat_hash, last_config_hash = get_last_hashes(today)

    chat_changed = current_chat_hash != last_chat_hash
    config_changed = current_config_hash != last_config_hash

    return chat_changed or config_changed, chat_text, current_chat_hash, current_config_hash


# ═══════════════════════════════════════════════════════════════
# Task 6: AI plan generation with Claude
# ═══════════════════════════════════════════════════════════════

def get_exchange_rates() -> dict[str, float]:
    """Fetch current NTD exchange rates from frankfurter.app (free, no key)."""
    try:
        resp = requests.get("https://api.frankfurter.app/latest?from=TWD", timeout=5)
        if resp.status_code == 200:
            rates = resp.json().get("rates", {})
            return {
                "JPY": round(1 / rates.get("JPY", 0.23), 2),   # TWD→JPY
                "EUR": round(1 / rates.get("EUR", 0.028), 2),  # TWD→EUR
                "USD": round(1 / rates.get("USD", 0.033), 2),  # TWD→USD
                "KRW": round(1 / rates.get("KRW", 0.044), 2),  # TWD→KRW
            }
    except requests.RequestException as e:
        print(f"Exchange rate API failed: {e}")
    # Fallback rates
    return {"JPY": 4.5, "EUR": 35.0, "USD": 30.0, "KRW": 0.035}


def build_prompt(config: dict[str, Any], chat_text: str, rates: dict[str, float]) -> str:
    destination = config.get("destination", "") or "any destination you think is perfect"
    return f"""You are a luxury travel planner. Generate a detailed romantic travel itinerary.

SETTINGS:
- Year: {config['year']}, Month: {config['month']}
- Travelers: {config['travelers']}
- Trip length: {config['days']} days
- Budget: NT$ {config['budget_ntd']:,} (New Taiwan Dollars)
- Destination: {destination}
- Departure from: {config['departure']}

CHAT REQUESTS (OVERRIDE SETTINGS — highest priority):
{chat_text if chat_text else '(none — use settings as-is)'}

Return a JSON object with this exact structure. All prices in NTD (New Taiwan Dollars).
All text in both English AND Chinese (Traditional: 繁體中文).

{{
  "destination_en": "Paris, France",
  "title_zh": "五月巴黎 · 浪漫五天之旅",
  "date_range": "2026/05/15–05/20",
  "start_date": "2026-05-15",
  "end_date": "2026-05-20",
  "departure": "Taiwan (TPE)",
  "departure_code": "TPE",
  "destination_code": "CDG",
  "travelers": 2,
  "days": 5,
  "budget_ntd": 150000,
  "flight": {{
    "airline": "長榮航空 EVA Air",
    "departure_date": "5月15日",
    "return_date": "5月20日",
    "total_price_ntd": 38000,
    "outbound": {{
      "flight_no": "BR 87",
      "route": "TPE → CDG 直飛",
      "depart_time": "23:40",
      "arrive_time": "07:30 (+1)",
      "duration": "13h 50m",
      "class": "經濟艙"
    }},
    "inbound": {{
      "flight_no": "BR 88",
      "route": "CDG → TPE 直飛",
      "depart_time": "11:20",
      "arrive_time": "06:30 (+1)",
      "duration": "13h 10m",
      "class": "經濟艙"
    }}
  }},
  "hotels": [
    {{
      "name": "Hôtel Le Narcisse Blanc & Spa",
      "name_zh": "水仙花白酒店",
      "district": "巴黎 6 區",
      "day_range": "1–3",
      "nights": 3,
      "price_ntd": 39000,
      "stars": "★★★★☆",
      "room_type": "經典豪華雙人房",
      "breakfast": "含法式早餐",
      "amenities": "🏊 室內泳池 · 💆 SPA & 土耳其浴 · 🍽️ 庭院餐廳 · 🌿 私密花園",
      "search_query": "Hôtel Le Narcisse Blanc Paris France"
    }}
  ],
  "restaurants": {{
    "fine_dining": [
      {{
        "name": "Le Cinq",
        "name_zh": "四季酒店米其林三星",
        "stars": "⭐⭐⭐",
        "dish": "🦞 招牌：龍蝦濃湯佐黑松露",
        "address": "31 Av. George V, 8區",
        "price_ntd": 5000,
        "price_label": "晚餐套餐 €145/人 · NT$5,000",
        "hours": "19:00–22:00 · 需預約",
        "search_query": "Le Cinq restaurant Four Seasons Paris food"
      }}
    ],
    "bistros": [
      {{
        "name": "Septime",
        "name_zh": "新派法式小酒館 · 米其林一星",
        "stars": "⭐",
        "dish": "🥩 招牌：熟成肋眼牛排 · 煙燻甜菜根",
        "address": "80 Rue de Charonne, 11區",
        "price_ntd": 1900,
        "price_label": "午餐套餐 €55/人 · NT$1,900",
        "hours": "12:15–14:00 / 19:30–22:00",
        "search_query": "Septime restaurant Paris food"
      }}
    ],
    "cafes": [
      {{
        "name": "Café de Flore",
        "name_zh": "花神咖啡館 · 1887年開業",
        "stars": "",
        "dish": "☕ 招牌：熱巧克力 · 可頌 · 焦糖布丁",
        "address": "172 Bd Saint-Germain, 6區",
        "price_ntd": 1200,
        "price_label": "兩人早午餐 €35 · NT$1,200",
        "hours": "07:30–01:30 · 文人雅士最愛",
        "search_query": "Cafe de Flore Paris interior"
      }}
    ]
  }},
  "itinerary": [
    {{
      "day": 1,
      "date": "May 15 · Thu",
      "label_zh": "抵達 · 巴黎初印象",
      "day_query": "Eiffel Tower Paris landmark",
      "hotel_name": "Hôtel Le Narcisse Blanc & Spa",
      "hotel_name_zh": "水仙花白酒店 · 經典雙人房",
      "hotel_room": "經典雙人房",
      "weather": "⛅ 18°/10°",
      "rain_pct": "10%",
      "slots": [
        {{"time": "07:30", "desc": "✈️ 抵達 CDG 戴高樂機場 Terminal 1 · 入境通關取行李（預計 30–45 分鐘）"}},
        {{"time": "09:00", "desc": "🚕 搭乘計程車前往酒店（約 45 分鐘 · €55）· 沿途欣賞巴黎市郊風光"}},
        {{"time": "10:00", "desc": "🏨 抵達 Hôtel Le Narcisse Blanc · 辦理入住 · 稍作休息"}},
        {{"time": "11:30", "desc": "🥐 Café de Flore 早午餐 · 花神經典歐蕾 + 可頌 + 法式洋蔥湯"}},
        {{"time": "14:00", "desc": "🎨 羅浮宮 Musée du Louvre（預約票 €17/人）· 必看：蒙娜麗莎、勝利女神"}},
        {{"time": "17:30", "desc": "🚶 杜樂麗花園散步 · 協和廣場 · 欣賞夕陽下的方尖碑"}},
        {{"time": "19:30", "desc": "🍽️ Le Cinq 米其林三星晚餐 · 預約 19:30 · 品嚐主廚招牌龍蝦濃湯"}},
        {{"time": "22:00", "desc": "🌙 返回酒店 · 途經亞歷山大三世橋欣賞夜間燈光"}}
      ]
    }}
  ],
  "costs": [
    {{"label": "✈️ 來回機票", "amount_ntd": 38000}},
    {{"label": "🏨 住宿（總計）", "amount_ntd": 87000}},
    {{"label": "🍽️ 餐飲", "amount_ntd": 20000}},
    {{"label": "🎫 景點門票", "amount_ntd": 12500}},
    {{"label": "🚇 交通", "amount_ntd": 5000}},
    {{"label": "🛍️ 購物伴手禮", "amount_ntd": 8000}}
  ],
  "cost_total_ntd": 148500,
  "budget_remaining_ntd": 1500
}}

IMPORTANT:
- Respond with ONLY the JSON object, no other text, no markdown fences.
- Generate REALISTIC flights, hotels, restaurants for the destination.
- Day-by-day time slots MUST be detailed (8-10 per day) with practical tips, transport info, costs.
- Each day MUST include "day_query": a short English search phrase for the most important place/landmark visited that day (e.g. "Eiffel Tower Paris", "Sensoji Temple Asakusa", "Keukenhof tulip gardens"). This is used to fetch a photo for the day card.
- If chat requests multiple hotels, split days between them and show hotel name in each day's slots.
- Hotel names MUST appear at the bottom of each day's schedule (hotel_name + hotel_room fields).
- Include hotel switching logistics (退房/入住) in the day where hotels change.
- Restaurant categories: "fine_dining", "bistros", "cafes"
- All text must be bilingual: English + Traditional Chinese (繁體中文).
- Prices in NTD. Use these LIVE exchange rates (1 NTD = ? foreign):
  JPY: 1 NTD = {rates['JPY']} JPY  (so ¥100 = NT$ {100/rates['JPY']:.0f})
  EUR: 1 NTD = {rates['EUR']} EUR  (so €1 = NT$ {1/rates['EUR']:.0f})
  USD: 1 NTD = {rates['USD']} USD  (so $1 = NT$ {1/rates['USD']:.0f})
  KRW: 1 NTD = {rates['KRW']} KRW
  Convert ALL local prices to NTD using these exact rates.
"""


GEMINI_MODEL = "gemini-3.5-flash"

# Free-tier quotas are per model, so on 429/503 we fall through to models with
# separate quota buckets instead of failing the run (same chain as flipbook).
GEMINI_MODEL_CHAIN = [GEMINI_MODEL, "gemini-flash-lite-latest", "gemini-2.5-flash"]


def call_ai(prompt: str) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set in environment")
    # Gemini JSON mode returns pure JSON. maxOutputTokens is generous because the
    # bilingual plan (itinerary + hotels + restaurants) is large; a finishReason
    # of MAX_TOKENS means it was truncated.
    resp = None
    for model in GEMINI_MODEL_CHAIN:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": GEMINI_API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "maxOutputTokens": 32768,
                    "temperature": 0.7,
                },
            },
            timeout=180,
        )
        if resp.status_code in (429, 503):
            safe_print(f"        Gemini {model} HTTP {resp.status_code} — trying next model")
            continue
        break
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Gemini API error: {data['error']}")
    cand = (data.get("candidates") or [{}])[0]
    if cand.get("finishReason") == "MAX_TOKENS":
        raise ValueError(
            "Gemini response hit MAX_TOKENS (truncated JSON). Raise maxOutputTokens or trim the prompt."
        )
    text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    if not text:
        raise ValueError(f"Gemini returned no text (finishReason={cand.get('finishReason')})")
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end <= start:
        raise ValueError(f"Could not find JSON in Gemini response: {text[:200]}...")
    return json.loads(text[start:end])


REQUIRED_PLAN_FIELDS = [
    "destination_en", "title_zh", "date_range", "start_date", "end_date",
    "departure", "departure_code", "destination_code", "travelers", "days",
    "budget_ntd", "hotels", "restaurants", "itinerary",
    "costs", "cost_total_ntd", "budget_remaining_ntd",
]


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Validate AI-generated plan has required fields. Raises ValueError on failure."""
    missing = [f for f in REQUIRED_PLAN_FIELDS if f not in plan]
    if missing:
        raise ValueError(f"AI response missing required fields: {missing}")
    if not isinstance(plan.get("itinerary"), list) or len(plan["itinerary"]) == 0:
        raise ValueError("AI response: itinerary must be a non-empty list")
    if not isinstance(plan.get("hotels"), list) or len(plan["hotels"]) == 0:
        raise ValueError("AI response: hotels must be a non-empty list")
    if not isinstance(plan.get("costs"), list) or len(plan["costs"]) == 0:
        raise ValueError("AI response: costs must be a non-empty list")
    cats = plan.get("restaurants", {})
    for cat in ("fine_dining", "bistros", "cafes"):
        if cat not in cats or not isinstance(cats[cat], list):
            raise ValueError(f"AI response: restaurants.{cat} must be a list")
    if isinstance(plan.get("flight"), dict):
        if "airline" not in plan["flight"]:
            plan["flight"] = None  # incomplete flight → treat as no flight
    elif "flight" in plan and plan["flight"] is not None:
        plan["flight"] = None  # non-dict flight → treat as no flight
    return plan


# ═══════════════════════════════════════════════════════════════
# Image search — Serper (Google Images) primary, DDG fallback
# ═══════════════════════════════════════════════════════════════

# Domains/keywords to block: watermarks, stock photo sites, ads, booking (ad-heavy)
_BAD_PATTERNS = [
    "alamy.com", "shutterstock", "gettyimages", "istockphoto", "dreamstime",
    "123rf.com", "depositphotos", "adobe.stock", "stock.adobe",
    "vecteezy", "freepik", "watermark", "logo", "icon", "vector",
    "pinterest", "pinimg.com",
    "booking.com", "agoda", "expedia", "tripadvisor", "hotels.com",
    "trivago", "kayak", "skyscanner", "orbitz", "priceline",
    "sponsored", "promoted", "affiliate", "banner", "popup",
]


def _is_good_photo(url: str, title: str, query: str) -> bool:
    """Shared relevance/quality filter used by both image backends."""
    url = (url or "").lower()
    for bad in _BAD_PATTERNS:
        if bad in url:
            return False
    # Reject vector/animated formats
    if any(url.endswith(x) for x in [".gif", ".svg"]):
        return False
    # Reject extremely short URLs (likely ads/trackers)
    if len(url) < 60:
        return False
    # Basic relevance: at least one significant query word should appear in title+url
    combined = ((title or "") + " " + url).lower()
    query_words = [w for w in query.lower().split() if len(w) > 2]
    if query_words and not any(w in combined for w in query_words[:3]):
        return False
    return True


def _collect(raw: list, url_key: str, title_key: str, query: str, count: int) -> list[dict[str, str]]:
    """Filter + dedupe raw backend results into [{url, label}], up to count."""
    photos = []
    seen = set()
    for r in raw:
        url = r.get(url_key, "") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        if _is_good_photo(url, r.get(title_key, ""), query):
            photos.append({"url": url, "label": r.get(title_key, "") or query})
            if len(photos) >= count:
                break
    return photos


# Tracks Serper outcomes within a run so the Log page can flag quota/fallback.
# Reset implicitly each run (the generator is a fresh process per invocation).
_SERPER_STATS = {"ok": 0, "quota": 0, "error": 0}


def photo_status() -> str:
    """Summarize this run's image-source health for the run log.
    'serper' = all good · 'quota' = credits exhausted (fell back to DDG)
    'error' = Serper errored (fell back to DDG) · 'ddg' = Serper not used."""
    if not SERPER_API_KEY:
        return "ddg"
    if _SERPER_STATS["quota"]:
        return "quota"
    if _SERPER_STATS["error"]:
        return "error"
    if _SERPER_STATS["ok"]:
        return "serper"
    return "ddg"


def _serper_images(query: str, count: int) -> list[dict[str, str]] | None:
    """Search Google Images via Serper. Returns photos, or None to signal fallback."""
    try:
        resp = requests.post(
            "https://google.serper.dev/images",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            data=json.dumps({"q": query, "num": max(count * 4, 20)}),
            timeout=20,
        )
        if resp.status_code in (402, 429):  # out of credits / rate limited → fall back
            _SERPER_STATS["quota"] += 1
            print(f"        Serper quota/limit (HTTP {resp.status_code}) — falling back to DDG")
            return None
        resp.raise_for_status()
        photos = _collect(resp.json().get("images", []), "imageUrl", "title", query, count)
        _SERPER_STATS["ok"] += 1
        return photos
    except Exception as e:
        _SERPER_STATS["error"] += 1
        print(f"        Serper Images: {type(e).__name__}: {e} — falling back to DDG")
        return None


def _ddg_images(query: str, count: int = 4) -> list[dict[str, str]]:
    """Search images via DDG. Best-effort; never raises (degrades to placeholders)."""
    try:
        from ddgs import DDGS
        raw = list(DDGS().images(query, max_results=max(count * 4, 20)))
        photos = _collect(raw, "image", "title", query, count)
        if not photos:
            return [{"url": "", "label": query}] * max(count, 1)
        return photos
    except Exception as e:
        # Missing package, empty result (DDGSException "No results found."),
        # rate limiting, or a network error must not crash the whole generation.
        print(f"        DDG Images: {type(e).__name__}: {e}")
        return [{"url": "", "label": query}] * max(count, 1)


# Photo cache: persists resolved Serper results across runs so re-generating a
# plan with the same venues costs no Serper credits — only new/changed venues
# hit the API. DDG fallbacks are NOT cached, so Serper is retried once it's
# available again (accuracy over a locked-in fallback).
PHOTO_CACHE = ROOT / "data" / "photo_cache.json"
_PHOTO_CACHE_MAX = 1000


def _load_photo_cache() -> dict:
    if PHOTO_CACHE.exists():
        try:
            return json.loads(PHOTO_CACHE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_photo_cache(cache: dict) -> None:
    # dict preserves insertion order → drop oldest entries when it grows too large.
    if len(cache) > _PHOTO_CACHE_MAX:
        for k in list(cache)[: len(cache) - _PHOTO_CACHE_MAX]:
            del cache[k]
    PHOTO_CACHE.parent.mkdir(parents=True, exist_ok=True)
    PHOTO_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


_PHOTO_CACHE = _load_photo_cache()
_PHOTO_CACHE_DIRTY = False


def search_images(query: str, count: int = 4) -> list[dict[str, str]]:
    """Resolve photos: cache → Serper (Google) → DDG → placeholders.
    Cached hits cost no Serper credit; only Serper-sourced results are cached."""
    global _PHOTO_CACHE_DIRTY
    key = f"{query}|{count}"
    cached = _PHOTO_CACHE.get(key)
    if cached:
        return cached
    if SERPER_API_KEY:
        photos = _serper_images(query, count)
        if photos:  # Serper succeeded → cache permanently
            _PHOTO_CACHE[key] = photos
            _PHOTO_CACHE_DIRTY = True
            return photos
    return _ddg_images(query, count)  # DDG fallback — not cached, retry Serper next run


def resolve_all_photos(plan: dict[str, Any]) -> dict[str, Any]:
    dest = plan.get("destination_en", "travel")
    city = dest.split(",")[0].strip()

    # Cover/hotels/restaurants use Serper (Google) for accuracy; reuse the first
    # cover image for the hero/og:image instead of a separate search.
    destination = search_images(f"{city} travel scenery", 6)
    plan["photos"] = {
        "hero": destination[:1],
        "destination": destination,
    }

    for hotel in plan.get("hotels", []):
        name = hotel.get("name", "")
        q = hotel.get("search_query", f"{name} {city}")
        photos = search_images(q, 6)
        if not photos or not photos[0]["url"]:
            photos = search_images(f"luxury hotel {city}", 6)
        hotel["photos"] = photos

    for category in ["fine_dining", "bistros", "cafes"]:
        for r in plan.get("restaurants", {}).get(category, []):
            name = r.get("name", "")
            q = r.get("search_query", f"{name} {city}")
            photos = search_images(q, 3)
            if not photos or not photos[0]["url"]:
                if category == "cafes":
                    photos = search_images(f"cafe coffee {city}", 3)
                else:
                    photos = search_images(f"{category.replace('_',' ')} food {city}", 3)
            r["photos"] = photos

    # Day-by-day photos are generic filler — source from DDG directly so they
    # stay free and don't consume the Serper quota.
    for day in plan.get("itinerary", []):
        q = day.get("day_query", f"{city} travel")
        day_photos = _ddg_images(q, 1)
        day["day_photo"] = day_photos[0]["url"] if day_photos and day_photos[0]["url"] else ""

    if _PHOTO_CACHE_DIRTY:
        _save_photo_cache(_PHOTO_CACHE)

    return plan


# ═══════════════════════════════════════════════════════════════
# HTML rendering + URL building
# ═══════════════════════════════════════════════════════════════

def render_html(plan: dict[str, Any]) -> None:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    env.filters["format_number"] = lambda x: f"{x:,}"

    # Google Flights URL
    dest_code = plan.get("destination_code", "")
    dep_code = plan.get("departure_code", "TPE")
    start_date = plan.get("start_date", "")
    plan["google_flights_url"] = (
        f"https://www.google.com/travel/flights"
        f"?q=Flights+to+{dest_code}+from+{dep_code}+{start_date}"
    )

    # Agoda URL
    dest_city = plan.get("destination_en", "").split(",")[0].strip()
    plan["agoda_url"] = (
        f"https://www.agoda.com/zh-tw/city/{dest_city.lower()}-fr.html"
        f"?checkIn={plan.get('start_date', '')}"
        f"&checkOut={plan.get('end_date', '')}"
        f"&adults={plan.get('travelers', 2)}"
    )

    template = env.get_template("plan_template.html")
    build_tag = datetime.now().strftime("%y%m%d.%H%M%S")
    html = template.render(plan=plan, build_tag=build_tag)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Rendered {OUTPUT_HTML}  build {build_tag}")


# ═══════════════════════════════════════════════════════════════
# Task 12: Git commit and push
# ═══════════════════════════════════════════════════════════════

def _sync_saved_files(token: str | None = None, owner: str | None = None, repo: str | None = None, headers: dict[str, str] | None = None) -> None:
    """Sync local saved files with GitHub: delete orphans, sync deletions.

    When called without arguments, reads token from file and constructs headers.
    Otherwise accepts pre-built values (for use after push_via_api).
    """
    if token is None:
        token = _get_github_token()
    if not token:
        return
    if owner is None:
        owner = "mengtahsu"
    if repo is None:
        repo = "travel-planner"
    if headers is None:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    # Fetch GitHub index
    github_files = set()
    try:
        r = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/data/saved/index.json",
            headers=headers, timeout=10
        )
        if r.status_code == 200:
            gh_idx = json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
            github_files = {e["file"] for e in gh_idx}
    except requests.RequestException as e:
        safe_print(f"        Sync: GitHub fetch failed: {e}")
        return

    local_idx = SAVED_DIR / "index.json"
    if not local_idx.exists():
        return
    try:
        local_index = json.loads(local_idx.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        safe_print(f"        Sync: local index read failed: {e}")
        return

    local_files = {e["file"] for e in local_index}

    # Delete local files that were deleted from GitHub
    deleted = local_files - github_files
    for filename in deleted:
        f = SAVED_DIR / filename
        if f.exists():
            f.unlink()
            safe_print(f"        Synced deletion: removed {filename}")

    # Clean up orphan HTML files not in local index
    for f in SAVED_DIR.glob("*.html"):
        if f.name not in local_files:
            f.unlink()
            safe_print(f"        Cleaned orphan: {f.name}")

    # Update local index to match GitHub (remove deleted entries)
    if deleted:
        updated = [e for e in local_index if e["file"] not in deleted]
        local_idx.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")

def push_via_api(today_key: str) -> None:
    """Push files via GitHub REST API (works with fine-grained tokens)."""
    token = _get_github_token()

    if not token:
        print("Warning: No GitHub token found, skipping push")
        return

    files_to_push = {
        "index.html": OUTPUT_HTML,
        f"data/plans/{today_key}.json": PLANS_DIR / f"{today_key}.json",
        ".nojekyll": ROOT / ".nojekyll",
    }

    # Also push all HTML files (chat, settings, log) if they've changed
    for html_file in ROOT.glob("*.html"):
        files_to_push[html_file.name] = html_file

    # Push run log
    if RUNS_LOG.exists():
        files_to_push["data/runs.json"] = RUNS_LOG

    # Push photo cache so cached Serper results persist across runs
    if PHOTO_CACHE.exists():
        files_to_push["data/photo_cache.json"] = PHOTO_CACHE

    # Push saved plans — only new files (avoid pushing 100+ duplicates)
    owner = "mengtahsu"
    repo = "travel-planner"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    if SAVED_DIR.exists():
        github_files = set()
        try:
            r = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/data/saved/index.json",
                headers=headers, timeout=10
            )
            if r.status_code == 200:
                gh_idx = json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
                github_files = {e["file"] for e in gh_idx}
        except (requests.RequestException, KeyError, json.JSONDecodeError, ValueError):
            pass
        for f in SAVED_DIR.glob("*.html"):
            if f.name not in github_files:
                files_to_push[f"data/saved/{f.name}"] = f
        idx = SAVED_DIR / "index.json"
        if idx.exists():
            files_to_push["data/saved/index.json"] = idx

    # (owner, repo, headers now defined above)

    for path, filepath in files_to_push.items():
        if not filepath.exists():
            continue
        content_bytes = filepath.read_bytes()
        body = {
            "message": f"Update {path} for {today_key}",
            "content": base64.b64encode(content_bytes).decode(),
            "branch": "main"
        }

        try:
            resp = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                headers=headers
            )
            if resp.status_code == 200:
                body["sha"] = resp.json()["sha"]
        except (requests.RequestException, KeyError):
            pass

        resp = requests.put(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            headers=headers,
            json=body
        )
        if resp.status_code in (200, 201):
            safe_print(f"  Pushed {path}")
        elif resp.status_code == 409:
            pass  # SHA conflict — another process already pushed, skip silently
        else:
            safe_print(f"  Failed {path}: {resp.status_code}")
    print("Push complete via API.")

    # Sync deletions AFTER push — newly archived files are now on GitHub
    if SAVED_DIR.exists():
        _sync_saved_files(token, owner, repo, headers)


# ═══════════════════════════════════════════════════════════════
# Run logging
# ═══════════════════════════════════════════════════════════════

RUNS_LOG = ROOT / "data" / "runs.json"

def log_run(status: str, summary: str = "", destination: str = "", chat_chars: int = 0,
            photos: str = "") -> None:
    """Append a run entry to runs.json (keeps last 90 days)."""
    runs = []
    if RUNS_LOG.exists():
        try:
            runs = json.loads(RUNS_LOG.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            runs = []

    entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": status,
        "summary": summary,
        "destination": destination,
        "chat_chars": chat_chars,
        "photos": photos,  # "serper" | "quota" | "error" | "ddg" | ""
    }
    runs.insert(0, entry)

    # Keep last 90 days
    cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    runs = [r for r in runs if r["ts"][:10] >= cutoff]

    RUNS_LOG.write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════
# Save-flag check (archive plan before regenerating)
# ═══════════════════════════════════════════════════════════════

SAVED_DIR = ROOT / "data" / "saved"

def check_and_archive() -> bool:
    """If save_flag is set, archive current index.html to data/saved/. Returns True if archived."""
    flag = _github_api_get("data/save_flag.json")
    if not flag:
        return False
    try:
        data = json.loads(flag)
        if not data.get("save", False):
            return False
    except (json.JSONDecodeError, ValueError):
        return False

    if not OUTPUT_HTML.exists():
        return False

    ts = datetime.now().strftime("%Y-%m-%d-%H%M")
    # Use English destination for filename — ASCII-safe, shareable URLs
    dest_name = data.get("dest", "plan")
    safe_title = re.sub(r'[^a-zA-Z0-9]+', '-', dest_name).strip('-')[:50]
    filename = f"{ts}-{safe_title}.html"
    SAVED_DIR.mkdir(parents=True, exist_ok=True)

    html = OUTPUT_HTML.read_text(encoding="utf-8")
    # Strip nav bar — links won't work from data/saved/ subdirectory
    html = re.sub(r'<nav>.*?</nav>\s*', '', html, flags=re.DOTALL)
    # Strip save checkbox + its script (already saved, doesn't apply)
    html = re.sub(r'<label class="save-plan-label".*?</label>\s*', '', html, flags=re.DOTALL)
    html = re.sub(r'<script>\s*// Write flag file.*?</script>\s*', '', html, flags=re.DOTALL)
    (SAVED_DIR / filename).write_text(html, encoding="utf-8")

    # Update saved index
    index_path = SAVED_DIR / "index.json"
    index = []
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            index = []
    index.insert(0, {
        "file": filename,
        "title": data.get("title", "plan"),
        "dest": data.get("dest", ""),
        "date": data.get("date", ""),
        "saved_at": ts
    })
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"        Archived: {filename}")

    # Clear the flag
    token = _get_github_token()
    if token:
        try:
            # Get sha
            resp = requests.get(
                "https://api.github.com/repos/mengtahsu/travel-planner/contents/data/save_flag.json",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                timeout=10
            )
            sha = resp.json().get("sha", "") if resp.status_code == 200 else ""
            requests.put(
                "https://api.github.com/repos/mengtahsu/travel-planner/contents/data/save_flag.json",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                json={
                    "message": "Clear save flag after archiving",
                    "content": base64.b64encode(
                        json.dumps({"save": False}).encode()
                    ).decode(),
                    "sha": sha or "",
                    "branch": "main"
                },
                timeout=10
            )
        except (requests.RequestException, KeyError) as e:
            print(f"        Warning: could not clear save flag: {e}")
    return True


# ═══════════════════════════════════════════════════════════════
# Main flow
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    def progress(pct: int, msg: str) -> None:
        filled = pct // 4
        bar = "#" * filled + "-" * (25 - filled)
        print(f"[{bar}] {pct:3d}%  {msg}", flush=True)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"[{ts}] Travel Planner Generator")
    print(f"{'='*60}")

    progress(5, "Loading config...")
    config = load_config()
    today = get_today_key()
    print(f"        Today: {today}  Destination: {config.get('destination') or '(AI pick)'}  Budget: NT${config.get('budget_ntd', 0):,}")

    # Sync saved files before archiving (don't delete newly archived files)
    progress(8, "Syncing saved files...")
    _sync_saved_files()

    # Check if user flagged this plan to save before overwriting
    progress(10, "Checking save flag...")
    archived = check_and_archive()

    # Check if chat or settings changed
    progress(12, "Checking for changes...")
    changed, chat_text, chat_hash, config_hash = has_changes()
    plan_exists = (PLANS_DIR / f"{today}.json").exists()
    force = os.environ.get("FORCE_REGENERATE", "").lower() == "true"

    if not changed and plan_exists and not force:
        progress(100, "No changes — skipping generation.")
        log_run("skipped", "No changes detected")
        # Only push if an archive was just created (avoid overwhelming Pages)
        if archived:
            push_via_api(today)
        print(f"{'='*60}\n")
        return

    print(f"        {'First run today!' if not plan_exists else 'Changes detected — regenerating...'}")
    if chat_text:
        print(f"        Chat: {len(chat_text)} chars — \"{chat_text[:80]}{'...' if len(chat_text)>80 else ''}\"")

    # Fetch live exchange rates
    progress(15, "Fetching live exchange rates...")
    rates = get_exchange_rates()
    print(f"        JPY={rates['JPY']}  EUR={rates['EUR']}  USD={rates['USD']}")

    # Build prompt and call AI
    progress(20, "Building AI prompt...")
    prompt = build_prompt(config, chat_text, rates)

    progress(25, "Calling AI (Claude) — this takes ~30–60s...")
    plan = call_ai(prompt)
    validate_plan(plan)
    plan["chat_input"] = chat_text  # preserve for display on plan page
    progress(65, "AI response received!")
    print(f"        Destination: {plan.get('destination_en')} — {plan.get('title_zh')}")

    # Resolve photos from Google Images (atmosphere/visual appeal)
    progress(70, "Fetching atmosphere photos...")
    plan = resolve_all_photos(plan)
    hotel_pics = sum(1 for h in plan.get("hotels", []) for p in h.get("photos", []) if p["url"])
    rest_pics = sum(1 for cat in plan.get("restaurants", {}).values() for r in cat for p in r.get("photos", []) if p["url"])
    progress(80, f"Photos: {hotel_pics} hotel + {rest_pics} restaurant")

    # Save plan JSON
    progress(85, "Saving plan JSON...")
    save_plan_json(today, plan, chat_hash, config_hash)

    # Render HTML
    progress(90, "Rendering HTML...")
    render_html(plan)

    # Log this run
    log_run("generated",
            summary=plan.get("title_zh", ""),
            destination=plan.get("destination_en", ""),
            chat_chars=len(chat_text),
            photos=photo_status())

    # Push to GitHub
    progress(90, "Pushing to GitHub...")
    push_via_api(today)

    progress(100, "Done!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Fix Windows console encoding for emoji/Chinese output
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (OSError, AttributeError):
        pass
    main()
