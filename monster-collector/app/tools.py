"""
Firestore database tools for Monster Collector Agent.
The GCP Project ID is hardcoded to avoid project number resolution issues in Agent Platform.
"""

import json
import os
import random
import time
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional
from google.cloud import firestore
from google.cloud import storage
from google import genai
from google.genai import types
from google.adk.tools import ToolContext

PROJECT_ID = "qwiklabs-gcp-04-a56af107c498"
BUCKET_NAME = "monster-collector-qwiklabs-gcp-04-a56af107c498-m3p0qt"

# Singleton Firestore client initialized with hardcoded project ID
_db: Optional[firestore.Client] = None

def get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def list_monsters(element: Optional[str] = None) -> List[Dict[str, Any]]:
    """몬스터 도감에서 등록된 몬스터 목록을 조회합니다.

    Args:
        element: 특정 속성(예: '불', '물', '풀', '전기', '어둠')으로 필터링할 때 사용 (선택 사항).

    Returns:
        몬스터들의 기본 정보와 스탯이 담긴 리스트.
    """
    db = get_db()
    docs = db.collection("monsters").stream()
    monsters = []
    for doc in docs:
        data = doc.to_dict()
        if element:
            if element.lower() not in data.get("element", "").lower():
                continue
        monsters.append(data)
    return monsters


def get_monster_detail(monster_name_or_id: str) -> Dict[str, Any]:
    """특정 몬스터의 상세 정보(스탯, 스킬, 서식지, 설명 등)를 조회합니다.

    Args:
        monster_name_or_id: 몬스터의 ID (예: 'pyrofox', 'aquatail') 또는 이름 (예: '파이로폭스').

    Returns:
        해당 몬스터의 상세 정보 딕셔너리.
    """
    db = get_db()
    # 1. Check direct document ID
    doc = db.collection("monsters").document(monster_name_or_id.lower()).get()
    if doc.exists:
        return doc.to_dict()
    
    # 2. Search by name
    docs = db.collection("monsters").stream()
    for d in docs:
        data = d.to_dict()
        if monster_name_or_id.lower() in data.get("name", "").lower() or monster_name_or_id.lower() in data.get("id", "").lower():
            return data
            
    return {"error": f"몬스터 '{monster_name_or_id}'를 도감에서 찾을 수 없습니다."}


def get_player_profile(trainer_id: str = "default_trainer") -> Dict[str, Any]:
    """플레이어(트레이너)의 프로필 정보, 보유 코인, 파티 및 수집 목록을 조회합니다.

    Args:
        trainer_id: 트레이너 ID (기본값: 'default_trainer').

    Returns:
        트레이너 프로필 정보 딕셔너리.
    """
    db = get_db()
    doc = db.collection("players").document(trainer_id).get()
    if doc.exists:
        return doc.to_dict()
    return {"error": f"트레이너 '{trainer_id}'의 정보를 찾을 수 없습니다."}


def catch_monster(monster_id: str, trainer_id: str = "default_trainer") -> Dict[str, Any]:
    """야생에서 마주친 몬스터를 포획하여 플레이어의 컬렉션 및 파티에 추가합니다.

    Args:
        monster_id: 포획할 몬스터의 ID (예: 'pyrofox', 'aquatail', 'sparkbeast').
        trainer_id: 몬스터를 포획한 트레이너의 ID (기본값: 'default_trainer').

    Returns:
        포획 결과 및 업데이트된 파티/컬렉션 상태 메시지.
    """
    db = get_db()
    monster_doc = db.collection("monsters").document(monster_id.lower()).get()
    if not monster_doc.exists:
        return {"error": f"몬스터 ID '{monster_id}'가 존재하지 않아 포획할 수 없습니다."}
    
    monster_data = monster_doc.to_dict()
    player_ref = db.collection("players").document(trainer_id)
    player_doc = player_ref.get()
    
    if not player_doc.exists:
        return {"error": f"트레이너 '{trainer_id}'가 존재하지 않습니다."}
        
    player_data = player_doc.to_dict()
    collection = set(player_data.get("collection", []))
    party = list(player_data.get("party", []))
    
    is_new = monster_id not in collection
    collection.add(monster_id)
    
    if len(party) < 3 and monster_id not in party:
        party.append(monster_id)
        
    player_ref.update({
        "collection": list(collection),
        "party": party
    })
    
    return {
        "status": "success",
        "message": f"🎉 축하합니다! {monster_data.get('name')}을(를) 성공적으로 포획했습니다!",
        "is_new_discovery": is_new,
        "monster": monster_data,
        "current_party": party,
        "total_collected": len(collection)
    }


def list_wild_areas() -> List[Dict[str, Any]]:
    """탐험 가능한 야생 지역 목록과 출현 몬스터 정보를 조회합니다.

    Returns:
        탐험 가능한 야생 지역 목록.
    """
    db = get_db()
    docs = db.collection("areas").stream()
    areas = [d.to_dict() for d in docs]
    return areas


