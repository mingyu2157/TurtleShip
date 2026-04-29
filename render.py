# render.py
# 역할:
#   게임 상태를 화면에 그립니다.
#   실제 위치/체력/탄환 데이터는 다른 파일에서 계산하고,
#   이 파일은 그 데이터를 pygame.draw 또는 이미지 blit으로 보여주는 일만 맡습니다.
#
# 초보자 포인트:
#   update 계열 함수는 "값을 바꾸는 함수"이고, draw 계열 함수는 "화면에 그리는 함수"입니다.
#   둘을 나눠두면 움직임 수정과 화면 디자인 수정을 따로 하기 쉬워집니다.
import math

import pygame

import allies
import assets
import items
import layout
import projectiles
import ui
from settings import GREEN, RED, WHITE, YELLOW


# 현재 게임 상태에 맞는 화면을 그립니다.
# menu면 메뉴, play면 게임 화면, gameover/clear면 결과 화면을 보여줍니다.
def draw_screen(game):
    if game.game_state == "menu":
        ui.draw_menu(game, draw_sea_background)
    elif game.game_state == "play":
        draw_game(game)
    elif game.game_state == "gameover":
        ui.draw_end_screen(game, False, draw_sea_background)
    elif game.game_state == "clear":
        ui.draw_end_screen(game, True, draw_sea_background)


