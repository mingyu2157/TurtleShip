# skins.py
# 역할:
#   이미지/효과음 파일 이름 규칙과 플레이어 크기, 배경 플레이 영역을 정의합니다.
#   assets.py는 이 파일에 적힌 이름을 보고 실제 파일을 찾아 불러옵니다.
#
# 초보자 포인트:
#   새 이미지를 추가하고 싶으면 보통 여기에 이름을 등록하고,
#   assets/images 폴더에 같은 이름의 png/jpg 파일을 넣으면 됩니다.
#
# 공부 순서:
#   PLAYER_WIDTH/HEIGHT는 플레이어가 화면에 보이는 크기입니다.
#   PLAYER_HITBOX_WIDTH/HEIGHT는 실제로 맞는 판정 크기입니다.
#   COMMON_IMAGE_NAMES는 모든 화면에서 공통으로 찾는 이미지 이름 목록입니다.
#   stage_image_names()는 stage1.png처럼 스테이지 번호가 붙는 이미지 이름을 자동으로 만듭니다.
#   stage_sound_names()는 shoot_stage1.mp3처럼 스테이지 번호가 붙는 효과음 이름을 자동으로 만듭니다.
# 플레이어 배 표시 크기입니다.
# 새 거북선 이미지는 가로가 넓은 형태라 이미지 비율에 맞춰 키웠습니다.
# 히트박스는 노/깃발/물결까지 모두 맞지 않도록 실제 선체 중심부보다 작게 둡니다.
PLAYER_WIDTH = 96
PLAYER_HEIGHT = 76
PLAYER_HITBOX_WIDTH = 54
PLAYER_HITBOX_HEIGHT = 42

# game_background.png 원본 이미지 안에서 실제 바다 전투 영역만 지정한 값입니다.
# (왼쪽 x, 위 y, 너비, 높이) 순서이며, 테두리 장식 부분을 제외하는 데 사용됩니다.
GAME_BACKGROUND_PLAY_RECT = (30, 34, 1476, 956)

# 증강 선택 화면에서 쓸 배경과 각 증강 카드 이미지 이름입니다.
# 파일 이름은 augments.py의 증강 id와 같게 두면 자동으로 불러옵니다.
AUGMENT_CARD_IMAGE_NAMES = [
    "argu_background",
    "basic_background",
    "basic_weapon",
    "basic_random",
    "basic_random_skill",
    "basic_hull",
    # 명량해전 생즉사 사즉생 선택 화면에서 쓰는 카드 이미지입니다.
    "live",
    "die",
    "cannon_damage",
    "cannon_size",
    "reload_training",
    "weapon_hyeonja",
    "weapon_jija",
    "weapon_cheonha",
    "hull_reinforce",
    "oar_training",
    "tanker_skill",
    "healer_skill",
    "hakikjin_skill",
    "repair_efficiency",
    "guard_duration",
    "hakikjin_mastery",
]

# 모든 스테이지에서 공통으로 사용할 이미지 이름입니다.
STAGE_SELECT_STATE_IMAGE_NAMES = [
    "stage_select_u1_s1",
    *[f"stage_select_u{unlocked}_s{selected}" for unlocked in range(2, 6) for selected in range(1, unlocked + 1)],
    *[f"stage_select_complete_s{selected}" for selected in range(1, 6)],
]


