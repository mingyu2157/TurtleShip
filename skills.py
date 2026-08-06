# skills.py
# 역할:
#   학익진, 몸빵, 치유, 생즉사 사즉생 같은 전술/스킬을 관리합니다.
#   저장형 지원선 시스템은 제거했고, 이제 학익진/몸빵/치유는 증강으로 해금되는 전술입니다.
#
# 초보자 포인트:
#   스킬은 보통 세 부분으로 나뉩니다.
#   1. 어떤 키가 눌렸는지 확인합니다.
#   2. 사용할 수 있는 상태인지 검사합니다.
#   3. 사용할 수 있다면 타이머를 켜고, update_skills()가 매 프레임 효과를 유지합니다.
#
# 공부 순서:
#   is_*_key() 함수로 입력 키를 보고,
#   try_use_*() 함수로 발동 조건을 보고,
#   update_skills()와 update_hakikjin_ships()로 지속 효과를 보면 됩니다.
import math

import pygame

import assets
import layout
import projectiles
import results


# 필살기 기능은 아직 본격 도입 전이라 기본값은 꺼둡니다.
ULTIMATE_ENABLED = False
ULTIMATE_MAX = 100
ULTIMATE_SCANCODES = {8, 224, 228}
ULTIMATE_KEYS = {pygame.K_e, pygame.K_LCTRL, pygame.K_RCTRL}

# 4단계 명량해전 생존 패시브 설정입니다.
LAST_STAND_STAGE_INDEX = 3
# 필생즉사(damage): 체력 20% 이하에서 발동, 공격력 250%, 받는 피해 50%, 지속 6초, 쿨타임 60초
LAST_STAND_TRIGGER_RATIO = 0.20
LAST_STAND_DAMAGE_SECONDS = 6.0
LAST_STAND_DAMAGE_MULTIPLIER = 2.5
LAST_STAND_DAMAGE_REDUCTION = 0.5
LAST_STAND_DAMAGE_COOLDOWN = 20.0
# 필사즉생(revive): 사망 시 1회 부활, 최대 체력 35% 회복, 3초 무적, 공격력 -20%, 쿨타임 180초
LAST_STAND_REVIVE_RATIO = 0.35
LAST_STAND_INVINCIBLE_SECONDS = 3.0
LAST_STAND_REVIVE_COOLDOWN = 60.0
LAST_STAND_REVIVE_PENALTY = 0.20
LAST_STAND_REVIVE_PENALTY_SECONDS = 60.0
# 발동 직후 순간 피격 방지를 위한 짧은 무적 시간입니다 (필생즉사 전용).
LAST_STAND_DAMAGE_TRIGGER_INVINCIBLE = 1.5

# 명량해전 직전 스토리 뒤에 플레이어가 고를 수 있는 생즉사 사즉생 선택지입니다.
# image_key는 선택 화면에서 카드 이미지로 쓸 파일 이름입니다 (live.png / die.png).
LAST_STAND_CHOICES = [
    {
        "id": "revive",
        "image_key": "live",
        "title": "죽고자 하면 살 것이다",
        "description": "사망 시 부활. 체력 35% 회복, 3초 무적, 공격력 -20%, 쿨타임 180초.",
    },
    {
        "id": "damage",
        "image_key": "die",
        "title": "살고자 하면 죽는다",
        "description": "체력 20% 이하에서 발동. 공격력 250%, 피해 50%, 6초 지속, 쿨타임 60초.",
    },
]

# 학익진은 Q/ㅂ 키로 발동합니다.
HAKIKJIN_SCANCODES = {20}
HAKIKJIN_KEYS = {pygame.K_q}
HAKIKJIN_DURATION = 5.0
HAKIKJIN_COOLDOWN = 30.0
HAKIKJIN_SHIP_COUNT = 12
HAKIKJIN_FIRE_INTERVAL = 0.22
HAKIKJIN_SHIP_SIZE = (34, 92)

# 몸빵은 Z/ㅋ 키로 발동합니다.
TANKER_SCANCODES = {29}
TANKER_KEYS = {pygame.K_z}
TANKER_DURATION = 4.0
TANKER_COOLDOWN = 20.0

