# stages.py
# 역할:
#   5개 스테이지의 공통 정보를 하나로 합쳐 최종 STAGES 리스트를 만듭니다.
#   일반 적 정보는 enemies.py, 보스 정보는 bosses.py에 따로 나눠져 있고,
#   이 파일에서 스테이지 이름/색상과 함께 합쳐집니다.
#
# 초보자 포인트:
#   스테이지 데이터를 코드 로직과 분리해두면 밸런스 조정이 쉬워집니다.
#   체력, 속도, 색상 같은 값만 바꾸고 게임 로직은 그대로 둘 수 있습니다.
from bosses import BOSS_STAGES
from enemies import ENEMY_STAGES


# 보스가 등장하기 전까지 잡아야 하는 일반 적 수입니다.
KILLS_TO_BOSS = 45

# 화면에 동시에 너무 많은 적이 쌓이지 않도록 제한하는 값입니다.
MAX_ENEMIES_ON_SCREEN = 9

# 스테이지 이름과 색상처럼 일반 적/보스와 공통으로 쓰는 정보입니다.
STAGE_INFO = [
    {
        "name": "1단계 안개 해협",
        "color": (84, 137, 170),
        "bullet_color": (255, 226, 155),
        "projectile_color": (255, 117, 92),
    },
    {
        "name": "2단계 소용돌이 해역",
        "color": (90, 122, 210),
        "bullet_color": (148, 223, 255),
        "projectile_color": (146, 168, 255),
    },
    {
        "name": "3단계 화공선 돌파",
        "color": (207, 93, 66),
        "bullet_color": (255, 194, 96),
        "projectile_color": (255, 92, 70),
    },
    {
        "name": "4단계 검은 함대",
        "color": (125, 94, 190),
        "bullet_color": (196, 169, 255),
        "projectile_color": (166, 96, 255),
    },
    {
        "name": "5단계 대장선 결전",
        "color": (218, 72, 58),
        "bullet_color": (255, 232, 118),
        "projectile_color": (255, 73, 73),
    },
]


# STAGE_INFO, ENEMY_STAGES, BOSS_STAGES를 같은 순서끼리 합쳐서
# 게임에서 바로 사용할 수 있는 STAGES 리스트를 만듭니다.
def build_stages():
    stages = []
    for info, enemy, boss in zip(STAGE_INFO, ENEMY_STAGES, BOSS_STAGES):
        stage = {}
        stage.update(info)
        stage.update(enemy)
        stage.update(boss)
        stages.append(stage)
    return stages


# 실제 게임이 참조하는 최종 스테이지 리스트와 전체 개수입니다.
STAGES = build_stages()
STAGE_MAX = len(STAGES)
