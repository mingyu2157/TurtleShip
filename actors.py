# actors.py
# 역할:
#   플레이어, 일반 적, 미니보스처럼 "움직이는 캐릭터/배"를 관리합니다.
#   탄환은 projectiles.py, 충돌은 combat.py, 보상은 rewards.py가 맡습니다.
#
# 초보자 포인트:
#   pygame.Rect는 위치와 크기를 가진 사각형입니다.
#   이미지가 없어도 Rect가 있으면 이동, 충돌, 화면 위치 계산을 할 수 있습니다.
#
# 공부 순서:
#   1. open_stage_select(), start_stage(), complete_stage()로 큰 캠페인 흐름을 봅니다.
#   2. update_player(), update_enemies(), update_boss()로 매 프레임 움직임을 봅니다.
#   3. create_enemy(), spawn_boss()로 실제 적/보스 데이터가 어떻게 만들어지는지 봅니다.
import math
import random

import pygame

import assets
import augments
import campaign
import layout
import obstacles
import projectiles
import rewards
import results
import story
import waves
import weather
from settings import MOVE_SCANCODES
from skins import PLAYER_HEIGHT, PLAYER_HITBOX_HEIGHT, PLAYER_HITBOX_WIDTH, PLAYER_WIDTH
from stages import (
    MAX_ENEMIES_ON_SCREEN,
    STAGE_MAX,
    get_kills_to_boss,
    get_stage_boss_name,
    get_stage_phase,
    get_stage_trait,
)


# 메인 메뉴에서 모드 선택 화면으로 이동합니다.
# 기본 포커스는 story_mode 이미지(인덱스 0)입니다.
def open_mode_select(game, selected_index=0):
    game.game_mode = "campaign"
    campaign.apply_progress_to_game(game)
    clear_battlefield(game)
    game.game_state = "mode_select"
    game.mode_select_index = 0 if selected_index <= 0 else 1 if selected_index == 1 else 2
    game.paused = False
    game.message_timer = 0
    game.message_text = ""


# 메인 메뉴나 결과 화면에서 캠페인 스테이지 선택 화면으로 이동합니다.
# 저장된 진행도를 다시 읽어와서, 게임을 껐다 켜도 잠금 해제가 유지됩니다.
def open_stage_select(game):
    game.game_mode = "campaign"
    campaign.apply_progress_to_game(game)
    clear_battlefield(game)
    game.game_state = "stage_select"
    game.paused = False
    game.story_id = "stage"
    game.story_page_index = 0
    game.stage_banner_timer = 0
    game.message_timer = 0
    game.message_text = ""
    # 스테이지 선택 화면 전용 BGM이 있으면 재생하고, 없으면 조용히 둡니다.



# 스테이지 선택 화면에서 잠긴 스테이지를 눌렀을 때 안내 문구를 띄웁니다.
def show_locked_stage_message(game, stage_index):
    needed = max(1, stage_index)
    game.message_text = f"{needed}단계를 클리어하면 해금됩니다"
    game.message_timer = 1.6


# 선택한 스테이지를 실제로 시작합니다.
# stage_index는 0부터 시작하므로 0은 1스테이지, 4는 5스테이지입니다.
def start_stage(game, stage_index):
    if not 0 <= stage_index < STAGE_MAX:
        return False

    campaign.apply_progress_to_game(game)
    game.stage_select_index = stage_index
    if not campaign.is_stage_unlocked(game, stage_index):
        show_locked_stage_message(game, stage_index)
        return False

    # game_state를 story로 바꾸면 render.py가 전투가 아니라 해전 브리핑 화면을 그립니다.
    game.game_state = "story"
    game.game_mode = "campaign"
    game.paused = False
    game.stage_index = stage_index
    reset_stage_run(game)
    # 첫 캠페인 1단계를 처음 시작할 때는 바로 해전 브리핑이 아니라 4월 13~15일 난중일기 도입부부터 보여줍니다.
    if stage_index == 0 and campaign.get_cleared_stage_count(game) == 0:
        game.story_id = "intro"
        game.story_page_index = 0
    reset_story_typing(game)
    # 선택한 스테이지의 난중일기/브리핑 BGM이 있으면 이 시점에 재생합니다.
    assets.play_story_music(game)
    return True


# 스토리 화면의 타자 애니메이션 상태를 처음부터 다시 시작합니다.
# ui.py가 이 값을 읽어서 새 페이지의 글자를 천천히 나타나게 합니다.
def reset_story_typing(game):
    game.story_typing_key = None
    game.story_typing_started_ms = 0
    game.story_typing_force_complete = False
    game.story_typing_complete = False