# 치유는 X/ㅌ 키로 발동합니다.
HEALER_SCANCODES = {27}
HEALER_KEYS = {pygame.K_x}
HEALER_DURATION = 5.0
HEALER_COOLDOWN = 20.0
HEALER_HEAL_PER_SECOND = 18.0


# 스킬 관련 상태를 초기화합니다.
def reset_skills(game):
    # 수동 필살기 충전량입니다.
    game.ultimate_max = ULTIMATE_MAX
    game.ultimate_charge = 0
    # 무적 타이머입니다.
    game.ultimate_invincible_timer = 0
    # 생즉사 사즉생 패시브가 이번 판에 쓰였는지입니다.
    game.last_stand_used = False
    game.last_stand_damage_timer = 0.0
    game.last_stand_damage_multiplier = 1.0
    # 학익진 지속/쿨타임과 실제 진형선 목록입니다.
    game.hakikjin_timer = 0.0
    game.hakikjin_cooldown = 0.0
    game.hakikjin_ships = []
    # 몸빵 방패선 지속/쿨타임과 표시용 Rect입니다.
    game.tanker_guard_timer = 0.0
    game.tanker_guard_cooldown = 0.0
    game.tanker_guard_rect = None
    # 치유 지속/쿨타임입니다.
    game.healer_timer = 0.0
    game.healer_cooldown = 0.0


# 키보드 이벤트가 학익진 키인지 확인합니다.
def is_hakikjin_key(event):
    typed = getattr(event, "unicode", "")
    return (
        event.key in HAKIKJIN_KEYS
        or typed.lower() == "q"
        or typed == "ㅂ"
        or getattr(event, "scancode", None) in HAKIKJIN_SCANCODES
    )


# 키보드 이벤트가 몸빵 키인지 확인합니다.
def is_tanker_key(event):
    typed = getattr(event, "unicode", "")
    return (
        event.key in TANKER_KEYS
        or typed.lower() == "z"
        or typed == "ㅋ"
        or getattr(event, "scancode", None) in TANKER_SCANCODES
    )


# 키보드 이벤트가 치유 키인지 확인합니다.
def is_healer_key(event):
    typed = getattr(event, "unicode", "")
    return (
        event.key in HEALER_KEYS
        or typed.lower() == "x"
        or typed == "ㅌ"
        or getattr(event, "scancode", None) in HEALER_SCANCODES
    )


# 키보드 이벤트가 필살기 키인지 확인합니다.
def is_ultimate_key(event):
    return event.key in ULTIMATE_KEYS or getattr(event, "scancode", None) in ULTIMATE_SCANCODES


# 학익진이 현재 판 증강으로 해금되어 있는지 확인합니다.
def is_hakikjin_unlocked(game):
    # 학익진은 이제 캠페인 진행도 저장이 아니라 "학익진 전술" 증강을 골랐을 때만 켜집니다.
    return getattr(game, "hakikjin_unlocked", False)


# Q/ㅂ를 눌렀을 때 학익진을 발동합니다.
def try_use_hakikjin(game):
    if is_stage_handicap_active(game):
        show_stage_handicap_message(game)
        return False

    if not is_hakikjin_unlocked(game):
        game.message_text = "학익진 증강 필요"
        game.message_timer = 1.2
        return False

    if getattr(game, "hakikjin_cooldown", 0) > 0:
        game.message_text = f"학익진 재정비 {game.hakikjin_cooldown:.0f}초"
        game.message_timer = 1.0
        return False

    game.hakikjin_timer = HAKIKJIN_DURATION
    game.hakikjin_cooldown = HAKIKJIN_COOLDOWN
    create_hakikjin_ships(game)
    results.record_skill_use(game, "hakikjin")
    game.message_text = "학익진 전개"
    game.message_timer = 1.4
    assets.play_sound(game, "ultimate", 0.75)
    return True


