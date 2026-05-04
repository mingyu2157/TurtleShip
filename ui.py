# ui.py
# 역할:
#   글자 출력, 시작 화면, 결과 화면, HUD 같은 사용자 인터페이스를 그립니다.
#   게임 오브젝트 자체는 render.py가 그리고, 점수/체력/버튼 같은 정보 화면은 이 파일이 맡습니다.
#
# 초보자 포인트:
#   한글을 pygame 기본 폰트로 그리면 깨질 수 있어서,
#   macOS/Windows/Linux에서 쓸 수 있는 한글 폰트를 순서대로 찾아 사용합니다.
#
# 공부 순서:
#   draw_text()는 모든 글자 출력의 기본 함수입니다.
#   draw_menu(), draw_story(), draw_hud()처럼 화면 종류별 함수가 이 draw_text()를 재사용합니다.
from pathlib import Path
from time import sleep

import pygame

import augments
import assets
import campaign
import layout
import skills
import story
from settings import BLACK, BLUE, GRAY, GREEN, RED, WHITE, YELLOW
from stages import get_kills_to_boss, get_stage_boss_name, get_stage_display_name, get_stage_phase


# 스토리 화면에서 1초에 몇 글자씩 써질지 정합니다.
# 숫자가 낮을수록 일기가 천천히 쓰이는 느낌이 강해집니다.
STORY_TYPING_CHARS_PER_SECOND = 24

# 일시정지 메뉴 버튼 순서입니다. input.py도 같은 순서를 사용합니다.
PAUSE_MENU_ITEMS = ("계속하기", "재시작", "나가기")

# 새 일기지 이미지 위에 올릴 진한 먹색입니다.
DIARY_INK = (23, 15, 9)
# 본문 보조 글자도 배경과 섞이지 않게 기존보다 어둡게 둡니다.
DIARY_MUTED_INK = (43, 28, 17)
# 날짜와 안내 문구에 쓰는 갈색 강조색입니다.
DIARY_ACCENT = (89, 36, 18)
# 일기지 이미지가 어두운 경우 글자 뒤에 깔아줄 밝은 종이색입니다.
DIARY_TEXT_BACK = (255, 246, 220, 158)


# 사용할 폰트를 가져옵니다.
# 같은 크기/굵기의 폰트는 game.fonts에 저장해두고 다시 재사용해서 성능을 아낍니다.
def get_font(game, size, bold=False):
    key = (size, bold)
    if key in game.fonts:
        # 이미 만든 폰트는 다시 만들지 않고 캐시에서 꺼내 씁니다.
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
            # 한글 지원 폰트를 찾으면 pygame Font 객체로 만들어 저장합니다.
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
    # font.render()는 글자를 pygame Surface 이미지로 바꿉니다.
    image = font.render(text, True, color)
    rect = image.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    game.screen.blit(image, rect)
    return rect


# 긴 한글 문장을 지정한 너비 안에서 여러 줄로 나눕니다.
# 먼저 띄어쓰기 단위로 자르고, 그래도 너무 길면 글자 단위로 한 번 더 나눕니다.
def wrap_text(font, text, max_width):
    words = text.split(" ")
    lines = []
    current = ""

    for word in words:
        # 현재 줄에 단어를 붙여보고 max_width 안에 들어가면 같은 줄에 둡니다.
        candidate = word if not current else f"{current} {word}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)
            current = ""

        if font.size(word)[0] <= max_width:
            current = word
            continue

        piece = ""
        for char in word:
            # 띄어쓰기 없는 긴 단어도 화면 밖으로 나가지 않게 글자 단위로 나눕니다.
            candidate = piece + char
            if font.size(candidate)[0] <= max_width:
                piece = candidate
            else:
                if piece:
                    lines.append(piece)
                piece = char
        current = piece

    if current:
        lines.append(current)

    return lines


# 지정한 사각형 안에 여러 줄 문장을 그립니다.
# 반환값은 마지막 줄 아래 y 좌표라서 다음 문장을 이어 그릴 때 사용할 수 있습니다.
def draw_wrapped_text(game, text, size, color, rect, line_gap=8, bold=False):
    font = get_font(game, size, bold)
    y = rect.top
    line_height = font.get_linesize()

    for line in wrap_text(font, text, rect.width):
        image = font.render(line, True, color)
        game.screen.blit(image, (rect.left, y))
        y += line_height + line_gap

    return y


# 지정한 줄 수까지만 줄바꿈 문장을 그립니다.
# 증강 이름처럼 긴 문장이 카드 밖으로 삐져나가지 않게 마지막 줄은 ...으로 줄입니다.
def draw_wrapped_text_limited(game, text, size, color, rect, line_gap=6, bold=False, max_lines=2):
    font = get_font(game, size, bold)
    lines = wrap_text(font, text, rect.width)
    visible_lines = lines[:max_lines]

    if len(lines) > max_lines and visible_lines:
        visible_lines[-1] = trim_text_to_width(font, visible_lines[-1], rect.width)

    y = rect.top
    for line in visible_lines:
        if y + font.get_linesize() > rect.bottom:
            break
        image = font.render(line, True, color)
        game.screen.blit(image, (rect.left, y))
        y += font.get_linesize() + line_gap

    return y


# 글자가 지정 너비를 넘으면 뒤를 잘라 ...을 붙입니다.
def trim_text_to_width(font, text, max_width):
    suffix = "..."
    if font.size(text)[0] <= max_width:
        return text

    while text and font.size(text + suffix)[0] > max_width:
        text = text[:-1]

    return text + suffix if text else suffix