# 스테이지를 시작할 때 전투 관련 진행 상태를 깨끗하게 초기화합니다.
# 캠페인 해금 정보는 유지하고, 현재 출전 한 판의 점수/탄환만 새로 시작합니다.
def reset_stage_run(game):
    game.kill_count = 0
    game.stage_total_kills = 0
    game.stage_phase = 0
    game.score = 0
    # 스테이지 결과 화면에 쓸 피격/스킬/발사 기록을 새로 시작합니다.
    results.reset_stage_stats(game)
    game.enemy_spawn_timer = 0
    game.stage_banner_timer = 0
    game.message_timer = 0
    game.message_text = ""
    game.story_id = "stage"
    game.story_page_index = 0
    game.basic_ability_choices = []
    game.basic_ability_chosen = False
    game.stage_handicap_timer = 0.0
    game.stage_effect_message = ""
    # 4스테이지(명량해전)은 필생즉사/필사즉생 선택과 쿨타임 상태를 유지합니다.
    # 다른 스테이지는 last_stand 상태를 완전히 초기화합니다.
    is_myeongnyang = getattr(game, "stage_index", 0) == 3
    if not is_myeongnyang:
        game.last_stand_choice = "damage"
        game.last_stand_choice_made = False
        game.last_stand_damage_cooldown = 0.0
        game.last_stand_revive_cooldown = 0.0
        game.last_stand_revive_penalty_timer = 0.0
    # 활성 버프/상태는 스테이지 시작 시 항상 초기화합니다.
    game.last_stand_used = False
    game.last_stand_damage_timer = 0.0
    game.last_stand_damage_multiplier = 1.0
    game.last_stand_damage_active = False
    game.shoot_cooldown = 0
    clear_battlefield(game)
    obstacles.reset_obstacles(game)
    weather.reset_weather(game)
    rewards.reset_rewards(game)
    # 캠페인 증강은 저장하지 않고 현재 스테이지 안에서만 유지합니다.
    augments.reset_run(game)
    reset_player(game)
    # 전투 BGM은 begin_stage()에서 따로 시작합니다.
    # 여기서는 스토리 화면이므로 start_stage()가 story 전용 음악을 틀어줍니다.


# 현재 전장에 떠 있는 배, 탄환, 아이템, 날씨를 정리합니다.
# 스테이지 선택 화면으로 돌아가거나 새 스테이지를 시작할 때 이전 전투가 남지 않게 합니다.
def clear_battlefield(game):
    game.bullets = []
    game.enemies = []
    game.enemy_projectiles = []
    game.obstacles = []
    game.weather_events = []
    game.hakikjin_ships = []
    game.tanker_guard_rect = None
    game.boss = None


# 플레이어 상태를 초기화하고 현재 전투 영역 아래쪽에 배치합니다.
# 새 게임 시작 때와 혹시 전투 진입 전에 플레이어가 비어 있을 때 재사용합니다.
def reset_player(game):
    # player는 딕셔너리입니다. Rect, 체력, 속도처럼 플레이어에게 필요한 값을 한곳에 넣습니다.
    # 기본값에서 시작하고, 현재 판 증강을 얻으면 augments.py가 이 값을 더해줍니다.
    base_hp = 140 + getattr(game, "augment_max_hp_bonus", 0)
    stage = game.current_stage()
    base_speed = int(360 * stage.get("player_speed_multiplier", 1.0))
    game.player = {
        "rect": pygame.Rect(0, 0, PLAYER_WIDTH, PLAYER_HEIGHT),
        "hitbox": pygame.Rect(0, 0, PLAYER_HITBOX_WIDTH, PLAYER_HITBOX_HEIGHT),
        "maxHp": base_hp,
        "hp": float(base_hp),
        "speed": base_speed + getattr(game, "augment_speed_bonus", 0),
    }
    # combat_area는 실제 전투가 가능한 바다 영역입니다. 테두리/HUD 영역은 제외됩니다.
    combat_area = layout.get_combat_area(game)
    game.player["rect"].center = (combat_area.centerx, combat_area.bottom - 72)
    keep_player_inside(game)
    sync_player_hitbox(game)


# 스토리 화면에서 Enter 또는 클릭을 눌렀을 때 실제 전투를 시작합니다.
# 도입 화면에서는 먼저 1단계 해전 브리핑으로 넘어가고,
# 스테이지 브리핑 화면에서는 실제 전투를 시작합니다.
def advance_story(game):
    # 글자가 아직 쓰이는 중이면 첫 Enter/클릭은 페이지를 넘기지 않고 전체 문장을 즉시 보여줍니다.
    # 이렇게 해야 천천히 쓰이는 연출을 보다가도 답답할 때 한 번에 펼칠 수 있습니다.
    if not getattr(game, "story_typing_complete", True):
        game.story_typing_force_complete = True
        game.story_typing_complete = True
        return

    # 첫 스토리는 도입부입니다. 여러 날짜를 넘긴 뒤 같은 story 화면에서 1단계 브리핑으로 바뀝니다.
    if getattr(game, "story_id", "intro") == "intro":
        if not story.is_last_story_page(game):
            game.story_page_index += 1
            reset_story_typing(game)
            assets.play_story_music(game)
            return
        game.story_id = "stage"
        game.story_page_index = 0
        reset_story_typing(game)
        assets.play_story_music(game)
        return

    # 한 스테이지에 난중일기 페이지가 여러 편 있으면 마지막 페이지 전까지는 다음 페이지로 넘깁니다.
    if not story.is_last_story_page(game):
        game.story_page_index += 1
        reset_story_typing(game)
        assets.play_story_music(game)
        return

    if should_open_basic_ability_select(game):
        open_basic_ability_select(game)
        return

    if should_open_last_stand_select(game):
        open_last_stand_select(game)
        return

    begin_stage(game)


# 1단계 첫 전투 전에는 설계 문서처럼 기본 능력 하나를 고르게 합니다.
def should_open_basic_ability_select(game):
    return (
        getattr(game, "game_mode", "campaign") == "campaign"
        and getattr(game, "stage_index", 0) == 0
        and getattr(game, "stage_phase", 0) == 0
        and not getattr(game, "basic_ability_chosen", False)
    )


# 기본 능력 선택 화면으로 이동합니다.
def open_basic_ability_select(game):
    augments.prepare_basic_ability_choices(game)
    game.game_state = "ability_select"
    game.message_text = ""
    game.message_timer = 0