# Z/ㅋ를 눌렀을 때 몸빵 방패선을 발동합니다.
def try_use_tanker_guard(game):
    if is_stage_handicap_active(game):
        show_stage_handicap_message(game)
        return False

    if not getattr(game, "tanker_skill_unlocked", False):
        game.message_text = "몸빵 증강 필요"
        game.message_timer = 1.1
        return False

    if getattr(game, "tanker_guard_cooldown", 0) > 0:
        game.message_text = f"몸빵 재정비 {game.tanker_guard_cooldown:.0f}초"
        game.message_timer = 1.0
        return False

    game.tanker_guard_timer = TANKER_DURATION + getattr(game, "augment_guard_bonus", 0)
    game.tanker_guard_cooldown = TANKER_COOLDOWN
    update_tanker_guard_rect(game)
    results.record_skill_use(game, "tanker")
    game.message_text = "몸빵 전개"
    game.message_timer = 1.1
    assets.play_stage_sound(game, "skill", 0.65)
    return True


# X/ㅌ를 눌렀을 때 치유를 발동합니다.
def try_use_healer(game):
    if is_stage_handicap_active(game):
        show_stage_handicap_message(game)
        return False

    if not getattr(game, "healer_skill_unlocked", False):
        game.message_text = "치유 증강 필요"
        game.message_timer = 1.1
        return False

    if getattr(game, "healer_cooldown", 0) > 0:
        game.message_text = f"치유 재정비 {game.healer_cooldown:.0f}초"
        game.message_timer = 1.0
        return False

    game.healer_timer = HEALER_DURATION
    game.healer_cooldown = HEALER_COOLDOWN
    results.record_skill_use(game, "healer")
    game.message_text = "치유 시작"
    game.message_timer = 1.1
    assets.play_stage_sound(game, "skill", 0.65)
    return True


# 매 프레임 스킬 타이머와 지속 효과를 갱신합니다.
def update_skills(game, dt):
    game.ultimate_invincible_timer = max(0, getattr(game, "ultimate_invincible_timer", 0) - dt)
    game.stage_handicap_timer = max(0, getattr(game, "stage_handicap_timer", 0) - dt)
    # 필생즉사 버프 타이머
    game.last_stand_damage_timer = max(0, getattr(game, "last_stand_damage_timer", 0) - dt)
    if getattr(game, "last_stand_damage_timer", 0) <= 0:
        game.last_stand_damage_multiplier = 1.0
        game.last_stand_damage_active = False
    # 필생즉사/필사즉생 쿨타임
    game.last_stand_damage_cooldown = max(0, getattr(game, "last_stand_damage_cooldown", 0) - dt)
    game.last_stand_revive_cooldown = max(0, getattr(game, "last_stand_revive_cooldown", 0) - dt)
    # 필사즉생 공격력 패널티 타이머
    game.last_stand_revive_penalty_timer = max(0, getattr(game, "last_stand_revive_penalty_timer", 0) - dt)
    # 부활 플래시 타이머
    game.revive_flash_timer = max(0, getattr(game, "revive_flash_timer", 0) - dt)
    game.hakikjin_timer = max(0, getattr(game, "hakikjin_timer", 0) - dt)
    game.hakikjin_cooldown = max(0, getattr(game, "hakikjin_cooldown", 0) - dt)
    game.tanker_guard_timer = max(0, getattr(game, "tanker_guard_timer", 0) - dt)
    game.tanker_guard_cooldown = max(0, getattr(game, "tanker_guard_cooldown", 0) - dt)
    game.healer_timer = max(0, getattr(game, "healer_timer", 0) - dt)
    game.healer_cooldown = max(0, getattr(game, "healer_cooldown", 0) - dt)

    update_hakikjin_ships(game, dt)
    update_tanker_guard(game)
    update_healer_effect(game, dt)
    apply_passive_repair(game, dt)


# 랜덤 기본 능력 "상시 수리 인력"이 있으면 전투 중 계속 체력을 조금씩 회복합니다.
def apply_passive_repair(game, dt):
    if not getattr(game, "player", None):
        return
    heal_per_second = getattr(game, "augment_passive_heal_per_second", 0.0)
    if heal_per_second <= 0:
        return
    max_hp = game.player.get("maxHp", 0)
    game.player["hp"] = min(max_hp, game.player.get("hp", max_hp) + heal_per_second * dt)


# 학익진 진형선 12척을 현재 전투 영역에 배치합니다.
def create_hakikjin_ships(game):
    combat_area = layout.get_combat_area(game)
    ships = []
    for index in range(HAKIKJIN_SHIP_COUNT):
        x, y = get_hakikjin_position(combat_area, index, HAKIKJIN_SHIP_COUNT)
        rect = pygame.Rect(0, 0, *HAKIKJIN_SHIP_SIZE)
        rect.center = (int(x), int(y))
        ships.append({"rect": rect, "cooldown": 0.0})
    game.hakikjin_ships = ships


