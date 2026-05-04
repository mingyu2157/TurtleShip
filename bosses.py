# bosses.py
# 역할:
#   스테이지별 미니보스 이름, 특징, 체력, 보호막, 탄막 패턴을 정합니다.
#   보스를 실제로 움직이고 탄환을 쏘게 하는 코드는 actors.py와 projectiles.py에 있습니다.
#
# 값 설명:
#   boss: 보스 이름입니다.
#   trait: HUD/등장 안내에 보여줄 보스 특징입니다.
#   boss_hp, boss_shield: 보스 체력과 보호막입니다.
#   pattern: 보스 공격 패턴 이름입니다. actors.py의 shoot_boss_burst()에서 사용합니다.
#   boss_can_shoot: False면 보스가 탄환을 쏘지 않습니다.
#   boss_hp_per_score_level, boss_shield_per_score_level:
#     점수 경쟁 레벨이 높을 때 보스 체력/보호막을 추가하는 값입니다.
#   boss_contact_damage: 보스 몸통에 직접 부딪혔을 때 플레이어가 받는 피해입니다.
#   boss_contact_cooldown: 보스 접촉 피해가 다시 들어가기까지 기다리는 시간입니다.
#
# 공부 순서:
#   BOSS_STAGES 리스트도 1단계부터 5단계 순서입니다.
#   pattern 값은 actors.py의 shoot_boss_burst()와 update_boss()가 읽어 공격 방식을 바꿉니다.
BOSS_STAGES = [
    {
        "boss": "도쿠이 미치유키 지휘선",
        "trait": "산 위 항전 + 약한 화살",
        "boss_hp": 320,
        "boss_shield": 0,
        "boss_hp_per_score_level": 18,
        "boss_shield_per_score_level": 0,
        "boss_contact_damage": 24,
        "boss_contact_cooldown": 0.85,
        "pattern": "guided",
        "boss_can_shoot": False,
        "boss_shot_interval": 1.55,
        "boss_burst_interval": 3.3,
        "boss_projectile_speed": 155,
    },
    {
        "boss": "와키자카 야스하루 함대",
        "trait": "대열 공격 + 학익진 전술",
        "boss_hp": 560,
        "boss_shield": 120,
        "boss_hp_per_score_level": 24,
        "boss_shield_per_score_level": 7,
        "boss_contact_damage": 30,
        "boss_contact_cooldown": 0.85,
        "pattern": "spread",
    },
    {
        "boss": "부산포 대형선 4척",
        "trait": "470여 척 함대 + 강한 파도",
        "boss_hp": 660,
        "boss_shield": 150,
        "boss_hp_per_score_level": 30,
        "boss_shield_per_score_level": 9,
        "boss_contact_damage": 36,
        "boss_contact_cooldown": 0.85,
        "pattern": "fan",
    },
    {
        "boss": "도도 다카토라 전함",
        "trait": "133척 포위 + 울돌목 조류",
        "boss_hp": 860,
        "boss_shield": 240,
        "boss_hp_per_score_level": 37,
        "boss_shield_per_score_level": 12,
        "boss_contact_damage": 44,
        "boss_contact_cooldown": 0.85,
        "pattern": "sniper",
    },
    {
        "boss": "노량 최후 대장선",
        "trait": "방어막 재생 + 자폭선 엄호",
        "boss_hp": 1220,
        "boss_shield": 420,
        "boss_hp_per_score_level": 48,
        "boss_shield_per_score_level": 15,
        "boss_contact_damage": 56,
        "boss_contact_cooldown": 0.85,
        "pattern": "storm",
    },
]
