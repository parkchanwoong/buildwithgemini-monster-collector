#!/usr/bin/env python3
"""
Seed script to initialize Firestore with starter monsters and wild areas.
Project ID is hardcoded to prevent resolution issues in Agent Platform.
"""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-a56af107c498"

db = firestore.Client(project=PROJECT_ID)

# Initial monster encyclopedia (catalog)
MONSTERS = [
    {
        "id": "pyrofox",
        "name": "파이로폭스 (Pyrofox)",
        "element": "불 (Fire)",
        "rarity": "희귀 (Rare)",
        "hp": 120,
        "attack": 65,
        "defense": 40,
        "speed": 80,
        "description": "꼬리 끝에서 불꽃을 피우는 여우형 몬스터. 호기심이 많고 민첩합니다.",
        "skills": ["화염 세례", "불꽃 꼬리치기", "민첩한 도약"],
        "habitat": "볼캐닉 밸리 (Volcanic Valley)"
    },
    {
        "id": "aquatail",
        "name": "아쿠아테일 (Aquatail)",
        "element": "물 (Water)",
        "rarity": "일반 (Common)",
        "hp": 140,
        "attack": 50,
        "defense": 55,
        "speed": 60,
        "description": "맑은 호숫가에 서식하는 수룡형 몬스터. 방어력이 높고 온순합니다.",
        "skills": ["물대포", "아쿠아 링", "거품 보호막"],
        "habitat": "에메랄드 호수 (Emerald Lake)"
    },
    {
        "id": "leafwing",
        "name": "리프윙 (Leafwing)",
        "element": "풀 (Grass)",
        "rarity": "일반 (Common)",
        "hp": 110,
        "attack": 58,
        "defense": 45,
        "speed": 75,
        "description": "나뭇잎 날개로 바람을 타는 조류 몬스터. 빠른 속도로 기습합니다.",
        "skills": ["잎날가르기", "광합성", "돌풍"],
        "habitat": "위스퍼링 숲 (Whispering Woods)"
    },
    {
        "id": "sparkbeast",
        "name": "스파크비스트 (Sparkbeast)",
        "element": "전기 (Electric)",
        "rarity": "에픽 (Epic)",
        "hp": 130,
        "attack": 75,
        "defense": 45,
        "speed": 95,
        "description": "전신에서 번개를 뿜어내는 호랑이형 몬스터. 매우 빠르고 파괴력이 강합니다.",
        "skills": ["10만 볼트", "전광석화", "번개 발톱"],
        "habitat": "썬더 피크 (Thunder Peak)"
    },
    {
        "id": "shadowgolem",
        "name": "섀도우골렘 (Shadowgolem)",
        "element": "어둠 (Dark)",
        "rarity": "전설 (Legendary)",
        "hp": 200,
        "attack": 85,
        "defense": 90,
        "speed": 35,
        "description": "고대 폐허 깊은 곳에서 깨어난 거석 골렘. 압도적인 내구력을 자랑합니다.",
        "skills": ["암흑 파동", "바위 쪼개기", "절대 방벽"],
        "habitat": "황혼의 폐허 (Twilight Ruins)"
    }
]

# Initial wild areas
AREAS = [
    {
        "id": "whispering_woods",
        "name": "위스퍼링 숲 (Whispering Woods)",
        "recommended_level": 1,
        "encounter_rate": 0.8,
        "available_monsters": ["leafwing", "aquatail"]
    },
    {
        "id": "emerald_lake",
        "name": "에메랄드 호수 (Emerald Lake)",
        "recommended_level": 5,
        "encounter_rate": 0.7,
        "available_monsters": ["aquatail", "leafwing"]
    },
    {
        "id": "volcanic_valley",
        "name": "볼캐닉 밸리 (Volcanic Valley)",
        "recommended_level": 10,
        "encounter_rate": 0.6,
        "available_monsters": ["pyrofox", "sparkbeast"]
    },
    {
        "id": "thunder_peak",
        "name": "썬더 피크 (Thunder Peak)",
        "recommended_level": 15,
        "encounter_rate": 0.5,
        "available_monsters": ["sparkbeast", "pyrofox"]
    },
    {
        "id": "twilight_ruins",
        "name": "황혼의 폐허 (Twilight Ruins)",
        "recommended_level": 25,
        "encounter_rate": 0.3,
        "available_monsters": ["shadowgolem", "sparkbeast"]
    }
]

def seed_database():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    
    # 1. Seed monsters
    monsters_ref = db.collection("monsters")
    for m in MONSTERS:
        doc_id = m["id"]
        monsters_ref.document(doc_id).set(m)
        print(f"  [+] Monster seeded: {m['name']} ({doc_id})")
        
    # 2. Seed areas
    areas_ref = db.collection("areas")
    for a in AREAS:
        doc_id = a["id"]
        areas_ref.document(doc_id).set(a)
        print(f"  [+] Area seeded: {a['name']} ({doc_id})")
        
    # 3. Create default player profile for testing
    player_ref = db.collection("players").document("default_trainer")
    player_ref.set({
        "trainer_id": "default_trainer",
        "trainer_name": "초보 트레이너",
        "level": 1,
        "coins": 500,
        "party": ["leafwing"],
        "collection": ["leafwing"],
        "last_area": "whispering_woods"
    })
    print("  [+] Default player profile seeded: default_trainer")
    print("Firestore seeding completed successfully! ✨")

if __name__ == "__main__":
    seed_database()