# 둥근 학익진 위치를 계산합니다.
def get_hakikjin_position(area, index, count):
    ratio = index / max(1, count - 1)
    angle = math.radians(165 + (15 - 165) * ratio)
    radius_x = area.width * 0.46
    radius_y = area.height * 0.42
    center_x = area.centerx
    center_y = area.top + area.height * 0.34
    x = center_x + math.cos(angle) * radius_x
    y = center_y + math.sin(angle) * radius_y
    return x, y


# 학익진 진형선들이 자동으로 사격하게 합니다.
def update_hakikjin_ships(game, dt):
    if getattr(game, "hakikjin_timer", 0) <= 0:
        game.hakikjin_ships = []
        return

    interval_bonus = getattr(game, "augment_hakikjin_bonus", 0) * 0.035
    fire_interval = max(0.18, HAKIKJIN_FIRE_INTERVAL - interval_bonus)
    for ship in getattr(game, "hakikjin_ships", []):
        ship["cooldown"] = max(0, ship.get("cooldown", 0) - dt)
        if ship["cooldown"] <= 0:
            fire_hakikjin_bullet(game, ship)
            ship["cooldown"] = fire_interval


# 학익진 배 한 척이 가장 가까운 적이나 보스를 향해 탄환을 쏩니다.
def fire_hakikjin_bullet(game, ship):
    target = get_skill_fire_target(game, ship["rect"])
    if target is None:
        return

    target_x, target_y = target
    dx = target_x - ship["rect"].centerx
    dy = target_y - ship["rect"].centery
    length = max(1, math.sqrt(dx * dx + dy * dy))
    stage = game.current_stage()
    damage = 10 * getattr(game, "augment_allied_attack_multiplier", 1.0)
    projectiles.make_player_bullet(
        game,
        ship["rect"].centerx,
        ship["rect"].centery,
        dx / length * 820,
        dy / length * 820,
        max(1, damage),
        5,
        stage["bullet_color"],
        image_padding=4,
    )


# 스킬 사격이 노릴 목표를 정합니다.
def get_skill_fire_target(game, source_rect):
    if getattr(game, "boss", None) is not None:
        return game.boss["rect"].center

    if getattr(game, "enemies", []):
        nearest = min(
            game.enemies,
            key=lambda enemy: (
                (enemy["rect"].centerx - source_rect.centerx) ** 2
                + (enemy["rect"].centery - source_rect.centery) ** 2
            ),
        )
        return nearest["rect"].center

    return None


# 몸빵 방패선 위치를 플레이어 앞에 맞춥니다.
def update_tanker_guard(game):
    if getattr(game, "tanker_guard_timer", 0) <= 0:
        game.tanker_guard_rect = None
        return
    update_tanker_guard_rect(game)


# 몸빵 방패선 Rect를 실제로 계산합니다.
def update_tanker_guard_rect(game):
    if not getattr(game, "player", None):
        return
    rect = pygame.Rect(0, 0, 128, 52)
    rect.centerx = game.player["rect"].centerx
    rect.bottom = game.player["rect"].top - 12
    rect.clamp_ip(layout.get_combat_area(game).inflate(-8, -8))
    game.tanker_guard_rect = rect


# 치유가 켜져 있으면 플레이어 체력을 천천히 회복합니다.
def update_healer_effect(game, dt):
    if getattr(game, "healer_timer", 0) <= 0 or not getattr(game, "player", None):
        return
    heal = HEALER_HEAL_PER_SECOND + getattr(game, "augment_heal_bonus", 0)
    max_hp = game.player.get("maxHp", 0)
    game.player["hp"] = min(max_hp, game.player.get("hp", max_hp) + heal * dt)


