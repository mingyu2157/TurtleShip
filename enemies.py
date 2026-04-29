# enemies.py
# 역할:
#   스테이지별 일반 적 배의 이름, 체력, 속도, 등장 간격을 정합니다.
#   실제 적 생성과 이동은 actors.py가 담당하고, 이 파일은 데이터만 제공합니다.
#
# 값 설명:
#   enemy_words: 적 배 위에 표시할 이름 목록입니다.
#   enemy_hp: 적 한 척의 체력입니다.
#   enemy_speed: 적이 이동하는 기본 속도입니다.
#   spawn_ms: 몇 밀리초마다 적을 생성할지 정합니다. 숫자가 작을수록 자주 나옵니다.
#   max_enemies: 화면에 동시에 나올 수 있는 적 수입니다. 없으면 stages.py 기본값을 씁니다.
ENEMY_STAGES = [
    {
        "enemy_words": ["정찰선", "선봉선", "소형 왜선", "노젓는 배"],
        "enemy_hp": 9,
        "enemy_speed": 78,
        "spawn_ms": 560,
        "max_enemies": 16,
    },
    {
        "enemy_words": ["기습선", "방패선", "급류선", "창병선"],
        "enemy_hp": 24,
        "enemy_speed": 108,
        "spawn_ms": 900,
    },
    {
        "enemy_words": ["화공선", "불화살선", "돌격선", "폭약선"],
        "enemy_hp": 31,
        "enemy_speed": 122,
        "spawn_ms": 820,
    },
    {
        "enemy_words": ["정예 왜선", "검은 방패선", "쌍돛선", "저격선"],
        "enemy_hp": 38,
        "enemy_speed": 137,
        "spawn_ms": 760,
    },
    {
        "enemy_words": ["대형 왜선", "철갑선", "대포선", "대장 호위선"],
        "enemy_hp": 46,
        "enemy_speed": 148,
        "spawn_ms": 700,
    },
]
