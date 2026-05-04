# augments.py
# 역할:
#   현재 플레이 중인 판에서만 사용하는 경험치, 레벨업, 증강 선택을 관리합니다.
#   캠페인은 스테이지를 새로 시작할 때 증강을 초기화하고, 점수 경쟁은 새 판을 시작할 때 초기화합니다.
#
# 초보자 포인트:
#   "증강"은 플레이어가 레벨업할 때 고르는 현재 판 전용 버프입니다.
#   저장 파일에 남기지 않으므로 게임을 다시 시작하거나 새 판을 시작하면 초기화됩니다.
#   캠페인 1단계에서는 학익진 증강이 나오지 않고, 점수 경쟁에서는 단계 제한 없이 나올 수 있습니다.
#
# 공부 순서:
#   1. AUGMENTS에서 증강 종류를 봅니다.
#   2. add_experience()에서 경험치를 얻고 레벨업하는 흐름을 봅니다.
#   3. choose_augment()에서 선택한 증강이 실제 능력치로 바뀌는 과정을 봅니다.
import random


# 현재 판에서 1레벨에서 2레벨로 가기 위해 필요한 기본 경험치입니다.
BASE_XP_TO_LEVEL = 45

# 레벨이 오를수록 경험치 요구량이 얼마나 가파르게 늘어날지 정합니다.
XP_GROWTH = 1.32

# 한 번 레벨업할 때 화면에 보여줄 선택지 개수입니다.
CHOICE_COUNT = 3

# PDF 설정의 화포 진화 단계입니다.
# 0단계 황자총통은 기본 무기이고, 증강을 고를수록 현자 -> 지자 -> 천자총통으로 올라갑니다.
WEAPON_TIER_NAMES = {
    0: "황자총통",
    1: "현자총통",
    2: "지자총통",
    3: "천자총통",
}


# 1단계 첫 출전 전에 고르는 기본 능력입니다.
# 일반 레벨업 증강과 같은 apply_augment_effect()를 재사용해서, 초보자가 흐름을 따라가기 쉽습니다.
BASIC_ABILITY_CHOICES = [
    {
        "id": "basic_weapon",
        "image_key": "basic_weapon",
        "title": "무기 진화",
        "description": "황자총통에서 현자총통으로 시작합니다. 일자 포격 피해가 늘어납니다.",
        "augment_id": "weapon_hyeonja",
    },
    {
        "id": "basic_random_skill",
        "image_key": "basic_random",
        "title": "랜덤 스킬",
        "description": "장전 훈련, 노군 훈련, 치유 전술 중 하나를 얻습니다.",
        "augment_id": None,
    },
    {
        "id": "basic_hull",
        "image_key": "basic_hull",
        "title": "기본 체력 증가",
        "description": "선체 보강을 얻고 최대 체력이 증가합니다.",
        "augment_id": "hull_reinforce",
    },
]

# 랜덤 스킬 기본 능력에서 나올 수 있는 후보입니다.
BASIC_RANDOM_SKILLS = ("reload_training", "oar_training", "healer_skill")