COMMON_IMAGE_NAMES = [
    "main_menu",
    # 모드 선택 화면:
    #   mode_back.png는 뒤로 버튼 선택 상태, story_mode.png/com_mode.png는 각 모드 선택 상태입니다.
    "mode_back",
    "story_mode",
    "com_mode",
    # menu_start_button.png:
    #   메인 메뉴에서 이순신 시뮬레이션 시작 버튼 이미지로 사용합니다.
    #   이미지 자체에 "게임 시작" 글자가 들어 있으면 ui.py가 별도 글자를 덮지 않습니다.
    "menu_start_button",
    "splash",
    # stage_select_background.png:
    #   스테이지 선택 화면 전체 배경으로 사용할 이미지입니다.
    #   없으면 기존 바다 배경을 그대로 사용합니다.
    "stage_select_background",
    # stage_select_panel.png:
    #   스테이지 선택 화면 중앙 패널 장식 이미지가 필요할 때 사용할 수 있는 예비 칸입니다.
    #   지금은 없어도 동작하고, 나중에 UI 디자인 이미지를 주면 assets.py가 자동으로 읽습니다.
    "stage_select_panel",
    # 배경.png:
    #   스테이지 선택 화면 전용 배경 이미지입니다. stage_select_background 대신 우선 사용됩니다.
    "배경",
    # stage_select_u3_s2.png:
    #   진행도와 현재 선택 스테이지가 반영된 완성형 스테이지 선택 화면입니다.
    #   있으면 개별 카드 조립 대신 이 이미지를 화면 전체에 사용합니다.
    *STAGE_SELECT_STATE_IMAGE_NAMES,
    # 잠금_2.png ~ 잠금_5.png:
    #   해당 스테이지가 잠겼을 때 카드 자리에 표시되는 이미지입니다.
    *[f"잠금_{n}" for n in range(2, 6)],
    # 글귀_1.png ~ 글귀_5.png:
    #   스테이지를 가리킬 때 화면 하단에 표시되는 해전 명언/글귀 이미지입니다.
    *[f"글귀_{n}" for n in range(1, 6)],
    # 완료_1.png ~ 완료_5.png:
    #   해당 스테이지를 완료했을 때 카드 자리에 표시되는 이미지입니다.
    *[f"완료_{n}" for n in range(1, 6)],
    # 출전 준비1.png / 출전 준비_2.png ~ 출전 준비_5.png:
    #   해금된(다음 출전 가능한) 스테이지 또는 완료 카드를 가리킬 때 표시되는 이미지입니다.
    #   1번 파일은 언더스코어가 없으므로 별도 등록합니다.
    "출전 준비1",
    *[f"출전 준비_{n}" for n in range(2, 6)],
    # story_background.png:
    #   난중일기/스토리 화면 공통 배경 이미지입니다.
    #   스테이지별/페이지별 이미지가 없으면 이 이미지를 우선 사용합니다.
    "story_background",
    # story_paper.png:
    #   난중일기 글상자 배경으로 사용할 수 있는 이미지입니다.
    #   투명 PNG를 넣으면 글상자 디자인을 쉽게 바꿀 수 있습니다.
    "story_paper",
    # story_diary_horizontal.png:
    #   스테이지 시작 전 난중일기 화면의 가로형 일기지 이미지입니다.
    #   이 이미지 위에 글자가 천천히 쓰이는 애니메이션으로 표시됩니다.
    "story_diary_horizontal",
    # story_summary_vertical.png:
    #   전투 중 왼쪽 사이드 영역에 표시하는 세로형 요약지 이미지입니다.
    #   현재 출전 직전 가로 일기에 나온 내용을 짧게 요약해서 보여줍니다.
    "story_summary_vertical",
    # 전투 중 오른쪽 정보 UI와 Z/X/C 스킬 아이콘입니다.
    "right_ui_panel",
    "hp_gauge",
    "boss_hp_fill",
    "boss_hp_stage1_phase1",
    "boss_hp_stage1_phase2",
    "boss_hp_stage2",
    "boss_hp_stage3",
    "boss_hp_stage4",
    "boss_hp_stage5",
    "skill_icon_q",
    "skill_icon_z",
    "skill_icon_x",
    "leaderboard_background",
    "leaderboard_background_vertical",
    "account_profile_icon",
    "account_login_panel",
    "account_signup_panel",
    "account_mypage_panel",
    "account_edit_panel",
    # story_intro.png:
    #   도입 스토리 전용 이미지 슬롯입니다.
    #   지금 캠페인 흐름에서는 주로 스테이지별 스토리를 보지만, 도입부를 다시 쓸 때 바로 연결됩니다.
    "story_intro",
    # story_intro_page1.png ~ story_intro_page9.png:
    #   4월 13일, 14일, 15일처럼 도입부 난중일기를 날짜별 이미지로 꾸밀 때 사용합니다.
    *[f"story_intro_page{page_number}" for page_number in range(1, 10)],
    # stage_result_background.png:
    #   스테이지 클리어 결과 화면 전체 배경으로 사용할 이미지입니다.
    #   없으면 기존 바다 배경을 그대로 사용합니다.
    "stage_result_background",
    # stage_result_panel.png:
    #   점수/피격/스킬 사용량이 들어가는 결과 패널 디자인 이미지입니다.
    #   나중에 UI 이미지를 주면 이 칸에 넣어 바로 교체할 수 있습니다.
    "stage_result_panel",
    "game_background",
    "wave_overlay",
    "player",
    "bullet",
    "enemy",
    "obstacle_rock1",
    "obstacle_rock2",
    "weather_typhoon1",
    "weather_typhoon2",
    "weather_fog1",
    "weather_rain1",
    "weather_lightning1",
    "mini_boss",
    *AUGMENT_CARD_IMAGE_NAMES,
]