# 기본 능력을 고른 뒤 바로 사천포 전투를 시작합니다.
def choose_basic_ability(game, choice_index):
    if not augments.choose_basic_ability(game, choice_index):
        return False
    ability_message = getattr(game, "message_text", "")
    begin_stage(game)
    if ability_message:
        game.message_text = ability_message
        game.message_timer = 1.8
    return True


# 4단계 명량해전 직전에는 생즉사 사즉생 방향을 한 번 고르게 합니다.
def should_open_last_stand_select(game):
    return (
        getattr(game, "game_mode", "campaign") == "campaign"
        and getattr(game, "stage_index", 0) == 3
        and not getattr(game, "last_stand_choice_made", False)
    )


# 생즉사 사즉생 선택 화면으로 이동합니다.
def open_last_stand_select(game):
    game.game_state = "last_stand_select"
    game.message_text = ""
    game.message_timer = 0
    # 생즉사 사즉생 선택지도 방향키를 누르면 첫 카드부터 움직이게 합니다.
    game.choice_select_index = 0


# 생즉사 사즉생 선택지를 저장한 뒤 명량해전 전투를 시작합니다.
def choose_last_stand(game, choice_index):
    import skills

    choices = skills.LAST_STAND_CHOICES
    if not 0 <= choice_index < len(choices):
        return False

    game.last_stand_choice = choices[choice_index]["id"]
    game.last_stand_choice_made = True
    game.last_stand_choice_version = 2
    begin_stage(game)
    game.message_text = choices[choice_index]["title"]
    game.message_timer = 1.8
    return True


# 해전 브리핑에서 출전을 선택했을 때 실제 전투를 시작합니다.
# 스테이지가 바뀐 뒤에도 이 함수로 전투 상태를 다시 열 수 있습니다.
def begin_stage(game):
    # 혹시 플레이어 데이터가 비어 있다면 안전하게 다시 만듭니다.
    if not game.player:
        reset_player(game)

    game.game_state = "play"
    game.paused = False
    game.enemy_spawn_timer = 0
    game.stage_banner_timer = 2.0
    game.message_timer = 0
    game.message_text = ""
    apply_stage_start_effects(game)
    # 스테이지 고유 페널티나 날씨 변화처럼 전투 직후 알아야 하는 문구만 중앙 메시지로 띄웁니다.
    stage_effect_message = getattr(game, "stage_effect_message", "")
    if stage_effect_message:
        game.message_text = stage_effect_message
        game.message_timer = 2.0

    assets.play_music(game)


# 캠페인 특정 스테이지에서 시작과 동시에 적용되는 고정 보상을 처리합니다.
def apply_stage_start_effects(game):
    stage = game.current_stage()
    game.stage_handicap_timer = float(stage.get("stage_handicap_seconds", 0.0))
    game.stage_effect_message = ""

    if getattr(game, "game_mode", "campaign") == "campaign":
        hp_ratio = stage.get("start_hp_ratio")
        if hp_ratio is not None and getattr(game, "player", None):
            # 칠천량해전 이후 명량해전은 무너진 수군을 다시 세우는 흐름이라 체력을 절반으로 낮춰 시작합니다.
            game.player["hp"] = max(1, int(game.player["maxHp"] * float(hp_ratio)))
            game.stage_effect_message = "칠천량 이후 체력 절반"

        weapon_cap = stage.get("start_weapon_tier_cap")
        if weapon_cap is not None:
            # 스테이지 기본 능력으로 시작하는 캠페인에서는 이전 무기 진화가 이어지지 않지만,
            # 혹시 테스트나 확장 모드에서 무기 단계가 남아 있어도 이 값으로 안전하게 낮춥니다.
            game.weapon_tier = min(getattr(game, "weapon_tier", 0), int(weapon_cap))

    if getattr(game, "game_mode", "campaign") == "campaign" and getattr(game, "stage_index", 0) >= 1:
        # 한산도해전 이후 캠페인은 학익진 전술을 확정으로 사용합니다.
        if not getattr(game, "hakikjin_unlocked", False):
            augments.grant_augment(game, "hakikjin_skill")


# 메인 메뉴에서 점수 경쟁 모드를 시작합니다.
# 이 모드는 캠페인 잠금/스토리와 별개로 한 판 동안 경험치와 증강을 사용합니다.
def start_score_mode(game):
    game.game_mode = "score"
    campaign.apply_progress_to_game(game)
    game.stage_index = 0
    game.stage_phase = 0
    game.stage_total_kills = 0
    game.basic_ability_choices = []
    game.basic_ability_chosen = False
    game.basic_ability_augment_id = None
    game.stage_handicap_timer = 0.0
    game.stage_effect_message = ""
    game.last_stand_choice = "damage"
    game.last_stand_choice_made = True
    game.score = 0
    game.enemy_spawn_timer = 0
    game.stage_banner_timer = 2.0
    game.message_timer = 0
    game.message_text = "점수 경쟁 시작"
    game.paused = False
    results.reset_stage_stats(game)
    clear_battlefield(game)
    obstacles.reset_obstacles(game)
    weather.reset_weather(game)
    rewards.reset_rewards(game)
    # 증강은 저장하지 않고 점수 경쟁 한 판 동안만 유지합니다.
    augments.reset_run(game)
    reset_player(game)
    game.game_state = "play"
    assets.play_music(game)