# 증강 목록입니다.
# id는 코드에서 구분하는 이름이고, title/description은 화면에 보여줄 문구입니다.
# max_stack은 같은 증강을 몇 번까지 고를 수 있는지입니다.
AUGMENTS = {
    "cannon_damage": {
        "title": "장수들을 독려하여",
        "description": "대포 피해량 +5, 이동속도 +8",
        "max_stack": 6,
        "stages": (0, 1, 2, 3, 4),
    },
    "cannon_size": {
        "title": "화살을 비 퍼붓듯이",
        "description": "포탄 범위 +1",
        "max_stack": 3,
        "stages": (1, 2, 3, 4),
    },
    "reload_training": {
        "title": "총포들을 우레같이",
        "description": "발사 대기시간 감소",
        "max_stack": 5,
        "stages": (0, 1, 2, 3, 4),
    },
    "weapon_hyeonja": {
        "title": "현자총통",
        "description": "1진화: 일자 포격 피해 증가",
        "max_stack": 1,
        "stages": (0, 1, 2, 3, 4),
    },
    "weapon_jija": {
        "title": "지자총통",
        "description": "2진화: 광역 포격 3발 발사",
        "max_stack": 1,
        "stages": (1, 2, 3, 4),
        "score_any_stage": True,
        "requires": "weapon_hyeonja",
    },
    "weapon_cheonha": {
        "title": "천자총통",
        "description": "3진화: 강한 광역 포격 5발 발사",
        "max_stack": 1,
        "stages": (2, 3, 4),
        "score_any_stage": True,
        "requires": "weapon_jija",
    },
    "hull_reinforce": {
        "title": "신에게는 아직 12척",
        "description": "최대 체력 +25",
        "max_stack": 5,
        "stages": (0, 2, 3, 4),
    },
    "oar_training": {
        "title": "한산도 바다 가운데로 유인",
        "description": "이동속도 +28",
        "max_stack": 4,
        "stages": (0, 1, 2),
    },
    "tanker_skill": {
        "title": "대장선이 홀로 적진 속으로",
        "description": "Z/ㅋ 방패선을 사용 가능",
        "max_stack": 1,
        "stages": (2, 3, 4),
    },
    "healer_skill": {
        "title": "군선 수리",
        "description": "X/ㅌ 체력 회복 사용 가능",
        "max_stack": 1,
        "stages": (1, 2, 3, 4),
    },
    "hakikjin_skill": {
        "title": "학익진 전술",
        "description": "Q/ㅂ 학익진 사용 가능. 12척이 진형을 펼쳐 자동 공격합니다.",
        "max_stack": 1,
        # 캠페인에서는 2단계부터만 등장합니다. stage_index 1은 화면상 2단계입니다.
        "stages": (1, 2, 3, 4),
        # 점수 경쟁은 스테이지 제한을 보지 않고 언제든 후보가 될 수 있게 합니다.
        "score_any_stage": True,
    },
    "repair_efficiency": {
        "title": "우수영 앞바다 정비",
        "description": "치유량 증가",
        "max_stack": 4,
        "stages": (2, 3, 4),
        "requires": "healer_skill",
    },
    "guard_duration": {
        "title": "감히 곧바로 덤벼들지 못할 것",
        "description": "몸빵 지속시간 증가",
        "max_stack": 3,
        "stages": (3, 4),
        "requires": "tanker_skill",
    },
    "hakikjin_mastery": {
        "title": "그 형세가 바람같고 우레같아",
        "description": "학익진 사격 간격 감소",
        "max_stack": 3,
        "stages": (2, 3, 4),
        "score_any_stage": True,
        "requires": "hakikjin_skill",
    },
}


# 새 전투/새 점수 경쟁 판을 시작할 때 경험치와 이번 판 증강 상태를 초기화합니다.
def reset_run(game):
    # run_level은 현재 판에서만 쓰는 레벨입니다.
    game.run_level = 1
    # run_xp는 현재 레벨 안에서 쌓인 경험치입니다.
    game.run_xp = 0
    # run_xp_to_next는 다음 레벨까지 필요한 경험치입니다.
    game.run_xp_to_next = get_xp_to_next_level(1)
    # augment_stacks는 이번 판에서 증강별로 몇 번 골랐는지입니다.
    game.augment_stacks = {}
    # augment_choices는 레벨업 시 화면에 보일 3개 선택지입니다.
    game.augment_choices = []
    # augment_pending은 증강 선택 화면을 띄워야 하는지 나타냅니다.
    game.augment_pending = False
    # 선택지 화면이 열릴 때 첫 번째 카드를 기본 선택 상태로 둡니다.
    game.choice_select_index = 0
    # 아래 값들은 증강이 실제 전투 계산에 쓰는 능력치 보정입니다.
    reset_augment_effects(game)


# 첫 출전 전 기본 능력 선택지를 준비합니다.
def prepare_basic_ability_choices(game):
    # dict.copy()를 사용해 원본 BASIC_ABILITY_CHOICES를 직접 수정하지 않게 합니다.
    game.basic_ability_choices = [choice.copy() for choice in BASIC_ABILITY_CHOICES]
    # 기본 능력 선택 화면도 방향키 선택 위치를 첫 카드로 초기화합니다.
    game.choice_select_index = 0


# 첫 출전 전 기본 능력 하나를 적용합니다.
def choose_basic_ability(game, choice_index):
    choices = getattr(game, "basic_ability_choices", [])
    if not 0 <= choice_index < len(choices):
        return False

    choice = choices[choice_index]
    augment_id = choice.get("augment_id")

    if augment_id is None:
        # 랜덤 스킬은 현재 판에서 아직 최대치가 아닌 후보만 뽑습니다.
        candidates = [
            candidate
            for candidate in BASIC_RANDOM_SKILLS
            if getattr(game, "augment_stacks", {}).get(candidate, 0) < AUGMENTS[candidate]["max_stack"]
        ]
        augment_id = random.choice(candidates or list(BASIC_RANDOM_SKILLS))

    if not grant_augment(game, augment_id):
        return False

    game.basic_ability_chosen = True
    game.basic_ability_choices = []
    game.message_text = f"기본 능력: {AUGMENTS[augment_id]['title']}"
    game.message_timer = 1.8
    return True


