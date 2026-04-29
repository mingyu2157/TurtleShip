# bosses.py
# 역할:
#   스테이지별 미니보스 이름, 특징, 체력, 보호막, 탄막 패턴을 정합니다.
#   보스를 실제로 움직이고 탄환을 쏘게 하는 코드는 actors.py와 projectiles.py에 있습니다.
#
# 값 설명:
#   boss: 보스 이름입니다.
#   trait: HUD/등장 안내에 보여줄 보스 특징입니다.
#   boss_words: 보스 탄환 안에 표시할 글자 목록입니다.
#   boss_hp, boss_shield: 보스 체력과 보호막입니다.
#   pattern: 보스 공격 패턴 이름입니다. actors.py의 shoot_boss_burst()에서 사용합니다.
#   boss_can_shoot: False면 보스가 탄환을 쏘지 않습니다.
BOSS_STAGES = [
    {
        "boss": "안개 지휘선",
        "trait": "공격 없음 + 물량 지휘",
        "boss_words": ["압박", "포위", "물량"],
        "boss_hp": 180,
        "boss_shield": 0,
        "pattern": "guided",
        "boss_can_shoot": False,
        "boss_shot_interval": 1.55,
        "boss_burst_interval": 3.3,
        "boss_projectile_speed": 155,
    },
    {
        "boss": "소용돌이 장수선",
        "trait": "좌우 확산 탄막",
        "boss_words": ["회오리탄", "방패 파편", "측면 포격"],
        "boss_hp": 340,
        "boss_shield": 70,
        "pattern": "spread",
    },
    {
        "boss": "화공 대장선",
        "trait": "화염 분열탄",
        "boss_words": ["불화살", "화염 파편", "연막탄"],
        "boss_hp": 430,
        "boss_shield": 110,
        "pattern": "fan",
    },
    {
        "boss": "검은 포위선",
        "trait": "추적 저격",
        "boss_words": ["저격탄", "검은 파편", "집중 포격"],
        "boss_hp": 540,
        "boss_shield": 150,
        "pattern": "sniper",
    },
    {
        "boss": "왜군 대장선",
        "trait": "방어막 재생 + 폭풍 탄막",
        "boss_words": ["대형 포탄", "분산 포격", "파도 탄막"],
        "boss_hp": 780,
        "boss_shield": 270,
        "pattern": "storm",
    },
]