# 지정한 사각형 안에 이미지를 꽉 채워 그립니다.
# 이미지 비율은 유지하고, 넘치는 부분은 잘라서 카드/패널 안에 빈 공간이 생기지 않게 합니다.
def draw_image_cover_in_rect(game, image, rect):
    if image is None:
        return

    # scale은 이미지가 rect를 완전히 덮기 위해 필요한 확대/축소 비율입니다.
    scale = max(rect.width / image.get_width(), rect.height / image.get_height())
    # int()는 소수점을 버리므로, 1픽셀 부족해서 subsurface가 실패하지 않게 +1을 붙입니다.
    scaled_width = max(rect.width, int(image.get_width() * scale) + 1)
    scaled_height = max(rect.height, int(image.get_height() * scale) + 1)
    # 같은 카드/패널 이미지는 매 프레임 같은 크기로 쓰이므로 확대 결과를 캐시합니다.
    scaled = assets.get_scaled_image(game, image, (scaled_width, scaled_height))

    # crop_rect는 확대된 이미지 가운데에서 rect 크기만큼 잘라낼 영역입니다.
    crop_rect = pygame.Rect(0, 0, rect.width, rect.height)
    crop_rect.center = (scaled_width // 2, scaled_height // 2)
    cropped = scaled.subsurface(crop_rect).copy()
    game.screen.blit(cropped, rect)


# 지정한 사각형 안에 이미지를 전부 보이게 맞춰 그립니다.
# cover와 달리 이미지를 자르지 않아서 보스 초상처럼 전체 형태가 보여야 할 때 사용합니다.
def draw_image_contain_in_rect(game, image, rect):
    if image is None or rect.width <= 0 or rect.height <= 0:
        return

    # scale은 이미지 전체가 rect 안에 들어가기 위해 필요한 확대/축소 비율입니다.
    scale = min(rect.width / image.get_width(), rect.height / image.get_height())
    # 너무 작은 rect에서도 1픽셀 이상은 나오도록 최소 크기를 보장합니다.
    scaled_width = max(1, int(image.get_width() * scale))
    scaled_height = max(1, int(image.get_height() * scale))
    # 같은 보스 초상은 매 프레임 같은 크기로 반복되므로 캐시된 확대 이미지를 재사용합니다.
    scaled = assets.get_scaled_image(game, image, (scaled_width, scaled_height))
    # get_rect(center=...)를 쓰면 남는 여백 안에서 이미지가 자연스럽게 가운데 정렬됩니다.
    game.screen.blit(scaled, scaled.get_rect(center=rect.center))


# 스토리 페이지가 바뀌었는지 확인하기 위한 키를 만듭니다.
# 이 값이 달라지면 새 일기 페이지이므로 타자 애니메이션을 처음부터 다시 시작합니다.
def get_story_typing_key(game):
    return (
        getattr(game, "story_id", "stage"),
        getattr(game, "stage_index", 0),
        getattr(game, "stage_phase", 0),
        getattr(game, "story_page_index", 0),
    )


# 타자 애니메이션으로 천천히 보여줄 문장 묶음을 만듭니다.
# 제목과 날짜는 바로 보이고, 인용문과 본문만 서서히 쓰이게 합니다.
def get_story_typing_blocks(data):
    blocks = [data.get("quote", "")]
    blocks.extend(data.get("lines", []))
    return [block for block in blocks if block]


# 현재 시간 기준으로 어디까지 써졌는지 계산해 각 문장을 잘라서 돌려줍니다.
def get_visible_story_blocks(game, data):
    typing_key = get_story_typing_key(game)
    if getattr(game, "story_typing_key", None) != typing_key:
        game.story_typing_key = typing_key
        game.story_typing_started_ms = pygame.time.get_ticks()
        game.story_typing_force_complete = False
        game.story_typing_complete = False

    blocks = get_story_typing_blocks(data)
    total_characters = sum(len(block) for block in blocks)
    if total_characters <= 0:
        game.story_typing_complete = True
        return blocks

    if getattr(game, "story_typing_force_complete", False):
        visible_characters = total_characters
    else:
        elapsed_seconds = max(0, pygame.time.get_ticks() - getattr(game, "story_typing_started_ms", 0)) / 1000
        visible_characters = int(elapsed_seconds * STORY_TYPING_CHARS_PER_SECOND)

    game.story_typing_complete = visible_characters >= total_characters
    remaining = max(0, min(total_characters, visible_characters))
    visible_blocks = []
    cursor_added = False

    for block in blocks:
        if remaining >= len(block):
            visible_blocks.append(block)
            remaining -= len(block)
            continue

        piece = block[:remaining]
        if not game.story_typing_complete and not cursor_added:
            piece += "|"
            cursor_added = True
        visible_blocks.append(piece)
        remaining = 0

    if not game.story_typing_complete and not cursor_added and visible_blocks:
        visible_blocks[-1] += "|"

    return visible_blocks


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
# main_menu.png 위에 실제 클릭 가능한 캠페인/점수 경쟁 버튼을 덧그립니다.
def draw_menu(game, draw_sea_background):
    menu_image = game.images.get("main_menu")
    if menu_image:
        layout.draw_cover(game, menu_image)
    else:
        draw_sea_background(game)
        draw_text(game, "PyShooting", 52, WHITE, game.pad_width // 2, int(game.pad_height * 0.28), True, True)
        draw_text(game, "거북선 전쟁", 26, YELLOW, game.pad_width // 2, int(game.pad_height * 0.36), True, True)

    campaign_rect, score_rect = layout.get_menu_button_rects(game)
    mouse_pos = pygame.mouse.get_pos()
    selected_index = getattr(game, "menu_select_index", 0)
    draw_menu_mode_button(game, campaign_rect, "이순신 시뮬레이션", selected_index == 0, campaign_rect.collidepoint(mouse_pos))
    draw_menu_mode_button(game, score_rect, "점수 경쟁", selected_index == 1, score_rect.collidepoint(mouse_pos))


# 메인 메뉴의 버튼 하나를 그립니다.
# selected는 키보드로 선택된 상태이고, hovered는 마우스가 올라간 상태입니다.
def draw_menu_mode_button(game, rect, label, selected, hovered):
    start_button_image = game.images.get("menu_start_button") if label == "이순신 시뮬레이션" else None
    if start_button_image:
        # 제공받은 "게임 시작" 버튼 이미지를 캠페인 시작 버튼에 그대로 사용합니다.
        # 이미지 안에 글자가 있으므로 별도 텍스트는 덮어쓰지 않습니다.
        draw_image_cover_in_rect(game, start_button_image, rect)
        if selected or hovered:
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            overlay.fill((255, 224, 145, 34 if hovered else 22))
            game.screen.blit(overlay, rect)
        pygame.draw.rect(game.screen, (255, 225, 137), rect, 4 if selected or hovered else 2, border_radius=8)
        return

    base_color = (130, 80, 34)
    hover_color = (165, 103, 45)
    selected_color = (176, 111, 48)
    button_color = selected_color if selected else hover_color if hovered else base_color
    border_color = (255, 225, 137) if selected or hovered else (255, 209, 117)

    pygame.draw.rect(game.screen, button_color, rect, border_radius=8)
    pygame.draw.rect(game.screen, border_color, rect, 4 if selected else 3, border_radius=8)
    draw_text(game, label, max(20, rect.height // 3), WHITE, rect.centerx, rect.centery, True, True)


# 플레이 화면 위에 올라오는 일시정지 메뉴입니다.
# 전투 장면을 흐리게 덮고, 검은 패널과 금색 선으로 제공된 예시 이미지와 비슷한 분위기를 냅니다.
def draw_pause_menu(game):
    shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 164))
    game.screen.blit(shade, (0, 0))

    panel, buttons = layout.get_pause_menu_layout(game)
    panel_surface = pygame.Surface(panel.size, pygame.SRCALPHA)
    panel_surface.fill((7, 10, 12, 238))
    game.screen.blit(panel_surface, panel)

    gold = (229, 169, 55)
    bright_gold = (255, 217, 110)
    dark_gold = (126, 75, 18)
    pygame.draw.rect(game.screen, dark_gold, panel.inflate(10, 10), 3, border_radius=8)
    pygame.draw.rect(game.screen, bright_gold, panel, 2, border_radius=8)
    pygame.draw.rect(game.screen, dark_gold, panel.inflate(-18, -18), 1, border_radius=5)

    crest_y = panel.top + 28
    pygame.draw.circle(game.screen, (14, 15, 15), (panel.centerx, crest_y), 38)
    pygame.draw.circle(game.screen, bright_gold, (panel.centerx, crest_y), 38, 2)
    pygame.draw.circle(game.screen, dark_gold, (panel.centerx, crest_y), 27, 1)
    draw_text(game, "龍", 30, gold, panel.centerx, crest_y, True, True)

    title_size = 54 if panel.width >= 500 else 43
    title_y = panel.top + max(88, panel.height // 5)
    draw_text(game, "일시정지", title_size, bright_gold, panel.centerx, title_y, True, True)
    line_y = title_y + 54
    pygame.draw.line(game.screen, dark_gold, (panel.left + 42, line_y), (panel.right - 42, line_y), 1)
    pygame.draw.line(game.screen, bright_gold, (panel.centerx - 36, line_y), (panel.centerx + 36, line_y), 2)

    mouse_pos = pygame.mouse.get_pos()
    selected_index = getattr(game, "pause_select_index", 0)
    for index, rect in enumerate(buttons):
        hovered = rect.collidepoint(mouse_pos)
        selected = index == selected_index
        draw_pause_button(game, rect, PAUSE_MENU_ITEMS[index], selected, hovered)


# 일시정지 메뉴 버튼 하나를 그립니다.
def draw_pause_button(game, rect, label, selected, hovered):
    active = selected or hovered
    fill = (15, 16, 17, 238) if not active else (28, 22, 12, 248)
    border = (255, 204, 76) if active else (180, 119, 31)
    inner_border = (112, 69, 19)

    button_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    button_surface.fill(fill)
    game.screen.blit(button_surface, rect)
    pygame.draw.rect(game.screen, border, rect, 3 if active else 2, border_radius=4)
    pygame.draw.rect(game.screen, inner_border, rect.inflate(-12, -12), 1, border_radius=3)

    accent_y = rect.centery
    pygame.draw.circle(game.screen, border, (rect.left + 32, accent_y), 4)
    pygame.draw.line(game.screen, border, (rect.left + 18, accent_y), (rect.left + 46, accent_y), 1)
    pygame.draw.circle(game.screen, border, (rect.right - 32, accent_y), 4)
    pygame.draw.line(game.screen, border, (rect.right - 46, accent_y), (rect.right - 18, accent_y), 1)
    draw_text(game, label, max(27, rect.height // 2), (255, 219, 128), rect.centerx, rect.centery, True, True)


# 현재 전투에서 레벨업했을 때 3개 증강 선택지를 보여줍니다.
# 증강은 저장되지 않고 현재 캠페인 스테이지/점수 경쟁 한 판 안에서만 유지됩니다.
def draw_augment_select(game, draw_sea_background):
    augment_background = game.images.get("argu_background")
    if augment_background:
        # contain 방식으로 그려서 이미지 가장자리가 쟘리지 않게 합니다.
        game.screen.fill((8, 8, 12))
        draw_image_contain_in_rect(game, augment_background, game.screen.get_rect())
    else:
        draw_sea_background(game)
        shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 168))
        game.screen.blit(shade, (0, 0))

    choices = getattr(game, "augment_choices", [])
    rects = layout.get_augment_choice_rects(game, len(choices))
    mouse_pos = pygame.mouse.get_pos()
    selected_index = get_safe_choice_index(game, len(choices))
    for index, rect in enumerate(rects):
        augment_id = choices[index]
        data = augments.AUGMENTS[augment_id]
        current_stack = getattr(game, "augment_stacks", {}).get(augment_id, 0)
        hovered = rect.collidepoint(mouse_pos)
        draw_augment_card(game, rect, index, augment_id, data, current_stack, hovered, index == selected_index)


# 1단계 첫 전투 전 기본 능력 선택 화면을 그립니다.
# argu_background 이미지를 배경으로 쓰고 증강 카드 스타일로 선택지를 보여줍니다.
def draw_basic_ability_select(game, draw_sea_background):
    augment_background = game.images.get("basic_background") or game.images.get("argu_background")
    if augment_background:
        game.screen.fill((8, 8, 12))
        draw_image_contain_in_rect(game, augment_background, game.screen.get_rect())
    else:
        draw_sea_background(game)
        shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 168))
        game.screen.blit(shade, (0, 0))

    choices = getattr(game, "basic_ability_choices", [])
    rects = layout.get_augment_choice_rects(game, len(choices))
    mouse_pos = pygame.mouse.get_pos()
    selected_index = get_safe_choice_index(game, len(choices))
    for index, rect in enumerate(rects):
        choice = choices[index]
        image_key = choice.get("image_key") or choice.get("id", "")
        data = {
            "title": choice.get("title", ""),
            "description": choice.get("description", ""),
            "max_stack": 1,
        }
        hovered = rect.collidepoint(mouse_pos)
        draw_augment_card(game, rect, index, image_key, data, 0, hovered, index == selected_index)


# 4단계 명량해전 직전 생즉사 사즉생 방향을 고르는 화면입니다.
# argu_background를 배경으로 하고, live.png(필사즉생)/die.png(필생즉사) 카드로 선택합니다.
def draw_last_stand_select(game, draw_sea_background):
    augment_background = game.images.get("argu_background")
    if augment_background:
        game.screen.fill((8, 8, 12))
        draw_image_contain_in_rect(game, augment_background, game.screen.get_rect())
    else:
        draw_sea_background(game)
        shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 178))
        game.screen.blit(shade, (0, 0))

    choices = skills.LAST_STAND_CHOICES
    rects = layout.get_augment_choice_rects(game, len(choices))
    mouse_pos = pygame.mouse.get_pos()
    selected_index = get_safe_choice_index(game, len(choices))
    for index, rect in enumerate(rects):
        choice = choices[index]
        image_key = choice.get("image_key", choice.get("id", ""))
        hovered = rect.collidepoint(mouse_pos)
        data = {
            "title": choice["title"],
            "description": choice["description"],
            "max_stack": 1,
        }
        draw_augment_card(game, rect, index, image_key, data, 0, hovered, index == selected_index)