# 일시정지 메뉴의 재시작 버튼에서 현재 모드를 처음부터 다시 시작합니다.
# 캠페인은 현재 선택된 해전을 전투 화면부터 다시 열고, 점수 경쟁은 새 점수 경쟁 한 판으로 시작합니다.
def restart_current_play(game):
    if getattr(game, "game_mode", "campaign") == "score":
        start_score_mode(game)
        return

    stage_index = getattr(game, "stage_index", 0)
    if not 0 <= stage_index < STAGE_MAX:
        open_stage_select(game)
        return

    campaign.apply_progress_to_game(game)
    if not campaign.is_stage_unlocked(game, stage_index):
        open_stage_select(game)
        return

    game.stage_index = stage_index
    game.game_mode = "campaign"
    game.paused = False
    reset_stage_run(game)

    if should_open_basic_ability_select(game):
        open_basic_ability_select(game)
        return

    if should_open_last_stand_select(game):
        open_last_stand_select(game)
        return

    begin_stage(game)


# 보스를 처치했을 때 현재 스테이지를 클리어 처리합니다.
# 다음 스테이지는 자동으로 시작하지 않고, 잠금 해제 후 스테이지 선택 화면으로 돌아갑니다.
def complete_stage(game):
    cleared_stage_number = game.stage_index + 1
    newly_unlocked = campaign.unlock_stage_after_clear(game, game.stage_index)
    final_clear = game.stage_index >= STAGE_MAX - 1
    # 결과 화면에 보여줄 점수/피격/스킬 사용량을 먼저 만들어 둡니다.
    results.build_stage_result(game, newly_unlocked, final_clear)

    # 스테이지 선택 화면으로 돌아가기 전에 전투 오브젝트를 모두 정리합니다.
    game.kill_count = 0
    game.stage_total_kills = 0
    game.stage_phase = 0
    clear_battlefield(game)
    obstacles.reset_obstacles(game)
    weather.reset_weather(game)
    game.stage_banner_timer = 0
    game.story_id = "stage"
    game.story_page_index = 0
    game.game_state = "stage_result"
    game.paused = False
    game.stage_select_index = min(game.stage_index + 1, STAGE_MAX - 1)
    if newly_unlocked:
        game.message_text = f"{cleared_stage_number}단계 클리어! {cleared_stage_number + 1}단계 해금"
    else:
        game.message_text = f"{cleared_stage_number}단계 클리어"
    game.message_timer = 2.4
    # 결과 화면에서는 전투 BGM을 멈춰서 클리어 화면이 또렷하게 느껴지게 합니다.
    assets.stop_music(game)


# 보스를 격파했을 때 캠페인과 점수 경쟁을 다르게 처리합니다.
def handle_boss_defeated(game):
    if augments.is_score_mode(game):
        rewards.on_boss_destroyed(game)
        game.score += 1200 + game.stage_index * 420
        game.boss = None
        game.enemy_projectiles = []
        game.kill_count = 0
        game.stage_index = min(STAGE_MAX - 1, game.stage_index + 1)
        game.message_text = f"점수 경쟁 {game.stage_index + 1}단계 진입"
        game.message_timer = 1.8
        return

    if getattr(game, "game_mode", "campaign") == "campaign" and game.stage_index == 0 and get_stage_phase(game) == 0:
        advance_to_next_stage_phase(game)
        return

    complete_stage(game)


# 1단계 사천포 전투가 끝나면 결과 화면으로 가지 않고 당포 브리핑으로 이어집니다.
def advance_to_next_stage_phase(game):
    game.stage_total_kills = getattr(game, "stage_total_kills", 0) + getattr(game, "kill_count", 0)
    game.stage_phase = 1
    game.kill_count = 0
    game.enemy_spawn_timer = 0
    game.stage_banner_timer = 0
    game.message_text = "당포해전으로 이어집니다"
    game.message_timer = 1.8
    game.story_id = "stage"
    game.story_page_index = 0
    reset_story_typing(game)
    clear_battlefield(game)
    obstacles.reset_obstacles(game)
    weather.reset_weather(game)
    rewards.reset_rewards(game)
    game.game_state = "story"
    assets.play_story_music(game)


# 결과 화면에서 Enter 또는 클릭을 눌렀을 때 다음 화면으로 이동합니다.
def close_stage_result(game):
    result = getattr(game, "stage_result", {})
    if result.get("final_clear"):
        # 마지막 스테이지 결과 화면 다음에는 전체 캠페인 클리어 화면으로 이동합니다.
        end_game(game, True)
        return

    unlock_text = result.get("unlock_text", "스테이지 선택")
    open_stage_select(game)
    game.stage_select_index = min(result.get("stage_index", game.stage_index) + 1, STAGE_MAX - 1)
    game.message_text = unlock_text
    game.message_timer = 2.4


# 게임을 끝내고 결과 화면 상태로 바꿉니다.
# clear=True면 클리어 화면, False면 게임오버 화면입니다.
def end_game(game, clear):
    # 게임오버/전체 클리어 화면에서도 점수, 피격 횟수, 스킬 사용량을 보여주기 위해
    # 현재까지의 전투 기록을 end_result 딕셔너리로 묶어 둡니다.
    results.build_end_result(game, clear)
    game.game_state = "clear" if clear else "gameover"
    assets.stop_music(game)


