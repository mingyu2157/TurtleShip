# input.py
# 역할:
#   키보드, 마우스, 창 크기 변경 같은 pygame 이벤트를 처리합니다.
#   입력을 직접 게임 로직으로 섞지 않고, 여기에서 어떤 기능을 호출할지만 정합니다.
#
# 초보자 포인트:
#   pygame.event.get()으로 가져온 event는 "방금 일어난 일"입니다.
#   키를 눌렀는지, 뗐는지, 마우스를 눌렀는지 같은 정보를 event.type으로 구분합니다.
#
# 공부 순서:
#   handle_event()가 모든 이벤트의 입구이고,
#   실제 처리는 handle_key_down(), handle_key_up(), handle_mouse_down()으로 나뉩니다.
import sys

import pygame

import actors
import augments
import assets
import combat
import layout
import skills
import ui
from settings import MIN_PAD_HEIGHT, MIN_PAD_WIDTH
from stages import STAGE_MAX


# pygame 이벤트 1개를 받아 종류에 맞게 처리합니다.
# runGame()에서 매 프레임마다 모든 이벤트를 이 함수로 넘깁니다.
def handle_event(game, event):
    if event.type == pygame.QUIT:
        # 창의 X 버튼을 누르면 pygame을 정리하고 프로그램을 종료합니다.
        pygame.quit()
        sys.exit()

    if event.type == pygame.VIDEORESIZE:
        # 창 크기가 바뀌면 game의 화면 크기와 screen을 새 크기로 다시 맞춥니다.
        game.pad_width = max(MIN_PAD_WIDTH, event.w)
        game.pad_height = max(MIN_PAD_HEIGHT, event.h)
        game.screen = pygame.display.set_mode((game.pad_width, game.pad_height), pygame.RESIZABLE)
        # 창 크기가 바뀌면 이전 크기로 확대/축소해 둔 이미지 캐시는 필요 없어집니다.
        assets.clear_image_cache(game)
        actors.keep_player_inside(game)
        return

    if event.type == pygame.KEYDOWN:
        handle_key_down(game, event)
        return

    if event.type == pygame.KEYUP:
        handle_key_up(game, event)
        return

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        handle_mouse_down(game, event.pos)


# 선택지 화면에서 방향키로 현재 선택 카드를 움직입니다.
# 방향키와 WASD를 같이 받으므로 한글 입력 상태가 아니면 키보드만으로도 고를 수 있습니다.
def move_choice_selection(game, direction, choice_count):
    if choice_count <= 0:
        game.choice_select_index = 0
        return

    current = getattr(game, "choice_select_index", 0)
    game.choice_select_index = (current + direction) % choice_count


# 일시정지 메뉴에서 선택한 항목을 실행합니다.
def activate_pause_menu_item(game, index):
    if index == 0:
        game.paused = False
        return

    if index == 1:
        actors.restart_current_play(game)
        return

    if index == 2:
        actors.open_stage_select(game)
        assets.stop_music(game)


# 개발자 테스트용으로 현재 전투를 바로 보스전으로 넘깁니다.
def start_boss_battle_for_test(game):
    if getattr(game, "boss", None) is not None:
        game.message_text = "이미 보스전입니다"
        game.message_timer = 1.2
        return

    actors.spawn_boss(game)