# 한 스테이지 안에 난중일기/스토리 페이지를 몇 편까지 미리 열어둘지 정합니다.
# 사용자가 말한 "1편 ~ 9편"을 바로 넣을 수 있도록 9칸을 만들어 둡니다.
MAX_STORY_PAGES_PER_STAGE = 9

# 1단계처럼 한 스테이지 안에 여러 전투가 들어갈 때를 위한 예비 phase 칸입니다.
MAX_STORY_PHASES_PER_STAGE = 2

# 예전 지원선 시스템은 제거했으므로 비워 둡니다.
# assets.py가 이 목록을 읽기 때문에 변수 자체는 남겨 두면 다른 코드가 안전합니다.
ALLY_IMAGE_NAMES = []

# 나중에 필살기 연출을 추가할 때 사용할 이미지 이름입니다.
SKILL_IMAGE_NAMES = [
    "ultimate_flash",
    "skill_hakikjin_ship",
    "skill_tanker_guard",
    "skill_healer_aura",
]

# 모든 스테이지에서 공통으로 사용할 효과음 이름입니다.
COMMON_SOUND_NAMES = [
    "shoot",
    "hit",
    "weather_lightning",
    "boss",
    "destroy",
    "skill",
    "ultimate",
    "typing",
]


# stage1.png, enemy_stage1.png처럼 스테이지 번호가 붙은 이미지 이름을 자동 생성합니다.
def stage_image_names(stage_max):
    names = []
    for stage_number in range(1, stage_max + 1):
        names += [
            # stage_select_stage1.png:
            #   스테이지 선택 카드 안에 들어갈 스테이지별 대표 이미지입니다.
            f"stage_select_stage{stage_number}",
            # story_stage1.png:
            #   특정 스테이지 스토리 화면의 공통 이미지입니다.
            #   page 이미지가 없을 때 이 이미지가 대신 쓰입니다.
            f"story_stage{stage_number}",
            # story_boss_stage1.png:
            #   전투 중 왼쪽 세로 난중일기 요약 아래에 표시할 스테이지별 보스 초상 이미지입니다.
            #   없으면 기존 mini_boss_stage1 또는 boss_stage1 이미지를 대신 사용합니다.
            f"story_boss_stage{stage_number}",
            # stage_result_stage1.png:
            #   특정 스테이지 결과 화면에만 쓰는 대표 이미지입니다.
            #   없으면 stage_result_background.png 또는 기본 바다 배경을 씁니다.
            f"stage_result_stage{stage_number}",
            f"stage{stage_number}",
            f"enemy_stage{stage_number}",
            f"mini_boss_stage{stage_number}",
            f"boss_stage{stage_number}",
            f"bullet_stage{stage_number}",
            f"projectile_stage{stage_number}",
            f"enemy_projectile_stage{stage_number}",
            f"boss_projectile_stage{stage_number}",
        ]
        # story_stage1_page1.png ~ story_stage1_page9.png:
        #   한 스테이지 안에서 여러 편의 난중일기 이미지를 순서대로 넣을 수 있는 칸입니다.
        for page_number in range(1, MAX_STORY_PAGES_PER_STAGE + 1):
            names.append(f"story_stage{stage_number}_page{page_number}")
            # story_stage1_phase2_page1.png:
            #   1단계 사천포/당포처럼 내부 전투별 스토리 이미지를 따로 줄 때 쓰는 칸입니다.
            for phase_number in range(1, MAX_STORY_PHASES_PER_STAGE + 1):
                names.append(f"story_stage{stage_number}_phase{phase_number}_page{page_number}")
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
            f"skill_stage{stage_number}",
            f"ultimate_stage{stage_number}",
        ]
    return names
