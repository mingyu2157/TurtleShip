# projectiles.py
# 역할:
#   플레이어 탄환, 적 탄환, 보스 탄환처럼 "날아다니는 물체"를 관리합니다.
#   탄환은 화면에 그려지는 그림이 아니라, 먼저 딕셔너리 데이터로 만들어져
#   game.bullets 또는 game.enemy_projectiles 리스트에 저장됩니다.
#
# 초보자 포인트:
#   x, y는 현재 위치이고 vx, vy는 속도입니다.
#   매 프레임마다 "현재 위치 += 속도 * dt"를 해주면 탄환이 움직입니다.
#   dt는 지난 프레임부터 지금 프레임까지 걸린 시간이라서,
#   컴퓨터 속도가 달라도 비슷한 속도로 움직이게 해줍니다.
import math
import random

import pygame

import layout


# 플레이어 탄환 1개를 생성합니다.
# 여기서는 화면에 바로 그리지 않고, game.bullets 리스트에 탄환 정보를 저장합니다.
# render.py가 나중에 이 리스트를 읽어서 실제 화면에 탄환을 그립니다.
def make_player_bullet(game, x, y, vx, vy, damage, radius, color):
    game.bullets.append(
        {
            "x": float(x),
            "y": float(y),
            "vx": float(vx),
            "vy": float(vy),
            "damage": float(damage),
            "radius": radius,
            "color": color,
        }
    )


# 플레이어 탄환들을 한 프레임만큼 이동시킵니다.
# 탄환이 전투 영역 밖으로 너무 멀리 나가면 리스트에서 제거해서
# 화면 밖 탄환이 계속 쌓이며 게임이 느려지는 일을 막습니다.
def update_player_bullets(game, dt):
    play_area = layout.get_combat_area(game)
    for bullet in game.bullets[:]:
        bullet["x"] += bullet["vx"] * dt
        bullet["y"] += bullet["vy"] * dt
        if (
            bullet["y"] < play_area.top - 60
            or bullet["x"] < play_area.left - 60
            or bullet["x"] > play_area.right + 60
        ):
            game.bullets.remove(bullet)


# 적이나 보스가 쏘는 탄환 1개를 생성합니다.
# word는 탄환 안에 표시할 글자이고, split은 분열탄으로 몇 번 더 갈라질 수 있는지입니다.
def make_enemy_projectile(game, x, y, vx, vy, radius, damage, word, split, color):
    game.enemy_projectiles.append(
        {
            "x": float(x),
            "y": float(y),
            "vx": float(vx),
            "vy": float(vy),
            "radius": radius,
            "damage": float(damage),
            "word": word,
            "split": split,
            "age": 0.0,
            "splitDone": False,
            "color": color,
        }
    )


# 보스 위치를 기준으로 보스 탄환을 생성합니다.
# aimed=True이면 플레이어 위치를 향해 날아가는 유도탄이 됩니다.
# aimed=False이면 angle_offset 값을 가로 속도로 사용해서 좌우로 퍼지는 탄막을 만듭니다.
def make_boss_projectile(game, x_offset, aimed=False, angle_offset=0):
    if game.boss is None or not game.player:
        return

    stage = game.current_stage()
    rect = game.boss["rect"]
    start_x = rect.centerx + x_offset
    start_y = rect.bottom - 8
    speed = stage.get("boss_projectile_speed", 210 + game.stage_index * 28)

    if aimed:
        dx = game.player["rect"].centerx - start_x
        dy = game.player["rect"].centery - start_y
        length = max(1, math.sqrt(dx * dx + dy * dy))
        vx = dx / length * speed
        vy = dy / length * speed
    else:
        vx = angle_offset
        vy = speed

    make_enemy_projectile(
        game,
        start_x,
        start_y,
        vx,
        vy,
        18 + game.stage_index * 2,
        12 + game.stage_index * 3,
        random.choice(stage["boss_words"]),
        1 if stage["pattern"] in ("fan", "storm") else 0,
        stage["projectile_color"],
    )


# 적 탄환들을 한 프레임만큼 이동시킵니다.
# 분열 가능한 탄환은 일정 시간이 지나면 split_projectile()로 새 탄환을 만들고,
# 화면 밖으로 나간 탄환은 제거합니다.
def update_enemy_projectiles(game, dt):
    play_area = layout.get_play_area(game)
    for projectile in game.enemy_projectiles[:]:
        projectile["age"] += dt
        projectile["x"] += projectile["vx"] * dt
        projectile["y"] += projectile["vy"] * dt

        if projectile["split"] > 0 and not projectile["splitDone"] and projectile["age"] > 0.75:
            projectile["splitDone"] = True
            split_projectile(game, projectile)

        if (
            projectile["x"] < play_area.left - 80
            or projectile["x"] > play_area.right + 80
            or projectile["y"] < play_area.top - 80
            or projectile["y"] > play_area.bottom + 80
        ):
            game.enemy_projectiles.remove(projectile)


# 분열탄을 실제로 3갈래 탄환으로 나눕니다.
# 원래 탄환의 위치와 일부 속도를 이어받아서 자연스럽게 퍼지도록 합니다.
def split_projectile(game, projectile):
    for vx in (-120, 0, 120):
        make_enemy_projectile(
            game,
            projectile["x"],
            projectile["y"],
            projectile["vx"] * 0.45 + vx,
            max(170, projectile["vy"] * 0.9),
            max(12, int(projectile["radius"] * 0.62)),
            projectile["damage"] * 0.58,
            projectile["word"],
            projectile["split"] - 1,
            projectile["color"],
        )


# 원형 탄환도 pygame 충돌 판정은 사각형 Rect가 편합니다.
# 그래서 원의 중심과 반지름을 기준으로 충돌용 사각형을 만들어 돌려줍니다.
def get_circle_rect(x, y, radius):
    rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    rect.center = (int(x), int(y))
    return rect
