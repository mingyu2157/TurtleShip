# actors.py
# 역할:
#   플레이어, 일반 적, 미니보스처럼 "움직이는 캐릭터/배"를 관리합니다.
#   탄환은 projectiles.py, 충돌은 combat.py, 보상은 rewards.py가 맡습니다.
#
# 초보자 포인트:
#   pygame.Rect는 위치와 크기를 가진 사각형입니다.
#   이미지가 없어도 Rect가 있으면 이동, 충돌, 화면 위치 계산을 할 수 있습니다.
import math
import random

import pygame

import assets
import layout
import projectiles
import rewards
from settings import MOVE_SCANCODES
from skins import PLAYER_HEIGHT, PLAYER_WIDTH
from stages import KILLS_TO_BOSS, MAX_ENEMIES_ON_SCREEN, STAGE_MAX


# 새 게임을 시작할 때 모든 진행 상태를 처음으로 되돌립니다.
# 플레이어 Rect도 여기에서 만들고, 전투 영역 맨 아래쪽에 배치합니다.
def start_game(game):
    game.game_state = "play"
    game.paused = False
    game.stage_index = 0
    game.kill_count = 0
    game.score = 0
    game.enemy_spawn_timer = 0
    game.stage_banner_timer = 2.0
    game.message_timer = 0
    game.message_text = ""
    game.shoot_cooldown = 0
    game.bullets = []
    game.enemies = []
    game.enemy_projectiles = []
    game.boss = None
    rewards.reset_rewards(game)

    game.player = {
        "rect": pygame.Rect(0, 0, PLAYER_WIDTH, PLAYER_HEIGHT),
        "maxHp": 140,
        "hp": 140.0,
        "speed": 360,
    }
    combat_area = layout.get_combat_area(game)
    game.player["rect"].center = (combat_area.centerx, combat_area.bottom - 72)
    keep_player_inside(game)


# 보스를 처치했을 때 다음 스테이지로 넘어갑니다.
# 마지막 스테이지를 넘어서면 게임 클리어 상태로 바뀝니다.
def next_stage(game):
    game.stage_index += 1
    if game.stage_index >= STAGE_MAX:
        end_game(game, True)
        return

    game.kill_count = 0
    game.boss = None
    game.enemies = []
    game.bullets = []
    game.enemy_projectiles = []
    game.stage_banner_timer = 2.0
    rewards.on_stage_change(game)


# 게임을 끝내고 결과 화면 상태로 바꿉니다.
# clear=True면 클리어 화면, False면 게임오버 화면입니다.
def end_game(game, clear):
    game.game_state = "clear" if clear else "gameover"


# 플레이어 이동을 처리합니다.
# WASD, 방향키, 한글 입력 상태에서도 물리 키 scancode로 움직일 수 있게 되어 있습니다.
def update_player(game, dt):
    keys = pygame.key.get_pressed()
    move_x = 0
    move_y = 0

    if keys[pygame.K_LEFT] or keys[pygame.K_a] or game.held_scancodes & MOVE_SCANCODES["left"]:
        move_x -= 1
    if keys[pygame.K_RIGHT] or keys[pygame.K_d] or game.held_scancodes & MOVE_SCANCODES["right"]:
        move_x += 1
    if keys[pygame.K_UP] or keys[pygame.K_w] or game.held_scancodes & MOVE_SCANCODES["up"]:
        move_y -= 1
    if keys[pygame.K_DOWN] or keys[pygame.K_s] or game.held_scancodes & MOVE_SCANCODES["down"]:
        move_y += 1

    if move_x != 0 or move_y != 0:
        length = math.sqrt(move_x * move_x + move_y * move_y)
        game.player["rect"].x += int(move_x / length * game.player["speed"] * dt)
        game.player["rect"].y += int(move_y / length * game.player["speed"] * dt)

    keep_player_inside(game)


# 플레이어가 바다 전투 영역 밖으로 나가지 못하게 제한합니다.
# 배경 이미지의 테두리 영역은 layout.py에서 전투 영역 밖으로 계산됩니다.
def keep_player_inside(game):
    if not game.player:
        return

    rect = game.player["rect"]
    combat_area = layout.get_combat_area(game)
    rect.left = max(combat_area.left + 8, rect.left)
    rect.right = min(combat_area.right - 8, rect.right)
    rect.top = max(combat_area.top + 8, rect.top)
    rect.bottom = min(combat_area.bottom - 8, rect.bottom)