# 선택지 개수 안에서 현재 키보드 선택 위치를 안전하게 가져옵니다.
# 화면을 그리는 도중 선택지 수가 바뀌어도 인덱스 오류가 나지 않게 막습니다.
def get_safe_choice_index(game, choice_count):
    if choice_count <= 0:
        game.choice_select_index = 0
        return 0

    game.choice_select_index = max(0, min(getattr(game, "choice_select_index", 0), choice_count - 1))
    return game.choice_select_index


# 증강 카드 하나를 그립니다.
# title/description은 augments.py의 AUGMENTS 딕셔너리에서 가져옵니다.
def draw_augment_card(game, rect, index, augment_id, data, current_stack, hovered, selected=False):
    # 마우스 hover와 키보드 selected를 같은 강조 계열로 보여주어 현재 선택 위치를 한눈에 알 수 있게 합니다.
    active = hovered or selected
    image = game.images.get(augment_id)

    if image is None:
        return

    image_box = rect.inflate(164, 194)
    if active:
        image_box.inflate_ip(56, 72)
    image_box.center = rect.center

    draw_image_contain_in_rect(game, image, image_box)


# 캠페인 스테이지 선택 화면을 그립니다.
# 잠긴 스테이지는 어둡게 보이고, 열린 스테이지를 클릭/선택하면 브리핑 화면으로 넘어갑니다.
def draw_stage_select(game, draw_sea_background):
    # stage_select_background.png가 있으면 선택 화면 전용 배경으로 사용합니다.
    stage_select_background = assets.get_stage_select_image(game, "background")
    if stage_select_background:
        layout.draw_cover(game, stage_select_background)
    else:
        draw_sea_background(game)

    # 바다 배경 위에 살짝 어두운 막을 깔아 카드와 글자가 잘 보이게 합니다.
    shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 118))
    game.screen.blit(shade, (0, 0))

    # stage_select_panel.png는 나중에 전체 선택창 디자인 이미지를 얹고 싶을 때 쓰는 예비 칸입니다.
    stage_select_panel = assets.get_stage_select_image(game, "panel")
    if stage_select_panel:
        layout.draw_cover(game, stage_select_panel)

    title_y = max(42, int(game.pad_height * 0.1))
    draw_text(game, "해전 선택", 44 if game.pad_width >= 720 else 34, WHITE, game.pad_width // 2, title_y, True, True)
    progress = f"진행도 {campaign.get_cleared_stage_count(game)}/{len(story.STAGE_STORIES)}"
    draw_text(game, progress, 18, YELLOW, game.pad_width // 2, title_y + 48, True, True)

    rects = layout.get_stage_select_card_rects(game, len(story.STAGE_STORIES))
    selected_index = getattr(game, "stage_select_index", 0)
    mouse_pos = pygame.mouse.get_pos()

    for index, rect in enumerate(rects):
        data = story.STAGE_STORIES[index]
        unlocked = campaign.is_stage_unlocked(game, index)
        cleared = campaign.is_stage_cleared(game, index)
        selected = index == selected_index
        hovered = rect.collidepoint(mouse_pos)
        draw_stage_card(game, rect, index, data, unlocked, cleared, selected, hovered)

    if game.message_timer > 0 and game.message_text:
        message_rect = pygame.Rect(0, 0, min(720, int(game.pad_width * 0.84)), 46)
        message_rect.center = (game.pad_width // 2, game.pad_height - 64)
        message_layer = pygame.Surface(message_rect.size, pygame.SRCALPHA)
        message_layer.fill((20, 18, 16, 210))
        game.screen.blit(message_layer, message_rect)
        pygame.draw.rect(game.screen, (226, 186, 96), message_rect, 1, border_radius=8)
        draw_text(game, game.message_text, 18, YELLOW, message_rect.centerx, message_rect.centery, True, True)


# 스테이지 선택 화면의 카드 하나를 그립니다.
# unlocked/cleared/selected 값을 색과 문구로 바꿔서 상태를 한눈에 볼 수 있게 합니다.
def draw_stage_card(game, rect, index, data, unlocked, cleared, selected, hovered):
    if unlocked:
        fill = (29, 43, 57, 226) if not hovered else (39, 56, 74, 236)
        border = (255, 213, 92) if selected else (172, 141, 81)
        title_color = WHITE
        sub_color = GRAY
        status = "완료" if cleared else "출전 가능"
        status_color = GREEN if cleared else YELLOW
    else:
        fill = (18, 20, 24, 218)
        border = (91, 94, 104) if not selected else RED
        title_color = (128, 132, 145)
        sub_color = (104, 108, 119)
        status = "잠김"
        status_color = RED

    card = pygame.Surface(rect.size, pygame.SRCALPHA)
    card.fill(fill)
    game.screen.blit(card, rect)
    pygame.draw.rect(game.screen, border, rect, 3 if selected else 1, border_radius=8)

    # stage_select_stage1.png 같은 카드 전용 이미지가 있으면 카드 상단 썸네일로 사용합니다.
    card_image = assets.get_stage_select_image(game, "card", index)
    thumbnail_rect = pygame.Rect(rect.left + 10, rect.top + 10, rect.width - 20, max(42, int(rect.height * 0.34)))
    if card_image:
        draw_image_cover_in_rect(game, card_image, thumbnail_rect)
        tint = pygame.Surface(thumbnail_rect.size, pygame.SRCALPHA)
        tint.fill((0, 0, 0, 68 if unlocked else 150))
        game.screen.blit(tint, thumbnail_rect)
        pygame.draw.rect(game.screen, border, thumbnail_rect, 1, border_radius=6)

    inner_x = rect.left + 18
    y = thumbnail_rect.bottom + 12 if card_image else rect.top + 18
    draw_text(game, f"{index + 1}단계", 18, status_color, inner_x, y, False, True)
    draw_text(game, status, 15, status_color, rect.right - 74, y + 1, False, True)
    y += 36

    title_font_size = 24 if rect.width >= 200 else 21
    draw_text(game, data["title"], title_font_size, title_color, inner_x, y, False, True)
    y += 34
    date_rect = pygame.Rect(inner_x, y, rect.width - 36, 44)
    draw_wrapped_text(game, data["date"], 15, sub_color, date_rect, 2, True)

    footer_y = rect.bottom - 44
    if unlocked:
        footer = "선택 후 Enter"
    else:
        footer = "이전 해전 클리어 필요"
    draw_text(game, footer, 14, sub_color, inner_x, footer_y, False, True)

    # 잠긴 카드는 자물쇠 느낌의 작은 사각 아이콘을 그립니다.
    if not unlocked:
        lock_rect = pygame.Rect(rect.centerx - 12, rect.bottom - 74, 24, 18)
        pygame.draw.rect(game.screen, (93, 96, 108), lock_rect, border_radius=4)
        pygame.draw.arc(game.screen, (93, 96, 108), (lock_rect.left + 3, lock_rect.top - 13, 18, 22), 3.14, 6.28, 3)


# 난중일기/해전 브리핑 화면을 그립니다.
# 실제 문장 데이터는 story.py에 있고, 여기서는 보기 좋게 배치만 합니다.
def draw_story(game, draw_sea_background):
    # story_stage1_page1.png, story_stage1.png, story_background.png 순서로 스토리 배경을 찾습니다.
    if getattr(game, "story_id", "intro") == "intro":
        story_background = assets.get_story_image(game, "intro")
    else:
        story_background = assets.get_story_image(game, "background")

    if story_background:
        layout.draw_cover(game, story_background)
    else:
        draw_sea_background(game)

    # 배경 위에 어두운 반투명 막을 덮어 글자가 잘 보이게 합니다.
    shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 120))
    game.screen.blit(shade, (0, 0))

    data = story.get_current_story(game)
    diary_image = game.images.get("story_diary_horizontal")
    # 가로 일기지 이미지가 있으면 더 넓은 편지지 비율로 패널을 잡습니다.
    # 없으면 기존 어두운 패널 크기를 사용합니다.
    if diary_image:
        panel_width = min(1180, int(game.pad_width * 0.88))
        panel_height = min(660, int(game.pad_height * 0.74))
    else:
        # 화면이 너무 커져도 글 읽는 폭이 과하게 넓어지지 않도록 최대 크기를 제한합니다.
        panel_width = min(860, int(game.pad_width * 0.82))
        panel_height = min(620, int(game.pad_height * 0.78))
    panel = pygame.Rect(0, 0, panel_width, panel_height)
    panel.center = (game.pad_width // 2, game.pad_height // 2)

    # story_diary_horizontal.png가 있으면 스테이지 시작 전 가로 일기지로 사용합니다.
    # story_paper.png는 그 이미지가 없을 때 쓰는 예비 패널입니다.
    paper_image = assets.get_story_image(game, "paper")
    if diary_image:
        draw_image_cover_in_rect(game, diary_image, panel)
        paper_shade = pygame.Surface(panel.size, pygame.SRCALPHA)
        # 배경 이미지와 글자 색이 비슷해지지 않도록 밝은 종이막을 조금 더 강하게 올립니다.
        paper_shade.fill((255, 244, 216, 112))
        game.screen.blit(paper_shade, panel)
    elif paper_image:
        draw_image_cover_in_rect(game, paper_image, panel)
        paper_shade = pygame.Surface(panel.size, pygame.SRCALPHA)
        paper_shade.fill((0, 0, 0, 72))
        game.screen.blit(paper_shade, panel)
    else:
        paper = pygame.Surface(panel.size, pygame.SRCALPHA)
        paper.fill((18, 20, 24, 218))
        game.screen.blit(paper, panel)
    pygame.draw.rect(game.screen, (137, 84, 42) if diary_image else (214, 174, 99), panel, 2, border_radius=8)

    margin = max(26, min(58, panel.width // 11))
    x = panel.left + margin
    y = panel.top + margin
    content_width = panel.width - margin * 2
    if diary_image:
        # 일기지 장식은 살리되, 실제 글자 영역 뒤에는 밝은 배경을 깔아 가독성을 확보합니다.
        text_back = pygame.Rect(x - 18, y - 16, content_width + 36, panel.height - margin * 2 + 2)
        text_surface = pygame.Surface(text_back.size, pygame.SRCALPHA)
        text_surface.fill(DIARY_TEXT_BACK)
        game.screen.blit(text_surface, text_back)
        pygame.draw.rect(game.screen, (142, 91, 48), text_back, 1, border_radius=8)

    title_size = 34 if panel.width >= 620 else 27
    # 좁은 화면에서는 글자 크기를 줄여 겹침을 줄입니다.
    quote_size = 22 if panel.width >= 760 else 17
    body_size = 20 if panel.width >= 760 else 16
    main_color = DIARY_INK if diary_image else WHITE
    sub_color = DIARY_MUTED_INK if diary_image else GRAY
    accent_color = DIARY_ACCENT if diary_image else YELLOW

    draw_text(game, data["kicker"], 17, accent_color, x, y, False, True)
    # 여러 편 스토리 구조일 때 현재 몇 편을 보고 있는지 작게 표시합니다.
    page_text = f"{story.get_current_story_page_index(game) + 1}/{story.get_story_page_count(game)}"
    draw_text(game, page_text, 15, sub_color, panel.right - margin - 42, y + 1, False, True)
    y += 28
    draw_text(game, data["title"], title_size, main_color, x, y, False, True)
    y += title_size + 18
    draw_text(game, data["date"], 18, accent_color if diary_image else BLUE, x, y, False, True)
    y += 34

    visible_blocks = get_visible_story_blocks(game, data)
    has_typing_text = any(get_story_typing_blocks(data))
    assets.set_story_typing_sound_enabled(
        game,
        has_typing_text and not getattr(game, "story_typing_complete", True),
    )
    visible_quote = visible_blocks[0] if visible_blocks else ""
    visible_lines = visible_blocks[1:] if len(visible_blocks) > 1 else []

    quote_rect = pygame.Rect(x + 16, y, content_width - 16, 82)
    line_color = (137, 91, 50) if diary_image else (92, 104, 124)
    pygame.draw.line(game.screen, line_color, (x, y - 2), (x, y + 74), 4)
    quote_y = draw_wrapped_text(game, visible_quote, quote_size, main_color, quote_rect, 4, True)
    y = max(y + 82, quote_y + 12)

    for line in visible_lines:
        line_rect = pygame.Rect(x, y, content_width, 90)
        y = draw_wrapped_text(game, line, body_size, sub_color, line_rect, 5)
        y += 10

    footer_y = panel.bottom - margin - 48
    next_text = story.get_story_next_text(game)
    draw_text(game, next_text, 18, main_color, x, footer_y, False, True)
    prompt_font = get_font(game, 16, True)
    if getattr(game, "story_typing_complete", True):
        prompt = f"{story.get_story_prompt(game)}  Enter / 클릭"
    else:
        prompt = "Enter / 클릭: 전체 표시"
    prompt_image = prompt_font.render(prompt, True, accent_color)
    prompt_rect = prompt_image.get_rect(topright=(panel.right - margin, footer_y + 4))
    game.screen.blit(prompt_image, prompt_rect)


# 스테이지 클리어 결과 화면을 그립니다.
# 지금은 텍스트 중심의 임시 UI이고, 나중에 stage_result_background/panel 이미지로 디자인을 교체할 수 있습니다.
def draw_stage_result(game, draw_sea_background):
    # stage_result_stage1.png 또는 stage_result_background.png가 있으면 결과 화면 배경으로 씁니다.
    result_background = assets.get_stage_result_image(game, "background")
    if result_background:
        layout.draw_cover(game, result_background)
    else:
        draw_sea_background(game)

    # 배경 위에 반투명 어두운 막을 깔아 결과 글자가 잘 보이게 합니다.
    shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 132))
    game.screen.blit(shade, (0, 0))

    # 결과 데이터가 없더라도 화면이 깨지지 않게 빈 딕셔너리를 기본값으로 사용합니다.
    result = getattr(game, "stage_result", {}) or {}
    # 화면이 넓어져도 결과 패널이 너무 커지지 않도록 최대 너비/높이를 제한합니다.
    panel_width = min(840, int(game.pad_width * 0.82))
    panel_height = min(620, int(game.pad_height * 0.76))
    panel = pygame.Rect(0, 0, panel_width, panel_height)
    panel.center = (game.pad_width // 2, game.pad_height // 2)

    # stage_result_panel.png가 있으면 결과 패널 디자인 이미지로 사용합니다.
    panel_image = assets.get_stage_result_image(game, "panel")
    if panel_image:
        draw_image_cover_in_rect(game, panel_image, panel)
        panel_shade = pygame.Surface(panel.size, pygame.SRCALPHA)
        panel_shade.fill((0, 0, 0, 82))
        game.screen.blit(panel_shade, panel)
    else:
        panel_surface = pygame.Surface(panel.size, pygame.SRCALPHA)
        panel_surface.fill((14, 18, 24, 228))
        game.screen.blit(panel_surface, panel)
    pygame.draw.rect(game.screen, (218, 176, 95), panel, 2, border_radius=8)

    margin = max(24, min(42, panel.width // 12))
    x = panel.left + margin
    y = panel.top + margin
    content_width = panel.width - margin * 2

    # 제목은 스테이지 번호와 클리어 상태를 함께 보여줍니다.
    stage_number = result.get("stage_number", getattr(game, "stage_index", 0) + 1)
    draw_text(game, f"{stage_number}단계 클리어", 20, YELLOW, x, y, False, True)
    y += 34
    draw_text(game, result.get("stage_name", "해전 결과"), 36 if panel.width >= 620 else 28, WHITE, x, y, False, True)
    y += 52

    # 새 해금이나 최종 클리어 문구를 한 줄로 강조합니다.
    unlock_rect = pygame.Rect(x, y, content_width, 42)
    pygame.draw.rect(game.screen, (72, 55, 22), unlock_rect, border_radius=6)
    pygame.draw.rect(game.screen, (255, 213, 92), unlock_rect, 1, border_radius=6)
    draw_text(game, result.get("unlock_text", "스테이지 클리어"), 19, YELLOW, unlock_rect.centerx, unlock_rect.centery, True, True)
    y += 66

    # 결과 수치를 보기 좋게 2열 카드로 나누어 표시합니다.
    stat_rows = [
        ("총 점수", f"{result.get('score', 0):,}점"),
        ("격침 수", f"{result.get('kills', 0)}척"),
        ("대포 발사", f"{result.get('shots_fired', 0)}회"),
        ("피격 횟수", f"{result.get('hits_taken', 0)}회"),
        ("받은 피해", f"{result.get('damage_taken', 0)}"),
    ]
    y = draw_result_stat_grid(game, stat_rows, pygame.Rect(x, y, content_width, 150))
    y += 22

    # 스킬 사용량은 문장이 길어질 수 있으므로 줄바꿈 가능한 영역에 표시합니다.
    draw_text(game, "스킬 사용", 20, WHITE, x, y, False, True)
    y += 34
    skill_rect = pygame.Rect(x, y, content_width, 88)
    pygame.draw.rect(game.screen, (26, 31, 42), skill_rect, border_radius=6)
    pygame.draw.rect(game.screen, (88, 100, 124), skill_rect, 1, border_radius=6)
    draw_wrapped_text(game, result.get("skill_summary", "기록 없음"), 18, GRAY, skill_rect.inflate(-24, -18), 6, True)

    # 하단에는 다음 행동을 알려줍니다.
    footer_y = panel.bottom - margin - 34
    if result.get("final_clear"):
        footer_text = "Enter / 클릭: 전체 클리어 화면"
    else:
        footer_text = "Enter / 클릭: 해전 선택으로"
    draw_text(game, footer_text, 17, WHITE, x, footer_y, False, True)


# 결과 화면의 숫자 카드들을 2열 그리드로 그립니다.
def draw_result_stat_grid(game, stat_rows, rect):
    # 카드 사이 간격입니다.
    gap = 12
    # 2열 카드 폭을 계산합니다.
    card_width = (rect.width - gap) // 2
    # 카드 높이는 화면 크기와 행 수를 기준으로 적당히 고정합니다.
    card_height = 44
    # 마지막 y 좌표를 계산하기 위해 현재 y를 따로 둡니다.
    current_y = rect.top

    for index, (label, value) in enumerate(stat_rows):
        # 짝수는 왼쪽, 홀수는 오른쪽에 배치합니다.
        col = index % 2
        # 2개마다 다음 줄로 내려갑니다.
        row = index // 2
        # 카드의 왼쪽 위치를 계산합니다.
        card_x = rect.left + col * (card_width + gap)
        # 카드의 위쪽 위치를 계산합니다.
        card_y = rect.top + row * (card_height + gap)
        # 실제 카드 Rect를 만듭니다.
        card = pygame.Rect(card_x, card_y, card_width, card_height)
        # 카드 배경을 그립니다.
        pygame.draw.rect(game.screen, (26, 31, 42), card, border_radius=6)
        # 카드 테두리를 그립니다.
        pygame.draw.rect(game.screen, (88, 100, 124), card, 1, border_radius=6)
        # 왼쪽에는 항목 이름을 작게 표시합니다.
        draw_text(game, label, 15, GRAY, card.left + 14, card.top + 12, False, True)
        # 오른쪽에는 실제 값을 굵게 표시합니다.
        draw_text(game, value, 18, WHITE, card.right - 116, card.top + 10, False, True)
        # 마지막 카드 아래쪽 y를 갱신합니다.
        current_y = max(current_y, card.bottom)

    # 다음 내용을 이어 그릴 수 있도록 마지막 카드 아래 y 좌표를 돌려줍니다.
    return current_y


# 게임오버 또는 클리어 화면을 그립니다.
# clear 값에 따라 제목과 안내 문구가 달라집니다.
def draw_end_screen(game, clear, draw_sea_background):
    draw_sea_background(game)
    # end_result는 actors.end_game()에서 results.py가 만든 최종 전투 기록입니다.
    result = getattr(game, "end_result", {}) or {}
    title = result.get("title", "승리했습니다" if clear else "게임 오버")
    detail = result.get("detail", "5개의 스테이지를 모두 돌파했습니다." if clear else "다시 도전해보세요.")

    shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 132))
    game.screen.blit(shade, (0, 0))

    panel_width = min(820, int(game.pad_width * 0.82))
    panel_height = min(560, int(game.pad_height * 0.72))
    panel = pygame.Rect(0, 0, panel_width, panel_height)
    panel.center = (game.pad_width // 2, game.pad_height // 2)

    panel_surface = pygame.Surface(panel.size, pygame.SRCALPHA)
    panel_surface.fill((14, 18, 24, 228))
    game.screen.blit(panel_surface, panel)
    pygame.draw.rect(game.screen, (218, 176, 95), panel, 2, border_radius=8)

    margin = max(24, min(42, panel.width // 12))
    x = panel.left + margin
    y = panel.top + margin
    content_width = panel.width - margin * 2

    draw_text(game, title, 44 if panel.width >= 620 else 34, WHITE, x, y, False, True)
    y += 52
    draw_wrapped_text(game, detail, 19, GRAY, pygame.Rect(x, y, content_width, 54), 4, True)
    y += 72

    stat_rows = [
        ("총 점수", f"{result.get('score', getattr(game, 'score', 0)):,}점"),
        ("도달 단계", f"{result.get('stage_number', getattr(game, 'stage_index', 0) + 1)}단계"),
        ("격침 수", f"{result.get('kills', getattr(game, 'kill_count', 0))}척"),
        ("대포 발사", f"{result.get('shots_fired', 0)}회"),
        ("피격 횟수", f"{result.get('hits_taken', 0)}회"),
        ("받은 피해", f"{result.get('damage_taken', 0)}"),
    ]
    y = draw_result_stat_grid(game, stat_rows, pygame.Rect(x, y, content_width, 150))
    y += 26

    draw_text(game, "스킬 사용", 20, WHITE, x, y, False, True)
    y += 34
    skill_rect = pygame.Rect(x, y, content_width, 88)
    pygame.draw.rect(game.screen, (26, 31, 42), skill_rect, border_radius=6)
    pygame.draw.rect(game.screen, (88, 100, 124), skill_rect, 1, border_radius=6)
    draw_wrapped_text(game, result.get("skill_summary", "기록 없음"), 18, GRAY, skill_rect.inflate(-24, -18), 6, True)

    draw_text(game, "Enter / 클릭: 해전 선택", 18, WHITE, x, panel.bottom - margin - 26, False, True)


# 플레이 중 HUD를 그립니다.
# 넓은 화면에서는 중앙 플레이 영역 밖 좌우 패널에 표시하고,
# 좁은 화면에서는 예전처럼 위쪽 HUD를 사용합니다.
def draw_hud(game):
    if layout.has_side_panels(game):
        draw_side_hud(game)
        return

    draw_top_hud(game)


# 좁은 화면용 위쪽 HUD입니다.
def draw_top_hud(game):
    hud_height = layout.get_hud_height(game)
    panel = pygame.Surface((game.pad_width, hud_height), pygame.SRCALPHA)
    panel.fill((5, 9, 17, 185))
    game.screen.blit(panel, (0, 0))

    stage = game.current_stage()
    draw_text(game, get_stage_display_name(game), 20, WHITE, 14, 9, False, True)
    draw_text(game, f"점수 {game.score:,}", 16, GRAY, 14, 36)

    hp_w = min(190, max(120, game.pad_width // 4))
    hp_rect = pygame.Rect(14, hud_height - 22, hp_w, 12)
    # 체력 비율 = 현재 체력 / 최대 체력입니다. 이 비율만큼 막대 폭을 줄입니다.
    pygame.draw.rect(game.screen, (45, 35, 40), hp_rect, border_radius=6)
    hp_fill = hp_rect.copy()
    hp_fill.width = int(hp_rect.width * max(0, game.player["hp"] / game.player["maxHp"]))
    pygame.draw.rect(game.screen, GREEN if game.player["hp"] > 45 else RED, hp_fill, border_radius=6)
    pygame.draw.rect(game.screen, WHITE, hp_rect, 1, border_radius=6)
    draw_text(game, f"체력 {int(game.player['hp'])}/{game.player['maxHp']}", 14, WHITE, hp_rect.right + 8, hp_rect.centery - 9)

    center_x = game.pad_width // 2
    kills_to_boss = get_kills_to_boss(stage, get_stage_phase(game))
    if game.boss is None:
        draw_text(game, f"격침 {game.kill_count}/{kills_to_boss}", 22, YELLOW, center_x, 17, True, True)
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


# 넓은 화면용 사이드 HUD입니다.
# 중앙 플레이 영역을 가리지 않도록 오른쪽 바깥 영역에 핵심 정보를 모아 표시합니다.
# 왼쪽 바깥 영역은 다음 UI 확장을 위해 비워 둡니다.
def draw_side_hud(game):
    left_area, right_area = layout.get_side_areas(game)
    draw_story_summary_panel(game, left_area)

    right_panel = right_area.inflate(-28, -28)

    draw_side_panel(game, right_panel)

    stage = game.current_stage()
    kills_to_boss = get_kills_to_boss(stage, get_stage_phase(game))
    x = right_panel.left + 16
    y = right_panel.top + 18
    draw_text(game, get_stage_display_name(game), 18, WHITE, x, y, False, True)
    draw_text(game, f"점수 {game.score:,}", 17, YELLOW, x, y + 34, False, True)

    hp_rect = pygame.Rect(x, y + 76, max(80, right_panel.width - 32), 14)
    draw_text(game, "체력", 15, GRAY, x, hp_rect.top - 24)
    draw_bar(game, hp_rect, game.player["hp"], game.player["maxHp"], GREEN if game.player["hp"] > 45 else RED)
    draw_text(game, f"{int(game.player['hp'])}/{game.player['maxHp']}", 14, WHITE, x, hp_rect.bottom + 8)

    stat_y = hp_rect.bottom + 34
    draw_text(game, "능력치", 15, GRAY, x, stat_y)
    attack = augments.get_current_bullet_damage(game)
    move_speed = augments.get_current_move_speed(game)
    fire_cooldown = augments.get_current_fire_cooldown(game)
    bullet_radius = augments.get_current_bullet_radius(game)
    draw_text(game, f"공격력 {attack}  탄환크기 {bullet_radius // 3}", 14, WHITE, x, stat_y + 23, False, True)
    draw_text(game, f"이동속도 {move_speed}  연사간격 {fire_cooldown:.2f}초", 14, WHITE, x, stat_y + 43, False, True)

    mode_y = hp_rect.bottom + 94
    draw_text(game, "모드", 15, GRAY, x, mode_y)
    mode_name = "점수 경쟁" if augments.is_score_mode(game) else "이순신 시뮬레이션"
    level = getattr(game, "run_level", 1)
    xp = getattr(game, "run_xp", 0)
    xp_to_next = getattr(game, "run_xp_to_next", 1)
    draw_text(game, f"{mode_name} Lv.{level}", 21, WHITE, x, mode_y + 24, False, True)
    xp_rect = pygame.Rect(x, mode_y + 60, max(80, right_panel.width - 32), 13)
    draw_bar(game, xp_rect, xp, xp_to_next, YELLOW)
    draw_text(game, f"경험치 {xp}/{xp_to_next}", 13, GRAY, x, xp_rect.bottom + 7, False, True)
    summary_rect = pygame.Rect(x, xp_rect.bottom + 30, max(80, right_panel.width - 32), 46)
    draw_wrapped_text(game, augments.get_augment_summary(game), 13, WHITE, summary_rect, 2, True)
    skill_y = summary_rect.bottom + 26

    skill_width = max(80, right_panel.width - 32)
    draw_text(game, "전술", 16, WHITE, x, skill_y - 26, False, True)
    draw_skill_bar(
        game,
        pygame.Rect(x, skill_y, skill_width, 13),
        "Z/ㅋ 몸빵",
        getattr(game, "tanker_guard_timer", 0),
        skills.TANKER_DURATION + getattr(game, "augment_guard_bonus", 0),
        getattr(game, "tanker_guard_cooldown", 0),
        skills.TANKER_COOLDOWN,
        getattr(game, "tanker_skill_unlocked", False),
        BLUE,
    )
    draw_skill_bar(
        game,
        pygame.Rect(x, skill_y + 42, skill_width, 13),
        "X/ㅌ 치유",
        getattr(game, "healer_timer", 0),
        skills.HEALER_DURATION,
        getattr(game, "healer_cooldown", 0),
        skills.HEALER_COOLDOWN,
        getattr(game, "healer_skill_unlocked", False),
        GREEN,
    )
    draw_skill_bar(
        game,
        pygame.Rect(x, skill_y + 84, skill_width, 13),
        "Q 보스전",
        getattr(game, "hakikjin_timer", 0),
        skills.HAKIKJIN_DURATION,
        getattr(game, "hakikjin_cooldown", 0),
        skills.HAKIKJIN_COOLDOWN,
        getattr(game, "hakikjin_unlocked", False),
        YELLOW,
    )

    status_y = skill_y + 126
    if getattr(game, "stage_handicap_timer", 0) > 0:
        draw_text(game, f"고립 전투 {game.stage_handicap_timer:.0f}초", 13, RED, x, status_y, False, True)
        status_y += 22

    if game.stage_index >= skills.LAST_STAND_STAGE_INDEX:
        choice = getattr(game, "last_stand_choice", "damage")
        if choice == "damage":
            dmg_timer = getattr(game, "last_stand_damage_timer", 0)
            dmg_cd = getattr(game, "last_stand_damage_cooldown", 0)
            if dmg_timer > 0:
                last_status = f"공격력↑ {dmg_timer:.0f}초"
                color = (255, 200, 50)
            elif dmg_cd > 0:
                last_status = f"쿨타임 {dmg_cd:.0f}초"
                color = GRAY
            else:
                last_status = "준비"
                color = YELLOW
            draw_text(game, f"필생즉사 {last_status}", 13, color, x, status_y, False, True)
        else:
            rev_cd = getattr(game, "last_stand_revive_cooldown", 0)
            pen_timer = getattr(game, "last_stand_revive_penalty_timer", 0)
            if pen_timer > 0:
                last_status = f"공격↓ {pen_timer:.0f}초 | 쿨 {rev_cd:.0f}초"
                color = (180, 130, 255)
            elif rev_cd > 0:
                last_status = f"쿨타임 {rev_cd:.0f}초"
                color = GRAY
            else:
                last_status = "준비"
                color = YELLOW
            draw_text(game, f"필사즉생 {last_status}", 13, color, x, status_y, False, True)
        status_y += 22

    progress_y = skill_y + 170
    draw_text(game, "진행", 18, WHITE, x, progress_y, False, True)
    progress_rect = pygame.Rect(x, progress_y + 42, max(80, right_panel.width - 32), 14)
    draw_bar(game, progress_rect, game.kill_count, kills_to_boss, YELLOW)
    total_kills = getattr(game, "stage_total_kills", 0) + game.kill_count
    draw_text(game, f"격침 {game.kill_count}/{kills_to_boss}  총 {total_kills}", 16, WHITE, x, progress_rect.bottom + 8, False, True)

    boss_y = progress_rect.bottom + 54
    if game.boss is None:
        draw_text(game, "미니보스 대기", 17, GRAY, x, boss_y, False, True)
        return

    draw_text(game, "미니보스", 17, RED, x, boss_y, False, True)
    boss_hp_rect = pygame.Rect(x, boss_y + 36, max(80, right_panel.width - 32), 14)
    draw_bar(game, boss_hp_rect, game.boss["hp"], game.boss["maxHp"], RED)
    draw_text(game, game.boss.get("name", get_stage_boss_name(game)), 14, WHITE, x, boss_hp_rect.bottom + 8)

    if game.boss["maxShield"] > 0:
        shield_rect = boss_hp_rect.move(0, 50)
        draw_text(game, "보호막", 14, GRAY, x, shield_rect.top - 22)
        draw_bar(game, shield_rect, game.boss["shield"], game.boss["maxShield"], BLUE)


# 넓은 화면에서 왼쪽 전체 영역에 현재 출전 직전 일기의 요약을 표시합니다.
# story_summary_vertical.png가 있으면 세로 일기지 이미지 위에 글을 올립니다.
def draw_story_summary_panel(game, left_area):
    if left_area.width < 120 or left_area.height < 160:
        return

    # 세로 일기지 이미지는 사용자가 준 왼쪽 플레이어 영역 전체를 꽉 채우도록 여백 없이 씁니다.
    panel = left_area.copy()
    if panel.width <= 0 or panel.height <= 0:
        return

    image = game.images.get("story_summary_vertical")
    if image:
        draw_image_cover_in_rect(game, image, panel)
        shade = pygame.Surface(panel.size, pygame.SRCALPHA)
        # 세로 일기지 역시 배경과 본문이 섞이지 않도록 밝은 종이막을 충분히 올립니다.
        shade.fill((255, 244, 216, 126))
        game.screen.blit(shade, panel)
        text_color = DIARY_INK
        sub_color = DIARY_MUTED_INK
        border_color = (121, 76, 39)
    else:
        draw_side_panel(game, panel)
        text_color = WHITE
        sub_color = GRAY
        border_color = (107, 91, 64)

    pygame.draw.rect(game.screen, border_color, panel, 2, border_radius=8)

    # 이미지는 꽉 채우되, 글자는 가장자리 장식과 겹치지 않게 내부 여백을 둡니다.
    margin = max(16, min(30, panel.width // 7))
    x = panel.left + margin
    y = panel.top + margin
    width = panel.width - margin * 2

    draw_text(game, "출전 기록", 18, text_color, x, y, False, True)
    y += 34
    summary_text = story.get_current_story_summary(game)
    # 세로 패널은 좁으므로 문단 간 빈 줄을 조금 넓게 주어 읽기 쉽게 합니다.
    for paragraph in summary_text.split("\n"):
        if not paragraph.strip():
            y += 10
            continue
        y = draw_wrapped_text(game, paragraph.strip(), 14, sub_color, pygame.Rect(x, y, width, panel.bottom - y - margin), 4)
        y += 12
        if y > panel.bottom - margin - 24:
            break

    # 스토리 요약 아래 남는 빈칸에는 현재 스테이지의 보스 초상 이미지를 표시합니다.
    # story_boss_stage1.png 같은 전용 이미지가 있으면 그것을 쓰고, 없으면 기존 보스 이미지를 재사용합니다.
    boss_image = assets.get_story_image(game, "boss")
    remaining_height = panel.bottom - y - margin
    if boss_image and remaining_height >= 96:
        # 이미지가 텍스트와 너무 붙지 않도록 작은 간격을 두고 시작합니다.
        y += 4
        remaining_height = panel.bottom - y - margin
        # 세로 패널이 긴 화면에서도 보스가 요약지를 과하게 덮지 않도록 최대 높이를 제한합니다.
        image_height = min(remaining_height, int(panel.height * 0.36))
        image_rect = pygame.Rect(x, y, width, image_height)
        # 투명 PNG는 배경을 그대로 살려야 하므로 잘라내지 않는 contain 방식으로 그립니다.
        draw_image_contain_in_rect(game, boss_image, image_rect)


# 사이드 HUD의 어두운 패널 배경입니다.
def draw_side_panel(game, rect):
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((5, 9, 17, 150))
    game.screen.blit(panel, rect)
    pygame.draw.rect(game.screen, (210, 176, 105), rect, 1, border_radius=6)


# HUD에서 반복해서 쓰는 막대 그래프입니다.
def draw_bar(game, rect, value, max_value, color):
    pygame.draw.rect(game.screen, (38, 35, 42), rect, border_radius=6)
    fill = rect.copy()
    # value/max_value를 0~1 사이로 제한해 막대가 튀어나가지 않게 합니다.
    fill.width = int(rect.width * max(0, min(1, value / max(1, max_value))))
    pygame.draw.rect(game.screen, color, fill, border_radius=6)
    pygame.draw.rect(game.screen, WHITE, rect, 1, border_radius=6)


# 전술 스킬의 지속시간/대기시간/준비 상태를 막대로 보여줍니다.
def draw_skill_bar(game, rect, label, timer, duration, cooldown, cooldown_max, available, color):
    if timer > 0:
        # 스킬이 켜져 있으면 남은 지속시간 비율을 표시합니다.
        status = f"지속 {timer:.0f}초"
        fill_ratio = timer / max(0.1, duration)
        fill_color = color
    elif not available:
        status = "필요"
        fill_ratio = 0
        fill_color = GRAY
    elif cooldown > 0:
        # 쿨타임 중이면 0에서 1로 차오르는 형태로 보여줍니다.
        status = f"대기 {cooldown:.0f}초"
        fill_ratio = 1 - cooldown / max(0.1, cooldown_max)
        fill_color = BLUE
    else:
        status = "준비"
        fill_ratio = 1
        fill_color = GREEN

    draw_text(game, label, 13, WHITE, rect.left, rect.top - 18, False, True)
    draw_text(game, status, 12, GRAY if not available or cooldown > 0 else WHITE, rect.right - 64, rect.top - 18, False, True)
    pygame.draw.rect(game.screen, (38, 35, 42), rect, border_radius=6)
    fill = rect.copy()
    fill.width = int(rect.width * max(0, min(1, fill_ratio)))
    if fill.width > 0:
        pygame.draw.rect(game.screen, fill_color, fill, border_radius=6)
    pygame.draw.rect(game.screen, WHITE, rect, 1, border_radius=6)
