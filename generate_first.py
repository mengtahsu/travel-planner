"""Generate initial index.html with mock Paris data (no API calls needed)."""
import json, sys
from generator import render_html

with open(".mockups/first_plan.json", "w", encoding="utf-8") as f:
    json.dump({
        "destination_en": "Paris, France",
        "title_zh": "五月巴黎 · 浪漫五天之旅",
        "date_range": "2026/05/15–05/20",
        "start_date": "2026-05-15", "end_date": "2026-05-20",
        "departure": "Taiwan (TPE)", "departure_code": "TPE", "destination_code": "CDG",
        "travelers": 2, "days": 5, "budget_ntd": 150000,
        "flight": {
            "airline": "長榮航空 EVA Air",
            "departure_date": "5月15日", "return_date": "5月20日",
            "total_price_ntd": 38000,
            "outbound": {"flight_no": "BR 87", "route": "TPE → CDG 直飛", "depart_time": "23:40", "arrive_time": "07:30 (+1)", "duration": "13h 50m", "class": "經濟艙"},
            "inbound": {"flight_no": "BR 88", "route": "CDG → TPE 直飛", "depart_time": "11:20", "arrive_time": "06:30 (+1)", "duration": "13h 10m", "class": "經濟艙"}
        },
        "hotels": [
            {"name": "Hôtel Le Narcisse Blanc & Spa", "name_zh": "水仙花白酒店", "district": "巴黎 6 區", "day_range": "1–3", "nights": 3, "price_ntd": 39000, "stars": "★★★★☆", "room_type": "經典豪華雙人房", "breakfast": "含法式早餐", "amenities": "\U0001f3ca 室內泳池 · \U0001f486 SPA & 土耳其浴 · \U0001f37d️ 庭院餐廳 · \U0001f33f 私密花園", "photos": [{"url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400&h=300&fit=crop", "label": ""}, {"url": "https://images.unsplash.com/photo-1582719508461-905c673771fd?w=400&h=300&fit=crop", "label": ""}, {"url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400&h=300&fit=crop", "label": ""}, {"url": "https://images.unsplash.com/photo-1582719508461-905c673771fd?w=400&h=300&fit=crop", "label": ""}]},
            {"name": "Shangri-La Hotel Paris", "name_zh": "巴黎香格里拉大酒店", "district": "巴黎 16 區", "day_range": "4–5", "nights": 2, "price_ntd": 48000, "stars": "★★★★★", "room_type": "艾菲爾鐵塔景觀套房", "breakfast": "含香槟早餐", "amenities": "\U0001f3ca 室內泳池 · \U0001f486 CHI SPA 水療 · ⭐ 米其林二星 · \U0001f33f 法式花園", "photos": [{"url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=400&h=300&fit=crop", "label": ""}, {"url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=400&h=300&fit=crop", "label": ""}, {"url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=400&h=300&fit=crop", "label": ""}, {"url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=400&h=300&fit=crop", "label": ""}]}
        ],
        "restaurants": {
            "fine_dining": [
                {"name": "Le Cinq", "name_zh": "四季酒店米其林三星", "stars": "⭐⭐⭐", "dish": "\U0001f99e 招牌：龍蝦濃湯佐黑松露", "address": "31 Av. George V, 8區", "price_label": "晚餐套餐 €145/人 · NT$5,000", "hours": "19:00–22:00 · 需預約", "photos": [{"url": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&h=300&fit=crop", "label": ""}, {"url": "https://images.unsplash.com/photo-1544025162-d76694265947?w=400&h=300&fit=crop", "label": ""}]},
                {"name": "L'Ambroisie", "name_zh": "孚日廣場 · 米其林三星", "stars": "⭐⭐⭐", "dish": "\U0001f41f 招牌：海鰸魚佐魚子醬 · 松露千層酥", "address": "9 Pl. des Vosges, 4區", "price_label": "晚餐套餐 €160/人 · NT$5,500", "hours": "12:00–13:30 / 19:00–21:30", "photos": [{"url": "https://images.unsplash.com/photo-1550966871-3ed3cdb51f3a?w=400&h=300&fit=crop", "label": ""}, {"url": "https://images.unsplash.com/photo-1579027989536-b7b1f875659b?w=400&h=300&fit=crop", "label": ""}]}
            ],
            "bistros": [
                {"name": "Septime", "name_zh": "新派法式小酒館 · 米其林一星", "stars": "⭐", "dish": "\U0001f969 招牌：熟成肋眼牛排 · 煙竻甜菜根", "address": "80 Rue de Charonne, 11區", "price_label": "午餐套餐 €55/人 · NT$1,900", "hours": "12:15–14:00 / 19:30–22:00", "photos": [{"url": "https://images.unsplash.com/photo-1559339352-11d035aa65de?w=400&h=300&fit=crop", "label": ""}, {"url": "https://images.unsplash.com/photo-1432139509613-5c4255a1d179?w=400&h=300&fit=crop", "label": ""}]},
                {"name": "Chez Janou", "name_zh": "瑪黑區普羅旺斯小館", "stars": "", "dish": "\U0001f377 招牌：巧克力慕斯 · 茴香酒貽貝", "address": "2 Rue Roger Verlomme, 3區", "price_label": "人均 €35 · NT$1,200", "hours": "12:00–15:00 / 19:00–00:00", "photos": [{"url": "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=400&h=300&fit=crop", "label": ""}, {"url": "https://images.unsplash.com/photo-1551218808-94e220e084d2?w=400&h=300&fit=crop", "label": ""}]},
                {"name": "Bouillon Chartier", "name_zh": "百年傳奇平價食堂", "stars": "", "dish": "\U0001f956 招牌：法式洋蔥湯 · 油封鴨腿 · 蝸牛", "address": "7 Rue du Faubourg Montmartre, 9區", "price_label": "人均 €20 · NT$700", "hours": "11:30–00:00 全年無休", "photos": [{"url": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=400&h=300&fit=crop", "label": ""}, {"url": "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=400&h=300&fit=crop", "label": ""}]}
            ],
            "cafes": [
                {"name": "Café de Flore", "name_zh": "花神咖啡館 · 1887年開業", "stars": "", "dish": "☕ 招牌：熱巧克力 · 可頌 · 焦糖布丁", "address": "172 Bd Saint-Germain, 6區", "price_label": "兩人早午餐 €35 · NT$1,200", "hours": "07:30–01:30 · 文人雅士最愛", "photos": [{"url": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=400&h=300&fit=crop", "label": ""}, {"url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=400&h=300&fit=crop", "label": ""}]},
                {"name": "Angelina", "name_zh": "1903年創立 · 甜點傳奇", "stars": "", "dish": "\U0001f36b 招牌：熱巧克力 L'Africain · 蒙布朗", "address": "226 Rue de Rivoli, 1區", "price_label": "兩人下午茶 €30 · NT$1,050", "hours": "08:00–19:00 · 羅浮宮旁", "photos": [{"url": "https://images.unsplash.com/photo-1484723091739-30a097e8f929?w=400&h=300&fit=crop", "label": ""}, {"url": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=400&h=300&fit=crop", "label": ""}]}
            ]
        },
        "itinerary": [
            {"day": 1, "date": "May 15 · Thu", "label_zh": "抵達日", "hotel_name": "Hôtel Le Narcisse Blanc & Spa", "hotel_name_zh": "水仙花白酒店 · 經典雙人房", "hotel_room": "經典雙人房", "weather": "⛅ 18°/10°", "rain_pct": "10%", "slots": [
                {"time": "07:30", "desc": "✈️ 抵達 CDG 戴高樂機場 Terminal 1 · 入境通關取行李"},
                {"time": "08:30", "desc": "\U0001f690 機場接送專車 → 飯店（預約 Welcome Pickups · 約 €45）"},
                {"time": "09:30", "desc": "\U0001f3e8 抵達 Le Narcisse Blanc 水仙花白酒店 · 寄放行李 · 梳洗"},
                {"time": "10:30", "desc": "\U0001f950 Café de Flore 早午餐 · 花神經典歐蕾 + 可頌 + 法式炒蛋"},
                {"time": "12:00", "desc": "\U0001f3e8 返回 Le Narcisse Blanc 辦理入住 · 經典雙人房 · 稍作休息"},
                {"time": "13:30", "desc": "\U0001f3a8 羅浮宮 Musée du Louvre（預約票 €17/人 · 從玻璃金字塔入場）"},
                {"time": "", "desc": "\U0001f5fa️ 必看：蒙娜麗莎 → 勝利女神 → 米羅維納斯 → 拿破崙三世廳"},
                {"time": "17:00", "desc": "\U0001f33f 杜樂麗花園散步 Jardin des Tuileries · 噴泉邊休息"},
                {"time": "19:30", "desc": "\U0001f377 塞納河晚餐遊船 Bateaux Parisiens（3 小時）"},
                {"time": "22:30", "desc": "\U0001f6b6 沿河漫步回飯店 · 夜賞艾菲爾鐵塔整點燈光秀"}
            ]},
            {"day": 2, "date": "May 16 · Fri", "label_zh": "左岸文藝日", "hotel_name": "Hôtel Le Narcisse Blanc & Spa", "hotel_name_zh": "水仙花白酒店 · 經典雙人房", "hotel_room": "經典雙人房", "weather": "☀️ 21°/12°", "rain_pct": "5%", "slots": [
                {"time": "08:30", "desc": "\U0001f950 飯店早餐 · 新鮮可頌、果醬、現樣柳橙汁、法式濾壓咖啡"},
                {"time": "09:30", "desc": "\U0001f3a8 奧賽美術館 Musée d'Orsay（預約票 €16/人 · 舊火車站改建）"},
                {"time": "", "desc": "\U0001f5fa️ 必看：梵谷《星夜》→ 莫內《睡蓮》→ 雷諾瓦《煎餅磨坊舞會》"},
                {"time": "12:30", "desc": "\U0001f957 午餐 · Septime 新派法式小館（預約必備！午餐 €55/人套餐）"},
                {"time": "14:30", "desc": "\U0001f338 盧森堡公園 Jardin du Luxembourg · 租帆船模型 · 躺椅曬太陽"},
                {"time": "15:45", "desc": "\U0001f36c Pierre Hermé 買馬卡龍伴手禮 · Ispahan 玫瑰荔枝必吃"},
                {"time": "16:15", "desc": "\U0001f6cd️ 聖日耳曼德佩區逛街 · Le Bon Marché 樂蓬馬歉百貨"},
                {"time": "18:00", "desc": "\U0001f3e8 返回 Le Narcisse Blanc 梳洗換裝（dress code：優雅正裝）"},
                {"time": "19:30", "desc": "\U0001f56f️ 晚餐 · Le Cinq 米其林三星（預約 19:30 · 約 3.5 小時用餐）"}
            ]},
            {"day": 3, "date": "May 17 · Sat", "label_zh": "鐵塔地標日", "hotel_name": "Hôtel Le Narcisse Blanc & Spa", "hotel_name_zh": "水仙花白酒店 · 經典雙人房", "hotel_room": "經典雙人房", "weather": "\U0001f324️ 20°/11°", "rain_pct": "15%", "slots": [
                {"time": "08:00", "desc": "\U0001f950 Le Narcisse Blanc 飯店早餐 · 輕食早點，為登塔保留體力"},
                {"time": "09:00", "desc": "\U0001f5fc 艾菲爾鐵塔 Tour Eiffel（預約票 €28/人 · 電梯直達頂層）"},
                {"time": "", "desc": "\U0001f4f8 最佳拍照點：戰神廣場草地 · Trocadéro 廣場遠瞰全景"},
                {"time": "11:30", "desc": "\U0001f9fa 戰神廣場 Champ de Mars 草地野餐 · 自備三明治、水果、葡萄酒"},
                {"time": "13:30", "desc": "\U0001f3db️ 凱旋門 Arc de Triomphe（登頂 €13/人 · 284階俯瞰 12 條大道放射）"},
                {"time": "15:00", "desc": "\U0001f6cd️ 香櫛麗舍大道漫步 Avenue des Champs-Élysées · 精品櫥窗"},
                {"time": "16:00", "desc": "☕ Angelina Rivoli 店下午茶 · 招牌熱巧克力 + 蒙布朗栗子蛋糕"},
                {"time": "18:00", "desc": "\U0001f3e8 返回 Le Narcisse Blanc 休息換裝"},
                {"time": "20:00", "desc": "\U0001f37e 晚餐 · L'Ambroisie 米其林三星（預約 20:00 · 孚日廣場夜景）"}
            ]},
            {"day": 4, "date": "May 18 · Sun", "label_zh": "凡爾賽宮日", "hotel_name": "Shangri-La Hotel Paris", "hotel_name_zh": "巴黎香格里拉 · 鐵塔景觀套房", "hotel_room": "鐵塔景觀套房", "weather": "☀️ 23°/13°", "rain_pct": "0%", "slots": [
                {"time": "07:30", "desc": "\U0001f3e8 Le Narcisse Blanc 退房 · 行李寄放 · 最後一次水仙花早餐"},
                {"time": "08:30", "desc": "\U0001f682 RER C 線往 Versailles-Château-Rive Gauche（車程 40 分 · €4.5/人）"},
                {"time": "09:15", "desc": "\U0001f3f0 凡爾賽宮 Château de Versailles（預約票 €21/人 · 含語音導覽）"},
                {"time": "", "desc": "\U0001f5fa️ 必看：鏡廳 Galerie des Glaces → 國王大寢宮 → 戰爭廳"},
                {"time": "12:00", "desc": "\U0001f33f 凡爾賽花園漫步 · 大運河 Grand Canal 租劃船（€15/30分）"},
                {"time": "13:00", "desc": "\U0001f9fa 花園內野餐（從巴黎自備三明治、乳酪、長棍麵包、葡萄酒）"},
                {"time": "14:30", "desc": "\U0001f3e1 小特里亞農宮 Petit Trianon · 瑪麗皇后的田園農莊"},
                {"time": "16:30", "desc": "\U0001f682 RER C 返回巴黎市區"},
                {"time": "17:30", "desc": "\U0001f3e8 ✨ 換飯店！入住 Shangri-La Hotel Paris 香格里拉 · 鐵塔景觀套房"},
                {"time": "18:30", "desc": "\U0001f942 香格里拉陽台 · 艾菲爾鐵塔景觀 · 迎賓香槟"},
                {"time": "20:00", "desc": "\U0001f37d️ 輕鬆晚餐 · Chez Janou 瑪黑區普羅旺斯小館 · 巧克力慕斯必點"}
            ]},
            {"day": 5, "date": "May 19 · Mon", "label_zh": "蒙馬特離別日", "hotel_name": "Shangri-La Hotel Paris", "hotel_name_zh": "巴黎香格里拉 · 鐵塔景觀套房", "hotel_room": "鐵塔景觀套房（已退房）", "weather": "⛅ 19°/10°", "rain_pct": "20%", "slots": [
                {"time": "08:00", "desc": "\U0001f950 Shangri-La 香槟早餐 · 辦理退房 · 行李寄放櫃檯"},
                {"time": "09:30", "desc": "\U0001f3a8 蒙馬特 Montmartre 漫步 · 地鐵 Abbesses 站出發"},
                {"time": "10:00", "desc": "⛪ 聖心堂 Sacré-Cœur 登頂（免費入場 · 穹頂 €6/人爬300階 · 巴黎全景）"},
                {"time": "11:00", "desc": "\U0001f3a8 小丘廣場 Place du Tertre · 街頭畫家區 · 找畫家畫雙人肖像 €30"},
                {"time": "12:00", "desc": "\U0001f956 午餐 · Bouillon Chartier 百年平價食堂 · 法式洋蔥湯 + 油封鴨"},
                {"time": "13:30", "desc": "\U0001f366 Berthillon 聖路易島冰淇淋 · 最後一支法式冰淇淋"},
                {"time": "14:30", "desc": "\U0001f6cd️ 瑪德蓮廣場最後採購 · Fauchon 高級食材伴手禮 · 鵝肝醬罐頭"},
                {"time": "16:30", "desc": "\U0001f3e8 返回 Shangri-La 取行李"},
                {"time": "17:30", "desc": "\U0001f690 機場接送出發 · 建議提早 3 小時到機場辦理退稅"},
                {"time": "20:30", "desc": "✈️ CDG 登機 BR 88 · 巴黎 → 台北 · Au revoir Paris!"}
            ]}
        ],
        "costs": [
            {"label": "✈️ 來回機票", "amount_ntd": 38000},
            {"label": "\U0001f3e8 水仙花白（Day 1–3 · 3晚）", "amount_ntd": 39000},
            {"label": "\U0001f3e8 香格里拉（Day 4–5 · 2晚）", "amount_ntd": 48000},
            {"label": "\U0001f37d️ 餐飲（10餐）", "amount_ntd": 20000},
            {"label": "\U0001f3ab 景點門票", "amount_ntd": 12500},
            {"label": "\U0001f687 交通", "amount_ntd": 5000},
            {"label": "\U0001f6cd️ 購物伴手禮", "amount_ntd": 8000}
        ],
        "cost_total_ntd": 148500,
        "budget_remaining_ntd": 1500,
        "photos": {
            "hero": [{"url": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800&h=400&fit=crop", "label": "Paris"}],
            "destination": [
                {"url": "https://images.unsplash.com/photo-1511739001486-6bfe10ce6611?w=400&h=300&fit=crop", "label": ""},
                {"url": "https://images.unsplash.com/photo-1550340499-a6c60fc8287c?w=400&h=300&fit=crop", "label": ""},
                {"url": "https://images.unsplash.com/photo-1509439581779-6298f75bf6e5?w=400&h=300&fit=crop", "label": ""},
                {"url": "https://images.unsplash.com/photo-1431274172761-fca41d930114?w=400&h=300&fit=crop", "label": ""},
                {"url": "https://images.unsplash.com/photo-1511739001486-6bfe10ce6611?w=400&h=300&fit=crop", "label": ""},
                {"url": "https://images.unsplash.com/photo-1550340499-a6c60fc8287c?w=400&h=300&fit=crop", "label": ""}
            ]
        }
    }, f, ensure_ascii=False)

# Now load and render
with open(".mockups/first_plan.json", "r", encoding="utf-8") as f:
    plan = json.load(f)

render_html(plan)
print("Rendered index.html successfully!")
