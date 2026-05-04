# waves.py
# 역할:
#   바다 파도의 현재 방향과 속도를 계산하고, 플레이어가 그 파도에 밀리게 합니다.
#   render.py는 이 값을 보고 파도 선을 움직이고,
#   actors.py는 같은 값을 보고 플레이어를 조금씩 이동시킵니다.
#
# 초보자 포인트:
#   wave_x, wave_y는 "1초 동안 파도가 미는 픽셀 속도"입니다.
#   예를 들어 wave_y가 -40이면 1초에 위쪽으로 40픽셀 정도 밀린다는 뜻입니다.
#   방향은 랜덤 시간마다 새 목표 방향을 고르고, 천천히 그쪽으로 회전합니다.
#
# 공부 순서:
#   get_wave_state()는 현재 파도 정보를 읽는 함수,
#   update_wave_target()은 파도 목표 방향을 바꾸는 함수,
#   apply_to_actor()는 실제 배를 파도 방향으로 밀어주는 함수입니다.
import math
import random

import pygame


# 기본 파도 방향입니다.
# -pi/2는 pygame 좌표계에서 위쪽을 뜻하므로, 시작 파도는 아래에서 위로 흐릅니다.
BASE_WAVE_ANGLE = -math.pi / 2
DEFAULT_WAVE_SPEED = 42
WAVE_CHANGE_INTERVAL_RANGE = (18.0, 30.0)
WAVE_SPEED_FACTOR_RANGE = (0.55, 0.95)
WAVE_TURN_SMOOTHING = 0.18
WAVE_SPEED_SMOOTHING = 0.25
WAVE_WITH_SPEED_BONUS = 0.16
WAVE_AGAINST_SPEED_PENALTY = 0.24


# 현재 파도 방향과 속도를 계산합니다.
# 랜덤 시간이 지나면 새 랜덤 방향과 속도를 고르고, 현재 값이 부드럽게 따라갑니다.
def get_wave_state(game):
    # pygame.time.get_ticks()는 게임 시작 후 흐른 시간을 밀리초로 줍니다.
    # /1000을 해서 초 단위로 바꿉니다.
    time = pygame.time.get_ticks() / 1000
    stage = game.current_stage() if getattr(game, "game_state", None) == "play" else {}
    base_speed = stage.get("wave_speed", DEFAULT_WAVE_SPEED)

    update_wave_target(game, time, base_speed)

    angle = getattr(game, "wave_angle", BASE_WAVE_ANGLE)
    speed = getattr(game, "wave_speed_current", base_speed * 0.75)
    unit_x = math.cos(angle)
    unit_y = math.sin(angle)

    return {
        "time": time,
        "angle": angle,
        "speed": speed,
        # unit_x/unit_y는 화면 파도 애니메이션과 실제 배 밀림이 함께 쓰는 방향입니다.
        # 그래서 render.py의 파도선이 움직이는 방향과 apply_to_actor()의 이동 방향이 일치합니다.
        "unit_x": unit_x,
        "unit_y": unit_y,
        "x": unit_x * speed,
        "y": unit_y * speed,
        "perp_x": -unit_y,
        "perp_y": unit_x,
    }


