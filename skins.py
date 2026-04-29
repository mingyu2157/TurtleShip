# skins.py
# 역할:
#   이미지/효과음 파일 이름 규칙과 플레이어 크기, 배경 플레이 영역을 정의합니다.
#   assets.py는 이 파일에 적힌 이름을 보고 실제 파일을 찾아 불러옵니다.
#
# 초보자 포인트:
#   새 이미지를 추가하고 싶으면 보통 여기에 이름을 등록하고,
#   assets/images 폴더에 같은 이름의 png/jpg 파일을 넣으면 됩니다.
PLAYER_WIDTH = 64
PLAYER_HEIGHT = 144

# game_background.png 원본 이미지 안에서 실제 바다 전투 영역만 지정한 값입니다.
# (왼쪽 x, 위 y, 너비, 높이) 순서이며, 테두리 장식 부분을 제외하는 데 사용됩니다.
GAME_BACKGROUND_PLAY_RECT = (30, 34, 1476, 956)

# 모든 스테이지에서 공통으로 사용할 이미지 이름입니다.
COMMON_IMAGE_NAMES = [
    "main_menu",
    "splash",
    "game_background",
    "player",
    "bullet",
    "enemy",
    "mini_boss",
    "boss_room",
]

# 나중에 동료 기능을 켰을 때 사용할 이미지 이름입니다.
ALLY_IMAGE_NAMES = [
    "ally_support_ship",
    "ally_guard_ship",
    "ally_rapid_ship",
    "ally_support_bullet",
    "ally_guard_bullet",
    "ally_rapid_bullet",
]

# 나중에 아이템 기능을 켰을 때 사용할 이미지 이름입니다.
ITEM_IMAGE_NAMES = [
    "item_bullet_upgrade",
    "item_rapid_fire",
    "item_ultimate_charge",
]

# 나중에 필살기 연출을 추가할 때 사용할 이미지 이름입니다.
SKILL_IMAGE_NAMES = [
    "ultimate_flash",
]

# 모든 스테이지에서 공통으로 사용할 효과음 이름입니다.
COMMON_SOUND_NAMES = [
    "shoot",
    "hit",
    "boss",
    "destroy",
    "ally",
    "item",
    "ultimate",
]


# stage1.png, enemy_stage1.png처럼 스테이지 번호가 붙은 이미지 이름을 자동 생성합니다.
def stage_image_names(stage_max):
    names = []
    for stage_number in range(1, stage_max + 1):
        names += [
            f"stage{stage_number}",
            f"enemy_stage{stage_number}",
            f"mini_boss_stage{stage_number}",
            f"boss_stage{stage_number}",
            f"bullet_stage{stage_number}",
            f"projectile_stage{stage_number}",
        ]
    return names


# shoot_stage1.mp3처럼 스테이지 번호가 붙은 효과음 이름을 자동 생성합니다.
def stage_sound_names(stage_max):
    names = []
    for stage_number in range(1, stage_max + 1):
        names += [
            f"shoot_stage{stage_number}",
            f"hit_stage{stage_number}",
            f"boss_stage{stage_number}",
            f"destroy_stage{stage_number}",
            f"ally_stage{stage_number}",
            f"item_stage{stage_number}",
            f"ultimate_stage{stage_number}",
        ]
    return names
