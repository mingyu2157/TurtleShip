# weather.py
# 역할:
#   바다 위에 가끔 나타나는 날씨 효과를 관리합니다.
#   태풍은 랜덤 위치, 빗물/번개는 전체 플레이 영역에 적용되고 사라지기 1초 전부터 깜빡입니다.
#
# 현재 날씨:
#   태풍: 범위 안의 플레이어/적/보스가 지속 피해를 받고, 전장 전체 파도를 강하게 만듭니다.
#   빗물: 플레이 영역 전체에서 플레이어/적/보스 이동속도가 느려집니다.
#   번개: 플레이어/적/보스 중 랜덤 1명이 1초 동안 이동만 마비됩니다.
#
# 초보자 포인트:
#   날씨 밸런스나 투명도를 바꾸고 싶으면 아래 WEATHER_TYPES 숫자만 고치면 됩니다.
#   예를 들어 태풍을 더 아프게 하려면 "damage_per_second"를 올리고,
#   비를 덜 거슬리게 하려면 "alpha"를 낮추면 됩니다.
#
# 공부 순서:
#   WEATHER_TYPES에서 날씨별 설정을 먼저 보고,
#   update_weather() -> spawn_weather() -> apply_weather_effects() 순서로 읽으면 흐름이 보입니다.
import random

import pygame

import assets
import layout
import rewards


MAX_WEATHER_EVENTS = 1
# 날씨는 10~15초마다 한 번 새로 등장할 기회를 얻습니다.
WEATHER_SPAWN_INTERVAL_RANGE = (10.0, 15.0)
WEATHER_BLINK_SECONDS = 1.0
WEATHER_BLINKS_PER_SECOND = 8

WEATHER_TYPES = {
    # 각 날씨는 딕셔너리 하나로 정의합니다.
    # weight는 랜덤 선택 확률의 상대값이고, alpha는 화면에 그릴 때의 투명도입니다.
    "typhoon": {
        "images": ("weather_typhoon1", "weather_typhoon2"),
        "area_mode": "local",
        "weight": 0.32,
        "size_range": ((150, 120), (230, 190)),
        "duration_range": (5.0, 8.5),
        "alpha": 150,
        "blink_alpha_low": 55,
        "blink_alpha_high": 165,
        "effect_inflate": 0.28,
        "damage_per_second": 20.0,
        "enemy_damage_per_second": 10.0,
        "boss_damage_per_second": 7.0,
        "wave_boost": 2.25,
        "fallback_color": (116, 169, 205),
    },
    "rain": {
        "images": ("weather_rain1",),
        "area_mode": "full",
        "weight": 0.46,
        "size_range": ((250, 130), (390, 205)),
        "duration_range": (7.5, 13.0),
        "alpha": 105,
        "blink_alpha_low": 45,
        "blink_alpha_high": 140,
        "effect_inflate": 0.05,
        "speed_multiplier": 0.58,
        "fallback_color": (119, 180, 230),
    },
    "lightning": {
        "images": ("weather_lightning1",),
        "area_mode": "full",
        "weight": 0.22,
        "size_range": ((120, 82), (190, 126)),
        "duration_range": (0.9, 1.4),
        "alpha": 150,
        "blink_alpha_low": 70,
        "blink_alpha_high": 205,
        "effect_inflate": 0.16,
        "stun_seconds": 1.0,
        "fallback_color": (252, 228, 114),
    },
}


# 새 게임이나 새 스테이지에서 날씨 목록과 다음 등장 시간을 초기화합니다.
def reset_weather(game):
    game.weather_events = []
    game.weather_spawn_timer = random.uniform(*WEATHER_SPAWN_INTERVAL_RANGE)


# 매 프레임 날씨 시간을 줄이고, 새 날씨를 만들고, 효과를 적용합니다.
def update_weather(game, dt):
    if not hasattr(game, "weather_events"):
        reset_weather(game)

    # 먼저 기존 마비 시간을 줄입니다. 그래야 1초가 지나면 자연스럽게 풀립니다.
    tick_actor_statuses(game, dt)

    # 현재 떠 있는 날씨들의 남은 시간을 줄이고, 끝난 날씨는 제거합니다.
    for event in game.weather_events[:]:
        event["timer"] -= dt
        event["age"] += dt
        if event["timer"] <= 0:
            game.weather_events.remove(event)

    # 다음 날씨 등장까지 남은 시간을 줄입니다.
    game.weather_spawn_timer = max(0, getattr(game, "weather_spawn_timer", 0) - dt)
    if game.weather_spawn_timer <= 0:
        game.weather_spawn_timer = random.uniform(*WEATHER_SPAWN_INTERVAL_RANGE)
        if len(game.weather_events) < MAX_WEATHER_EVENTS:
            spawn_weather(game)

    apply_weather_effects(game, dt)


