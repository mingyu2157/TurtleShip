# allies.py
# 역할:
#   나중에 추가할 "동료 배" 기능을 담당합니다.
#   적 배가 파괴되었을 때 랜덤으로 동료가 생성되고,
#   동료는 플레이어 주변을 따라다니며 자동으로 탄환을 쏘는 구조입니다.
#
# 현재 상태:
#   ALLY_DROP_ENABLED 값이 False라서 실제 게임에서는 아직 동료가 나오지 않습니다.
#   나중에 True로 바꾸고 이미지 파일을 넣으면 바로 확장할 수 있게 준비만 해둔 파일입니다.
import random

import pygame

import assets
import layout
import projectiles


ALLY_DROP_ENABLED = False
ALLY_DROP_RATE = 0.08

# 동료 종류별 설정입니다.
# image는 assets/images 폴더에 넣을 이미지 이름이고,
# offset은 플레이어 기준으로 동료가 따라다닐 위치입니다.
# cooldown은 몇 초마다 탄환을 쏘는지, damage는 동료 탄환 공격력입니다.
ALLY_TYPES = {
    "support_ship": {
        "image": "ally_support_ship",
        "bullet_image": "ally_support_bullet",
        "offset": (-74, 34),
        "size": (46, 58),
        "cooldown": 0.95,
        "damage": 7,
        "bullet_radius": 5,
    },
    "guard_ship": {
        "image": "ally_guard_ship",
        "bullet_image": "ally_guard_bullet",
        "offset": (74, 34),
        "size": (50, 62),
        "cooldown": 1.25,
        "damage": 11,
        "bullet_radius": 6,
    },
    "rapid_ship": {
        "image": "ally_rapid_ship",
        "bullet_image": "ally_rapid_bullet",
        "offset": (0, 76),
        "size": (42, 54),
        "cooldown": 0.58,
        "damage": 5,
        "bullet_radius": 4,
    },
}


# 게임을 새로 시작할 때 동료 목록을 비웁니다.
# game.allies는 현재 살아 있는 동료들을 담는 리스트입니다.
def reset_allies(game):
    game.allies = []


# 동료 종류 이름으로 설정값을 가져옵니다.
# 잘못된 이름이 들어와도 support_ship 기본값을 돌려줘서 게임이 멈추지 않게 합니다.
def get_ally_type(kind):
    return ALLY_TYPES.get(kind, ALLY_TYPES["support_ship"])


# 적이 파괴되었을 때 동료를 생성할지 랜덤으로 결정합니다.
# 지금은 ALLY_DROP_ENABLED가 False라서 아무 일도 하지 않습니다.
def maybe_spawn_ally(game, enemy):
    if not ALLY_DROP_ENABLED or random.random() > ALLY_DROP_RATE:
        return

    kind = random.choice(list(ALLY_TYPES))
    config = get_ally_type(kind)
    rect = pygame.Rect(0, 0, *config["size"])
    rect.center = enemy["rect"].center
    game.allies.append({"type": kind, "rect": rect, "cooldown": random.uniform(0.1, 0.5)})
    assets.play_sound(game, "ally", 0.55)


# 모든 동료를 매 프레임 업데이트합니다.
# 동료는 플레이어 주변 목표 위치를 향해 부드럽게 따라오고,
# cooldown이 0이 되면 자동으로 shoot_ally_bullet()을 호출합니다.
def update_allies(game, dt):
    if not getattr(game, "allies", None) or not game.player:
        return

    combat_area = layout.get_combat_area(game)
    for ally in game.allies[:]:
        config = get_ally_type(ally["type"])
        target_x = game.player["rect"].centerx + config["offset"][0]
        target_y = game.player["rect"].centery + config["offset"][1]
        ally["rect"].centerx += int((target_x - ally["rect"].centerx) * min(1, dt * 7))
        ally["rect"].centery += int((target_y - ally["rect"].centery) * min(1, dt * 7))
        ally["rect"].clamp_ip(combat_area)

        ally["cooldown"] = max(0, ally["cooldown"] - dt)
        if ally["cooldown"] <= 0:
            shoot_ally_bullet(game, ally, config)
            ally["cooldown"] = config["cooldown"]


# 동료가 발사하는 탄환을 만듭니다.
# 실제 탄환 생성은 projectiles.py의 make_player_bullet()을 재사용합니다.
def shoot_ally_bullet(game, ally, config):
    stage = game.current_stage()
    projectiles.make_player_bullet(
        game,
        ally["rect"].centerx,
        ally["rect"].top - 6,
        0,
        -560,
        config["damage"],
        config["bullet_radius"],
        stage["bullet_color"],
    )
