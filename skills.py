# skills.py
# 역할:
#   필살기 입력, 필살기 충전량, 필살기 효과를 관리합니다.
#   지금 준비된 필살기는 폭탄처럼 적과 적 탄환을 지우고 잠깐 무적이 되는 방식입니다.
#
# 현재 상태:
#   ULTIMATE_ENABLED 값이 False라서 실제 게임에서는 아직 필살기가 발동하지 않습니다.
#   나중에 True로 바꾸면 E 키, 왼쪽 Ctrl, 오른쪽 Ctrl로 발동할 수 있습니다.
import pygame

import assets


ULTIMATE_ENABLED = False
ULTIMATE_MAX = 100
ULTIMATE_SCANCODES = {8, 224, 228}
ULTIMATE_KEYS = {pygame.K_e, pygame.K_LCTRL, pygame.K_RCTRL}


# 게임을 새로 시작할 때 필살기 관련 값을 초기화합니다.
# ultimate_charge는 현재 충전량, ultimate_max는 발동에 필요한 최대 충전량입니다.
def reset_skills(game):
    game.ultimate_max = ULTIMATE_MAX
    game.ultimate_charge = 0
    game.ultimate_invincible_timer = 0


# 키보드 이벤트가 필살기 키인지 확인합니다.
# event.key는 현재 입력 언어의 영향을 받을 수 있고,
# scancode는 물리 키 위치를 보기 때문에 한글 입력 상태에서도 인식하기 좋습니다.
def is_ultimate_key(event):
    return event.key in ULTIMATE_KEYS or getattr(event, "scancode", None) in ULTIMATE_SCANCODES


# 필살기 관련 시간 값을 매 프레임 줄입니다.
# 지금은 무적 시간이 지나가도록 ultimate_invincible_timer만 관리합니다.
def update_skills(game, dt):
    game.ultimate_invincible_timer = max(0, getattr(game, "ultimate_invincible_timer", 0) - dt)


# 적을 파괴했을 때 필살기 충전량을 올리는 함수입니다.
# ULTIMATE_ENABLED가 False면 충전도 하지 않아서 현재 플레이에는 영향이 없습니다.
def add_ultimate_charge(game, amount):
    if not ULTIMATE_ENABLED:
        return

    game.ultimate_charge = min(getattr(game, "ultimate_max", ULTIMATE_MAX), getattr(game, "ultimate_charge", 0) + amount)


# 필살기 키를 눌렀을 때 실제로 발동 가능한지 확인합니다.
# 충전량이 가득 차 있으면 trigger_bomb()을 실행하고 충전량을 0으로 되돌립니다.
def try_use_ultimate(game):
    if not ULTIMATE_ENABLED or getattr(game, "ultimate_charge", 0) < getattr(game, "ultimate_max", ULTIMATE_MAX):
        return False

    trigger_bomb(game)
    game.ultimate_charge = 0
    return True


# 폭탄형 필살기 효과입니다.
# 일반 적과 적 탄환을 지우고, 보스가 있다면 보호막을 없앤 뒤 체력을 일부 깎습니다.
def trigger_bomb(game):
    game.enemies = []
    game.enemy_projectiles = []
    game.ultimate_invincible_timer = 2.0

    if game.boss is not None:
        game.boss["shield"] = 0
        game.boss["hp"] = max(0, game.boss["hp"] - 600)

    assets.play_sound(game, "ultimate", 0.85)
