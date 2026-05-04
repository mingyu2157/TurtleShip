# render.py
# 역할:
#   게임 상태를 화면에 그립니다.
#   실제 위치/체력/탄환 데이터는 다른 파일에서 계산하고,
#   이 파일은 그 데이터를 pygame.draw 또는 이미지 blit으로 보여주는 일만 맡습니다.
#
# 초보자 포인트:
#   update 계열 함수는 "값을 바꾸는 함수"이고, draw 계열 함수는 "화면에 그리는 함수"입니다.
#   둘을 나눠두면 움직임 수정과 화면 디자인 수정을 따로 하기 쉬워집니다.
#
# 공부 순서:
#   draw_screen()에서 상태별 화면 분기를 먼저 보고,
#   draw_game()의 그리는 순서를 보면 어떤 오브젝트가 앞/뒤에 보이는지 이해하기 쉽습니다.
import math

import pygame

import assets
import layout
import obstacles
import projectiles
import ui
import waves
import weather
from settings import RED, WHITE, YELLOW
from stages import get_stage_boss_name, get_stage_display_name, get_stage_trait


# 현재 게임 상태에 맞는 화면을 그립니다.
# menu면 메뉴, play면 게임 화면, gameover/clear면 결과 화면을 보여줍니다.
def draw_screen(game):
    # game_state 하나로 현재 화면 전체를 결정합니다.
    if game.game_state != "story":
        assets.set_story_typing_sound_enabled(game, False)

    if game.game_state == "menu":
        ui.draw_menu(game, draw_sea_background)
    elif game.game_state == "stage_select":
        ui.draw_stage_select(game, draw_sea_background)
    elif game.game_state == "story":
        ui.draw_story(game, draw_sea_background)
    elif game.game_state == "play":
        draw_game(game)
    elif game.game_state == "ability_select":
        ui.draw_basic_ability_select(game, draw_sea_background)
    elif game.game_state == "last_stand_select":
        ui.draw_last_stand_select(game, draw_sea_background)
    elif game.game_state == "augment_select":
        ui.draw_augment_select(game, draw_sea_background)
    elif game.game_state == "stage_result":
        ui.draw_stage_result(game, draw_sea_background)
    elif game.game_state == "gameover":
        ui.draw_end_screen(game, False, draw_sea_background)
    elif game.game_state == "clear":
        ui.draw_end_screen(game, True, draw_sea_background)


