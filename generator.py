#!/usr/bin/env python3
"""Travel Planner Generator — runs hourly, generates index.html from AI + Unsplash."""

import json
import hashlib
import os
import subprocess
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

def build_prompt(config, chat_text):
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
- Prices in NTD. Be realistic about conversion rates (roughly NT$35 = €1, NT$30 = US$1, NT$4.5 = ¥100).
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

    for hotel in plan.get("hotels", []):
        query = hotel.get("search_query", hotel["name"])
        hotel["photos"] = search_unsplash(f"{query} hotel room pool lobby", 6)

    for category in ["fine_dining", "bistros", "cafes"]:
        for rest in plan.get("restaurants", {}).get(category, []):
            query = rest.get("search_query", rest["name"])
            rest["photos"] = search_unsplash(f"{query} dish interior", 3)

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

def git_commit_and_push(today_key):
    try:
        subprocess.run(
            ["git", "-C", str(ROOT), "add", "index.html",
             f"data/plans/{today_key}.json"],
            check=True, capture_output=True, text=True
        )
        subprocess.run(
            ["git", "-C", str(ROOT), "commit", "-m",
             f"Generate plan for {today_key}"],
            check=True, capture_output=True, text=True
        )
        subprocess.run(
            ["git", "-C", str(ROOT), "push"],
            check=True, capture_output=True, text=True
        )
        print("Pushed to GitHub successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e.stderr}")
        # Non-fatal: page is generated locally even if push fails


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

    # Build prompt and call AI
    prompt = build_prompt(config, chat_text)
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
    git_commit_and_push(today)

    print("Done!")


if __name__ == "__main__":
    # Fix Windows console encoding for emoji/Chinese output
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