# 캠페인 모드 또는 새 판 시작 시 증강 효과를 확실히 끕니다.
def reset_augment_effects(game):
    # 현재 화포 진화 단계입니다. 0은 기본 황자총통입니다.
    game.weapon_tier = 0
    # 대포 추가 피해량입니다.
    game.augment_bullet_damage = 0
    # 대포 추가 반지름입니다.
    game.augment_bullet_radius = 0
    # 최대 체력 추가값입니다. 플레이어를 다시 만들어도 체력 증강이 유지되게 따로 저장합니다.
    game.augment_max_hp_bonus = 0
    # 발사 대기시간을 줄이는 비율입니다.
    game.augment_reload_bonus = 0.0
    # 이동속도 추가값입니다.
    game.augment_speed_bonus = 0
    # 치유 스킬 회복량 보정입니다.
    game.augment_heal_bonus = 0
    # 몸빵 스킬 지속시간 보정입니다.
    game.augment_guard_bonus = 0
    # 학익진 자동 사격 간격 보정입니다.
    game.augment_hakikjin_bonus = 0
    # 증강으로 해금되는 몸빵/치유/학익진 스킬입니다.
    game.tanker_skill_unlocked = False
    game.healer_skill_unlocked = False
    game.hakikjin_unlocked = False


# 증강 함수만 따로 호출해도 필요한 기본 보정값이 없어서 깨지지 않게 기본값을 채웁니다.
def ensure_augment_state(game):
    defaults = {
        "weapon_tier": 0,
        "augment_bullet_damage": 0,
        "augment_bullet_radius": 0,
        "augment_max_hp_bonus": 0,
        "augment_reload_bonus": 0.0,
        "augment_speed_bonus": 0,
        "augment_heal_bonus": 0,
        "augment_guard_bonus": 0,
        "augment_hakikjin_bonus": 0,
        "tanker_skill_unlocked": False,
        "healer_skill_unlocked": False,
        "hakikjin_unlocked": False,
    }

    for name, value in defaults.items():
        if not hasattr(game, name):
            setattr(game, name, value)

    if not hasattr(game, "augment_stacks") or not isinstance(game.augment_stacks, dict):
        game.augment_stacks = {}


# 현재 레벨에서 다음 레벨까지 필요한 경험치를 계산합니다.
def get_xp_to_next_level(level):
    # 레벨이 오를수록 BASE_XP_TO_LEVEL * XP_GROWTH^(level-1) 형태로 요구량이 증가합니다.
    return int(BASE_XP_TO_LEVEL * (XP_GROWTH ** max(0, level - 1)))


# 현재 게임이 점수 경쟁 모드인지 확인합니다.
def is_score_mode(game):
    return getattr(game, "game_mode", "campaign") == "score"


# 적을 파괴했을 때 경험치를 더합니다.
def add_experience(game, amount):
    ensure_augment_state(game)
    if getattr(game, "augment_pending", False):
        # 선택지가 떠 있는 동안 추가 레벨업이 겹치지 않게 잠시 멈춥니다.
        return

    # 경험치를 누적합니다.
    game.run_xp = getattr(game, "run_xp", 0) + int(amount)

    # 충분히 모이면 레벨을 올리고 선택지를 준비합니다.
    game.run_xp_to_next = getattr(game, "run_xp_to_next", get_xp_to_next_level(getattr(game, "run_level", 1)))
    if game.run_xp >= game.run_xp_to_next:
        game.run_xp -= game.run_xp_to_next
        game.run_level = getattr(game, "run_level", 1) + 1
        game.run_xp_to_next = get_xp_to_next_level(game.run_level)
        prepare_augment_choices(game)


# 레벨업 시 보여줄 3개 선택지를 만듭니다.
def prepare_augment_choices(game):
    # 현재 가상 스테이지에 맞는 증강 후보를 가져옵니다.
    available = get_available_augments(game)
    # 후보가 3개보다 적어도 화면이 깨지지 않게 가능한 만큼만 뽑습니다.
    count = min(CHOICE_COUNT, len(available))
    # random.sample은 중복 없이 여러 개를 뽑습니다.
    game.augment_choices = random.sample(available, count) if count > 0 else []
    # 새 증강 선택지가 열릴 때 이전 선택 위치가 남지 않게 첫 카드로 맞춥니다.
    game.choice_select_index = 0
    # 선택지가 있으면 증강 선택 화면으로 전환합니다.
    game.augment_pending = bool(game.augment_choices)
    if game.augment_pending:
        game.previous_game_state = game.game_state
        game.game_state = "augment_select"


# 현재 스테이지/해금 상태에서 선택 가능한 증강 목록을 돌려줍니다.
def get_available_augments(game):
    ensure_augment_state(game)
    stage_index = getattr(game, "stage_index", 0)
    stacks = getattr(game, "augment_stacks", {})
    available = []

    for augment_id, data in AUGMENTS.items():
        # 현재 모드와 스테이지에서 나올 수 없는 증강은 제외합니다.
        if not is_augment_available_for_stage(game, data, stage_index):
            continue
        # 이미 최대 중첩까지 찍은 증강은 다시 나오지 않습니다.
        if stacks.get(augment_id, 0) >= data["max_stack"]:
            continue
        # 특정 증강을 먼저 배워야 하는 증강은 조건을 확인합니다.
        required = data.get("requires")
        if required and stacks.get(required, 0) <= 0:
            continue
        available.append(augment_id)

    return available