# 일반 적들을 이동시키고 새 적을 생성합니다.
# 보스가 등장해 있으면 일반 적은 더 이상 생성하지 않습니다.
# 스테이지 데이터에 max_enemies가 있으면 그 값을 우선 사용해서 물량 단계를 만들 수 있습니다.
def update_enemies(game, dt):
    if game.boss is not None:
        return

    combat_area = layout.get_combat_area(game)
    remove_area = combat_area.inflate(220, 220)
    for enemy in game.enemies[:]:
        enemy["age"] += dt
        drift = math.sin(enemy["age"] * 2.6) * dt
        enemy["rect"].x += int(enemy["vx"] * dt + enemy["drift_x"] * drift)
        enemy["rect"].y += int(enemy["vy"] * dt + enemy["drift_y"] * drift)

        if not remove_area.colliderect(enemy["rect"]):
            game.enemies.remove(enemy)

    game.enemy_spawn_timer += dt * 1000
    stage = game.current_stage()
    spawn_ms = stage["spawn_ms"]
    max_enemies = stage.get("max_enemies", MAX_ENEMIES_ON_SCREEN)

    if game.kill_count >= KILLS_TO_BOSS:
        spawn_boss(game)
        return

    if game.enemy_spawn_timer < spawn_ms or len(game.enemies) >= max_enemies:
        return

    game.enemy_spawn_timer = 0
    create_enemy(game)