# 실제 플레이 화면을 그립니다.
# 배경 -> 탄환/적/보스/전술/플레이어 -> 날씨 -> HUD 순서로 그려서 겹침 순서를 정합니다.
def draw_game(game):
    draw_stage_background(game)

    # 먼저 그린 것은 뒤에 깔리고, 나중에 그린 것은 앞에 덮입니다.
    # 그래서 배경 -> 장애물/탄환/배 -> 날씨/HUD 순서로 그립니다.
    for obstacle in getattr(game, "obstacles", []):
        draw_obstacle(game, obstacle)

    for bullet in game.bullets:
        draw_bullet(game, bullet)

    for enemy in game.enemies:
        draw_enemy(game, enemy)

    if game.boss is not None:
        draw_boss(game)

    for projectile in game.enemy_projectiles:
        draw_enemy_projectile(game, projectile)

    for ship in getattr(game, "hakikjin_ships", []):
        draw_hakikjin_ship(game, ship)

    draw_tanker_guard(game)

    draw_player(game)

    for event in getattr(game, "weather_events", []):
        draw_weather_event(game, event)

    ui.draw_hud(game)

    if game.stage_banner_timer > 0:
        # stage_banner_timer가 남아 있는 동안 스테이지 이름을 잠깐 크게 보여줍니다.
        ui.draw_text(game, get_stage_display_name(game), 36, WHITE, game.pad_width // 2, game.pad_height // 2 - 30, True, True)
        boss_text = f"미니보스: {get_stage_boss_name(game)} / {get_stage_trait(game)}"
        ui.draw_text(game, boss_text, 21, YELLOW, game.pad_width // 2, game.pad_height // 2 + 12, True)

    if game.message_timer > 0:
        ui.draw_text(game, game.message_text, 30, YELLOW, game.pad_width // 2, int(game.pad_height * 0.72), True, True)

    # 부활 플래시: 화면 전체를 밝은 금빛으로 잠깐 물들입니다.
    revive_flash = getattr(game, "revive_flash_timer", 0)
    if revive_flash > 0:
        alpha = int(min(220, 220 * (revive_flash / 0.7)))
        flash_surf = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
        flash_surf.fill((255, 230, 80, alpha))
        game.screen.blit(flash_surf, (0, 0))
        ui.draw_text(game, "부활!", 48, (255, 255, 255), game.pad_width // 2, game.pad_height // 2, True, True)

    if game.paused:
        ui.draw_pause_menu(game)


# 스테이지 이미지가 없을 때 사용하는 기본 바다 배경입니다.
# 간단한 줄무늬와 물결 아크로 바다 느낌을 냅니다.
def draw_sea_background(game):
    game.screen.fill((11, 20, 34))
    # y 좌표마다 색을 조금씩 바꿔서 단색 배경보다 바다 깊이감이 나게 합니다.
    for y in range(0, game.pad_height, 22):
        color = (12, 36 + min(95, y // 8), 62 + min(90, y // 10))
        pygame.draw.rect(game.screen, color, (0, y, game.pad_width, 22))

    # 얇은 반원 arc를 반복해서 간단한 물결을 만듭니다.
    for i in range(14):
        x = (i * 127 + pygame.time.get_ticks() // 18) % (game.pad_width + 80) - 40
        y = int(game.pad_height * 0.28) + i * 37 % max(1, int(game.pad_height * 0.65))
        pygame.draw.arc(game.screen, (52, 117, 150), (x, y, 80, 16), 0, math.pi, 1)


# 실제 게임 공간 위에 반투명 파도 애니메이션을 덧그립니다.
# pygame.time.get_ticks()로 현재 시간을 가져와서 매 프레임 파도 위치가 조금씩 바뀌게 합니다.
# layout.get_play_area()를 사용하므로 배경 이미지의 테두리 장식 부분에는 파도가 그려지지 않습니다.
# waves.py의 현재 파도 방향을 그대로 사용하므로, 화면의 파도와 배들이 밀리는 방향이 맞습니다.
def draw_wave_overlay(game):
    play_area = layout.get_play_area(game)
    if play_area.width <= 0 or play_area.height <= 0:
        return

    state = waves.get_wave_state(game)
    # flow_x/flow_y는 파도가 흘러가는 방향, perp_x/perp_y는 그 방향에 수직인 방향입니다.
    time = state["time"]
    flow_x = state["unit_x"]
    flow_y = state["unit_y"]
    perp_x = state["perp_x"]
    perp_y = state["perp_y"]
    extent = int(math.hypot(play_area.width, play_area.height)) + 120
    wave_layer = pygame.Surface((play_area.width, play_area.height), pygame.SRCALPHA)

    wave_gap = max(34, play_area.height // 14)
    wave_count = extent // wave_gap + 5
    # scroll은 waves.py의 unit_x/unit_y와 같은 방향으로 증가합니다.
    # 따라서 화면에 보이는 파도 흐름과 실제 배가 밀리는 방향이 서로 어긋나지 않습니다.
    scroll = (time * state["speed"] * 0.48) % wave_gap
    center_x = play_area.width / 2
    center_y = play_area.height / 2

    for i in range(wave_count):
        # along은 파도선이 흐름 방향으로 얼마나 떨어져 있는지 나타냅니다.
        along = -extent / 2 + i * wave_gap + scroll
        phase = time * 1.05 + i * 0.54
        wave_center_x = center_x + flow_x * along
        wave_center_y = center_y + flow_y * along

        bright_points = []
        shadow_points = []
        for side in range(-extent, extent + 1, 24):
            # side 방향으로 긴 선을 만들고, sin으로 살짝 흔들어 자연스러운 물결을 만듭니다.
            wiggle = math.sin(side * 0.021 + phase) * 5 + math.sin(side * 0.009 + phase * 1.5) * 3
            x = wave_center_x + perp_x * side + flow_x * wiggle
            y = wave_center_y + perp_y * side + flow_y * wiggle
            bright_points.append((x, y))
            shadow_points.append((x - flow_x * 8, y - flow_y * 8))

        if len(shadow_points) > 1:
            pygame.draw.lines(wave_layer, (4, 20, 42, 28), False, shadow_points, 2)
        if len(bright_points) > 1:
            pygame.draw.lines(wave_layer, (176, 233, 252, 62), False, bright_points, 2)

        if i % 3 == 0 and len(bright_points) > 1:
            foam_points = bright_points[::3]
            pygame.draw.lines(wave_layer, (238, 252, 255, 34), False, foam_points, 1)

    game.screen.blit(wave_layer, play_area.topleft)


# 중앙 모바일 플레이 영역 밖의 좌우 공간을 살짝 어둡게 표시합니다.
# 지금은 비전투 영역이고, 추후 스킬/정보 패널을 넣을 수 있는 자리입니다.
def draw_side_reserve_areas(game):
    play_area = layout.get_play_area(game)
    if play_area.left <= 0 and play_area.right >= game.pad_width:
        return

    shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
    color = (0, 0, 0, 72)
    if play_area.left > 0:
        pygame.draw.rect(shade, color, (0, play_area.top, play_area.left, play_area.height))
    if play_area.right < game.pad_width:
        pygame.draw.rect(shade, color, (play_area.right, play_area.top, game.pad_width - play_area.right, play_area.height))

    game.screen.blit(shade, (0, 0))
    pygame.draw.line(game.screen, (210, 176, 105), (play_area.left, play_area.top), (play_area.left, play_area.bottom), 2)
    pygame.draw.line(game.screen, (210, 176, 105), (play_area.right, play_area.top), (play_area.right, play_area.bottom), 2)


# 현재 스테이지 배경 이미지를 그립니다.
# stageN.png가 있으면 그것을 쓰고, 없으면 기본 바다 배경에 스테이지 색을 살짝 입힙니다.
# 마지막에는 항상 draw_wave_overlay()를 호출해서 바다가 찰랑이는 느낌을 더합니다.
def draw_stage_background(game):
    image = assets.get_stage_image(game, "stage")
    if image:
        # 배경 이미지가 있으면 화면을 덮도록 확대/축소해서 그립니다.
        layout.draw_cover(game, image)
        shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 34))
        game.screen.blit(shade, (0, 0))
        draw_side_reserve_areas(game)
        draw_wave_overlay(game)
        draw_stage_darkness(game)
        return

    # 배경 이미지가 없을 때는 기본 바다 배경과 스테이지 색상 tint를 사용합니다.
    draw_sea_background(game)
    stage = game.current_stage()
    tint = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
    color = stage["color"]
    tint.fill((color[0], color[1], color[2], 42))
    game.screen.blit(tint, (0, 0))
    draw_side_reserve_areas(game)
    draw_wave_overlay(game)
    draw_stage_darkness(game)


# 노량해전처럼 어두운 새벽 바다를 표현해야 하는 스테이지는 배경 위에 어둠 레이어를 덮습니다.
# 적과 플레이어는 이 함수 뒤에 그려지므로 완전히 안 보이지 않고, 바다만 더 어둡게 깔립니다.
def draw_stage_darkness(game):
    alpha = game.current_stage().get("darkness_alpha", 0)
    if alpha <= 0:
        return

    play_area = layout.get_play_area(game)
    darkness = pygame.Surface(play_area.size, pygame.SRCALPHA)
    darkness.fill((0, 0, 0, alpha))
    game.screen.blit(darkness, play_area.topleft)


# 플레이어 배를 그립니다.
# player.png가 있으면 이미지를 쓰고, 없으면 기본 삼각형 도형으로 대체합니다.
def draw_player(game):
    rect = game.player["rect"]
    image = game.images.get("player")

    if image:
        # 플레이어는 매 프레임 같은 크기로 그려지므로 확대 이미지를 재사용합니다.
        scaled = assets.get_scaled_image(game, image, rect.size)
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
    # 탄환은 원형 판정이지만 이미지는 사각형으로 그리므로, 원을 감싸는 rect를 기준으로 배치합니다.
    rect = projectiles.get_circle_rect(bullet["x"], bullet["y"], bullet["radius"])

    if image:
        padding = bullet.get("image_padding", 10)
        # 탄환 이미지는 같은 반지름으로 많이 반복되므로 캐시 효과가 큽니다.
        scaled = assets.get_scaled_image(game, image, rect.inflate(padding, padding).size)
        game.screen.blit(scaled, scaled.get_rect(center=rect.center))
        return

    pygame.draw.circle(game.screen, bullet["color"], rect.center, bullet["radius"])
    pygame.draw.circle(game.screen, WHITE, rect.center, max(2, bullet["radius"] - 4))


# 일반 적 배를 그립니다.
# 적군 배 이름은 화면에 표시하지 않고, 배 이미지와 체력바만 보여줍니다.
def draw_enemy(game, enemy):
    rect = enemy["rect"]
    image = assets.get_stage_image(game, "enemy")

    if image:
        # 적 이미지는 같은 크기 범위가 반복되므로 캐시에서 꺼내 씁니다.
        scaled = assets.get_scaled_image(game, image, rect.size)
        game.screen.blit(scaled, rect)
        if enemy.get("is_suicide"):
            pygame.draw.rect(game.screen, RED, rect.inflate(6, 6), 2, border_radius=6)
    else:
        pygame.draw.rect(game.screen, (82, 40, 50), rect, border_radius=7)
        pygame.draw.rect(game.screen, RED, rect, 2, border_radius=7)

    hp_rect = pygame.Rect(rect.left + 8, rect.bottom + 4, rect.width - 16, 5)
    # 체력바는 어두운 배경을 먼저 그리고, 남은 체력 비율만큼 밝은 막대를 채웁니다.
    pygame.draw.rect(game.screen, (42, 34, 38), hp_rect, border_radius=2)
    fill = hp_rect.copy()
    fill.width = int(hp_rect.width * max(0, enemy["hp"] / enemy["maxHp"]))
    pygame.draw.rect(game.screen, YELLOW, fill, border_radius=2)


# 랜덤 지형지물을 그립니다.
# 사라지기 직전에는 obstacles.get_draw_alpha() 값으로 깜빡이게 합니다.
def draw_obstacle(game, obstacle):
    rect = obstacle["rect"]
    image = game.images.get(obstacle["image"])
    alpha = obstacles.get_draw_alpha(obstacle)

    if image:
        # 지형지물도 랜덤 크기지만 반복되는 값은 캐시로 재사용합니다.
        scaled = assets.get_scaled_image(game, image, rect.size)
        if alpha < 255:
            scaled = scaled.copy()
            scaled.set_alpha(alpha)
        game.screen.blit(scaled, rect)
        return

    color = (115, 108, 94, alpha)
    fallback = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(fallback, color, fallback.get_rect())
    game.screen.blit(fallback, rect)


# 랜덤 날씨 효과를 그립니다.
# 투명도는 weather.py의 WEATHER_TYPES 안 alpha 값으로 조절합니다.
def draw_weather_event(game, event):
    rect = event["rect"]
    config = weather.WEATHER_TYPES[event["kind"]]
    image = game.images.get(event["image"])
    alpha = weather.get_draw_alpha(event)

    if image:
        # 날씨 이미지는 투명도만 자주 바뀌므로 크기 변환 결과는 캐시하고 alpha만 복사본에 적용합니다.
        scaled = assets.get_scaled_image(game, image, rect.size)
        scaled = scaled.copy()
        scaled.set_alpha(alpha)
        game.screen.blit(scaled, rect)
        return

    fallback = pygame.Surface(rect.size, pygame.SRCALPHA)
    color = config["fallback_color"]
    fallback.fill((color[0], color[1], color[2], alpha))
    game.screen.blit(fallback, rect)


# 미니보스를 그립니다.
# 보스 이름과 특징 문구도 같이 표시합니다.
def draw_boss(game):
    stage = game.current_stage()
    rect = game.boss["rect"]
    image = assets.get_stage_image(game, "boss")

    if image:
        # 보스 이미지는 크기가 고정이라 매 프레임 새로 스케일하지 않습니다.
        scaled = assets.get_scaled_image(game, image, rect.size)
        game.screen.blit(scaled, rect)
    else:
        pygame.draw.rect(game.screen, (62, 37, 48), rect, border_radius=10)
        pygame.draw.rect(game.screen, stage["color"], rect, 4, border_radius=10)
        pygame.draw.circle(game.screen, RED, (rect.centerx, rect.centery), min(rect.width, rect.height) // 4)

    ui.draw_text(game, game.boss.get("name", get_stage_boss_name(game)), 22, WHITE, rect.centerx, rect.centery - 12, True, True)
    ui.draw_text(game, game.boss.get("trait", get_stage_trait(game)), 16, YELLOW, rect.centerx, rect.centery + 18, True)


# 적 또는 보스 탄환을 그립니다.
# 적군 총알 이름은 화면에 표시하지 않고, 탄환 이미지만 보여줍니다.
def draw_enemy_projectile(game, projectile):
    image = assets.get_stage_image(game, "projectile")
    rect = projectiles.get_circle_rect(projectile["x"], projectile["y"], projectile["radius"])

    if image:
        # 1단계 화살 이미지는 실제 판정보다 조금 크게 그려야 화면에서 화살로 읽힙니다.
        # 충돌 판정은 projectile["radius"] 그대로라서 이미지가 커져도 난이도가 갑자기 올라가지 않습니다.
        if game.stage_index == 0:
            draw_rect = rect.inflate(34, 34)
        else:
            draw_rect = rect.inflate(12, 12)
        # 적 탄환 이미지도 같은 크기가 많이 반복되므로 캐시를 사용합니다.
        scaled = assets.get_scaled_image(game, image, draw_rect.size)
        game.screen.blit(scaled, scaled.get_rect(center=rect.center))
    else:
        pygame.draw.circle(game.screen, (77, 30, 42), rect.center, projectile["radius"])
        pygame.draw.circle(game.screen, projectile["color"], rect.center, projectile["radius"], 2)


# 학익진 스킬로 잠깐 등장하는 12척의 전술선을 그립니다.
# 저장되는 배가 아니라 스킬 지속시간 동안만 화면에 보입니다.
def draw_hakikjin_ship(game, ship):
    rect = ship["rect"]
    image = game.images.get("skill_hakikjin_ship")

    if image:
        scaled = assets.get_scaled_image(game, image, rect.size)
        game.screen.blit(scaled, rect)
        return

    pygame.draw.rect(game.screen, (24, 39, 48), rect, border_radius=6)
    pygame.draw.rect(game.screen, YELLOW, rect, 2, border_radius=6)
    pygame.draw.line(game.screen, WHITE, rect.midbottom, rect.midtop, 2)


# 몸빵 증강으로 발동하는 방패선을 그립니다.
# 이 Rect는 combat.py에서 적 탄환과 적 배를 막는 충돌 판정에도 그대로 사용합니다.
def draw_tanker_guard(game):
    rect = getattr(game, "tanker_guard_rect", None)
    if rect is None or getattr(game, "tanker_guard_timer", 0) <= 0:
        return

    image = game.images.get("skill_tanker_guard")
    if image:
        scaled = assets.get_scaled_image(game, image, rect.size)
        game.screen.blit(scaled, rect)
        return

    guard = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(guard, (38, 93, 146, 168), guard.get_rect(), border_radius=8)
    pygame.draw.rect(guard, (180, 230, 255, 230), guard.get_rect(), 3, border_radius=8)
    game.screen.blit(guard, rect)
