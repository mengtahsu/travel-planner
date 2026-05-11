#!/usr/bin/env python3
"""Travel Planner Generator — runs hourly, generates index.html from AI + Unsplash."""

import json
import hashlib
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from openai import OpenAI
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config" / "settings.json"
CHAT_DIR = ROOT / "data" / "chat"
PLANS_DIR = ROOT / "data" / "plans"
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_HTML = ROOT / "index.html"

def _load_key(filename, env_name):
    """Load API key from file, then env var, in that order."""
    key_file = ROOT / filename
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    return os.environ.get(env_name, "")

DEEPSEEK_API_KEY = _load_key("deep_seek_api_key.txt", "DEEPSEEK_API_KEY")
UNSPLASH_ACCESS_KEY = _load_key("unsplash_access_key.txt", "UNSPLASH_ACCESS_KEY")


# ═══════════════════════════════════════════════════════════════
# Task 5: Config, chat reading, hash checking
# ═══════════════════════════════════════════════════════════════

def load_config():
    """Load settings from GitHub API first (so web changes take effect), fall back to local file."""
    token_file = ROOT / "github_token.txt"
    token = ""
    if token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()

    if token:
        try:
            resp = requests.get(
                "https://api.github.com/repos/mengtahsu/travel-planner/contents/config/settings.json",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                timeout=10
            )
            if resp.status_code == 200:
                import base64
                content = resp.json().get("content", "")
                return json.loads(base64.b64decode(content).decode("utf-8"))
        except Exception as e:
            print(f"Failed to fetch config from GitHub: {e}")

    # Fall back to local file
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_today_key():
    return date.today().isoformat()


def get_chat_text(today_key):
    chat_file = CHAT_DIR / f"{today_key}.txt"
    if chat_file.exists():
        return chat_file.read_text(encoding="utf-8").strip()
    return ""


def get_chat_hash(text):
    return hashlib.sha256(text.encode()).hexdigest() if text else ""


def get_last_chat_hash(today_key):
    plan_file = PLANS_DIR / f"{today_key}.json"
    if plan_file.exists():
        plan = json.loads(plan_file.read_text(encoding="utf-8"))
        return plan.get("chat_hash", "")
    return ""


def save_plan_json(today_key, plan_data, chat_hash):
    plan_data["chat_hash"] = chat_hash
    plan_data["generated_at"] = datetime.now().isoformat()
    plan_file = PLANS_DIR / f"{today_key}.json"
    plan_file.write_text(json.dumps(plan_data, ensure_ascii=False, indent=2), encoding="utf-8")


def has_chat_changed():
    today = get_today_key()
    chat_text = get_chat_text(today)
    current_hash = get_chat_hash(chat_text)
    last_hash = get_last_chat_hash(today)
    return current_hash != last_hash, chat_text, current_hash


# ═══════════════════════════════════════════════════════════════
# Task 6: AI plan generation with Claude
# ═══════════════════════════════════════════════════════════════

def get_exchange_rates():
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
    except Exception as e:
        print(f"Exchange rate API failed: {e}")
    # Fallback rates
    return {"JPY": 4.5, "EUR": 35.0, "USD": 30.0, "KRW": 0.035}


