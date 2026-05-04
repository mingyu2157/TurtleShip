# obstacles.py
# 역할:
#   바다 위에 잠깐 나타나는 지형지물, 즉 "벽" 역할의 장애물을 관리합니다.
#   장애물은 랜덤 위치에 생기고, 랜덤 시간 동안 유지되다가 사라집니다.
#
# 현재 상태:
#   지형지물은 중앙 전투 영역 중간에 생성됩니다.
#   플레이어와 적은 지형지물을 통과하지 못합니다.
#   플레이어 탄환, 전술 탄환, 적 탄환은 지형지물을 관통하지 못하고 사라집니다.
#   사라지기 1초 전부터 깜빡여서 곧 없어질 것을 보여줍니다.
#
# 초보자 포인트:
#   이미지 전체에는 물보라가 포함되어 있어서, 그 전체를 벽으로 쓰면 부딪힘이 억울합니다.
#   그래서 get_block_rect()에서 실제 막히는 영역을 이미지보다 작게 잡습니다.
#
# 공부 순서:
#   update_obstacles()에서 생성/삭제 흐름을 보고,
#   spawn_obstacle()에서 랜덤 위치 생성,
#   get_block_rect()/resolve_player_collision()/block_projectiles()에서 벽 역할을 보면 됩니다.
import random

import pygame

import layout
import projectiles


OBSTACLE_TYPES = [
    # block_scale은 이미지 전체 중 실제로 막히는 중심부 비율입니다.
    {
        "image": "obstacle_rock1",
        "size_range": ((92, 46), (142, 72)),
        "block_scale": (0.48, 0.50),
    },
    {
        "image": "obstacle_rock2",
        "size_range": ((86, 56), (132, 88)),
        "block_scale": (0.44, 0.58),
    },
]

MAX_OBSTACLES = 2
SPAWN_INTERVAL_RANGE = (5.0, 9.0)
DURATION_RANGE = (7.0, 13.0)

# 지형지물 깜박임 설정입니다.
# 깜박이는 시간을 바꾸고 싶으면 OBSTACLE_BLINK_SECONDS만 조정하면 됩니다.
# 깜박임 속도와 투명도도 아래 숫자만 바꾸면 전체 지형지물에 바로 적용됩니다.
OBSTACLE_BLINK_SECONDS = 1.0
OBSTACLE_BLINKS_PER_SECOND = 8
OBSTACLE_BLINK_ALPHA_LOW = 95
OBSTACLE_BLINK_ALPHA_HIGH = 230


# 새 게임이나 새 스테이지가 시작될 때 지형지물 상태를 초기화합니다.
def reset_obstacles(game):
    game.obstacles = []
    game.obstacle_spawn_timer = random.uniform(*SPAWN_INTERVAL_RANGE)


# 매 프레임 지형지물 시간을 줄이고, 필요하면 새 지형지물을 생성합니다.
def update_obstacles(game, dt):
    if not hasattr(game, "obstacles"):
        reset_obstacles(game)

    for obstacle in game.obstacles[:]:
        # timer는 남은 시간, age는 생성 후 지난 시간입니다.
        obstacle["timer"] -= dt
        obstacle["age"] += dt
        if obstacle["timer"] <= 0:
            game.obstacles.remove(obstacle)

    game.obstacle_spawn_timer = max(0, getattr(game, "obstacle_spawn_timer", 0) - dt)
    if game.obstacle_spawn_timer > 0:
        return

    game.obstacle_spawn_timer = random.uniform(*SPAWN_INTERVAL_RANGE)
    if len(game.obstacles) >= MAX_OBSTACLES:
        return

    spawn_obstacle(game)