# 실제 플레이 화면을 그립니다.
# 배경 -> 탄환/적/아이템/보스/동료/플레이어 -> HUD 순서로 그려서 겹침 순서를 정합니다.
def draw_game(game):
    draw_stage_background(game)

    for bullet in game.bullets:
        draw_bullet(game, bullet)

    for enemy in game.enemies:
        draw_enemy(game, enemy)

    for item in getattr(game, "items", []):
        draw_item(game, item)

    if game.boss is not None:
        draw_boss(game)

    for projectile in game.enemy_projectiles:
        draw_enemy_projectile(game, projectile)

    for ally in getattr(game, "allies", []):
        draw_ally(game, ally)

    draw_player(game)
    ui.draw_hud(game)

    if game.stage_banner_timer > 0:
        stage = game.current_stage()
        ui.draw_text(game, stage["name"], 36, WHITE, game.pad_width // 2, game.pad_height // 2 - 30, True, True)
        ui.draw_text(game, f"미니보스: {stage['boss']} / {stage['trait']}", 21, YELLOW, game.pad_width // 2, game.pad_height // 2 + 12, True)

    if game.message_timer > 0:
        ui.draw_text(game, game.message_text, 30, YELLOW, game.pad_width // 2, int(game.pad_height * 0.72), True, True)

    if game.paused:
        shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 145))
        game.screen.blit(shade, (0, 0))
        ui.draw_text(game, "일시정지", 48, WHITE, game.pad_width // 2, game.pad_height // 2 - 20, True, True)


# 스테이지 이미지가 없을 때 사용하는 기본 바다 배경입니다.
# 간단한 줄무늬와 물결 아크로 바다 느낌을 냅니다.
def draw_sea_background(game):
    game.screen.fill((11, 20, 34))
    for y in range(0, game.pad_height, 22):
        color = (12, 36 + min(95, y // 8), 62 + min(90, y // 10))
        pygame.draw.rect(game.screen, color, (0, y, game.pad_width, 22))

    for i in range(14):
        x = (i * 127 + pygame.time.get_ticks() // 18) % (game.pad_width + 80) - 40
        y = int(game.pad_height * 0.28) + i * 37 % max(1, int(game.pad_height * 0.65))
        pygame.draw.arc(game.screen, (52, 117, 150), (x, y, 80, 16), 0, math.pi, 1)


# 현재 스테이지 배경 이미지를 그립니다.
# stageN.png가 있으면 그것을 쓰고, 없으면 기본 바다 배경에 스테이지 색을 살짝 입힙니다.
def draw_stage_background(game):
    image = assets.get_stage_image(game, "stage")
    if image:
        layout.draw_cover(game, image)
        shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 34))
        game.screen.blit(shade, (0, 0))
        return

    draw_sea_background(game)
    stage = game.current_stage()
    tint = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
    color = stage["color"]
    tint.fill((color[0], color[1], color[2], 42))
    game.screen.blit(tint, (0, 0))


# 플레이어 배를 그립니다.
# player.png가 있으면 이미지를 쓰고, 없으면 기본 삼각형 도형으로 대체합니다.
def draw_player(game):
    rect = game.player["rect"]
    image = game.images.get("player")

    if image:
        scaled = pygame.transform.smoothscale(image, rect.size)
        game.screen.blit(scaled, rect)
    else:
        pygame.draw.polygon(
            game.screen,
            (53, 158, 122),
            [(rect.centerx, rect.top), (rect.left, rect.bottom), (rect.right, rect.bottom)],
        )
        pygame.draw.polygon(
            game.screen,
            (235, 246, 240),
            [(rect.centerx, rect.top + 8), (rect.left + 10, rect.bottom - 8), (rect.right - 10, rect.bottom - 8)],
            2,
        )
        pygame.draw.circle(game.screen, YELLOW, (rect.centerx, rect.top + 22), 7)


# 플레이어 탄환을 그립니다.
# 스테이지별 bullet_stageN 이미지가 있으면 먼저 쓰고, 없으면 공통 bullet.png를 씁니다.
# 둘 다 없을 때만 기본 원으로 그립니다.
def draw_bullet(game, bullet):
    image = assets.get_stage_image(game, "bullet")
    rect = projectiles.get_circle_rect(bullet["x"], bullet["y"], bullet["radius"])

    if image:
        scaled = pygame.transform.smoothscale(image, rect.inflate(10, 10).size)
        game.screen.blit(scaled, scaled.get_rect(center=rect.center))
        return

    pygame.draw.circle(game.screen, bullet["color"], rect.center, bullet["radius"])
    pygame.draw.circle(game.screen, WHITE, rect.center, max(2, bullet["radius"] - 4))


# 일반 적 배를 그립니다.
# 이미지가 없을 때도 체력바와 이름이 보이도록 기본 사각형으로 대체합니다.
def draw_enemy(game, enemy):
    rect = enemy["rect"]
    image = assets.get_stage_image(game, "enemy")

    if image:
        scaled = pygame.transform.smoothscale(image, rect.size)
        game.screen.blit(scaled, rect)
    else:
        pygame.draw.rect(game.screen, (82, 40, 50), rect, border_radius=7)
        pygame.draw.rect(game.screen, RED, rect, 2, border_radius=7)

    ui.draw_text(game, enemy["word"], 16, WHITE, rect.centerx, rect.centery - 2, True, True)

    hp_rect = pygame.Rect(rect.left + 8, rect.bottom + 4, rect.width - 16, 5)
    pygame.draw.rect(game.screen, (42, 34, 38), hp_rect, border_radius=2)
    fill = hp_rect.copy()
    fill.width = int(hp_rect.width * max(0, enemy["hp"] / enemy["maxHp"]))
    pygame.draw.rect(game.screen, YELLOW, fill, border_radius=2)


# 미니보스를 그립니다.
# 보스 이름과 특징 문구도 같이 표시합니다.
def draw_boss(game):
    stage = game.current_stage()
    rect = game.boss["rect"]
    image = assets.get_stage_image(game, "boss")

    if image:
        scaled = pygame.transform.smoothscale(image, rect.size)
        game.screen.blit(scaled, rect)
    else:
        pygame.draw.rect(game.screen, (62, 37, 48), rect, border_radius=10)
        pygame.draw.rect(game.screen, stage["color"], rect, 4, border_radius=10)
        pygame.draw.circle(game.screen, RED, (rect.centerx, rect.centery), min(rect.width, rect.height) // 4)

    ui.draw_text(game, stage["boss"], 22, WHITE, rect.centerx, rect.centery - 12, True, True)
    ui.draw_text(game, stage["trait"], 16, YELLOW, rect.centerx, rect.centery + 18, True)


# 적 또는 보스 탄환을 그립니다.
# projectile_stageN 이미지가 있으면 이미지로, 없으면 원형 탄환과 글자로 표시합니다.
def draw_enemy_projectile(game, projectile):
    image = assets.get_stage_image(game, "projectile")
    rect = projectiles.get_circle_rect(projectile["x"], projectile["y"], projectile["radius"])

    if image:
        scaled = pygame.transform.smoothscale(image, rect.inflate(12, 12).size)
        game.screen.blit(scaled, scaled.get_rect(center=rect.center))
    else:
        pygame.draw.circle(game.screen, (77, 30, 42), rect.center, projectile["radius"])
        pygame.draw.circle(game.screen, projectile["color"], rect.center, projectile["radius"], 2)

    ui.draw_text(game, projectile["word"], max(12, projectile["radius"] // 2), WHITE, rect.centerx, rect.centery, True, True)


# 동료 배를 그립니다.
# 동료 기능이 켜졌을 때 game.allies 리스트에 들어 있는 동료들이 이 함수로 표시됩니다.
def draw_ally(game, ally):
    config = allies.get_ally_type(ally["type"])
    rect = ally["rect"]
    image = game.images.get(config["image"])

    if image:
        scaled = pygame.transform.smoothscale(image, rect.size)
        game.screen.blit(scaled, rect)
        return

    pygame.draw.rect(game.screen, (38, 92, 84), rect, border_radius=8)
    pygame.draw.rect(game.screen, GREEN, rect, 2, border_radius=8)
    pygame.draw.circle(game.screen, WHITE, rect.center, min(rect.width, rect.height) // 5)


# 아이템을 그립니다.
# 아이템 이미지가 없으면 색깔 원으로 대체해서 테스트하기 쉽게 합니다.
def draw_item(game, item):
    config = items.get_item_type(item["type"])
    rect = projectiles.get_circle_rect(item["x"], item["y"], item["radius"])
    image = game.images.get(config["image"])

    if image:
        scaled = pygame.transform.smoothscale(image, rect.inflate(10, 10).size)
        game.screen.blit(scaled, scaled.get_rect(center=rect.center))
        return

    pygame.draw.circle(game.screen, (24, 40, 58), rect.center, item["radius"] + 4)
    pygame.draw.circle(game.screen, config["color"], rect.center, item["radius"])
    pygame.draw.circle(game.screen, WHITE, rect.center, max(4, item["radius"] // 3))