# 점수 경쟁과 캠페인의 증강 등장 조건을 나눠 확인합니다.
def is_augment_available_for_stage(game, data, stage_index):
    if is_score_mode(game) and data.get("score_any_stage", False):
        # 점수 경쟁에서 score_any_stage=True인 증강은 1단계부터 후보가 될 수 있습니다.
        return True

    # 캠페인 또는 일반 증강은 stages에 적힌 stage_index에서만 등장합니다.
    return stage_index in data["stages"]


# 플레이어가 선택지 중 하나를 골랐을 때 실제 증강을 적용합니다.
def choose_augment(game, choice_index):
    if not getattr(game, "augment_pending", False):
        return False

    if not 0 <= choice_index < len(game.augment_choices):
        return False

    augment_id = game.augment_choices[choice_index]
    if not grant_augment(game, augment_id):
        return False
    game.augment_choices = []
    game.augment_pending = False
    # 레벨업은 전투 중에 열리므로, 선택 후에는 원래 전투 화면으로 돌아갑니다.
    game.game_state = getattr(game, "previous_game_state", "play")
    game.message_text = f"{AUGMENTS[augment_id]['title']} 획득"
    game.message_timer = 1.4
    return True


# 증강 하나를 현재 판에 추가하고 효과를 적용합니다.
# 캠페인 보상처럼 레벨업 선택지가 아닌 곳에서도 같은 함수를 재사용합니다.
def grant_augment(game, augment_id):
    ensure_augment_state(game)
    if augment_id not in AUGMENTS:
        return False

    stacks = getattr(game, "augment_stacks", {})
    max_stack = AUGMENTS[augment_id]["max_stack"]
    if stacks.get(augment_id, 0) >= max_stack:
        return False

    stacks[augment_id] = stacks.get(augment_id, 0) + 1
    game.augment_stacks = stacks
    apply_augment_effect(game, augment_id)
    return True


# 증강 id 하나를 실제 능력치 변화로 바꿉니다.
def apply_augment_effect(game, augment_id):
    ensure_augment_state(game)
    player = getattr(game, "player", None)
    if augment_id == "cannon_damage":
        game.augment_bullet_damage += 5
        game.augment_speed_bonus += 8
        if player:
            player["speed"] += 8
    elif augment_id == "cannon_size":
        game.augment_bullet_radius += 1
    elif augment_id == "reload_training":
        game.augment_reload_bonus = min(0.55, game.augment_reload_bonus + 0.08)
    elif augment_id == "weapon_hyeonja":
        game.weapon_tier = max(getattr(game, "weapon_tier", 0), 1)
    elif augment_id == "weapon_jija":
        game.weapon_tier = max(getattr(game, "weapon_tier", 0), 2)
    elif augment_id == "weapon_cheonha":
        game.weapon_tier = max(getattr(game, "weapon_tier", 0), 3)
    elif augment_id == "hull_reinforce":
        game.augment_max_hp_bonus += 25
        if player:
            player["maxHp"] += 25
            player["hp"] = min(player["maxHp"], player["hp"] + 25)
    elif augment_id == "oar_training":
        game.augment_speed_bonus += 28
        if player:
            player["speed"] += 28
    elif augment_id == "tanker_skill":
        game.tanker_skill_unlocked = True
    elif augment_id == "healer_skill":
        game.healer_skill_unlocked = True
    elif augment_id == "hakikjin_skill":
        game.hakikjin_unlocked = True
    elif augment_id == "repair_efficiency":
        game.augment_heal_bonus += 6
    elif augment_id == "guard_duration":
        game.augment_guard_bonus += 0.7
    elif augment_id == "hakikjin_mastery":
        game.augment_hakikjin_bonus += 1


# HUD에 짧게 보여줄 증강 요약 문장을 만듭니다.
def get_augment_summary(game):
    ensure_augment_state(game)
    stacks = getattr(game, "augment_stacks", {})
    if not stacks:
        return f"무기 {get_weapon_tier_name(game)}"

    parts = [f"무기 {get_weapon_tier_name(game)}"]
    for augment_id, count in stacks.items():
        title = AUGMENTS.get(augment_id, {}).get("title", augment_id)
        parts.append(f"{title} x{count}")
    return ", ".join(parts[:4])


# 현재 무기 단계 이름을 화면/문서용 문자열로 바꿉니다.
def get_weapon_tier_name(game):
    tier = max(0, min(3, getattr(game, "weapon_tier", 0)))
    return WEAPON_TIER_NAMES.get(tier, "황자총통")
