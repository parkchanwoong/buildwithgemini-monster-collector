# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types


MODEL = "gemini-3.6-flash"


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


from app.tools import (
    list_monsters,
    get_monster_detail,
    get_player_profile,
    catch_monster,
    list_wild_areas,
    explore_wild_area,
    lookup_pokemon_api,
    generate_monster_image,
)


# Load Agent Engine resource name from deployment_metadata.json if available
METADATA_PATH = Path(__file__).resolve().parent.parent / "deployment_metadata.json"
agent_engine_resource_name = None
memory_bank_id = "3223905531592704000"
if METADATA_PATH.exists():
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            agent_engine_resource_name = metadata.get("remote_agent_runtime_id")
            if agent_engine_resource_name:
                memory_bank_id = agent_engine_resource_name.split("/")[-1]
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name
)


# Memory Bank: WRITE callback to extract durable facts and preferences across conversations
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


# Memory Bank: builder function for deployed Agent Runtime
def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project="qwiklabs-gcp-04-a56af107c498",
        location="us-east1",
        agent_engine_id=memory_bank_id,
    )


from app.a2ui_utils import a2ui_callback

try:
    from a2ui.schema.manager import A2uiSchemaManager
    from a2ui.basic_catalog.provider import BasicCatalog

    schema_manager = A2uiSchemaManager(
        version="0.8",
        catalogs=[BasicCatalog.get_config("0.8")],
    )

    a2ui_instruction = schema_manager.generate_system_prompt(
        role_description=(
            "당신은 몬스터 수집 및 배틀 모험을 돕는 친절하고 열정적인 '몬스터 콜렉터 안내 AI 에이전트'입니다. "
            "당신은 플레이어가 이전 대화에서 언급한 트레이너 이름, 선호하는 몬스터 타입, 주력 파트너 몬스터, 목표 등의 기억(Memory Bank)을 기억하고 이를 바탕으로 대화를 개인화하여 맞춤형 응답을 제공합니다. "
            "플레이어가 몬스터 도감을 검색하거나, 몬스터의 상세 정보 및 스탯을 묻거나, 야생 탐험 지역을 물어보거나, "
            "야생 지역을 탐험(explore_wild_area)하거나 몬스터를 포획하려고 할 때 제공된 Firestore 도구(tools)를 적극적으로 활용하세요. "
            "또한 피카츄, 리자몽 등 외부 공식 포켓몬 데이터나 이미지를 원할 경우 공개 PokeAPI 도구(lookup_pokemon_api)를 사용하세요. "
            "몬스터의 일러스트나 새로운 크리처/몬스터 이미지를 그려달라고 요청하면 generate_monster_image 도구를 호출하여 멋진 고화질 일러스트를 생성해 제공하세요. "
            "복잡한 배틀 데미지 공식 계산, 경험치/스탯 성장 곡선 시뮬레이션, 확률 계산이나 파이썬 코드 실행이 필요한 경우 격리된 Agent Engine 샌드박스 코드 실행 환경을 활용해 직접 코드를 실행하여 정확한 수치를 계산하세요."
        ),
        workflow_description="Analyze the request and return structured UI when appropriate.",
        ui_description=(
            "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
            "Never nest a Card inside a Card. "
            "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
            "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
            "nothing in adk web). "
            "You may include one Image component, but only when you have a public https "
            "URL for the image (for example the URL an image tool returns after uploading "
            "to a public bucket). Set the Image url to that exact https link, for example "
            '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
            "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
            "not have a public URL, add a short Text line noting the image instead. "
            "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
            "headings and emphasis. "
            "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
            "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
        ),
        include_schema=True,
        include_examples=True,
    )
except Exception:
    prompt_file = Path(__file__).parent / "a2ui_prompt.txt"
    if prompt_file.exists():
        a2ui_instruction = prompt_file.read_text(encoding="utf-8")
    else:
        a2ui_instruction = "당신은 몬스터 수집 및 배틀 모험을 돕는 '몬스터 콜렉터 안내 AI 에이전트'입니다."


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        client_kwargs={"vertexai": True, "location": "global"},
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    code_executor=code_executor,
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    tools=[
        PreloadMemoryTool(),
        list_monsters,
        get_monster_detail,
        get_player_profile,
        catch_monster,
        list_wild_areas,
        explore_wild_area,
        lookup_pokemon_api,
        generate_monster_image,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