# 일반 적 1척을 만듭니다.
# 아래쪽에서는 나오지 않고, 위/왼쪽/오른쪽 중 하나에서 등장해 반대 방향으로 이동합니다.
# 적 이미지가 있으면 이미지 비율에 맞춰 Rect 크기를 잡아서 배가 납작하게 찌그러지지 않게 합니다.
def create_enemy(game):
    stage = game.current_stage()
    combat_area = layout.get_combat_area(game)
    enemy_image = assets.get_stage_image(game, "enemy")
    if enemy_image:
        height = random.randint(78, 96)
        aspect = enemy_image.get_width() / max(1, enemy_image.get_height())
        width = max(54, min(118, int(height * aspect)))
    else:
        width = random.randint(72, 94)
        height = random.randint(42, 54)
    rect = pygame.Rect(0, 0, width, height)
    side = random.choice(("top", "left", "right"))

    if side == "top":
        start = (
            random.randint(combat_area.left + width // 2, combat_area.right - width // 2),
            combat_area.top - height,
        )
        target = (
            random.randint(combat_area.left + width // 2, combat_area.right - width // 2),
            combat_area.bottom + height,
        )
    elif side == "left":
        start = (
            combat_area.left - width,
            random.randint(combat_area.top + height // 2, combat_area.bottom - height // 2),
        )
        target = (
            combat_area.right + width,
            random.randint(combat_area.top + height // 2, combat_area.bottom - height // 2),
        )
    else:
        start = (
            combat_area.right + width,
            random.randint(combat_area.top + height // 2, combat_area.bottom - height // 2),
        )
        target = (
            combat_area.left - width,
            random.randint(combat_area.top + height // 2, combat_area.bottom - height // 2),
        )

    rect.center = start
    dx = target[0] - start[0]
    dy = target[1] - start[1]
    distance = max(1, math.sqrt(dx * dx + dy * dy))
    speed = stage["enemy_speed"] * random.uniform(0.85, 1.18)
    vx = dx / distance * speed
    vy = dy / distance * speed
    drift_power = random.uniform(-42, 42)

    game.enemies.append(
        {
            "rect": rect,
            "hp": float(stage["enemy_hp"]),
            "maxHp": float(stage["enemy_hp"]),
            "vx": vx,
            "vy": vy,
            "word": random.choice(stage["enemy_words"]),
            "drift_x": -vy / speed * drift_power,
            "drift_y": vx / speed * drift_power,
            "age": random.random() * 10,
            "damage": 16 + game.stage_index * 4,
            "side": side,
        }
    )


# 현재 스테이지의 미니보스를 생성합니다.
# 보스가 등장하면 일반 적과 적 탄환을 정리하고, 등장 메시지와 효과음을 재생합니다.
def spawn_boss(game):
    stage = game.current_stage()
    play_area = layout.get_combat_area(game)
    width = 300 if game.stage_index == STAGE_MAX - 1 else 230 + game.stage_index * 18
    height = 126 if game.stage_index == STAGE_MAX - 1 else 96 + game.stage_index * 8
    rect = pygame.Rect(0, 0, width, height)
    rect.center = (play_area.centerx, play_area.top - height)

    game.boss = {
        "rect": rect,
        "hp": float(stage["boss_hp"]),
        "maxHp": float(stage["boss_hp"]),
        "shield": float(stage["boss_shield"]),
        "maxShield": float(stage["boss_shield"]),
        "age": 0.0,
        "shotTimer": stage.get("boss_shot_interval", 0.9),
        "burstTimer": stage.get("boss_burst_interval", 2.2),
        "restoreTimer": 0.0,
    }

    game.enemies = []
    game.enemy_projectiles = []
    game.message_text = f"{stage['boss']} 등장"
    game.message_timer = 2.0
    assets.play_stage_sound(game, "boss", 0.8)


# 미니보스 이동과 공격 타이머를 처리합니다.
# stage["pattern"] 값에 따라 보스 이동 방식과 탄막 패턴이 달라집니다.
# stage["boss_can_shoot"]가 False인 단계는 보스가 직접 공격하지 않습니다.
def update_boss(game, dt):
    if game.boss is None:
        return

    stage = game.current_stage()
    rect = game.boss["rect"]
    play_area = layout.get_play_area(game)
    game.boss["age"] += dt

    target_y = max(play_area.top + 92, layout.get_hud_height(game) + 36)
    rect.y += int((target_y - rect.y) * min(1, dt * 2.8))

    center_x = play_area.centerx
    sway = min(260, play_area.width * 0.22)
    pattern = stage["pattern"]

    if pattern == "sniper":
        player_x = game.player["rect"].centerx
        rect.centerx += int(max(-180 * dt, min(180 * dt, player_x - rect.centerx)))
    elif pattern == "storm":
        rect.centerx = int(center_x + math.sin(game.boss["age"] * 2.5) * sway + math.sin(game.boss["age"] * 5) * 35)
    else:
        rect.centerx = int(center_x + math.sin(game.boss["age"] * (1.2 + game.stage_index * 0.18)) * sway)

    rect.left = max(play_area.left + 12, rect.left)
    rect.right = min(play_area.right - 12, rect.right)

    if game.stage_index == STAGE_MAX - 1 and game.boss["shield"] <= 0:
        game.boss["restoreTimer"] += dt
        if game.boss["restoreTimer"] >= 8.0:
            game.boss["shield"] = game.boss["maxShield"] * 0.45
            game.boss["restoreTimer"] = 0

    if not stage.get("boss_can_shoot", True):
        return

    game.boss["shotTimer"] -= dt
    game.boss["burstTimer"] -= dt

    if game.boss["shotTimer"] <= 0:
        game.boss["shotTimer"] = stage.get("boss_shot_interval", max(0.38, 1.1 - game.stage_index * 0.11))
        projectiles.make_boss_projectile(game, 0, aimed=True)

    if game.boss["burstTimer"] <= 0:
        game.boss["burstTimer"] = stage.get("boss_burst_interval", max(1.3, 2.6 - game.stage_index * 0.15))
        shoot_boss_burst(game)


# 보스의 패턴별 다발 공격을 만듭니다.
# 실제 탄환 생성은 projectiles.make_boss_projectile()에 맡기고,
# 이 함수는 어떤 각도/간격으로 쏠지만 결정합니다.
def shoot_boss_burst(game):
    pattern = game.current_stage()["pattern"]

    if pattern == "guided":
        offsets = [0]
    elif pattern == "spread":
        offsets = [-90, -45, 0, 45, 90]
    elif pattern == "fan":
        offsets = [-150, -95, -45, 45, 95, 150]
    elif pattern == "sniper":
        offsets = [-40, 0, 40]
    elif pattern == "storm":
        offsets = [-180, -120, -60, 0, 60, 120, 180]
    else:
        offsets = [-70, 0, 70]

    for offset in offsets:
        projectiles.make_boss_projectile(game, offset * 0.35, aimed=pattern == "guided", angle_offset=offset)