# 플레이어 이동을 처리합니다.
# WASD, 방향키, 한글 입력 상태에서도 물리 키 scancode로 움직일 수 있게 되어 있습니다.
# 직접 조작 후에도 파도 방향으로 조금 밀리므로, 배가 바다 위에 떠 있는 느낌이 납니다.
def update_player(game, dt):
    # previous_rect는 지형지물에 부딪혔을 때 되돌아갈 위치입니다.
    previous_rect = game.player["rect"].copy()
    # get_pressed()는 지금 이 순간 눌려 있는 키 상태 전체를 가져옵니다.
    keys = pygame.key.get_pressed()
    move_x = 0
    move_y = 0

    # 방향 입력을 -1, 0, 1 값으로 모읍니다.
    # 예: 왼쪽이면 move_x=-1, 오른쪽이면 move_x=1입니다.
    if keys[pygame.K_LEFT] or keys[pygame.K_a] or game.held_scancodes & MOVE_SCANCODES["left"]:
        move_x -= 1
    if keys[pygame.K_RIGHT] or keys[pygame.K_d] or game.held_scancodes & MOVE_SCANCODES["right"]:
        move_x += 1
    if keys[pygame.K_UP] or keys[pygame.K_w] or game.held_scancodes & MOVE_SCANCODES["up"]:
        move_y -= 1
    if keys[pygame.K_DOWN] or keys[pygame.K_s] or game.held_scancodes & MOVE_SCANCODES["down"]:
        move_y += 1

    stunned = weather.is_stunned(game.player)
    if stunned:
        # 번개에 맞으면 이동 입력만 막고, 공격/스킬 입력은 input.py에서 그대로 처리합니다.
        move_x = 0
        move_y = 0

    if move_x != 0 or move_y != 0:
        # 대각선 이동이 직선 이동보다 빨라지지 않도록 벡터 길이로 나눕니다.
        length = math.sqrt(move_x * move_x + move_y * move_y)
        # 날씨 배율은 빗물처럼 전체 이동을 느리게 만드는 효과입니다.
        weather_multiplier = weather.get_speed_multiplier(game, game.player["hitbox"])
        # 파도 배율은 입력 방향과 파도 방향을 비교해 순풍/역풍 느낌을 만드는 효과입니다.
        wave_multiplier = waves.get_movement_speed_multiplier(game, move_x, move_y)
        # 최종 이동속도는 기본 속도, 날씨, 파도 보정을 모두 곱해서 만듭니다.
        speed = game.player["speed"] * weather_multiplier * wave_multiplier
        game.player["rect"].x += int(move_x / length * speed * dt)
        game.player["rect"].y += int(move_y / length * speed * dt)

    if not stunned:
        # 플레이어는 파도 방향으로 조금씩 밀립니다. 태풍이 등장하면 weather.py에서 배율이 더 커집니다.
        wave_influence = 0.9 * weather.get_wave_influence_multiplier(game, game.player["hitbox"])
        waves.apply_to_actor(game.player, game, dt, wave_influence)
    keep_player_inside(game)
    sync_player_hitbox(game)
    # 지형지물 충돌 검사 후 필요하면 previous_rect로 되돌립니다.
    obstacles.resolve_player_collision(game, previous_rect)
    keep_player_inside(game)
    sync_player_hitbox(game)


# 플레이어 이미지 Rect와 실제 피격 판정 히트박스를 맞춥니다.
# 히트박스는 이미지보다 작아서 탄 사이를 피할 여유가 생깁니다.
def sync_player_hitbox(game):
    if not game.player:
        return

    hitbox = game.player.get("hitbox")
    if hitbox is None:
        return

    hitbox.center = game.player["rect"].center


# 플레이어가 피해를 받을 때 사용할 작은 히트박스를 돌려줍니다.
# 혹시 예전 저장 상태처럼 hitbox가 없으면 안전하게 전체 rect를 대신 사용합니다.
def get_player_hitbox(game):
    if not game.player:
        return pygame.Rect(0, 0, 0, 0)

    sync_player_hitbox(game)
    return game.player.get("hitbox", game.player["rect"])


# 플레이어가 바다 전투 영역 밖으로 나가지 못하게 제한합니다.
# 배경 이미지의 테두리 영역은 layout.py에서 전투 영역 밖으로 계산됩니다.
def keep_player_inside(game):
    if not game.player:
        return

    rect = game.player["rect"]
    combat_area = layout.get_combat_area(game)
    rect.left = max(combat_area.left + 8, rect.left)
    rect.right = min(combat_area.right - 8, rect.right)
    rect.top = max(combat_area.top + 8, rect.top)
    rect.bottom = min(combat_area.bottom - 8, rect.bottom)


