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
#
# 공부 순서:
#   make_player_bullet()/make_enemy_projectile()는 탄환 데이터를 만들고,
#   update_player_bullets()/update_enemy_projectiles()는 그 데이터를 매 프레임 이동시킵니다.
import pygame

import layout


# 플레이어 또는 전술 탄환 1개를 생성합니다.
# 여기서는 화면에 바로 그리지 않고, game.bullets 리스트에 탄환 정보를 저장합니다.
# render.py가 나중에 이 리스트를 읽어서 실제 화면에 탄환을 그립니다.
# image_padding은 이미지 탄환을 그릴 때 원형 충돌 박스보다 얼마나 크게 보일지 정합니다.
def make_player_bullet(game, x, y, vx, vy, damage, radius, color, image_padding=10):
    # 탄환도 클래스 대신 딕셔너리로 저장합니다.
    # x/y는 위치, vx/vy는 속도, damage는 맞았을 때 줄 피해량입니다.
    game.bullets.append(
        {
            "x": float(x),
            "y": float(y),
            "vx": float(vx),
            "vy": float(vy),
            "damage": float(damage),
            "radius": radius,
            "color": color,
            "image_padding": image_padding,
        }
    )


# 플레이어 탄환들을 한 프레임만큼 이동시킵니다.
# 탄환이 전투 영역 밖으로 너무 멀리 나가면 리스트에서 제거해서
# 화면 밖 탄환이 계속 쌓이며 게임이 느려지는 일을 막습니다.
# 전술 탄환은 플레이 영역 가장자리에서 중앙으로 날아올 수 있으므로 좌우 여유를 넓게 둡니다.
def update_player_bullets(game, dt):
    # 플레이어와 전술 탄환은 중앙 영역 밖에서 날아올 수 있으므로 제거 영역을 조금 넓게 잡습니다.
    remove_area = layout.get_play_area(game).inflate(320, 140)
    for bullet in game.bullets[:]:
        # "현재 위치 = 이전 위치 + 속도 * 시간"은 거의 모든 2D 게임 이동의 기본 공식입니다.
        bullet["x"] += bullet["vx"] * dt
        bullet["y"] += bullet["vy"] * dt
        if not remove_area.colliderect(get_circle_rect(bullet["x"], bullet["y"], bullet["radius"])):
            game.bullets.remove(bullet)


# 적이나 보스가 쏘는 탄환 1개를 생성합니다.
# split은 분열탄으로 몇 번 더 갈라질 수 있는지입니다.
def make_enemy_projectile(game, x, y, vx, vy, radius, damage, split, color):
    # enemy_projectiles에는 일반 적 탄환과 보스 탄환을 같이 저장합니다.
    # split은 나중에 분열탄으로 갈라질 횟수입니다.
    game.enemy_projectiles.append(
        {
            "x": float(x),
            "y": float(y),
            "vx": float(vx),
            "vy": float(vy),
            "radius": radius,
            "damage": float(damage),
            "split": split,
            "age": 0.0,
            "splitDone": False,
            "color": color,
        }
    )


# 보스 위치를 기준으로 보스 탄환을 생성합니다.
# 예전 aimed=True 조준탄도 이제 플레이어를 직접 겨냥하지 않고 아래로 곧게 내려갑니다.
# aimed=False이면 angle_offset 값을 가로 속도로 사용해서 좌우로 퍼지는 탄막을 만듭니다.
def make_boss_projectile(game, x_offset, aimed=False, angle_offset=0):
    if game.boss is None or not game.player:
        return

    # 보스 탄환은 보스 rect의 아래쪽에서 시작합니다.
    stage = game.current_stage()
    rect = game.boss["rect"]
    start_x = rect.centerx + x_offset
    start_y = rect.bottom - 8
    speed = stage.get("boss_projectile_speed", 210 + game.stage_index * 28)

    if aimed:
        # aimed=True도 현재 기획에서는 플레이어 추적이 아니라 아래로 직진합니다.
        vx = 0
        vy = speed
    else:
        vx = angle_offset
        vy = speed

    make_enemy_projectile(
        game,
        start_x,
        start_y,
        vx,
        vy,
        stage.get("boss_projectile_radius", 11 + game.stage_index),
        12 + game.stage_index * 3,
        1 if stage["pattern"] in ("fan", "storm") else 0,
        stage["projectile_color"],
    )


# 적 탄환들을 한 프레임만큼 이동시킵니다.
# 분열 가능한 탄환은 일정 시간이 지나면 split_projectile()로 새 탄환을 만들고,
# 중앙 플레이 영역 밖으로 나간 탄환은 제거합니다.
# 오른쪽 HUD 구역은 전투 공간이 아니므로 적 탄환이 그쪽까지 따라가지 않게 막습니다.
def update_enemy_projectiles(game, dt):
    # 적 탄환은 플레이 영역 밖으로 나가면 제거합니다.
    # 오른쪽 HUD/왼쪽 예비 공간까지 따라가지 않게 하기 위해 여유를 작게 둡니다.
    remove_area = layout.get_play_area(game).inflate(16, 16)
    for projectile in game.enemy_projectiles[:]:
        projectile["age"] += dt
        projectile["x"] += projectile["vx"] * dt
        projectile["y"] += projectile["vy"] * dt

        if projectile["split"] > 0 and not projectile["splitDone"] and projectile["age"] > 0.75:
            # splitDone을 True로 해야 한 탄환이 매 프레임 계속 분열하지 않습니다.
            projectile["splitDone"] = True
            split_projectile(game, projectile)

        if not remove_area.colliderect(get_circle_rect(projectile["x"], projectile["y"], projectile["radius"])):
            game.enemy_projectiles.remove(projectile)


# 분열탄을 실제로 3갈래 탄환으로 나눕니다.
# 원래 탄환의 위치와 일부 속도를 이어받아서 자연스럽게 퍼지도록 합니다.
def split_projectile(game, projectile):
    # 기존 탄환 중심에서 왼쪽/중앙/오른쪽 3갈래로 새 탄환을 만듭니다.
    for vx in (-120, 0, 120):
        make_enemy_projectile(
            game,
            projectile["x"],
            projectile["y"],
            projectile["vx"] * 0.45 + vx,
            max(170, projectile["vy"] * 0.9),
            max(7, int(projectile["radius"] * 0.62)),
            projectile["damage"] * 0.58,
            projectile["split"] - 1,
            projectile["color"],
        )


# 원형 탄환도 pygame 충돌 판정은 사각형 Rect가 편합니다.
# 그래서 원의 중심과 반지름을 기준으로 충돌용 사각형을 만들어 돌려줍니다.
def get_circle_rect(x, y, radius):
    # pygame에는 원끼리의 충돌보다 Rect 충돌이 훨씬 간단합니다.
    # 그래서 원을 감싸는 정사각형을 만들어 충돌 판정에 사용합니다.
    rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    rect.center = (int(x), int(y))
    return rect
