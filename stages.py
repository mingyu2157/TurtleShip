# stages.py
# 역할:
#   5개 스테이지의 공통 정보를 하나로 합쳐 최종 STAGES 리스트를 만듭니다.
#   일반 적 정보는 enemies.py, 보스 정보는 bosses.py에 따로 나눠져 있고,
#   이 파일에서 스테이지 이름/색상과 함께 합쳐집니다.
#
# 초보자 포인트:
#   스테이지 데이터를 코드 로직과 분리해두면 밸런스 조정이 쉬워집니다.
#   체력, 속도, 색상 같은 값만 바꾸고 게임 로직은 그대로 둘 수 있습니다.
#
# 공부 순서:
#   STAGE_INFO는 스테이지 이름/색상 같은 공통 정보,
#   enemies.py는 일반 적 수치,
#   bosses.py는 보스 수치입니다.
#   build_stages()가 세 파일의 데이터를 한 스테이지 딕셔너리로 합칩니다.
from bosses import BOSS_STAGES
from enemies import ENEMY_STAGES


# 보스가 등장하기 전까지 잡아야 하는 기본 일반 적 수입니다.
# 각 스테이지 데이터에 kills_to_boss가 있으면 그 값을 우선 사용합니다.
KILLS_TO_BOSS = 45

# 화면에 동시에 너무 많은 적이 쌓이지 않도록 제한하는 값입니다.
MAX_ENEMIES_ON_SCREEN = 9

# 스테이지 이름과 색상처럼 일반 적/보스와 공통으로 쓰는 정보입니다.
STAGE_INFO = [
    {
        "name": "1단계 사천포·당포해전",
        "phase_names": ("1-1단계 사천포해전", "1-2단계 당포해전"),
        "phase_bosses": ("도쿠이 미치유키 지휘선", "가메이 고레노리 대장선"),
        "phase_traits": ("산 위 항전 + 약한 화살", "높은 누각 + 부채 보상"),
        "phase_kills_to_boss": (10, 14),
        "phase_boss_hp": (340, 460),
        "phase_boss_shield": (0, 55),
        "color": (84, 137, 170),
        "bullet_color": (255, 226, 155),
        "projectile_color": (255, 117, 92),
        "wave_speed": 38,
        "kills_to_boss": 14,
    },
    {
        "name": "2단계 한산도해전",
        "color": (90, 122, 210),
        "bullet_color": (148, 223, 255),
        "projectile_color": (146, 168, 255),
        "wave_speed": 50,
        "kills_to_boss": 36,
    },
    {
        "name": "3단계 부산포해전",
        "color": (207, 93, 66),
        "bullet_color": (255, 194, 96),
        "projectile_color": (255, 92, 70),
        "wave_speed": 76,
        "player_speed_multiplier": 0.9,
        "kills_to_boss": 52,
    },
    {
        "name": "4단계 명량해전",
        "color": (125, 94, 190),
        "bullet_color": (196, 169, 255),
        "projectile_color": (166, 96, 255),
        "wave_speed": 68,
        "stage_handicap_seconds": 30.0,
        "start_hp_ratio": 0.5,
        "start_weapon_tier_cap": 0,
        "kills_to_boss": 60,
    },
    {
        "name": "5단계 노량해전",
        "color": (218, 72, 58),
        "bullet_color": (255, 232, 118),
        "projectile_color": (255, 73, 73),
        "wave_speed": 60,
        "kills_to_boss": 90,
        "darkness_alpha": 78,
    },
]


# STAGE_INFO, ENEMY_STAGES, BOSS_STAGES를 같은 순서끼리 합쳐서
# 게임에서 바로 사용할 수 있는 STAGES 리스트를 만듭니다.
def build_stages():
    stages = []
    for info, enemy, boss in zip(STAGE_INFO, ENEMY_STAGES, BOSS_STAGES):
        # update()는 딕셔너리 내용을 합칩니다.
        # info -> enemy -> boss 순서로 합쳐서 하나의 stage 딕셔너리를 만듭니다.
        stage = {}
        stage.update(info)
        stage.update(enemy)
        stage.update(boss)
        stages.append(stage)
    return stages


# 실제 게임이 참조하는 최종 스테이지 리스트와 전체 개수입니다.
STAGES = build_stages()
STAGE_MAX = len(STAGES)


# 현재 스테이지에서 보스 등장 전까지 필요한 격침 수를 가져옵니다.
# 1단계처럼 특별히 낮은 목표가 있는 스테이지를 쉽게 만들 수 있습니다.
def get_stage_phase(game):
    return max(0, int(getattr(game, "stage_phase", 0)))


# 1단계처럼 내부 전투가 나뉜 경우 현재 phase에 맞는 이름을 돌려줍니다.
def get_stage_display_name(game):
    stage = game.current_stage()
    phase_names = stage.get("phase_names")
    if phase_names:
        phase = min(get_stage_phase(game), len(phase_names) - 1)
        return phase_names[phase]
    return stage["name"]


# 1단계 내부 전투마다 다른 미니보스 이름을 보여주기 위한 함수입니다.
def get_stage_boss_name(game):
    stage = game.current_stage()
    phase_bosses = stage.get("phase_bosses")
    if phase_bosses:
        phase = min(get_stage_phase(game), len(phase_bosses) - 1)
        return phase_bosses[phase]
    return stage["boss"]


# HUD/등장 배너에 표시할 보스 특징도 phase별로 바꿀 수 있게 합니다.
def get_stage_trait(game):
    stage = game.current_stage()
    phase_traits = stage.get("phase_traits")
    if phase_traits:
        phase = min(get_stage_phase(game), len(phase_traits) - 1)
        return phase_traits[phase]
    return stage["trait"]


# 현재 스테이지에서 보스 등장 전까지 필요한 격침 수를 가져옵니다.
# 1단계는 사천포/당포 내부 전투마다 목표 격침 수가 다릅니다.
def get_kills_to_boss(stage, phase=0):
    phase_kills = stage.get("phase_kills_to_boss")
    if phase_kills:
        safe_phase = max(0, min(int(phase), len(phase_kills) - 1))
        return phase_kills[safe_phase]
    return stage.get("kills_to_boss", KILLS_TO_BOSS)