# 파도 방향/속도 목표를 랜덤 시간마다 갱신하고, 현재 값을 목표 쪽으로 부드럽게 이동시킵니다.
def update_wave_target(game, time, base_speed):
    last_time = getattr(game, "wave_last_time", None)
    if last_time is None:
        # 처음 호출될 때는 이전 시간이 없으므로 현재 값을 초기화하고 바로 return 합니다.
        game.wave_last_time = time
        game.wave_angle = BASE_WAVE_ANGLE
        game.wave_target_angle = BASE_WAVE_ANGLE
        game.wave_speed_current = base_speed * 0.75
        game.wave_speed_target = base_speed * random.uniform(*WAVE_SPEED_FACTOR_RANGE)
        game.wave_change_timer = random.uniform(*WAVE_CHANGE_INTERVAL_RANGE)
        return

    dt = max(0.0, min(0.12, time - last_time))
    game.wave_last_time = time
    game.wave_change_timer = max(0.0, getattr(game, "wave_change_timer", 0.0) - dt)

    if game.wave_change_timer <= 0:
        # 랜덤 시간이 지나면 새 방향과 새 속도 목표를 뽑습니다.
        game.wave_target_angle = random.uniform(-math.pi, math.pi)
        game.wave_speed_target = base_speed * random.uniform(*WAVE_SPEED_FACTOR_RANGE)
        game.wave_change_timer = random.uniform(*WAVE_CHANGE_INTERVAL_RANGE)

    angle = getattr(game, "wave_angle", BASE_WAVE_ANGLE)
    target_angle = getattr(game, "wave_target_angle", BASE_WAVE_ANGLE)
    diff = normalize_angle(target_angle - angle)
    # 현재 각도를 목표 각도로 한 번에 바꾸지 않고 조금씩 따라가게 만들어 자연스럽게 보입니다.
    # 값이 낮을수록 파도 방향이 천천히 바뀌어 플레이어가 덜 어지럽게 느낍니다.
    game.wave_angle = angle + diff * min(1.0, dt * WAVE_TURN_SMOOTHING)

    current_speed = getattr(game, "wave_speed_current", base_speed * 0.75)
    target_speed = getattr(game, "wave_speed_target", base_speed * 0.75)
    game.wave_speed_current = current_speed + (target_speed - current_speed) * min(1.0, dt * WAVE_SPEED_SMOOTHING)


# 각도 차이를 -pi~pi 범위로 정리해서 가장 짧은 방향으로 회전하게 합니다.
def normalize_angle(angle):
    while angle > math.pi:
        angle -= math.tau
    while angle < -math.pi:
        angle += math.tau
    return angle


# 플레이어가 움직이는 방향과 파도 방향이 얼마나 같은지 보고 이동속도 배율을 계산합니다.
# 파도와 같은 방향이면 조금 빨라지고, 반대 방향이면 더 힘들게 느껴지도록 느려집니다.
def get_movement_speed_multiplier(game, move_x, move_y):
    if move_x == 0 and move_y == 0:
        return 1.0

    # 입력 방향을 길이 1짜리 벡터로 바꿉니다.
    # 대각선 입력도 같은 기준으로 비교하기 위해 정규화가 필요합니다.
    length = math.sqrt(move_x * move_x + move_y * move_y)
    input_x = move_x / length
    input_y = move_y / length

    # get_wave_state()의 unit_x/unit_y는 render.py도 쓰는 실제 파도 흐름 방향입니다.
    # 그래서 이 값으로 비교하면 화면의 파도 방향과 조작 보정 방향이 같은 기준을 씁니다.
    state = get_wave_state(game)
    alignment = input_x * state["unit_x"] + input_y * state["unit_y"]

    if alignment >= 0:
        # alignment가 1이면 완전히 파도 방향, 0이면 수직 방향입니다.
        return 1.0 + WAVE_WITH_SPEED_BONUS * alignment

    # alignment가 -1이면 완전히 파도 반대 방향입니다.
    return 1.0 - WAVE_AGAINST_SPEED_PENALTY * abs(alignment)


# actor 딕셔너리에 들어 있는 rect를 파도 방향으로 조금 이동시킵니다.
# 현재 게임에서는 플레이어에게만 사용합니다.
# 소수점 이동량은 _wave_carry_x/y에 모아두었다가 1픽셀이 되면 실제 Rect에 적용합니다.
def apply_to_actor(actor, game, dt, influence=1.0):
    if not actor or "rect" not in actor:
        return

    state = get_wave_state(game)
    # carry 값은 소수점 이동량을 모아두는 저금통입니다.
    # Rect는 정수 좌표만 가지므로 0.4픽셀 같은 이동을 잃어버리지 않게 합니다.
    actor["_wave_carry_x"] = actor.get("_wave_carry_x", 0.0) + state["x"] * dt * influence
    actor["_wave_carry_y"] = actor.get("_wave_carry_y", 0.0) + state["y"] * dt * influence

    move_x = int(actor["_wave_carry_x"])
    move_y = int(actor["_wave_carry_y"])
    actor["_wave_carry_x"] -= move_x
    actor["_wave_carry_y"] -= move_y

    actor["rect"].x += move_x
    actor["rect"].y += move_y