# 일반 적들을 이동시키고 새 적을 생성합니다.
# 보스가 등장해 있으면 일반 적은 더 이상 생성하지 않습니다.
# 스테이지 데이터에 max_enemies가 있으면 그 값을 우선 사용해서 물량 단계를 만들 수 있습니다.
# 스테이지 데이터에 enemy_can_shoot가 True이면 일반 적도 약한 탄환을 발사합니다.
# 적은 위쪽에서만 등장하고, 평소에는 파도 영향 없이 중앙 전투 영역 안에서만 활동합니다.
# 단, 태풍이 등장한 동안에는 전장 전체 파도가 거세져 적도 조금 밀립니다.
def update_enemies(game, dt):
    if game.boss is not None:
        # 보스전에서는 일반 적을 더 만들지 않습니다.
        return

    combat_area = layout.get_combat_area(game)
    # remove_area는 전투 영역보다 조금 넓게 잡아, 화면 밖으로 충분히 나간 적만 제거합니다.
    remove_area = combat_area.inflate(220, 220)
    stage = game.current_stage()

    # 리스트를 순회하면서 삭제할 수 있으므로 game.enemies[:] 복사본을 사용합니다.
    for enemy in game.enemies[:]:
        previous_rect = enemy["rect"].copy()
        enemy["age"] += dt
        if weather.is_stunned(enemy):
            keep_enemy_inside_lane(enemy, combat_area)
            continue

        speed_multiplier = weather.get_speed_multiplier(game, enemy["rect"])
        # drift는 적이 완전 직선으로만 내려오지 않게 하는 좌우 흔들림입니다.
        drift = math.sin(enemy["age"] * 2.6) * dt
        enemy["rect"].x += int((enemy["vx"] * dt + enemy["drift_x"] * drift) * speed_multiplier)
        enemy["rect"].y += int((enemy["vy"] * dt + enemy["drift_y"] * drift) * speed_multiplier)
        # 태풍이 등장해 전장 파도가 거세진 경우 적도 파도 영향을 조금 받습니다.
        wave_multiplier = weather.get_wave_influence_multiplier(game, enemy["rect"])
        if wave_multiplier > 1:
            waves.apply_to_actor(enemy, game, dt, 0.32 * (wave_multiplier - 1))
        keep_enemy_inside_lane(enemy, combat_area)
        obstacles.resolve_enemy_collision(game, enemy, previous_rect)
        keep_enemy_inside_lane(enemy, combat_area)

        # 화면 밖으로 충분히 나간 적은 리스트에서 제거해서 메모리와 연산을 아낍니다.
        if not remove_area.colliderect(enemy["rect"]):
            game.enemies.remove(enemy)
            continue

        update_enemy_attack(game, enemy, stage, dt, combat_area)

    # enemy_spawn_timer는 밀리초 단위입니다. stage["spawn_ms"]와 비교하기 쉽게 dt*1000을 더합니다.
    game.enemy_spawn_timer += dt * 1000
    spawn_ms = stage["spawn_ms"]
    max_enemies = stage.get("max_enemies", MAX_ENEMIES_ON_SCREEN)

    phase = get_stage_phase(game)
    if game.kill_count >= get_kills_to_boss(stage, phase):
        # 목표 격침 수를 채우면 일반 적 대신 보스를 등장시킵니다.
        spawn_boss(game)
        return

    if game.enemy_spawn_timer < spawn_ms or len(game.enemies) >= max_enemies:
        return

    game.enemy_spawn_timer = 0
    create_enemy(game)


# 일반 적이 중앙 모바일 전투 영역의 좌우 밖으로 나가지 않게 잡아줍니다.
# 위/아래 방향 이동은 그대로 두어 위에서 아래로 내려오는 흐름은 유지합니다.
def keep_enemy_inside_lane(enemy, combat_area):
    if enemy["rect"].left < combat_area.left:
        enemy["rect"].left = combat_area.left
        enemy["vx"] = abs(enemy["vx"]) * 0.55
        enemy["drift_x"] = abs(enemy["drift_x"]) * 0.55
    elif enemy["rect"].right > combat_area.right:
        enemy["rect"].right = combat_area.right
        enemy["vx"] = -abs(enemy["vx"]) * 0.55
        enemy["drift_x"] = -abs(enemy["drift_x"]) * 0.55


# 일반 적의 발사 타이머를 처리합니다.
# 2단계처럼 enemy_can_shoot가 켜진 스테이지에서만 작동합니다.
def update_enemy_attack(game, enemy, stage, dt, combat_area):
    if not stage.get("enemy_can_shoot", False) or not game.player:
        return

    if not combat_area.colliderect(enemy["rect"]):
        return

    enemy["shotTimer"] = enemy.get("shotTimer", random_enemy_shot_interval(stage))
    enemy["shotTimer"] -= dt

    if enemy["shotTimer"] > 0:
        return

    shoot_enemy_projectile(game, enemy, stage)
    enemy["shotTimer"] = random_enemy_shot_interval(stage)


# 적 탄환 발사 간격을 랜덤으로 뽑습니다.
# 같은 간격으로만 쏘면 너무 기계적으로 보이기 때문에 최소/최대 사이에서 고릅니다.
def random_enemy_shot_interval(stage):
    low, high = stage.get("enemy_shot_interval", (2.0, 3.0))
    return random.uniform(low, high)


# 일반 적이 아래쪽으로 약한 탄환을 1발 발사합니다.
# 플레이어 위치를 직접 조준하지 않아서 탄환 궤도가 일직선으로 내려옵니다.
# 실제 탄환 데이터 생성은 projectiles.make_enemy_projectile()을 재사용합니다.
def shoot_enemy_projectile(game, enemy, stage):
    start_x = enemy["rect"].centerx
    start_y = enemy["rect"].centery
    speed = stage.get("enemy_projectile_speed", 160)

    projectiles.make_enemy_projectile(
        game,
        start_x,
        start_y,
        0,
        speed,
        stage.get("enemy_projectile_radius", 10),
        stage.get("enemy_projectile_damage", 5),
        0,
        stage["projectile_color"],
    )

# 점수 경쟁 레벨이 높아질수록 적 체력을 조금 올리기 위한 보정값입니다.
def get_score_balance_count(game):
    if not augments.is_score_mode(game):
        return 0
    return max(0, getattr(game, "run_level", 1) - 1)


# 일반 적 한 척의 최종 체력을 계산합니다.
# 캠페인은 기본 체력만 쓰고, 점수 경쟁은 레벨에 따라 조금씩 더 단단해집니다.
def get_balanced_enemy_hp(game, stage):
    balance = get_score_balance_count(game)
    base_hp = float(stage["enemy_hp"] + balance * stage.get("enemy_hp_per_score_level", 0))
    return base_hp * 1.5


