# layout.py
# 역할:
#   화면 크기에 따라 배경 이미지, 전투 가능 영역, HUD 높이, 시작 버튼 위치를 계산합니다.
#   게임 창이 최대화되거나 크기가 바뀌어도 플레이 영역이 맞도록 도와줍니다.
#
# 초보자 포인트:
#   이미지를 화면에 꽉 채우려면 원본 비율과 현재 창 비율을 비교해서 scale을 구해야 합니다.
#   이 파일은 그런 위치 계산을 모아두어 다른 파일이 숫자 계산에 덜 신경 쓰게 합니다.
import pygame

import assets
from settings import DEFAULT_PAD_HEIGHT, DEFAULT_PAD_WIDTH
from skins import GAME_BACKGROUND_PLAY_RECT


# 이미지를 화면에 꽉 차게 덮을 때 필요한 위치와 배율을 계산합니다.
# cover 방식이라 이미지가 잘릴 수 있지만, 화면에 빈 공간이 생기지 않습니다.
def get_cover_rect(game, image):
    scale = max(game.pad_width / image.get_width(), game.pad_height / image.get_height())
    width = int(image.get_width() * scale)
    height = int(image.get_height() * scale)
    rect = pygame.Rect(0, 0, width, height)
    rect.center = (game.pad_width // 2, game.pad_height // 2)
    return rect, scale


# get_cover_rect()로 계산한 크기에 맞춰 이미지를 실제 화면에 그립니다.
def draw_cover(game, image):
    rect, scale = get_cover_rect(game, image)
    scaled = pygame.transform.smoothscale(image, rect.size)
    game.screen.blit(scaled, rect)
    return rect, scale


# HUD가 차지하는 위쪽 높이를 돌려줍니다.
# 작은 화면에서는 HUD가 조금 더 높아져 글자가 겹치지 않게 합니다.
def get_hud_height(game):
    return 98 if game.pad_width < 720 else 82


# 전체 배경 이미지 중 실제 바다 전투 영역을 계산합니다.
# 맵 이미지 테두리처럼 플레이하면 안 되는 부분은 여기에서 제외됩니다.
def get_play_area(game):
    background = assets.get_stage_image(game, "stage")
    if background:
        drawn_rect, scale = get_cover_rect(game, background)
        source_x, source_y, source_w, source_h = GAME_BACKGROUND_PLAY_RECT
        area = pygame.Rect(
            drawn_rect.left + int(source_x * scale),
            drawn_rect.top + int(source_y * scale),
            int(source_w * scale),
            int(source_h * scale),
        )
        return area.clip(pygame.Rect(0, 0, game.pad_width, game.pad_height))

    top = get_hud_height(game) + 12
    return pygame.Rect(8, top, game.pad_width - 16, game.pad_height - top - 12)


# HUD를 제외한 실제 전투 가능 영역입니다.
# 플레이어와 적 이동 제한은 대부분 이 영역을 사용합니다.
def get_combat_area(game):
    play_area = get_play_area(game)
    top = max(play_area.top, get_hud_height(game) + 10)
    height = max(80, play_area.bottom - top)
    return pygame.Rect(play_area.left, top, play_area.width, height)


# 메인 메뉴 이미지 위의 "게임 시작" 버튼 위치를 계산합니다.
# 이미지가 없을 때는 화면 크기에 맞춘 기본 버튼 위치를 사용합니다.
def get_start_button_rect(game):
    menu_image = game.images.get("main_menu")
    if menu_image:
        source_rect = (898, 584, 386, 92)
        scale = max(game.pad_width / menu_image.get_width(), game.pad_height / menu_image.get_height())
        width = int(menu_image.get_width() * scale)
        height = int(menu_image.get_height() * scale)
        left = (game.pad_width - width) // 2
        top = (game.pad_height - height) // 2
        rect = pygame.Rect(
            left + int(source_rect[0] * scale),
            top + int(source_rect[1] * scale),
            int(source_rect[2] * scale),
            int(source_rect[3] * scale),
        )
        if rect.colliderect(pygame.Rect(0, 0, game.pad_width, game.pad_height)):
            return rect

    rect = pygame.Rect(0, 0, min(380, int(game.pad_width * 0.72)), 68)
    rect.center = (game.pad_width // 2, int(game.pad_height * 0.64))
    return rect


# 기본 창 크기를 돌려주는 작은 helper 함수입니다.
def default_window_size():
    return DEFAULT_PAD_WIDTH, DEFAULT_PAD_HEIGHT