# 4단계 생존 패시브를 발동합니다.
# damage(필생즉사): 체력 20% 이하 시 쿨타임 기반으로 반복 발동
# revive(필사즉생): 사망 시 쿨타임 기반으로 부활
def try_use_last_stand(game):
    if getattr(game, "stage_index", 0) < LAST_STAND_STAGE_INDEX:
        return False
    max_hp = game.player.get("maxHp", 0)
    if max_hp <= 0:
        return False

    choice = getattr(game, "last_stand_choice", "damage")
    # 구버전(카드-효과 매핑이 뒤바뀐 상태)에서 저장된 선택값을 1회 자동 보정합니다.
    if getattr(game, "last_stand_choice_version", 0) < 2:
        if choice == "damage":
            choice = "revive"
        elif choice == "revive":
            choice = "damage"
        game.last_stand_choice = choice
        game.last_stand_choice_version = 2

    if choice == "revive":
        # 필사즉생: 체력이 0이 되었을 때만 부활 판정합니다.
        if game.player.get("hp", 0) > 0:
            return False
        if getattr(game, "last_stand_revive_cooldown", 0) > 0:
            return False
        # 쿨타임 내에 있으면 부활 불가
        game.player["hp"] = max(1, int(max_hp * LAST_STAND_REVIVE_RATIO))
        game.ultimate_invincible_timer = max(getattr(game, "ultimate_invincible_timer", 0), LAST_STAND_INVINCIBLE_SECONDS)
        game.last_stand_revive_cooldown = LAST_STAND_REVIVE_COOLDOWN
        game.last_stand_revive_penalty_timer = LAST_STAND_REVIVE_PENALTY_SECONDS
        results.record_skill_use(game, "last_stand")
        game.message_text = "필사즉생: 부활! (공격력 -20%, 3초 무적)"
        game.message_timer = 2.5
        assets.play_sound(game, "ultimate", 0.75)
        return True

    # 필생즉사: 체력 20% 이하에서 쿨타임이 없으면 발동합니다.
    if game.player.get("hp", 1) <= 0:
        return False
    if game.player.get("hp", max_hp) > max_hp * LAST_STAND_TRIGGER_RATIO:
        return False
    if getattr(game, "last_stand_damage_cooldown", 0) > 0:
        return False
    game.ultimate_invincible_timer = max(getattr(game, "ultimate_invincible_timer", 0), LAST_STAND_DAMAGE_TRIGGER_INVINCIBLE)
    game.last_stand_damage_timer = LAST_STAND_DAMAGE_SECONDS
    game.last_stand_damage_multiplier = LAST_STAND_DAMAGE_MULTIPLIER
    game.last_stand_damage_active = True
    game.last_stand_damage_cooldown = LAST_STAND_DAMAGE_COOLDOWN
    results.record_skill_use(game, "last_stand")
    game.message_text = "필생즉사: 공격력 250%, 피해 50% (6초)"
    game.message_timer = 2.5
    assets.play_sound(game, "ultimate", 0.75)
    return True


# 명량해전 초반 고립 구간처럼 전술 스킬을 잠시 막는 상태인지 확인합니다.
def is_stage_handicap_active(game):
    return getattr(game, "stage_handicap_timer", 0) > 0


# 전술 스킬이 막힌 상태에서 키를 눌렀을 때 안내합니다.
def show_stage_handicap_message(game):
    game.message_text = f"고립 전투 {game.stage_handicap_timer:.0f}초"
    game.message_timer = 1.0


# 적을 파괴했을 때 필살기 충전량을 올립니다.
def add_ultimate_charge(game, amount):
    if not ULTIMATE_ENABLED:
        return
    game.ultimate_charge = min(getattr(game, "ultimate_max", ULTIMATE_MAX), getattr(game, "ultimate_charge", 0) + amount)


# 필살기 키를 눌렀을 때 폭탄형 필살기를 시도합니다.
def try_use_ultimate(game):
    if not ULTIMATE_ENABLED or getattr(game, "ultimate_charge", 0) < getattr(game, "ultimate_max", ULTIMATE_MAX):
        return False
    trigger_bomb(game)
    results.record_skill_use(game, "ultimate")
    game.ultimate_charge = 0
    return True


# 폭탄형 필살기 효과입니다.
def trigger_bomb(game):
    game.enemies = []
    game.enemy_projectiles = []
    game.ultimate_invincible_timer = 2.0
    if game.boss is not None:
        game.boss["shield"] = 0
        game.boss["hp"] = max(0, game.boss["hp"] - 600)
    assets.play_sound(game, "ultimate", 0.85)