def explore_wild_area(area_name_or_id: str) -> Dict[str, Any]:
    """지정한 야생 지역을 탐험하여 야생 몬스터와 조우(Encounter)합니다.

    Args:
        area_name_or_id: 탐험할 지역의 ID (예: 'whispering_woods', 'volcanic_valley') 또는 지역명 (예: '위스퍼링 숲', '볼캐닉 밸리').

    Returns:
        조우 결과 메시지 및 나타난 야생 몬스터의 상세 정보 (조우 실패 시 실패 메시지).
    """
    db = get_db()
    target = area_name_or_id.strip().lower()

    # 1. 지역 검색 (ID 또는 이름 매칭)
    area_doc = db.collection("areas").document(target).get()
    area_data = area_doc.to_dict() if area_doc.exists else None

    if not area_data:
        for doc in db.collection("areas").stream():
            data = doc.to_dict()
            if target in data.get("name", "").lower() or target in data.get("id", "").lower():
                area_data = data
                break

    if not area_data:
        return {"error": f"'{area_name_or_id}' 지역을 찾을 수 없습니다. list_wild_areas 도구로 탐험 가능한 지역을 확인하세요."}

    # 2. 조우 확률 체크 (encounter_rate)
    encounter_rate = area_data.get("encounter_rate", 0.7)
    if random.random() > encounter_rate:
        return {
            "status": "peaceful",
            "message": f"🌿 {area_data.get('name')} 주변을 조용히 탐색했지만 이번엔 몬스터를 만나지 못했습니다. 다시 시도해 보세요!"
        }

    # 3. 출현 몬스터 풀에서 무작위 선택
    available = area_data.get("available_monsters", [])
    if not available:
        return {"status": "empty", "message": f"{area_data.get('name')}에는 현재 서식하는 몬스터가 없습니다."}

    chosen_id = random.choice(available)
    monster_doc = db.collection("monsters").document(chosen_id).get()

    if not monster_doc.exists:
        return {"error": f"몬스터 '{chosen_id}' 정보를 불러올 수 없습니다."}

    monster = monster_doc.to_dict()
    return {
        "status": "encounter",
        "message": f"⚔️ 야생의 {monster.get('name')}이(가) 나타났습니다!",
        "area": area_data.get("name"),
        "wild_monster": monster,
        "action_prompt": f"포획 도구(catch_monster)로 '{chosen_id}'를 잡거나, 도망칠 수 있습니다."
    }


def lookup_pokemon_api(pokemon_name_or_id: str) -> Dict[str, Any]:
    """공개 PokeAPI(무료 REST API)를 호출하여 포켓몬의 공식 스탯, 속성 타입, 특성 및 공식 일러스트 URL을 조회합니다.

    Args:
        pokemon_name_or_id: 조회할 포켓몬의 영문 이름 (예: 'pikachu', 'charizard', 'eevee', 'mewtwo') 또는 도감 번호 (예: '25', '6').

    Returns:
        공식 포켓몬 데이터 (이름, 타입, 기본 스탯, 특성, 키/몸무게, 고화질 공식 일러스트 이미지 URL).
    """
    clean_query = pokemon_name_or_id.strip().lower()
    # Support custom API base URL or key from environment if specified
    base_url = os.environ.get("POKEAPI_BASE_URL", "https://pokeapi.co/api/v2")
    url = f"{base_url}/pokemon/{clean_query}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MonsterCollectorAgent/1.0 (BuildWithGemini)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status != 200:
                return {"error": f"PokeAPI 호출 실패 (HTTP {response.status})"}
            raw_data = json.loads(response.read().decode("utf-8"))

        # Extract essential fields concisely
        types = [t["type"]["name"] for t in raw_data.get("types", [])]
        stats = {s["stat"]["name"]: s["base_stat"] for s in raw_data.get("stats", [])}
        abilities = [a["ability"]["name"] for a in raw_data.get("abilities", [])]
        sprites = raw_data.get("sprites", {})
        other_sprites = sprites.get("other", {})
        official_artwork = other_sprites.get("official-artwork", {}).get("front_default")
        image_url = official_artwork or sprites.get("front_default")

        return {
            "status": "success",
            "name": raw_data.get("name"),
            "id": raw_data.get("id"),
            "types": types,
            "stats": stats,
            "abilities": abilities,
            "height": raw_data.get("height", 0) / 10,  # convert decimetres to meters
            "weight": raw_data.get("weight", 0) / 10,  # convert hectograms to kg
            "image_url": image_url,
            "source": "PokeAPI (Public REST API)"
        }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"error": f"포켓몬 '{pokemon_name_or_id}'를 찾을 수 없습니다. 영문 이름(예: pikachu, charizard)으로 검색해 보세요."}
        return {"error": f"PokeAPI HTTP 오류: {e.code}"}
    except Exception as e:
        return {"error": f"PokeAPI 연동 중 오류 발생: {str(e)}"}