# 키를 눌렀을 때 실행됩니다.
# 메뉴/결과 화면/플레이 화면마다 같은 키도 다른 의미로 쓰일 수 있어서 상태별로 나눠 처리합니다.
def handle_key_down(game, event):
    if getattr(event, "scancode", None) is not None:
        # scancode는 키보드의 물리 위치에 가까워서 한글 입력 상태에서도 WASD를 추적할 수 있습니다.
        game.held_scancodes.add(event.scancode)

    if game.game_state == "menu":
        if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
            game.menu_select_index = 1 - getattr(game, "menu_select_index", 0)
            return
        if event.key == pygame.K_1:
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.open_stage_select(game)
            return
        if event.key == pygame.K_2:
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.start_score_mode(game)
            return
        if event.key == pygame.K_RETURN:
            assets.play_stage_sound(game, "shoot", 0.45)
            if getattr(game, "menu_select_index", 0) == 0:
                actors.open_stage_select(game)
            else:
                actors.start_score_mode(game)
            return
        if event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        return

    if game.game_state == "augment_select":
        choice_count = len(getattr(game, "augment_choices", []))
        if event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_a, pygame.K_w):
            move_choice_selection(game, -1, choice_count)
            return
        if event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_d, pygame.K_s):
            move_choice_selection(game, 1, choice_count)
            return
        if event.key == pygame.K_RETURN:
            assets.play_stage_sound(game, "shoot", 0.45)
            augments.choose_augment(game, getattr(game, "choice_select_index", 0))
            return
        if pygame.K_1 <= event.key <= pygame.K_3:
            assets.play_stage_sound(game, "shoot", 0.45)
            augments.choose_augment(game, event.key - pygame.K_1)
        return

    if game.game_state == "ability_select":
        # 기본 능력 선택 화면도 Space가 선택키가 되지 않게 방향키/Enter/숫자/클릭만 받습니다.
        choice_count = len(getattr(game, "basic_ability_choices", []))
        if event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_a, pygame.K_w):
            move_choice_selection(game, -1, choice_count)
            return
        if event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_d, pygame.K_s):
            move_choice_selection(game, 1, choice_count)
            return
        if event.key == pygame.K_RETURN:
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.choose_basic_ability(game, getattr(game, "choice_select_index", 0))
            return
        if pygame.K_1 <= event.key <= pygame.K_3:
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.choose_basic_ability(game, event.key - pygame.K_1)
        if event.key == pygame.K_ESCAPE:
            actors.open_stage_select(game)
            assets.stop_music(game)
        return

    if game.game_state == "last_stand_select":
        # 생즉사 사즉생 선택도 Space가 선택키가 되지 않도록 방향키/Enter/숫자/클릭만 받습니다.
        choice_count = len(skills.LAST_STAND_CHOICES)
        if event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_a, pygame.K_w):
            move_choice_selection(game, -1, choice_count)
            return
        if event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_d, pygame.K_s):
            move_choice_selection(game, 1, choice_count)
            return
        if event.key == pygame.K_RETURN:
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.choose_last_stand(game, getattr(game, "choice_select_index", 0))
            return
        if event.key in (pygame.K_1, pygame.K_2):
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.choose_last_stand(game, event.key - pygame.K_1)
        if event.key == pygame.K_ESCAPE:
            actors.open_stage_select(game)
            assets.stop_music(game)
        return

    if game.game_state == "stage_select":
        # 스테이지 선택 화면에서는 숫자키, 방향키, Enter를 사용합니다.
        # 잠긴 스테이지를 고르면 actors.py가 안내 메시지를 띄우고 시작하지 않습니다.
        if event.key == pygame.K_ESCAPE:
            game.game_state = "menu"
            return

        if pygame.K_1 <= event.key <= pygame.K_5:
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.start_stage(game, event.key - pygame.K_1)
            return

        if event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_a, pygame.K_w):
            game.stage_select_index = max(0, getattr(game, "stage_select_index", 0) - 1)
            return

        if event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_d, pygame.K_s):
            game.stage_select_index = min(STAGE_MAX - 1, getattr(game, "stage_select_index", 0) + 1)
            return

        if event.key == pygame.K_RETURN:
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.start_stage(game, getattr(game, "stage_select_index", 0))
            return

        return

    if game.game_state == "story":
        # 스토리 화면에서는 Enter 또는 마우스 클릭으로 다음 스토리/전투 시작을 진행합니다.
        # Space는 메뉴 자동 선택을 막기 위해 전투 중 발사 전용으로만 사용합니다.
        if event.key == pygame.K_RETURN:
            actors.advance_story(game)
        if event.key == pygame.K_ESCAPE:
            actors.open_stage_select(game)
            assets.stop_music(game)
        return

    if game.game_state == "stage_result":
        # 결과 화면에서는 Enter 또는 클릭으로만 넘어갑니다. Space는 선택키로 쓰지 않습니다.
        if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.close_stage_result(game)
        return

    if game.game_state in ("gameover", "clear"):
        # 게임 종료 화면에서도 Space로 자동 선택되지 않게 Enter만 받습니다.
        if event.key == pygame.K_RETURN:
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.open_stage_select(game)
        if event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        return

    if game.game_state == "play" and game.paused:
        if event.key in (pygame.K_UP, pygame.K_w):
            game.pause_select_index = (getattr(game, "pause_select_index", 0) - 1) % len(ui.PAUSE_MENU_ITEMS)
            return
        if event.key in (pygame.K_DOWN, pygame.K_s):
            game.pause_select_index = (getattr(game, "pause_select_index", 0) + 1) % len(ui.PAUSE_MENU_ITEMS)
            return
        if event.key == pygame.K_RETURN:
            assets.play_stage_sound(game, "shoot", 0.45)
            activate_pause_menu_item(game, getattr(game, "pause_select_index", 0))
            return
        if event.key in (pygame.K_ESCAPE, pygame.K_p):
            game.paused = False
            return
        return

    if game.game_state == "play" and event.key in (pygame.K_ESCAPE, pygame.K_p):
        game.paused = True
        game.pause_select_index = 0
        return

    if game.game_state != "play" or game.paused:
        # 아래 스킬/공격 입력은 실제 전투 중이고 일시정지가 아닐 때만 처리합니다.
        return

    # 스킬 키부터 검사합니다. 스킬을 쓴 프레임에는 일반 발사까지 같이 나가지 않게 return 합니다.
    if skills.is_ultimate_key(event):
        skills.try_use_ultimate(game)
        return

    if skills.is_hakikjin_key(event):
        start_boss_battle_for_test(game)
        return

    if skills.is_tanker_key(event):
        skills.try_use_tanker_guard(game)
        return

    if skills.is_healer_key(event):
        skills.try_use_healer(game)
        return

    if event.key == pygame.K_SPACE:
        # 스페이스 발사는 main.updateGame()에서 눌림 상태를 보고 처리합니다.
        # 이렇게 해야 한 번 누르기와 꾹 누르기 모두 같은 쿨다운 간격을 사용합니다.
        return