# 미니보스의 최종 체력과 보호막을 계산합니다.
# 점수 경쟁에서는 레벨이 높을수록 보스 체력/보호막이 조금씩 증가합니다.
def get_balanced_boss_stats(game, stage):
    balance = get_score_balance_count(game)
    phase = get_stage_phase(game)
    phase_hp = stage.get("phase_boss_hp")
    phase_shield = stage.get("phase_boss_shield")
    base_hp = phase_hp[min(phase, len(phase_hp) - 1)] if phase_hp else stage["boss_hp"]
    base_shield = phase_shield[min(phase, len(phase_shield) - 1)] if phase_shield else stage["boss_shield"]
    hp = float(base_hp + balance * stage.get("boss_hp_per_score_level", 0))
    shield = float(base_shield + balance * stage.get("boss_shield_per_score_level", 0))
    return hp, shield


# 일반 적 1척을 만듭니다.
# 적은 항상 화면 위쪽에서만 등장하고, 중앙 플레이 영역 안에서만 이동합니다.
# 적 이미지가 있으면 이미지 비율에 맞춰 Rect 크기를 잡아서 배가 납작하게 찌그러지지 않게 합니다.
def create_enemy(game):
    stage = game.current_stage()
    combat_area = layout.get_combat_area(game)
    enemy_image = assets.get_stage_image(game, "enemy")
    # 이미지가 있으면 이미지 비율을 기준으로 크기를 정하고,
    # 이미지가 없으면 스테이지 데이터나 기본 랜덤 크기를 사용합니다.
    if enemy_image:
        width, height = get_enemy_image_size(stage, enemy_image)
    elif stage.get("enemy_size_range"):
        (min_width, min_height), (max_width, max_height) = stage["enemy_size_range"]
        width = random.randint(min_width, max_width)
        height = random.randint(min_height, max_height)
    else:
        width = random.randint(72, 94)
        height = random.randint(42, 54)
    rect = pygame.Rect(0, 0, width, height)
    # start는 화면 위쪽, target은 화면 아래쪽입니다. 두 점을 잇는 방향으로 적이 내려옵니다.
    start = (
        random.randint(combat_area.left + width // 2, combat_area.right - width // 2),
        combat_area.top - height,
    )
    target = (
        random.randint(combat_area.left + width // 2, combat_area.right - width // 2),
        combat_area.bottom + height,
    )

    # dx/dy와 distance를 이용해 "출발점에서 목표점으로 향하는 단위 방향"을 계산합니다.
    rect.center = start
    dx = target[0] - start[0]
    dy = target[1] - start[1]
    distance = max(1, math.sqrt(dx * dx + dy * dy))
    speed = stage["enemy_speed"] * random.uniform(0.85, 1.18)
    is_suicide = stage.get("suicide_chance", 0) > 0 and random.random() < stage.get("suicide_chance", 0)
    if is_suicide:
        speed *= stage.get("suicide_speed_multiplier", 1.0)
    vx = dx / distance * speed
    vy = dy / distance * speed
    drift_limit = stage.get("enemy_drift", 42)
    drift_power = random.uniform(-drift_limit, drift_limit)
    enemy_hp = get_balanced_enemy_hp(game, stage)
    if is_suicide:
        enemy_hp *= stage.get("suicide_hp_multiplier", 1.0)

    # enemy 딕셔너리는 적 한 척의 모든 상태입니다.
    # rect는 위치/크기, hp는 체력, vx/vy는 초당 이동량입니다.
    enemy = {
        "rect": rect,
        "hp": enemy_hp,
        "maxHp": enemy_hp,
        "vx": vx,
        "vy": vy,
        "drift_x": -vy / speed * drift_power,
        "drift_y": vx / speed * drift_power,
        "age": random.random() * 10,
        "damage": stage.get("suicide_damage", 16 + game.stage_index * 4) if is_suicide else 16 + game.stage_index * 4,
        "side": "top",
        "is_suicide": is_suicide,
    }

    if stage.get("enemy_can_shoot", False):
        enemy["shotTimer"] = random_enemy_shot_interval(stage)

    game.enemies.append(enemy)


# 스테이지 데이터에 적어둔 enemy_size_range를 기준으로 이미지 적 크기를 정합니다.
# 이미지 비율을 최대한 유지하면서, 스테이지별 최소/최대 크기 안쪽으로 맞춥니다.
def get_enemy_image_size(stage, enemy_image):
    # aspect는 가로/세로 비율입니다. 예를 들어 2.0이면 가로가 세로의 2배입니다.
    aspect = enemy_image.get_width() / max(1, enemy_image.get_height())
    size_range = stage.get("enemy_size_range")

    if size_range:
        # 먼저 세로 크기를 고른 뒤 이미지 비율에 맞춰 가로 크기를 계산합니다.
        (min_width, min_height), (max_width, max_height) = size_range
        height = random.randint(min_height, max_height)
        width = int(height * aspect)

        if width < min_width:
            width = min_width
            height = int(width / max(0.1, aspect))
        elif width > max_width:
            width = max_width
            height = int(width / max(0.1, aspect))

        height = max(1, min(max_height, max(min_height, height)))
        return width, height

    height = random.randint(78, 96)
    width = max(54, min(118, int(height * aspect)))
    return width, height


# 현재 스테이지의 미니보스를 생성합니다.
# 보스가 등장하면 일반 적과 적 탄환을 정리하고, 등장 메시지와 효과음을 재생합니다.
def spawn_boss(game):
    stage = game.current_stage()
    play_area = layout.get_combat_area(game)
    # 마지막 보스는 다른 보스보다 크게 보이게 따로 크기를 키웁니다.
    width = 300 if game.stage_index == STAGE_MAX - 1 else 230 + game.stage_index * 18
    height = 126 if game.stage_index == STAGE_MAX - 1 else 96 + game.stage_index * 8
    rect = pygame.Rect(0, 0, width, height)
    rect.center = (play_area.centerx, play_area.top - height)
    boss_hp, boss_shield = get_balanced_boss_stats(game, stage)

    # 보스는 하나만 존재하므로 game.boss 딕셔너리에 저장합니다.
    # shotTimer/burstTimer는 각각 단발/패턴 공격까지 남은 시간입니다.
    game.boss = {
        "rect": rect,
        "name": get_stage_boss_name(game),
        "trait": get_stage_trait(game),
        "hp": boss_hp,
        "maxHp": boss_hp,
        "shield": boss_shield,
        "maxShield": boss_shield,
        "age": 0.0,
        "shotTimer": stage.get("boss_shot_interval", 0.9),
        "burstTimer": stage.get("boss_burst_interval", 2.2),
        "restoreTimer": 0.0,
        "contactTimer": 0.0,
    }

    game.enemies = []
    game.enemy_projectiles = []
    game.message_text = f"{get_stage_boss_name(game)} 등장"
    game.message_timer = 2.0
    assets.play_stage_sound(game, "boss", 0.8)


# 미니보스 이동과 공격 타이머를 처리합니다.
# stage["pattern"] 값에 따라 보스 이동 방식과 탄막 패턴이 달라집니다.
# stage["boss_can_shoot"]가 False인 단계는 보스가 직접 공격하지 않습니다.
def update_boss(game, dt):
    if game.boss is None:
        return

    stage = game.current_stage()
    rect = game.boss["rect"]
    play_area = layout.get_play_area(game)
    if weather.is_stunned(game.boss):
        # 번개에 맞은 보스는 이동과 공격 타이머 갱신을 잠깐 멈춥니다.
        return

    speed_multiplier = weather.get_speed_multiplier(game, rect)
    game.boss["age"] += dt * speed_multiplier
    game.boss["contactTimer"] = max(0, game.boss.get("contactTimer", 0) - dt)

    # 보스는 처음 화면 밖에서 생성되므로 target_y까지 부드럽게 내려오게 합니다.
    target_y = max(play_area.top + 92, layout.get_hud_height(game) + 36)
    rect.y += int((target_y - rect.y) * min(1, dt * 2.8 * speed_multiplier))

    center_x = play_area.centerx
    sway = min(260, play_area.width * 0.22)
    pattern = stage["pattern"]

    # pattern 값에 따라 보스의 좌우 이동 방식을 바꿉니다.
    if pattern == "sniper":
        player_x = game.player["rect"].centerx
        rect.centerx += int(max(-180 * dt, min(180 * dt, player_x - rect.centerx)))
    elif pattern == "storm":
        rect.centerx = int(center_x + math.sin(game.boss["age"] * 2.5) * sway + math.sin(game.boss["age"] * 5) * 35)
    else:
        rect.centerx = int(center_x + math.sin(game.boss["age"] * (1.2 + game.stage_index * 0.18)) * sway)

    # 보스가 플레이 영역 밖으로 완전히 나가지 않도록 좌우를 제한합니다.
    rect.left = max(play_area.left + 12, rect.left)
    rect.right = min(play_area.right - 12, rect.right)

    if game.stage_index == STAGE_MAX - 1 and game.boss["shield"] <= 0:
        # 최종 보스는 보호막이 깨져도 일정 시간이 지나면 일부 재생됩니다.
        game.boss["restoreTimer"] += dt
        if game.boss["restoreTimer"] >= 8.0:
            game.boss["shield"] = game.boss["maxShield"] * 0.45
            game.boss["restoreTimer"] = 0

    if not stage.get("boss_can_shoot", True):
        return

    # shotTimer는 단발, burstTimer는 여러 발 패턴 공격입니다.
    game.boss["shotTimer"] -= dt
    game.boss["burstTimer"] -= dt

    if game.boss["shotTimer"] <= 0:
        game.boss["shotTimer"] = stage.get("boss_shot_interval", max(0.38, 1.1 - game.stage_index * 0.11))
        projectiles.make_boss_projectile(game, 0, aimed=True)

    if game.boss["burstTimer"] <= 0:
        game.boss["burstTimer"] = stage.get("boss_burst_interval", max(1.3, 2.6 - game.stage_index * 0.15))
        shoot_boss_burst(game)


# 보스의 패턴별 다발 공격을 만듭니다.
# 실제 탄환 생성은 projectiles.make_boss_projectile()에 맡기고,
# 이 함수는 어떤 각도/간격으로 쏠지만 결정합니다.
def shoot_boss_burst(game):
    pattern = game.current_stage()["pattern"]

    if pattern == "guided":
        offsets = [0]
    elif pattern == "spread":
        offsets = [-90, -45, 0, 45, 90]
    elif pattern == "fan":
        offsets = [-150, -95, -45, 45, 95, 150]
    elif pattern == "sniper":
        offsets = [-40, 0, 40]
    elif pattern == "storm":
        offsets = [-180, -120, -60, 0, 60, 120, 180]
    else:
        offsets = [-70, 0, 70]

    for offset in offsets:
        projectiles.make_boss_projectile(game, offset * 0.35, aimed=pattern == "guided", angle_offset=offset)
