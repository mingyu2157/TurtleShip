# items.py
# 역할:
#   적 배가 파괴되었을 때 떨어질 수 있는 아이템을 관리합니다.
#   탄환 강화, 연사, 필살기 충전 같은 기능을 여기에서 다룹니다.
#
# 현재 상태:
#   ITEM_DROP_ENABLED 값이 False라서 아직 실제 게임에는 아이템이 나오지 않습니다.
#   기능을 켤 때는 이 값을 True로 바꾸고, ITEM_TYPES에 새 아이템을 추가하면 됩니다.
import random

import pygame

import assets
import layout
import projectiles
from settings import BLUE, GREEN, YELLOW


ITEM_DROP_ENABLED = False
ITEM_DROP_RATE = 0.12

# 아이템 종류별 설정입니다.
# image는 사용할 이미지 이름, effect는 먹었을 때 실행할 효과 이름입니다.
# radius는 충돌 판정과 기본 원형 그림 크기에 같이 사용합니다.
ITEM_TYPES = {
    "bullet_upgrade": {
        "image": "item_bullet_upgrade",
        "effect": "bullet_upgrade",
        "color": YELLOW,
        "radius": 17,
        "max_level": 5,
    },
    "rapid_fire": {
        "image": "item_rapid_fire",
        "effect": "rapid_fire",
        "color": BLUE,
        "radius": 16,
        "duration": 6.0,
    },
    "ultimate_charge": {
        "image": "item_ultimate_charge",
        "effect": "ultimate_charge",
        "color": GREEN,
        "radius": 18,
        "charge": 35,
    },
}


# 게임 시작 또는 스테이지 전환 때 화면에 남은 아이템을 정리합니다.
def reset_items(game):
    game.items = []


# 아이템 종류 이름으로 설정값을 가져옵니다.
# 잘못된 이름이 들어오면 bullet_upgrade를 기본값으로 사용합니다.
def get_item_type(kind):
    return ITEM_TYPES.get(kind, ITEM_TYPES["bullet_upgrade"])


# 적이 파괴되었을 때 아이템을 떨어뜨릴지 랜덤으로 결정합니다.
# 생성된 아이템은 game.items 리스트에 저장되고, update_items()가 움직임과 획득을 처리합니다.
def maybe_spawn_item(game, enemy):
    if not ITEM_DROP_ENABLED or random.random() > ITEM_DROP_RATE:
        return

    kind = random.choice(list(ITEM_TYPES))
    config = get_item_type(kind)
    game.items.append(
        {
            "type": kind,
            "x": float(enemy["rect"].centerx),
            "y": float(enemy["rect"].centery),
            "vy": 95.0,
            "radius": config["radius"],
        }
    )


# 화면에 떠 있는 아이템들을 아래로 움직이고, 플레이어와 닿았는지 확인합니다.
# 닿으면 apply_item()으로 효과를 적용한 뒤 리스트에서 제거합니다.
def update_items(game, dt):
    if not getattr(game, "items", None) or not game.player:
        return

    combat_area = layout.get_combat_area(game)
    for item in game.items[:]:
        item["y"] += item["vy"] * dt
        item_rect = projectiles.get_circle_rect(item["x"], item["y"], item["radius"])

        if item_rect.top > combat_area.bottom + 80:
            game.items.remove(item)
            continue

        if game.player["rect"].colliderect(item_rect):
            apply_item(game, item)
            game.items.remove(item)
            assets.play_sound(game, "item", 0.6)


# 아이템 효과를 실제로 적용합니다.
# 새 아이템을 추가할 때는 ITEM_TYPES에 effect 이름을 넣고,
# 이 함수에 elif를 하나 더 추가하면 됩니다.
def apply_item(game, item):
    config = get_item_type(item["type"])
    effect = config["effect"]

    if effect == "bullet_upgrade":
        max_level = config.get("max_level", 5)
        game.bullet_level = min(max_level, getattr(game, "bullet_level", 0) + 1)
    elif effect == "rapid_fire":
        game.rapid_fire_timer = max(getattr(game, "rapid_fire_timer", 0), config.get("duration", 6.0))
    elif effect == "ultimate_charge":
        game.ultimate_charge = min(getattr(game, "ultimate_max", 100), getattr(game, "ultimate_charge", 0) + config["charge"])
