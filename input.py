# input.py
# 역할:
#   키보드, 마우스, 창 크기 변경 같은 pygame 이벤트를 처리합니다.
#   입력을 직접 게임 로직으로 섞지 않고, 여기에서 어떤 기능을 호출할지만 정합니다.
#
# 초보자 포인트:
#   pygame.event.get()으로 가져온 event는 "방금 일어난 일"입니다.
#   키를 눌렀는지, 뗐는지, 마우스를 눌렀는지 같은 정보를 event.type으로 구분합니다.
import sys

import pygame

import actors
import combat
import layout
import skills
from settings import MIN_PAD_HEIGHT, MIN_PAD_WIDTH


# pygame 이벤트 1개를 받아 종류에 맞게 처리합니다.
# runGame()에서 매 프레임마다 모든 이벤트를 이 함수로 넘깁니다.
def handle_event(game, event):
    if event.type == pygame.QUIT:
        pygame.quit()
        sys.exit()

    if event.type == pygame.VIDEORESIZE:
        game.pad_width = max(MIN_PAD_WIDTH, event.w)
        game.pad_height = max(MIN_PAD_HEIGHT, event.h)
        game.screen = pygame.display.set_mode((game.pad_width, game.pad_height), pygame.RESIZABLE)
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


# 키를 눌렀을 때 실행됩니다.
# 메뉴/결과 화면/플레이 화면마다 같은 키도 다른 의미로 쓰일 수 있어서 상태별로 나눠 처리합니다.
def handle_key_down(game, event):
    if getattr(event, "scancode", None) is not None:
        game.held_scancodes.add(event.scancode)

    if game.game_state == "menu":
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            actors.start_game(game)
        if event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        return

    if game.game_state in ("gameover", "clear"):
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            actors.start_game(game)
        if event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        return

    if event.key == pygame.K_ESCAPE:
        game.game_state = "menu"
        return

    if event.key == pygame.K_p:
        game.paused = not game.paused
        return

    if game.game_state != "play" or game.paused:
        return

    if skills.is_ultimate_key(event):
        skills.try_use_ultimate(game)
        return

    if event.key == pygame.K_SPACE:
        combat.shoot_player_bullet(game)


# 키를 뗐을 때 실행됩니다.
# held_scancodes에서 키를 제거해야 한글 입력 상태에서도 이동이 계속 눌린 것으로 남지 않습니다.
def handle_key_up(game, event):
    if getattr(event, "scancode", None) is not None:
        game.held_scancodes.discard(event.scancode)


# 마우스 왼쪽 버튼을 눌렀을 때 실행됩니다.
# 메뉴에서는 시작 버튼 클릭, 플레이 중에는 발사로 사용합니다.
def handle_mouse_down(game, pos):
    if game.game_state == "menu":
        if layout.get_start_button_rect(game).collidepoint(pos):
            actors.start_game(game)
        return

    if game.game_state in ("gameover", "clear"):
        actors.start_game(game)
        return

    if game.game_state == "play" and not game.paused:
        combat.shoot_player_bullet(game)