# 전투 영역 안쪽의 랜덤 위치에 지형지물을 하나 생성합니다.
# 플레이어, 적, 보스, 기존 지형지물과 겹치는 위치는 피해서 갑자기 겹쳐 생기는 일을 줄입니다.
def spawn_obstacle(game):
    combat_area = layout.get_combat_area(game)
    # 화면 전체가 아니라 전투 영역 중간쯤에만 장애물이 생기게 범위를 좁힙니다.
    spawn_area = pygame.Rect(
        combat_area.left + 24,
        combat_area.top + int(combat_area.height * 0.18),
        max(40, combat_area.width - 48),
        max(40, int(combat_area.height * 0.58)),
    )
    if spawn_area.width <= 0 or spawn_area.height <= 0:
        return

    for _ in range(40):
        # 랜덤 위치가 플레이어/적/보스와 겹치면 다시 뽑습니다. 최대 40번만 시도합니다.
        config = random.choice(OBSTACLE_TYPES)
        rect = make_obstacle_rect(config)
        rect.center = (
            random.randint(spawn_area.left + rect.width // 2, spawn_area.right - rect.width // 2),
            random.randint(spawn_area.top + rect.height // 2, spawn_area.bottom - rect.height // 2),
        )
        obstacle = {
            "image": config["image"],
            "rect": rect,
            "timer": random.uniform(*DURATION_RANGE),
            "age": 0.0,
            "block_scale": config["block_scale"],
        }
        if can_place_obstacle(game, obstacle):
            game.obstacles.append(obstacle)
            return


# 지형지물 이미지 비율에 맞춰 표시 크기를 고릅니다.
def make_obstacle_rect(config):
    (min_width, min_height), (max_width, max_height) = config["size_range"]
    width = random.randint(min_width, max_width)
    height = random.randint(min_height, max_height)
    return pygame.Rect(0, 0, width, height)


# 지형지물이 갑자기 다른 물체 위에 생기지 않도록 배치 가능 여부를 확인합니다.
def can_place_obstacle(game, obstacle):
    # inflate(36, 36)는 실제 벽보다 조금 더 넓게 검사해서 너무 붙어 생성되는 일을 줄입니다.
    block_rect = get_block_rect(obstacle).inflate(36, 36)

    if game.player and block_rect.colliderect(game.player["rect"].inflate(80, 80)):
        return False

    for enemy in getattr(game, "enemies", []):
        if block_rect.colliderect(enemy["rect"].inflate(24, 24)):
            return False

    if getattr(game, "boss", None) is not None and block_rect.colliderect(game.boss["rect"].inflate(36, 36)):
        return False

    for other in getattr(game, "obstacles", []):
        if block_rect.colliderect(get_block_rect(other).inflate(42, 42)):
            return False

    return True


# 실제로 막히는 벽 영역입니다.
# 이미지의 물보라를 제외하고 바위 중심부 위주로 잡습니다.
def get_block_rect(obstacle):
    rect = obstacle["rect"]
    scale_x, scale_y = obstacle.get("block_scale", (0.5, 0.55))
    # 이미지 크기에 비례해서 실제 충돌 영역을 작게 만듭니다.
    width = max(10, int(rect.width * scale_x))
    height = max(10, int(rect.height * scale_y))
    block = pygame.Rect(0, 0, width, height)
    block.centerx = rect.centerx
    block.centery = rect.centery - int(rect.height * 0.08)
    return block


# Rect가 현재 지형지물 중 하나와 부딪히는지 확인합니다.
def collides_rect(game, rect):
    for obstacle in getattr(game, "obstacles", []):
        if get_block_rect(obstacle).colliderect(rect):
            return True
    return False


# 원형 탄환이 한 프레임 동안 이동한 경로가 바위 중심부를 스쳤는지 검사합니다.
# 고속 탄환이 프레임 사이에서 얇은 벽을 건너뛰는 문제(터널링)를 줄이기 위해
# 시작점/끝점 포함 + 선분 교차를 함께 사용합니다.
def projectile_hits_obstacle_path(obstacle, projectile):
    block_rect = get_block_rect(obstacle)
    radius = max(1, int(projectile.get("radius", 1)))
    expanded = block_rect.inflate(radius * 2, radius * 2)

    x0 = float(projectile.get("prev_x", projectile.get("x", 0.0)))
    y0 = float(projectile.get("prev_y", projectile.get("y", 0.0)))
    x1 = float(projectile.get("x", 0.0))
    y1 = float(projectile.get("y", 0.0))

    if expanded.collidepoint(x0, y0) or expanded.collidepoint(x1, y1):
        return True
    return bool(expanded.clipline((x0, y0), (x1, y1)))


# 플레이어가 지형지물을 통과하려고 하면 이전 위치로 되돌립니다.
def resolve_player_collision(game, previous_rect):
    if not game.player:
        return

    hitbox = game.player.get("hitbox", game.player["rect"])
    if not collides_rect(game, hitbox):
        return

    game.player["rect"] = previous_rect.copy()
    if "hitbox" in game.player:
        game.player["hitbox"].center = game.player["rect"].center
    game.player["_wave_carry_x"] = 0.0
    game.player["_wave_carry_y"] = 0.0


# 적 배가 지형지물에 닿으면 이전 위치로 돌아가고, 좌우로 살짝 튕기게 합니다.
def resolve_enemy_collision(game, enemy, previous_rect):
    if not collides_rect(game, enemy["rect"]):
        return

    enemy["rect"] = previous_rect.copy()
    enemy["vx"] = -enemy.get("vx", 0) * 0.65
    enemy["drift_x"] = -enemy.get("drift_x", 0) * 0.65
    if abs(enemy["vx"]) < 15:
        enemy["vx"] = random.choice((-55, 55))


# 플레이어/전술 탄환과 적 탄환이 지형지물에 닿으면 제거합니다.
def block_projectiles(game):
    for bullet in game.bullets[:]:
        # 플레이어/전술 탄환이 바위에 닿으면 사라집니다.
        if any(projectile_hits_obstacle_path(obstacle, bullet) for obstacle in getattr(game, "obstacles", [])):
            game.bullets.remove(bullet)

    for projectile in game.enemy_projectiles[:]:
        # 적 탄환도 같은 방식으로 지형지물을 관통하지 못합니다.
        if any(projectile_hits_obstacle_path(obstacle, projectile) for obstacle in getattr(game, "obstacles", [])):
            game.enemy_projectiles.remove(projectile)


# 사라지기 직전 지형지물을 깜빡이게 할 때 쓸 투명도를 계산합니다.
def get_draw_alpha(obstacle):
    blink_seconds = obstacle.get("blink_seconds", OBSTACLE_BLINK_SECONDS)
    blink_rate = obstacle.get("blink_rate", OBSTACLE_BLINKS_PER_SECOND)
    alpha_low = obstacle.get("blink_alpha_low", OBSTACLE_BLINK_ALPHA_LOW)
    alpha_high = obstacle.get("blink_alpha_high", OBSTACLE_BLINK_ALPHA_HIGH)

    if obstacle["timer"] > blink_seconds:
        return 255

    return alpha_low if int(obstacle["timer"] * blink_rate) % 2 == 0 else alpha_high