def build_prompt(config, chat_text, rates):
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
      "label_zh": "抵達日",
      "hotel_name": "Hôtel Le Narcisse Blanc & Spa",
      "hotel_name_zh": "水仙花白酒店 · 經典雙人房",
      "hotel_room": "經典雙人房",
      "weather": "⛅ 18°/10°",
      "rain_pct": "10%",
      "slots": [
        {{"time": "07:30", "desc": "✈️ 抵達 CDG 戴高樂機場 Terminal 1 · 入境通關取行李"}},
        {{"time": "10:30", "desc": "🥐 Café de Flore 早午餐 · 花神經典歐蕾 + 可頌"}},
        {{"time": "14:00", "desc": "🎨 羅浮宮 Musée du Louvre（預約票 €17/人）"}}
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
- Day-by-day time slots should be detailed (8-10 per day) with practical tips.
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


def call_ai(prompt):
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not set in environment")
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1"
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        max_tokens=8192,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.choices[0].message.content
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end <= start:
        raise ValueError(f"Could not find JSON in DeepSeek response: {text[:200]}...")
    return json.loads(text[start:end])


# ═══════════════════════════════════════════════════════════════
# Task 7: Unsplash photo resolution
# ═══════════════════════════════════════════════════════════════

def search_unsplash(query, count=4):
    if not UNSPLASH_ACCESS_KEY:
        print(f"Warning: UNSPLASH_ACCESS_KEY not set, using empty photos for '{query}'")
        return [{"url": "", "label": query}] * max(count, 1)

    try:
        resp = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": count, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            timeout=10
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        photos = []
        for r in results:
            photos.append({
                "url": r["urls"]["regular"] + "&w=400&h=300&fit=crop",
                "label": r.get("alt_description", query)
            })
        if not photos:
            return [{"url": "", "label": query}] * max(count, 1)
        # Duplicate for seamless slider loop
        if len(photos) < count * 2:
            photos = photos + photos
        return photos
    except Exception as e:
        print(f"Unsplash error for '{query}': {e}")
        return [{"url": "", "label": query}] * max(count, 1)


def resolve_all_photos(plan):
    dest = plan.get("destination_en", "travel")
    plan["photos"] = {
        "hero": search_unsplash(f"{dest} landmark skyline beautiful", 2),
        "destination": search_unsplash(f"{dest} travel beautiful scenery", 6),
    }

    dest = plan.get("destination_en", "travel").split(",")[0].strip()
    for hotel in plan.get("hotels", []):
        # Mix hotel name with generic terms for unique per-hotel photos
        name = hotel.get("name", "").split(" ")[0]  # first word of hotel name
        district = hotel.get("district", "")
        stars = hotel.get("stars", "").count("★")
        if stars >= 5:
            query = f"luxury {name} {dest} hotel suite spa"
        elif stars >= 4:
            query = f"boutique {name} {dest} hotel room"
        else:
            query = f"{name} {dest} hotel room"
        hotel["photos"] = search_unsplash(query, 6)

    for category in ["fine_dining", "bistros", "cafes"]:
        for rest in plan.get("restaurants", {}).get(category, []):
            rest_name = rest.get("name", "")
            if category == "cafes":
                query = f"{rest_name} cafe coffee {dest} dessert"
                fallback = f"{dest} cafe coffee dessert pastry"
            else:
                query = f"{rest_name} restaurant {dest} food dish"
                fallback = f"{dest} {category.replace('_',' ')} restaurant food"
            photos = search_unsplash(query, 3)
            # If search returned empty, fall back to generic terms
            if not photos or not photos[0]["url"]:
                photos = search_unsplash(fallback, 3)
            rest["photos"] = photos

    return plan


# ═══════════════════════════════════════════════════════════════
# Task 8: HTML rendering + URL building
# ═══════════════════════════════════════════════════════════════

def render_html(plan):
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
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
    html = template.render(plan=plan)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Rendered {OUTPUT_HTML}")


# ═══════════════════════════════════════════════════════════════
# Task 12: Git commit and push
# ═══════════════════════════════════════════════════════════════

def push_via_api(today_key):
    """Push files via GitHub REST API (works with fine-grained tokens)."""
    token_file = ROOT / "github_token.txt"
    token = ""
    if token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()

    if not token:
        print("Warning: No GitHub token found, skipping push")
        return

    files_to_push = {
        "index.html": OUTPUT_HTML,
        f"data/plans/{today_key}.json": PLANS_DIR / f"{today_key}.json",
    }

    # Also push all HTML files (chat, settings, log) if they've changed
    for html_file in ROOT.glob("*.html"):
        files_to_push[html_file.name] = html_file

    owner = "mengtahsu"
    repo = "travel-planner"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    for path, filepath in files_to_push.items():
        if not filepath.exists():
            continue
        content_bytes = filepath.read_bytes()
        body = {
            "message": f"Update {path} for {today_key}",
            "content": __import__("base64").b64encode(content_bytes).decode(),
            "branch": "main"
        }

        try:
            resp = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                headers=headers
            )
            if resp.status_code == 200:
                body["sha"] = resp.json()["sha"]
        except Exception:
            pass

        resp = requests.put(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            headers=headers,
            json=body
        )
        if resp.status_code in (200, 201):
            print(f"  Pushed {path}")
        else:
            print(f"  Failed {path}: {resp.status_code} {resp.text[:150]}")
    print("Push complete via API.")


# ═══════════════════════════════════════════════════════════════
# Main flow
# ═══════════════════════════════════════════════════════════════

def main():
    print(f"[{datetime.now()}] Travel Planner Generator starting...")

    config = load_config()
    today = get_today_key()
    print(f"Today: {today}")

    # Check if plan exists and chat changed
    changed, chat_text, chat_hash = has_chat_changed()
    plan_exists = (PLANS_DIR / f"{today}.json").exists()
    if not changed and plan_exists:
        print("No chat changes detected. Skipping generation.")
        return

    if not plan_exists:
        print("First generation of the day!")
    else:
        print("Chat changed! Regenerating...")

    if chat_text:
        print(f"Chat text ({len(chat_text)} chars): {chat_text[:100]}...")

    # Fetch live exchange rates
    rates = get_exchange_rates()
    print(f"Exchange rates: JPY={rates['JPY']}, EUR={rates['EUR']}, USD={rates['USD']}")

    # Build prompt and call AI
    prompt = build_prompt(config, chat_text, rates)
    print("Calling DeepSeek API...")
    plan = call_ai(prompt)
    print(f"Plan generated: {plan.get('destination_en')} - {plan.get('title_zh')}")

    # Resolve photos
    print("Fetching photos from Unsplash...")
    plan = resolve_all_photos(plan)
    hotel_photos = sum(len(h.get("photos", [])) for h in plan.get("hotels", []))
    rest_photos = sum(
        len(r.get("photos", []))
        for cats in plan.get("restaurants", {}).values()
        for r in cats
    )
    print(f"Photos resolved: {hotel_photos} hotel, {rest_photos} restaurant photos")

    # Save plan JSON
    save_plan_json(today, plan, chat_hash)
    print(f"Plan saved to data/plans/{today}.json")

    # Render HTML
    render_html(plan)

    # Push to GitHub
    print("Pushing to GitHub...")
    push_via_api(today)

    print("Done!")


if __name__ == "__main__":
    # Fix Windows console encoding for emoji/Chinese output
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
