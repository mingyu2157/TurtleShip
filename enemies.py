# enemies.py
# 역할:
#   스테이지별 일반 적 배의 체력, 속도, 등장 간격을 정합니다.
#   실제 적 생성과 이동은 actors.py가 담당하고, 이 파일은 데이터만 제공합니다.
#
# 값 설명:
#   enemy_hp: 적 한 척의 체력입니다.
#   enemy_speed: 적이 이동하는 기본 속도입니다.
#   spawn_ms: 몇 밀리초마다 적을 생성할지 정합니다. 숫자가 작을수록 자주 나옵니다.
#   max_enemies: 화면에 동시에 나올 수 있는 적 수입니다. 없으면 stages.py 기본값을 씁니다.
#   enemy_can_shoot: True면 일반 적도 약한 탄환을 발사합니다.
#   enemy_size_range: 이미지 적 크기를 단계별로 조정하는 값입니다.
#     ((최소 가로, 최소 세로), (최대 가로, 최대 세로)) 순서로 적습니다.
#     예: ((62, 84), (96, 100))이면 대략 가로 62~96, 세로 84~100 사이로 생성됩니다.
#   enemy_hp_per_score_level: 점수 경쟁 레벨이 오를 때 적 체력을 얼마나 추가할지 정합니다.
#     예를 들어 레벨 보정값이 4이면 enemy_hp_per_score_level * 4 만큼 체력이 더해집니다.
#
# 공부 순서:
#   ENEMY_STAGES 리스트의 첫 번째 딕셔너리가 1단계, 두 번째가 2단계입니다.
#   숫자를 바꾸면 actors.py의 적 생성/이동 로직이 그 값을 읽어 자동 반영합니다.
ENEMY_STAGES = [
    {
        "enemy_hp": 15,
        "enemy_hp_per_score_level": 0.75,
        "enemy_speed": 78,
        "enemy_size_range": ((62, 84), (96, 100)),
        "spawn_ms": 700,
        "max_enemies": 12,
        "enemy_can_shoot": True,
        "enemy_shot_interval": (2.7, 4.2),
        "enemy_projectile_damage": 3,
        "enemy_projectile_radius": 5,
        "enemy_projectile_speed": 135,
    },
    {
        "enemy_hp": 34,
        "enemy_hp_per_score_level": 1.2,
        "enemy_speed": 152,
        "enemy_drift": 96,
        "enemy_size_range": ((62, 104), (92, 124)),
        "spawn_ms": 980,
        "max_enemies": 8,
        "enemy_can_shoot": True,
        "enemy_shot_interval": (1.45, 2.35),
        "enemy_projectile_damage": 5,
        "enemy_projectile_radius": 7,
        "enemy_projectile_speed": 175,
    },
    {
        "enemy_hp": 45,
        "enemy_hp_per_score_level": 1.6,
        "enemy_speed": 122,
        "enemy_size_range": ((64, 112), (98, 132)),
        "spawn_ms": 820,
    },
    {
        "enemy_hp": 58,
        "enemy_hp_per_score_level": 2.1,
        "enemy_speed": 137,
        "enemy_size_range": ((122, 82), (172, 102)),
        "spawn_ms": 760,
        "max_enemies": 10,
        "enemy_can_shoot": True,
        "enemy_shot_interval": (1.2, 2.1),
        "enemy_projectile_damage": 8,
        "enemy_projectile_radius": 7,
        "enemy_projectile_speed": 205,
    },
    {
        "enemy_hp": 78,
        "enemy_hp_per_score_level": 2.7,
        "enemy_speed": 148,
        "enemy_size_range": ((82, 96), (120, 116)),
        "spawn_ms": 560,
        "max_enemies": 12,
        "enemy_can_shoot": True,
        "enemy_shot_interval": (1.15, 2.0),
        "enemy_projectile_damage": 10,
        "enemy_projectile_radius": 7,
        "enemy_projectile_speed": 210,
        "suicide_chance": 0.46,
        "suicide_damage": 68,
        "suicide_speed_multiplier": 1.4,
        "suicide_hp_multiplier": 0.72,
    },
]