# 플레이어/적/보스에게 남아 있는 마비 시간을 줄입니다.
def tick_actor_statuses(game, dt):
    for actor in get_status_actors(game):
        actor["weather_stun_timer"] = max(0, actor.get("weather_stun_timer", 0) - dt)


# 마비 시간을 관리할 수 있는 대상들을 모아 돌려줍니다.
def get_status_actors(game):
    actors = []
    if getattr(game, "player", None):
        actors.append(game.player)
    actors.extend(getattr(game, "enemies", []))
    if getattr(game, "boss", None) is not None:
        actors.append(game.boss)
    return actors


# 설정된 가중치에 따라 어떤 날씨가 나올지 고릅니다.
def pick_weather_kind():
    # 가중치 방식:
    # rain 0.46, typhoon 0.32처럼 숫자가 클수록 뽑힐 확률이 커집니다.
    total = sum(config["weight"] for config in WEATHER_TYPES.values())
    roll = random.uniform(0, total)
    upto = 0
    for kind, config in WEATHER_TYPES.items():
        upto += config["weight"]
        if roll <= upto:
            return kind
    return "rain"


# 전투 영역 안의 랜덤 위치에 날씨 하나를 생성합니다.
def spawn_weather(game):
    kind = pick_weather_kind()
    config = WEATHER_TYPES[kind]
    image_name = random.choice(config["images"])
    combat_area = layout.get_combat_area(game)

    if combat_area.width <= 0 or combat_area.height <= 0:
        return

    if config.get("area_mode") == "full":
        # 비와 번개는 전체 플레이 영역에 적용되므로 rect도 전투 영역 전체로 잡습니다.
        rect = combat_area.copy()
    else:
        # 태풍은 지역형 날씨라서 랜덤 위치와 랜덤 크기를 가집니다.
        rect = make_weather_rect(game, config, image_name)
        spawn_area = combat_area.inflate(-28, -28)
        if spawn_area.width <= 0 or spawn_area.height <= 0:
            return

        min_x = spawn_area.left + rect.width // 2
        max_x = max(min_x, spawn_area.right - rect.width // 2)
        min_y = spawn_area.top + rect.height // 2
        max_y = max(min_y, spawn_area.bottom - rect.height // 2)
        rect.center = (random.randint(min_x, max_x), random.randint(min_y, max_y))
        rect.clamp_ip(combat_area)

    game.weather_events.append(
        {
            # kind는 "typhoon", "rain", "lightning" 중 하나입니다.
            "kind": kind,
            "image": image_name,
            "rect": rect,
            "timer": random.uniform(*config["duration_range"]),
            "age": 0.0,
            "struck_ids": set(),
            "target_actor_id": None,
        }
    )

    if kind == "lightning":
        assets.play_sound(game, "weather_lightning", 0.8)


# 이미지 비율을 유지하면서 설정 범위 안에서 날씨 표시 크기를 정합니다.
def make_weather_rect(game, config, image_name):
    (min_width, min_height), (max_width, max_height) = config["size_range"]
    width = random.randint(min_width, max_width)
    height = random.randint(min_height, max_height)

    image = game.images.get(image_name)
    if image:
        aspect = image.get_width() / max(1, image.get_height())
        width = random.randint(min_width, max_width)
        height = int(width / max(0.1, aspect))

        if height < min_height:
            height = min_height
            width = int(height * aspect)
        elif height > max_height:
            height = max_height
            width = int(height * aspect)

    width = max(24, min(max_width, max(min_width, width)))
    height = max(24, min(max_height, max(min_height, height)))
    return pygame.Rect(0, 0, width, height)


# 현재 켜진 날씨들이 플레이어/적/보스에게 주는 효과를 적용합니다.
def apply_weather_effects(game, dt):
    for event in getattr(game, "weather_events", []):
        kind = event["kind"]
        # 비의 이동속도 감소는 actors.py가 get_speed_multiplier()를 호출할 때 적용됩니다.
        if kind == "typhoon":
            apply_typhoon(game, event, dt)
        elif kind == "lightning":
            apply_lightning(game, event)


# 태풍은 범위 안의 플레이어/적/보스에게 지속 피해를 줍니다.
# 파도 강화는 get_wave_influence_multiplier()에서 전장 전체 효과로 따로 처리합니다.
def apply_typhoon(game, event, dt):
    config = WEATHER_TYPES["typhoon"]
    effect_rect = get_effect_rect(event)

    # 태풍은 범위 안에 있는 동안 매 프레임 조금씩 체력을 깎습니다.
    if getattr(game, "player", None) and effect_rect.colliderect(game.player.get("hitbox", game.player["rect"])):
        incoming = config["damage_per_second"] * dt
        incoming *= getattr(game, "augment_allied_damage_taken_multiplier", 1.0)
        game.player["hp"] = max(0, game.player["hp"] - incoming)

    for enemy in getattr(game, "enemies", [])[:]:
        if not effect_rect.colliderect(enemy["rect"]):
            continue

        enemy["hp"] -= config["enemy_damage_per_second"] * dt
        if enemy["hp"] <= 0:
            destroy_enemy_by_weather(game, enemy)

    if getattr(game, "boss", None) is not None and effect_rect.colliderect(game.boss["rect"]):
        damage_boss_by_weather(game, config["boss_damage_per_second"] * dt)


# 날씨로 적이 파괴되었을 때도 격침 수와 보상을 자연스럽게 처리합니다.
def destroy_enemy_by_weather(game, enemy):
    if enemy not in getattr(game, "enemies", []):
        return

    game.enemies.remove(enemy)
    game.kill_count += 1
    game.score += 70 + game.stage_index * 20
    rewards.on_enemy_destroyed(game, enemy)


# 보스는 보호막이 먼저 깎이고, 남은 피해가 체력에 들어갑니다.
def damage_boss_by_weather(game, amount):
    if game.boss is None:
        return

    remain = amount
    if game.boss.get("shield", 0) > 0:
        shield_damage = min(game.boss["shield"], remain)
        game.boss["shield"] -= shield_damage
        remain -= shield_damage
        if game.boss["shield"] <= 0:
            game.boss["restoreTimer"] = 0

    if remain > 0:
        game.boss["hp"] = max(0, game.boss["hp"] - remain)


# 번개는 플레이어/적/보스 중 랜덤 1명을 1초 동안 이동 마비시킵니다.
# 플레이어가 맞아도 이동만 막히고, 스킬/발사는 기존 입력 로직 그대로 사용할 수 있습니다.
def apply_lightning(game, event):
    config = WEATHER_TYPES["lightning"]
    if event.get("target_actor_id") is None:
        # 같은 번개 이벤트가 매 프레임 새 대상을 고르지 않게 target_actor_id를 한 번만 저장합니다.
        target = pick_lightning_target(game)
        if target is None:
            return
        event["target_actor_id"] = id(target)
        target["weather_stun_timer"] = max(target.get("weather_stun_timer", 0), config["stun_seconds"])


# 번개가 맞출 대상을 랜덤으로 고릅니다.
def pick_lightning_target(game):
    candidates = [actor for actor in get_status_actors(game) if "rect" in actor]
    if not candidates:
        return None

    return random.choice(candidates)


# 빗물 범위 안에 있으면 이동속도 배율을 낮춰 돌려줍니다.
def get_speed_multiplier(game, rect):
    multiplier = 1.0
    for event in getattr(game, "weather_events", []):
        if event["kind"] != "rain":
            continue
        # 비가 켜져 있으면 속도 배율을 낮춥니다. 여러 비가 있어도 가장 낮은 값을 사용합니다.
        multiplier = min(multiplier, WEATHER_TYPES["rain"]["speed_multiplier"])
    return multiplier


# 태풍이 등장해 있는 동안에는 전체 플레이 영역의 파도 영향이 강해집니다.
# 데미지는 태풍 이미지/범위 안에서만 받지만, 거센 바다는 전장 전체에 영향을 준다는 규칙입니다.
def get_wave_influence_multiplier(game, rect):
    multiplier = 1.0
    for event in getattr(game, "weather_events", []):
        if event["kind"] != "typhoon":
            continue
        multiplier = max(multiplier, WEATHER_TYPES["typhoon"]["wave_boost"])
    return multiplier


# 마비 중인 대상인지 확인합니다.
def is_stunned(actor):
    return actor.get("weather_stun_timer", 0) > 0


# 날씨의 실제 효과 범위입니다.
# 이미지보다 살짝 크게/작게 조절하려면 WEATHER_TYPES의 effect_inflate를 바꾸면 됩니다.
def get_effect_rect(event):
    config = WEATHER_TYPES[event["kind"]]
    rect = event["rect"]
    inflate = config.get("effect_inflate", 0)
    return rect.inflate(int(rect.width * inflate), int(rect.height * inflate))


# 사라지기 1초 전 깜빡임까지 반영한 최종 투명도를 계산합니다.
def get_draw_alpha(event):
    config = WEATHER_TYPES[event["kind"]]
    alpha = event.get("alpha", config["alpha"])

    if event["timer"] > WEATHER_BLINK_SECONDS:
        return alpha

    low = event.get("blink_alpha_low", config["blink_alpha_low"])
    high = event.get("blink_alpha_high", config["blink_alpha_high"])
    return low if int(event["timer"] * WEATHER_BLINKS_PER_SECOND) % 2 == 0 else high