# 키를 뗐을 때 실행됩니다.
# held_scancodes에서 키를 제거해야 한글 입력 상태에서도 이동이 계속 눌린 것으로 남지 않습니다.
def handle_key_up(game, event):
    if getattr(event, "scancode", None) is not None:
        # 키를 떼면 held_scancodes에서 제거해서 계속 눌린 것으로 남지 않게 합니다.
        game.held_scancodes.discard(event.scancode)


# 마우스 왼쪽 버튼을 눌렀을 때 실행됩니다.
# 메뉴에서는 시작 버튼 클릭, 플레이 중에는 발사로 사용합니다.
def handle_mouse_down(game, pos):
    if game.game_state == "menu":
        campaign_rect, score_rect = layout.get_menu_button_rects(game)
        if campaign_rect.collidepoint(pos):
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.open_stage_select(game)
        elif score_rect.collidepoint(pos):
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.start_score_mode(game)
        return

    if game.game_state == "augment_select":
        for index, rect in enumerate(layout.get_augment_choice_rects(game, len(getattr(game, "augment_choices", [])))):
            if rect.collidepoint(pos):
                assets.play_stage_sound(game, "shoot", 0.45)
                game.choice_select_index = index
                augments.choose_augment(game, index)
                break
        return

    if game.game_state == "ability_select":
        for index, rect in enumerate(layout.get_basic_ability_choice_rects(game, len(getattr(game, "basic_ability_choices", [])))):
            if rect.collidepoint(pos):
                assets.play_stage_sound(game, "shoot", 0.45)
                game.choice_select_index = index
                actors.choose_basic_ability(game, index)
                break
        return

    if game.game_state == "last_stand_select":
        for index, rect in enumerate(layout.get_augment_choice_rects(game, len(skills.LAST_STAND_CHOICES))):
            if rect.collidepoint(pos):
                assets.play_stage_sound(game, "shoot", 0.45)
                game.choice_select_index = index
                actors.choose_last_stand(game, index)
                break
        return

    if game.game_state == "stage_select":
        # 스테이지 카드 안을 클릭하면 해당 스테이지를 선택하고, 열려 있으면 시작합니다.
        for stage_index, rect in enumerate(layout.get_stage_select_card_rects(game, STAGE_MAX)):
            if rect.collidepoint(pos):
                assets.play_stage_sound(game, "shoot", 0.45)
                game.stage_select_index = stage_index
                actors.start_stage(game, stage_index)
                break
        return

    if game.game_state == "story":
        actors.advance_story(game)
        return

    if game.game_state == "stage_result":
        # 결과 화면은 클릭해도 다음 화면으로 넘어가게 합니다.
        assets.play_stage_sound(game, "shoot", 0.45)
        actors.close_stage_result(game)
        return

    if game.game_state in ("gameover", "clear"):
        assets.play_stage_sound(game, "shoot", 0.45)
        actors.open_stage_select(game)
        return

    if game.game_state == "play":
        if game.paused:
            _, buttons = layout.get_pause_menu_layout(game)
            for index, rect in enumerate(buttons):
                if rect.collidepoint(pos):
                    assets.play_stage_sound(game, "shoot", 0.45)
                    game.pause_select_index = index
                    activate_pause_menu_item(game, index)
                    return
            return

        combat.shoot_player_bullet(game)
