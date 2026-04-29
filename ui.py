# ui.py
# 역할:
#   글자 출력, 시작 화면, 결과 화면, HUD 같은 사용자 인터페이스를 그립니다.
#   게임 오브젝트 자체는 render.py가 그리고, 점수/체력/버튼 같은 정보 화면은 이 파일이 맡습니다.
#
# 초보자 포인트:
#   한글을 pygame 기본 폰트로 그리면 깨질 수 있어서,
#   macOS/Windows/Linux에서 쓸 수 있는 한글 폰트를 순서대로 찾아 사용합니다.
from pathlib import Path
from time import sleep

import pygame

import layout
from settings import BLACK, BLUE, GRAY, GREEN, RED, WHITE, YELLOW
from stages import KILLS_TO_BOSS


# 사용할 폰트를 가져옵니다.
# 같은 크기/굵기의 폰트는 game.fonts에 저장해두고 다시 재사용해서 성능을 아낍니다.
def get_font(game, size, bold=False):
    key = (size, bold)
    if key in game.fonts:
        return game.fonts[key]

    candidates = [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/Library/Fonts/NanumGothic.ttf",
        "C:/Windows/Fonts/malgun.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]

    for candidate in candidates:
        if Path(candidate).exists():
            font = pygame.font.Font(candidate, size)
            font.set_bold(bold)
            game.fonts[key] = font
            return font

    font_path = pygame.font.match_font("applesdgothicneo,nanumgothic,malgungothic,arialunicode")
    if font_path:
        font = pygame.font.Font(font_path, size)
    else:
        font = pygame.font.Font(None, size)
    font.set_bold(bold)
    game.fonts[key] = font
    return font


# 화면에 글자를 그리는 공통 함수입니다.
# center=True면 x, y를 글자의 중심으로 쓰고, False면 왼쪽 위 좌표로 씁니다.
def draw_text(game, text, size, color, x, y, center=False, bold=False):
    font = get_font(game, size, bold)
    image = font.render(text, True, color)
    rect = image.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    game.screen.blit(image, rect)
    return rect


# 게임 실행 직후 잠깐 보여주는 시작 이미지 화면입니다.
# splash.png가 있으면 이미지를 보여주고, 없으면 기본 글자 화면을 보여줍니다.
def show_splash(game):
    splash = game.images.get("splash")
    if splash:
        layout.draw_cover(game, splash)
    else:
        game.screen.fill(BLACK)
        draw_text(game, "PyShooting", 48, WHITE, game.pad_width // 2, game.pad_height // 2 - 24, True, True)
        draw_text(game, "거북선 전쟁", 24, GRAY, game.pad_width // 2, game.pad_height // 2 + 28, True)
    pygame.display.update()
    sleep(0.35)


# 메인 메뉴 화면을 그립니다.
# main_menu.png 위에 실제 클릭 가능한 시작 버튼을 덧그립니다.
def draw_menu(game, draw_sea_background):
    menu_image = game.images.get("main_menu")
    if menu_image:
        layout.draw_cover(game, menu_image)
    else:
        draw_sea_background(game)
        draw_text(game, "PyShooting", 52, WHITE, game.pad_width // 2, int(game.pad_height * 0.28), True, True)
        draw_text(game, "거북선 전쟁", 26, YELLOW, game.pad_width // 2, int(game.pad_height * 0.36), True, True)

    start_rect = layout.get_start_button_rect(game)
    mouse_pos = pygame.mouse.get_pos()
    hovered = start_rect.collidepoint(mouse_pos)
    button_color = (130, 80, 34) if not hovered else (165, 103, 45)
    border_color = (255, 209, 117)

    pygame.draw.rect(game.screen, button_color, start_rect, border_radius=8)
    pygame.draw.rect(game.screen, border_color, start_rect, 3, border_radius=8)
    draw_text(game, "게임 시작", max(24, start_rect.height // 3), WHITE, start_rect.centerx, start_rect.centery, True, True)


# 게임오버 또는 클리어 화면을 그립니다.
# clear 값에 따라 제목과 안내 문구가 달라집니다.
def draw_end_screen(game, clear, draw_sea_background):
    draw_sea_background(game)
    title = "승리했습니다" if clear else "게임 오버"
    detail = "5개의 스테이지를 모두 돌파했습니다." if clear else "다시 도전해보세요."

    draw_text(game, title, 52, WHITE, game.pad_width // 2, game.pad_height // 2 - 70, True, True)
    draw_text(game, detail, 22, GRAY, game.pad_width // 2, game.pad_height // 2 - 20, True)
    draw_text(game, f"점수 {game.score:,}", 30, YELLOW, game.pad_width // 2, game.pad_height // 2 + 34, True, True)


# 플레이 중 위쪽 HUD를 그립니다.
# 스테이지 이름, 점수, 체력, 격침 수, 보스 체력/보호막을 보여줍니다.
def draw_hud(game):
    hud_height = layout.get_hud_height(game)
    panel = pygame.Surface((game.pad_width, hud_height), pygame.SRCALPHA)
    panel.fill((5, 9, 17, 185))
    game.screen.blit(panel, (0, 0))

    stage = game.current_stage()
    draw_text(game, stage["name"], 20, WHITE, 14, 9, False, True)
    draw_text(game, f"점수 {game.score:,}", 16, GRAY, 14, 36)

    hp_w = min(190, max(120, game.pad_width // 4))
    hp_rect = pygame.Rect(14, hud_height - 22, hp_w, 12)
    pygame.draw.rect(game.screen, (45, 35, 40), hp_rect, border_radius=6)
    hp_fill = hp_rect.copy()
    hp_fill.width = int(hp_rect.width * max(0, game.player["hp"] / game.player["maxHp"]))
    pygame.draw.rect(game.screen, GREEN if game.player["hp"] > 45 else RED, hp_fill, border_radius=6)
    pygame.draw.rect(game.screen, WHITE, hp_rect, 1, border_radius=6)
    draw_text(game, f"체력 {int(game.player['hp'])}/{game.player['maxHp']}", 14, WHITE, hp_rect.right + 8, hp_rect.centery - 9)

    center_x = game.pad_width // 2
    if game.boss is None:
        draw_text(game, f"격침 {game.kill_count}/{KILLS_TO_BOSS}", 22, YELLOW, center_x, 17, True, True)
    else:
        draw_text(game, "미니보스 교전", 22, RED, center_x, 17, True, True)
        boss_hp_rect = pygame.Rect(center_x - 130, 45, 260, 12)
        pygame.draw.rect(game.screen, (48, 29, 35), boss_hp_rect, border_radius=6)
        boss_fill = boss_hp_rect.copy()
        boss_fill.width = int(boss_hp_rect.width * max(0, game.boss["hp"] / game.boss["maxHp"]))
        pygame.draw.rect(game.screen, RED, boss_fill, border_radius=6)
        pygame.draw.rect(game.screen, WHITE, boss_hp_rect, 1, border_radius=6)
        if game.boss["maxShield"] > 0:
            shield_rect = boss_hp_rect.move(0, 17)
            pygame.draw.rect(game.screen, (29, 43, 55), shield_rect, border_radius=6)
            shield_fill = shield_rect.copy()
            shield_fill.width = int(shield_rect.width * max(0, game.boss["shield"] / game.boss["maxShield"]))
            pygame.draw.rect(game.screen, BLUE, shield_fill, border_radius=6)