def geocode_location(address_query: str) -> Dict[str, Any]:
    """Google Maps Geocoding API를 호출하여 특정 주소나 지명(예: '샌프란시스코', '도쿄 타워', '서울역')의 위도/경도 좌표 및 표준 주소를 반환합니다.

    Args:
        address_query: 검색할 주소, 도시 이름 또는 랜드마크 명칭.

    Returns:
        위도(lat), 경도(lng), 포맷된 전체 주소 및 상태 결과.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {
            "error": "GOOGLE_MAPS_API_KEY 환경변수가 설정되지 않았습니다. .env 파일에 키를 추가해 주세요."
        }

    try:
        encoded_query = urllib.parse.quote(address_query)
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_query}&key={api_key}&language=ko"
        req = urllib.request.Request(url, headers={"User-Agent": "MonsterCollectorAgent/1.0"})
        with urllib.request.urlopen(req, timeout=6) as response:
            res_data = json.loads(response.read().decode("utf-8"))

        if res_data.get("status") != "OK":
            return {"error": f"Geocoding 실패: {res_data.get('status')} - {res_data.get('error_message', '')}"}

        result = res_data["results"][0]
        location = result["geometry"]["location"]
        return {
            "status": "success",
            "query": address_query,
            "formatted_address": result.get("formatted_address"),
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "place_id": result.get("place_id"),
        }
    except Exception as e:
        return {"error": f"Google Maps Geocoding 호출 중 오류 발생: {str(e)}"}


def search_nearby_places(location_query: str, place_type: str = "park") -> Dict[str, Any]:
    """Google Maps Places API를 통해 특정 지역 주변의 장소(예: 공원, 랜드마크 등)를 검색하여 몬스터 출몰 장소를 추천합니다.

    Args:
        location_query: 중심 지역/도시 (예: '서울', '뉴욕', '도쿄').
        place_type: 찾을 장소 유형 (기본값: 'park' (공원), 또는 'tourist_attraction', 'museum' 등).

    Returns:
        주변 장소 목록 (이름, 주소, 평점, 위도/경도).
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {
            "error": "GOOGLE_MAPS_API_KEY 환경변수가 설정되지 않았습니다. .env 파일에 키를 추가해 주세요."
        }

    geo = geocode_location(location_query)
    if "error" in geo:
        return geo

    lat, lng = geo["latitude"], geo["longitude"]
    try:
        url = (
            f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            f"?location={lat},{lng}&radius=3000&type={place_type}&key={api_key}&language=ko"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "MonsterCollectorAgent/1.0"})
        with urllib.request.urlopen(req, timeout=6) as response:
            res_data = json.loads(response.read().decode("utf-8"))

        places = []
        for p in res_data.get("results", [])[:5]:
            places.append({
                "name": p.get("name"),
                "vicinity": p.get("vicinity"),
                "rating": p.get("rating"),
                "location": p.get("geometry", {}).get("location")
            })

        return {
            "status": "success",
            "center_address": geo.get("formatted_address"),
            "center_coords": {"lat": lat, "lng": lng},
            "places_found": places
        }
    except Exception as e:
        return {"error": f"Google Maps Places 호출 중 오류 발생: {str(e)}"}


async def generate_monster_image(
    prompt: str,
    tool_context: ToolContext,
    monster_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Gemini 3.1 Flash Lite Image 모델을 사용하여 몬스터의 일러스트 이미지를 생성합니다.
    생성된 이미지는 Playground의 Artifacts 탭에 저장되며, 공개 Cloud Storage 버킷에 업로드되어 퍼블릭 URL로 제공됩니다.

    Args:
        prompt: 생성할 몬스터의 외형, 속성, 분위기 등을 묘사한 프롬프트 (예: '귀여운 아기 불꽃 여우 몬스터, 디지털 아트, 고화질').
        monster_name: 몬스터 이름 또는 식별자 (선택 사항, 파일명 생성에 사용).

    Returns:
        생성 상태 및 퍼블릭 Cloud Storage URL (https://storage.googleapis.com/...).
    """
    try:
        # 1. Initialize GenAI client with global location and Vertex AI
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

        # 2. Call gemini-3.1-flash-lite-image model
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )

        image_bytes: Optional[bytes] = None
        mime_type = "image/jpeg"

        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return {"error": "모델로부터 생성된 이미지 바이너리를 추출하지 못했습니다."}

        # 3. Save as Artifact in ToolContext for the Playground UI
        clean_name = (monster_name or "monster").strip().lower().replace(" ", "_")
        timestamp = int(time.time())
        extension = "jpg" if "jpeg" in mime_type else "png"
        filename = f"{clean_name}_{timestamp}.{extension}"

        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        await tool_context.save_artifact(
            filename=filename,
            artifact=artifact_part,
            custom_metadata={"prompt": prompt, "model": "gemini-3.1-flash-lite-image"}
        )

        # 4. Upload bytes directly to Google Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "message": f"'{monster_name or '몬스터'}'의 이미지가 성공적으로 생성되었습니다!",
            "public_image_url": public_url,
            "artifact_filename": filename,
            "model_used": "gemini-3.1-flash-lite-image (global)",
            "prompt": prompt
        }
    except Exception as e:
        return {"error": f"몬스터 이미지 생성 중 오류 발생: {str(e)}"}




