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
from io import BytesIO
from pathlib import Path
import math
from time import sleep

from PIL import Image
import pygame

import account_store
import augments
import assets
import campaign
import layout
import scoreboard
import skills
import story
from settings import BLACK, BLUE, GRAY, GREEN, RED, WHITE, YELLOW
from stages import STAGE_MAX, get_kills_to_boss, get_stage_display_name, get_stage_phase


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

RIGHT_UI_SOURCE_SIZE = (887, 1774)
RIGHT_UI_SECTIONS = {
    "header": (165, 104, 555, 58),
    "stage": (125, 200, 636, 144),
    "score": (125, 398, 636, 146),
    "hp": (218, 612, 498, 48),
    "augments": (124, 1030, 638, 208),
    "stats": (124, 1306, 638, 316),
}
RIGHT_UI_SKILL_SLOTS = (
    (132, 712, 178, 178),
    (354, 712, 178, 178),
    (576, 712, 178, 178),
)
STAGE_RESULT_VALUE_RECTS = {
    "score": (872, 324, 330, 64),
    "play_time": (872, 405, 330, 64),
    "shots": (872, 484, 330, 64),
    "hits": (872, 562, 330, 64),
    "total_score": (720, 635, 510, 84),
}
SCORE_LEADERBOARD_START_BUTTON_SOURCE_RECT = (570, 900, 396, 86)
ACCOUNT_SOURCE_SIZE = (1448, 1086)
ACCOUNT_HIDDEN_STATES = {"story", "play", "account_login", "account_signup", "account_mypage", "account_edit", "account_profile_crop"}
ACCOUNT_PANEL_IMAGES = {
    "account_login": "account_login_panel",
    "account_signup": "account_signup_panel",
    "account_mypage": "account_mypage_panel",
    "account_edit": "account_edit_panel",
}
ACCOUNT_BUTTON_ORDER = {
    "account_login": ("login", "signup", "back"),
    "account_signup": ("submit", "back"),
    "account_mypage": ("edit", "back"),
    "account_edit": ("save", "back"),
}
ACCOUNT_SOURCE_RECTS = {
    "account_login": {
        "fields": (("login_id", (260, 356, 940, 92)), ("password", (260, 494, 940, 92))),
        "buttons": {
            "login": (250, 624, 950, 132),
            "signup": (300, 808, 420, 88),
            "back": (760, 808, 420, 88),
        },
    },
    "account_signup": {
        "fields": (("nickname", (760, 344, 535, 78)), ("login_id", (760, 480, 535, 78)), ("password", (760, 616, 535, 78))),
        "profile": (170, 300, 350, 360),
        "profile_button": (196, 710, 330, 76),
        "buttons": {
            "submit": (260, 820, 420, 90),
            "back": (770, 820, 420, 90),
        },
    },
    "account_mypage": {
        "profile": (170, 310, 350, 360),
        "values": {
            "nickname": (760, 346, 535, 72),
            "login_id": (760, 462, 535, 72),
            "best_score": (760, 577, 535, 72),
            "stage": (760, 686, 535, 72),
        },
        "buttons": {
            "edit": (268, 828, 418, 88),
            "back": (778, 828, 418, 88),
        },
    },
    "account_edit": {
        "fields": (("nickname", (760, 346, 535, 78)), ("login_id", (760, 480, 535, 78)), ("password", (760, 616, 535, 78))),
        "profile": (170, 300, 350, 360),
        "profile_button": (196, 710, 330, 76),
        "buttons": {
            "save": (268, 828, 418, 88),
            "back": (778, 828, 418, 88),
        },
    },
}


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


# 스토리 화면 전용 폰트를 가져옵니다.
# 프로젝트에 Joseon100Years/ChosunCentennial 폰트 파일이 있으면 우선 사용하고,
# 없으면 기존 get_font 폴백을 사용합니다.
def get_story_font(game, size, bold=False):
    key = ("story", size, bold)
    if key in game.fonts:
        return game.fonts[key]

    root = Path(__file__).resolve().parent
    fonts_dir = root / "assets" / "fonts"
    candidates = [
        fonts_dir / "Joseon100Years.ttf",
        fonts_dir / "Joseon100Years.otf",
        fonts_dir / "ChosunCentennial.ttf",
        fonts_dir / "ChosunCentennial.otf",
        # 사용자가 내려받아 둔 실제 파일명 패턴도 함께 지원합니다.
        fonts_dir / "ChosunCentennial_ttf.ttf",
        fonts_dir / "ChosunCentennial_otf.otf",
        Path("C:/Windows/Fonts/batang.ttc"),
        Path("C:/Windows/Fonts/gungsuh.ttf"),
        Path("/System/Library/Fonts/Supplemental/AppleMyungjo.ttf"),
        Path("/usr/share/fonts/truetype/nanum/NanumMyeongjo.ttf"),
    ]

    # assets/fonts 안의 모든 폰트 파일(.ttf/.otf/.ttc)을 후보에 추가합니다.
    # 파일명이 달라도 스토리 전용 폰트가 적용되도록 안전장치로 둡니다.
    if fonts_dir.exists():
        for extension in ("*.ttf", "*.otf", "*.ttc"):
            for path in sorted(fonts_dir.glob(extension)):
                if path not in candidates:
                    candidates.append(path)

    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            font = pygame.font.Font(str(candidate), size)
            font.set_bold(bold)
            game.fonts[key] = font
            return font
        except pygame.error:
            continue

    # 시스템에서 세리프 계열 한글 폰트를 먼저 찾고, 실패하면 기본 폰트를 사용합니다.
    font_path = pygame.font.match_font("batang,gungsuh,nanumgothic,malgungothic")
    if font_path:
        font = pygame.font.Font(font_path, size)
        font.set_bold(bold)
    else:
        font = get_font(game, size, bold)

    game.fonts[key] = font
    return font


def get_right_ui_font(game, size, bold=False):
    key = ("right_ui", size, bold)
    if key in game.fonts:
        return game.fonts[key]

    root = Path(__file__).resolve().parent
    fonts_dir = root / "assets" / "fonts"
    candidates = [
        fonts_dir / ("museum_classic_b.ttf" if bold else "museum_classic_m.ttf"),
        fonts_dir / "museum_classic_m.ttf",
        fonts_dir / "museum_classic_l.ttf",
    ]

    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            font = pygame.font.Font(str(candidate), size)
            game.fonts[key] = font
            return font
        except pygame.error:
            continue

    font = get_story_font(game, size, bold)
    game.fonts[key] = font
    return font


# 화면에 글자를 그리는 공통 함수입니다.
# center=True면 x, y를 글자의 중심으로 쓰고, False면 왼쪽 위 좌표로 씁니다.
def draw_text(game, text, size, color, x, y, center=False, bold=False, font_getter=None):
    font = (font_getter or get_font)(game, size, bold)
    # font.render()는 글자를 pygame Surface 이미지로 바꿉니다.
    image = font.render(text, True, color)
    rect = image.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    game.screen.blit(image, rect)
    return rect


def draw_soft_focus_frame(game, rect, selected=False, hovered=False, radius=8):
    if not selected and not hovered:
        return

    outer_rect = rect.inflate(10 if selected else 6, 10 if selected else 6)
    glow = pygame.Surface(outer_rect.size, pygame.SRCALPHA)
    for width, alpha in ((6, 24 if selected else 16), (2, 82 if hovered else 62)):
        pygame.draw.rect(glow, (255, 214, 94, alpha), glow.get_rect(), width, border_radius=radius + 5)
    game.screen.blit(glow, outer_rect)

    border_color = (255, 228, 134) if hovered else (255, 207, 78)
    pygame.draw.rect(game.screen, border_color, rect, 3 if selected else 2, border_radius=radius)
    inner_rect = rect.inflate(-12, -12)
    if inner_rect.width > 0 and inner_rect.height > 0:
        pygame.draw.rect(game.screen, (135, 83, 22), inner_rect, 1, border_radius=max(3, radius - 3))


def draw_toast(game, text, y, size=30, color=YELLOW, max_width_ratio=0.76):
    if not text:
        return

    font = get_font(game, size, True)
    max_width = int(game.pad_width * max_width_ratio)
    text = trim_text_to_width(font, str(text), max_width)
    image = font.render(text, True, color)
    image_rect = image.get_rect(center=(game.pad_width // 2, y))
    panel_rect = image_rect.inflate(42, 20)
    panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (10, 12, 14, 214), panel.get_rect(), border_radius=10)
    game.screen.blit(panel, panel_rect)
    pygame.draw.rect(game.screen, (220, 170, 78), panel_rect, 1, border_radius=10)
    game.screen.blit(image, image_rect)


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
def draw_wrapped_text(game, text, size, color, rect, line_gap=8, bold=False, font_getter=None):
    font = (font_getter or get_font)(game, size, bold)
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


def draw_text_in_rect(game, text, size, color, rect, center=False, bold=False, font_getter=None):
    font = (font_getter or get_font)(game, size, bold)
    text = trim_text_to_width(font, str(text), rect.width)
    image = font.render(text, True, color)
    image_rect = image.get_rect()
    if center:
        image_rect.center = rect.center
    else:
        image_rect.topleft = rect.topleft
    game.screen.blit(image, image_rect)
    return image_rect


def draw_text_fit_in_rect(game, text, size, color, rect, center=True, bold=True, font_getter=None, min_size=12):
    text = str(text)
    current_size = size
    while current_size > min_size:
        font = (font_getter or get_font)(game, current_size, bold)
        if font.size(text)[0] <= rect.width and font.get_height() <= rect.height:
            break
        current_size -= 1
    return draw_text_in_rect(game, text, current_size, color, rect, center, bold, font_getter)


def draw_text_fit_visual_center_in_rect(game, text, size, color, rect, bold=True, font_getter=None, min_size=12):
    text = str(text)
    current_size = size
    while current_size > min_size:
        font = (font_getter or get_font)(game, current_size, bold)
        if font.size(text)[0] <= rect.width and font.get_height() <= rect.height:
            break
        current_size -= 1

    font = (font_getter or get_font)(game, current_size, bold)
    text = trim_text_to_width(font, text, rect.width)
    image = font.render(text, True, color)
    ink_rect = image.get_bounding_rect()
    image_rect = image.get_rect()
    if ink_rect.width > 0 and ink_rect.height > 0:
        image_rect.left = int(rect.centerx - ink_rect.centerx)
        image_rect.top = int(rect.centery - ink_rect.centery)
    else:
        image_rect.center = rect.center
    game.screen.blit(image, image_rect)
    return image_rect


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


def get_image_cover_rect_in_rect(image, rect):
    if image is None or rect.width <= 0 or rect.height <= 0:
        return pygame.Rect(rect)

    scale = max(rect.width / image.get_width(), rect.height / image.get_height())
    scaled_width = max(rect.width, int(image.get_width() * scale) + 1)
    scaled_height = max(rect.height, int(image.get_height() * scale) + 1)
    image_rect = pygame.Rect(0, 0, scaled_width, scaled_height)
    image_rect.center = rect.center
    return image_rect


def get_image_contain_rect_in_rect(image, rect):
    if image is None or rect.width <= 0 or rect.height <= 0:
        return pygame.Rect(rect)

    scale = min(rect.width / image.get_width(), rect.height / image.get_height())
    scaled_width = max(1, int(image.get_width() * scale))
    scaled_height = max(1, int(image.get_height() * scale))
    image_rect = pygame.Rect(0, 0, scaled_width, scaled_height)
    image_rect.center = rect.center
    return image_rect


def draw_image_content_contain_in_rect(game, image, rect):
    if image is None or rect.width <= 0 or rect.height <= 0:
        return

    cropped = get_image_content_surface(game, image)
    if cropped is None:
        draw_image_contain_in_rect(game, image, rect)
        return

    draw_image_contain_in_rect(game, cropped, rect)


def get_image_content_surface(game, image):
    if image is None:
        return None

    source_rect = image.get_bounding_rect()
    if source_rect.width <= 0 or source_rect.height <= 0:
        return None

    crop_cache = getattr(game, "image_content_cache", None)
    if crop_cache is None:
        crop_cache = {}
        game.image_content_cache = crop_cache

    cache_key = (id(image), source_rect.x, source_rect.y, source_rect.width, source_rect.height)
    cropped = crop_cache.get(cache_key)
    if cropped is None:
        cropped = image.subsurface(source_rect).copy()
        crop_cache[cache_key] = cropped
    return cropped


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
# main_menu.png에는 이미 "게임 시작" 버튼이 그려져 있으므로 메인에서는 그 버튼만 보여줍니다.
def draw_menu(game, draw_sea_background):
    menu_image = game.images.get("main_menu")
    if menu_image:
        layout.draw_cover(game, menu_image)
    else:
        draw_sea_background(game)
        draw_text(game, "PyShooting", 52, WHITE, game.pad_width // 2, int(game.pad_height * 0.28), True, True)
        draw_text(game, "거북선 전쟁", 26, YELLOW, game.pad_width // 2, int(game.pad_height * 0.36), True, True)

    start_rect = layout.get_start_button_rect(game)
    login_rect = layout.get_login_button_rect(game)
    mouse_pos = pygame.mouse.get_pos()
    selected_button = "login" if getattr(game, "menu_select_index", 0) == 1 else "start"
    start_hovered = start_rect.collidepoint(mouse_pos)
    login_hovered = login_rect.collidepoint(mouse_pos)
    start_selected = selected_button == "start"
    login_selected = selected_button == "login"
    if menu_image:
        draw_menu_baked_button_highlight(game, start_rect, start_selected, start_hovered)
    else:
        draw_menu_mode_button(game, start_rect, "게임 시작", start_selected, start_hovered)
    draw_menu_login_button(game, login_rect, login_hovered or login_selected, getattr(game, "menu_pressed_button", "") == "login")


def draw_mode_select(game, draw_sea_background):
    selected_index = max(0, min(getattr(game, "mode_select_index", 0), 2))
    mode_images = (
        game.images.get("story_mode"),
        game.images.get("com_mode"),
        game.images.get("mode_back"),
    )
    mode_image = mode_images[selected_index] or game.images.get("mode_back")
    if mode_image:
        layout.draw_cover(game, mode_image)
        _, buttons = layout.get_mode_select_layout(game)
        mouse_pos = pygame.mouse.get_pos()
        for index, rect in enumerate(buttons):
            draw_soft_focus_frame(game, rect, selected_index == index, hovered=rect.collidepoint(mouse_pos), radius=10)
        return

    menu_image = game.images.get("main_menu")
    if menu_image:
        layout.draw_cover(game, menu_image)
    else:
        draw_sea_background(game)

    shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 138))
    game.screen.blit(shade, (0, 0))

    panel, buttons = layout.get_mode_select_layout(game)
    panel_surface = pygame.Surface(panel.size, pygame.SRCALPHA)
    panel_surface.fill((10, 14, 20, 232))
    game.screen.blit(panel_surface, panel)
    pygame.draw.rect(game.screen, (255, 218, 124), panel, 3, border_radius=8)
    pygame.draw.rect(game.screen, (118, 75, 24), panel.inflate(-18, -18), 1, border_radius=6)

    draw_text(game, "모드 선택", max(34, panel.height // 8), (255, 220, 142), panel.centerx, panel.top + max(58, panel.height // 6), True, True)

    mouse_pos = pygame.mouse.get_pos()
    selected_index = max(0, min(getattr(game, "mode_select_index", 0), len(buttons) - 1))
    labels = ("이순신 시뮬레이션", "점수 경쟁", "뒤로")
    for index, rect in enumerate(buttons):
        draw_menu_mode_button(game, rect, labels[index], selected_index == index, rect.collidepoint(mouse_pos))

    hint_y = panel.bottom - max(34, panel.height // 10)
    draw_text(game, "Enter / 클릭으로 선택    Esc 뒤로", max(15, panel.height // 24), GRAY, panel.centerx, hint_y, True, True)


def draw_menu_baked_button_highlight(game, rect, selected, hovered):
    if not selected and not hovered:
        return

    button_image = get_image_content_surface(game, game.images.get("menu_start_button"))
    if button_image:
        draw_menu_button_shape_glow(game, button_image, rect, hovered)
        return

    pygame.draw.rect(game.screen, (255, 219, 106), rect, 2, border_radius=10)


def draw_menu_button_shape_glow(game, button_image, rect, hovered):
    glow_rect = rect.inflate(max(12, rect.width // 26), max(8, rect.height // 9))
    target = pygame.Rect(0, 0, glow_rect.width, glow_rect.height)
    cover_rect = get_image_cover_rect_in_rect(button_image, target)
    scaled = assets.get_scaled_image(game, button_image, cover_rect.size)
    if scaled is None:
        return

    mask = pygame.mask.from_surface(scaled)
    outline = mask.outline(3)
    if len(outline) < 3:
        return

    glow = pygame.Surface(scaled.get_size(), pygame.SRCALPHA)
    for width, alpha in ((7, 34 if hovered else 22), (3, 96 if hovered else 70)):
        pygame.draw.lines(glow, (255, 222, 105, alpha), True, outline, width)

    base = (glow_rect.left + cover_rect.left, glow_rect.top + cover_rect.top)
    game.screen.blit(glow, base)


def draw_menu_login_button(game, rect, hovered=False, pressed=False):
    glow_alpha = 86 if hovered or pressed else 42
    glow_rect = rect.inflate(max(10, rect.width // 10), max(8, rect.height // 4))
    glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(glow, (255, 184, 46, glow_alpha), glow.get_rect(), border_radius=8)
    game.screen.blit(glow, glow_rect)

    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((8, 9, 10, 246))
    game.screen.blit(panel, rect)

    outer = (246, 188, 76) if hovered or pressed else (213, 145, 43)
    inner = (255, 229, 139) if hovered or pressed else (156, 96, 28)
    pygame.draw.rect(game.screen, outer, rect, 2 if rect.height < 48 else 3, border_radius=7)
    pygame.draw.rect(game.screen, inner, rect.inflate(-8, -8), 1, border_radius=5)

    accent_w = max(12, rect.width // 9)
    accent_h = max(5, rect.height // 7)
    left = rect.left + max(8, rect.width // 14)
    right = rect.right - max(8, rect.width // 14)
    y = rect.centery
    pygame.draw.line(game.screen, outer, (left, y), (left + accent_w, y), 1)
    pygame.draw.line(game.screen, outer, (right - accent_w, y), (right, y), 1)
    pygame.draw.circle(game.screen, outer, (left + accent_w + accent_h, y), max(2, accent_h // 2), 1)
    pygame.draw.circle(game.screen, outer, (right - accent_w - accent_h, y), max(2, accent_h // 2), 1)

    if hovered or pressed:
        shine = pygame.Surface(rect.size, pygame.SRCALPHA)
        shine.fill((255, 225, 145, 24 if hovered else 16))
        game.screen.blit(shine, rect)

    draw_text_fit_visual_center_in_rect(game, "로그인", max(18, int(rect.height * 0.52)), (255, 226, 151), rect, True, get_story_font, min_size=12)


# 메인 메뉴의 버튼 하나를 그립니다.
# selected는 키보드로 선택된 상태이고, hovered는 마우스가 올라간 상태입니다.
def draw_menu_mode_button(game, rect, label, selected, hovered):
    start_button_image = game.images.get("menu_start_button") if label == "게임 시작" else None
    if start_button_image:
        # 제공받은 "게임 시작" 버튼 이미지는 메인 시작 버튼에만 그대로 사용합니다.
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


def draw_score_name_input(game, draw_sea_background):
    background = game.images.get("leaderboard_background") or game.images.get("main_menu")
    if background:
        layout.draw_cover(game, background)
    else:
        draw_sea_background(game)

    shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 96))
    game.screen.blit(shade, (0, 0))

    panel = pygame.Rect(0, 0, min(640, int(game.pad_width * 0.78)), 260)
    panel.center = (game.pad_width // 2, game.pad_height // 2)
    panel_surface = pygame.Surface(panel.size, pygame.SRCALPHA)
    panel_surface.fill((30, 20, 11, 218))
    game.screen.blit(panel_surface, panel)
    pygame.draw.rect(game.screen, (223, 177, 92), panel, 2, border_radius=8)
    pygame.draw.rect(game.screen, (118, 76, 32), panel.inflate(-16, -16), 1, border_radius=5)

    draw_text(game, "닉네임 입력", 42 if panel.width >= 560 else 34, (255, 224, 150), panel.centerx, panel.top + 62, True, True)

    input_rect = pygame.Rect(panel.left + 54, panel.top + 114, panel.width - 108, 62)
    pygame.draw.rect(game.screen, (239, 222, 179), input_rect, border_radius=6)
    pygame.draw.rect(game.screen, (72, 45, 18), input_rect, 2, border_radius=6)

    nickname = getattr(game, "score_name_input", "")
    composing = getattr(game, "text_editing_text", "") if game.game_state == "score_name_input" else ""
    cursor = "|" if pygame.time.get_ticks() // 450 % 2 == 0 else ""
    display_name = f"{nickname}{composing}"
    text = f"{display_name}{cursor}" if display_name else f"닉네임{cursor}"
    color = DIARY_INK if display_name else (108, 86, 60)
    draw_text_in_rect(game, text, 30, color, input_rect.inflate(-24, 0), False, True)

    draw_text(game, "Enter", 18, (255, 224, 150), panel.centerx - 42, panel.bottom - 46, True, True)
    draw_text(game, "시작", 18, WHITE, panel.centerx + 18, panel.bottom - 46, True, True)
    draw_text(game, "Esc", 16, GRAY, panel.right - 86, panel.bottom - 46, True, True)
    draw_text(game, "메뉴", 16, GRAY, panel.right - 45, panel.bottom - 46, True, True)


def should_draw_profile_button(game):
    return getattr(game, "game_state", "menu") not in ACCOUNT_HIDDEN_STATES


def get_profile_button_rect(game):
    size = max(58, min(88, int(min(game.pad_width, game.pad_height) * 0.105)))
    return pygame.Rect(18, 18, size, size)


def draw_profile_button(game):
    rect = get_profile_button_rect(game)
    icon = game.images.get(account_store.DEFAULT_PROFILE_IMAGE_KEY)
    icon_content = None
    icon_rect = rect
    if icon:
        icon_content = get_image_content_surface(game, icon) or icon
        icon_rect = get_image_contain_rect_in_rect(icon_content, rect)
        draw_image_contain_in_rect(game, icon_content, icon_rect)
    else:
        pygame.draw.circle(game.screen, (14, 14, 14), rect.center, rect.width // 2)
        pygame.draw.circle(game.screen, (224, 176, 78), rect.center, rect.width // 2 - 2, 2)

    user = account_store.current_user(game)
    photo = get_account_profile_surface(game, user)
    if photo:
        draw_profile_photo_in_frame(game, photo, get_profile_button_photo_rect(icon_rect))
        if icon_content:
            draw_profile_frame_overlay(game, icon_content, icon_content.get_rect(), icon_rect)

    hovered = rect.collidepoint(pygame.mouse.get_pos())
    if hovered:
        glow = pygame.Surface(rect.inflate(12, 12).size, pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 220, 112, 90), glow.get_rect(), 4)
        game.screen.blit(glow, rect.inflate(12, 12))


def draw_account_background(game, draw_sea_background):
    background = game.images.get("main_menu") or game.images.get("leaderboard_background")
    if background:
        layout.draw_cover(game, background)
    else:
        draw_sea_background(game)

    shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 142))
    game.screen.blit(shade, (0, 0))


def get_account_panel_rect(game, state):
    image = game.images.get(ACCOUNT_PANEL_IMAGES.get(state, ""))
    outer = game.screen.get_rect().inflate(-max(24, game.pad_width // 18), -max(24, game.pad_height // 12))
    if image:
        return get_image_contain_rect_in_rect(image, outer)
    panel = pygame.Rect(0, 0, min(900, int(game.pad_width * 0.78)), min(620, int(game.pad_height * 0.78)))
    panel.center = game.screen.get_rect().center
    return panel


def get_account_layout(game, state):
    panel = get_account_panel_rect(game, state)
    image_key = ACCOUNT_PANEL_IMAGES.get(state, "")
    image = game.images.get(image_key)
    source_size = image.get_size() if image else ACCOUNT_SOURCE_SIZE
    source = ACCOUNT_SOURCE_RECTS.get(state, {})
    source_fields = [(name, pygame.Rect(rect)) for name, rect in source.get("fields", ())]
    source_buttons = {name: pygame.Rect(rect) for name, rect in source.get("buttons", {}).items()}
    source_values = {name: pygame.Rect(rect) for name, rect in source.get("values", {}).items()}
    source_profile = pygame.Rect(source["profile"]) if "profile" in source else None
    source_profile_button = pygame.Rect(source["profile_button"]) if "profile_button" in source else None
    fields = [(name, scale_source_rect(panel, source_size, rect)) for name, rect in source_fields]
    buttons = {name: scale_source_rect(panel, source_size, rect) for name, rect in source_buttons.items()}
    values = {name: scale_source_rect(panel, source_size, rect) for name, rect in source_values.items()}
    profile = scale_source_rect(panel, source_size, source_profile) if source_profile else None
    profile_button = scale_source_rect(panel, source_size, source_profile_button) if source_profile_button else None
    return {
        "state": state,
        "image_key": image_key,
        "panel": panel,
        "source_size": source_size,
        "source_fields": source_fields,
        "source_buttons": source_buttons,
        "source_values": source_values,
        "source_profile": source_profile,
        "source_profile_button": source_profile_button,
        "fields": fields,
        "buttons": buttons,
        "values": values,
        "profile": profile,
        "profile_button": profile_button,
    }


def get_account_profile_hit_rect(profile_rect):
    inflate_x = max(18, int(profile_rect.width * 0.14))
    inflate_y = max(18, int(profile_rect.height * 0.12))
    return profile_rect.inflate(inflate_x, inflate_y)


def get_account_focus_items(layout_info, state):
    source_fields = {name: rect for name, rect in layout_info.get("source_fields", [])}
    source_buttons = layout_info.get("source_buttons", {})
    fields = [
        {
            "kind": "field",
            "name": name,
            "rect": rect,
            "hit_rects": (rect,),
            "draw_rects": (rect,),
            "source_rects": (source_fields[name],) if name in source_fields else (),
            "source_shapes": ("border",) if name in source_fields else (),
        }
        for name, rect in layout_info.get("fields", [])
    ]
    buttons = [
        {
            "kind": "button",
            "name": name,
            "rect": layout_info["buttons"][name],
            "hit_rects": (layout_info["buttons"][name],),
            "draw_rects": (layout_info["buttons"][name],),
            "source_rects": (source_buttons[name],) if name in source_buttons else (),
            "source_shapes": ("border",) if name in source_buttons else (),
        }
        for name in ACCOUNT_BUTTON_ORDER.get(state, ())
        if name in layout_info.get("buttons", {})
    ]

    profile_item = None
    if state in ("account_signup", "account_mypage", "account_edit"):
        profile_rect = layout_info.get("profile")
        profile_button = layout_info.get("profile_button")
        source_profile = layout_info.get("source_profile")
        source_profile_button = layout_info.get("source_profile_button")
        hit_rects = []
        draw_rects = []
        source_rects = []
        source_shapes = []
        if profile_rect:
            hit_rects.append(get_account_profile_hit_rect(profile_rect))
            draw_rects.append(profile_rect)
            if source_profile:
                source_rects.append(source_profile)
                source_shapes.append("profile")
        if profile_button:
            hit_rects.append(profile_button)
            draw_rects.append(profile_button)
            if source_profile_button:
                source_rects.append(source_profile_button)
                source_shapes.append("border")
        if hit_rects:
            profile_item = {
                "kind": "profile",
                "name": "profile",
                "rect": profile_button or profile_rect,
                "hit_rects": tuple(hit_rects),
                "draw_rects": tuple(draw_rects),
                "source_rects": tuple(source_rects),
                "source_shapes": tuple(source_shapes),
            }

    if state == "account_mypage":
        return ([profile_item] if profile_item else []) + buttons
    return fields + ([profile_item] if profile_item else []) + buttons


def get_account_focus_item(layout_info, state, focus_index):
    items = get_account_focus_items(layout_info, state)
    if not items:
        return None
    return items[max(0, min(focus_index, len(items) - 1))]


def get_account_hovered_focus_index(layout_info, state, mouse_pos, items=None):
    if items is None:
        items = get_account_focus_items(layout_info, state)
    for index, item in enumerate(items):
        if any(rect.collidepoint(mouse_pos) for rect in item.get("hit_rects", (item["rect"],))):
            return index
    return None


def draw_account_panel(game, state, draw_sea_background):
    draw_account_background(game, draw_sea_background)
    panel = get_account_panel_rect(game, state)
    image = game.images.get(ACCOUNT_PANEL_IMAGES.get(state, ""))
    if image:
        scaled = assets.get_scaled_image(game, image, panel.size)
        game.screen.blit(scaled, panel)
    else:
        surface = pygame.Surface(panel.size, pygame.SRCALPHA)
        surface.fill((7, 8, 9, 238))
        game.screen.blit(surface, panel)
        pygame.draw.rect(game.screen, (220, 164, 70), panel, 2, border_radius=8)
    return get_account_layout(game, state)


def draw_account_form_fields(game, layout_info, include_cursor=True):
    form = getattr(game, "account_form", {})
    focus_item = get_account_focus_item(
        layout_info,
        getattr(game, "game_state", ""),
        getattr(game, "account_focus_index", 0),
    )
    cursor = "|" if include_cursor and pygame.time.get_ticks() // 450 % 2 == 0 else ""
    for name, rect in layout_info.get("fields", []):
        text = form.get(name, "")
        if name == "password":
            text = "*" * len(text)
        if focus_item and focus_item["kind"] == "field" and focus_item["name"] == name:
            text = f"{text}{cursor}"
        color = (246, 218, 150) if text else (154, 119, 70)
        text_rect = rect.inflate(-max(20, rect.width // 20), -max(4, rect.height // 8))
        if getattr(game, "game_state", "") == "account_login":
            inset = max(54, rect.width // 11)
            text_rect.left += inset
            text_rect.width = max(1, text_rect.width - inset)
        draw_account_field_value(game, text, max(24, rect.height // 2), color, text_rect)


def draw_account_field_value(game, text, size, color, rect):
    text = str(text)
    current_size = size
    while current_size > 12:
        font = get_right_ui_font(game, current_size, True)
        if font.size(text)[0] <= rect.width and font.get_height() <= rect.height:
            break
        current_size -= 1

    font = get_right_ui_font(game, current_size, True)
    text = trim_text_to_width(font, text, rect.width)
    image = font.render(text, True, color)
    image_rect = image.get_rect()
    image_rect.midleft = (rect.left, rect.centery)
    game.screen.blit(image, image_rect)


def draw_account_message(game, layout_info):
    message = getattr(game, "account_message_text", "")
    if not message:
        last_error = account_store.get_last_error()
        if last_error and game.game_state in ("account_login", "account_signup"):
            if account_store.use_api_store():
                message = last_error
            else:
                message = "game.env API 주소 또는 MySQL 설정이 필요합니다"
        else:
            return
    panel = layout_info["panel"]
    color = (128, 238, 166) if getattr(game, "account_message_ok", False) else (255, 154, 126)
    rect = pygame.Rect(panel.left + panel.width // 4, panel.bottom - max(130, panel.height // 8), panel.width // 2, max(26, panel.height // 34))
    draw_text_fit_in_rect(game, message, max(14, rect.height - 2), color, rect, True, True, get_right_ui_font)


def draw_account_button_feedback(game, layout_info):
    mouse_pos = pygame.mouse.get_pos()
    fields_count = len(layout_info.get("fields", []))
    button_focus_index = getattr(game, "account_focus_index", 0) - fields_count
    for index, rect in enumerate(layout_info.get("buttons", {}).values()):
        draw_soft_focus_frame(game, rect, selected=index == button_focus_index, hovered=rect.collidepoint(mouse_pos), radius=8)


def draw_account_profile_image(game, layout_info):
    rect = layout_info.get("profile") if layout_info else None
    if not rect:
        return
    user = account_store.current_user(game)
    photo = get_account_profile_surface(game, user)
    if photo:
        draw_profile_photo_in_frame(game, photo, get_account_profile_photo_rect(rect))
        image = game.images.get(layout_info.get("image_key", ""))
        source_rect = layout_info.get("source_profile")
        if image and source_rect:
            draw_profile_frame_overlay(game, image, source_rect, rect)


def get_account_profile_surface(game, user=None):
    image_bytes = getattr(game, "account_profile_upload_bytes", None)
    if image_bytes is None and user:
        image_bytes = user.get("profile_image_data")
    if not image_bytes:
        return None

    key = hash(image_bytes)
    if getattr(game, "_account_profile_surface_key", None) == key:
        return getattr(game, "_account_profile_surface", None)

    try:
        surface = pygame.image.load(BytesIO(image_bytes)).convert_alpha()
    except pygame.error:
        return None

    game._account_profile_surface_key = key
    game._account_profile_surface = surface
    return surface


def draw_profile_photo_in_frame(game, photo, photo_rect):
    if photo_rect.width <= 0 or photo_rect.height <= 0:
        return

    local_rect = pygame.Rect(0, 0, photo_rect.width, photo_rect.height)
    cover_rect = get_image_cover_rect_in_rect(photo, local_rect)
    scaled = assets.get_scaled_image(game, photo, cover_rect.size)

    circle = pygame.Surface(photo_rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(circle, (9, 10, 10, 255), local_rect)
    circle.blit(scaled, cover_rect)
    mask = pygame.Surface(photo_rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(mask, (255, 255, 255, 255), mask.get_rect())
    circle.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    game.screen.blit(circle, photo_rect)


def get_account_profile_photo_rect(frame_rect):
    diameter = int(min(frame_rect.width, frame_rect.height) * 0.91)
    rect = pygame.Rect(0, 0, max(1, diameter), max(1, diameter))
    rect.center = (frame_rect.centerx, frame_rect.top + int(frame_rect.height * 0.635))
    return rect


def get_profile_button_photo_rect(frame_rect):
    diameter = int(min(frame_rect.width, frame_rect.height) * 0.74)
    rect = pygame.Rect(0, 0, max(1, diameter), max(1, diameter))
    rect.center = (frame_rect.centerx, frame_rect.top + int(frame_rect.height * 0.54))
    return rect


def get_profile_frame_overlay_patch(game, image, source_rect, size):
    cache = getattr(game, "account_profile_frame_overlay_cache", None)
    if cache is None:
        cache = {}
        game.account_profile_frame_overlay_cache = cache

    width, height = max(1, int(size[0])), max(1, int(size[1]))
    source_rect = source_rect.clip(image.get_rect())
    key = (id(image), source_rect.x, source_rect.y, source_rect.width, source_rect.height, width, height)
    if key in cache:
        return cache[key]
    if source_rect.width <= 0 or source_rect.height <= 0:
        return None

    patch = image.subsurface(source_rect).copy()
    raw = pygame.image.tostring(patch, "RGBA")
    patch_image = Image.frombytes("RGBA", patch.get_size(), raw)
    overlay = Image.new("RGBA", patch_image.size, (0, 0, 0, 0))
    overlay_pixels = []
    for red, green, blue, alpha in patch_image.getdata():
        gold_score = min(red - blue, green - blue, red - green + 96)
        if alpha > 8 and red > 58 and green > 42 and gold_score > 16 and red + green > 126:
            overlay_pixels.append((red, green, blue, alpha))
        else:
            overlay_pixels.append((0, 0, 0, 0))
    overlay.putdata(overlay_pixels)

    surface = pygame.image.fromstring(overlay.tobytes(), overlay.size, "RGBA").convert_alpha()
    scaled = pygame.transform.smoothscale(surface, (width, height))
    if len(cache) >= 32:
        cache.clear()
    cache[key] = scaled
    return scaled


def draw_profile_frame_overlay(game, image, source_rect, draw_rect):
    overlay = get_profile_frame_overlay_patch(game, image, source_rect, draw_rect.size)
    if overlay:
        game.screen.blit(overlay, draw_rect)


def get_account_profile_crop_layout(game):
    screen_rect = game.screen.get_rect()
    panel = screen_rect.inflate(-max(40, game.pad_width // 10), -max(38, game.pad_height // 10))
    panel.width = min(panel.width, 1180)
    panel.height = min(panel.height, 760)
    panel.center = screen_rect.center

    margin = max(22, panel.width // 30)
    title_rect = pygame.Rect(panel.left + margin, panel.top + 20, panel.width - margin * 2, 54)
    button_height = max(58, panel.height // 11)
    bottom_y = panel.bottom - margin - button_height
    content_top = title_rect.bottom + 18
    content_bottom = bottom_y - 22

    preview_size = min(panel.height - 150, int(panel.width * 0.56), content_bottom - content_top)
    preview = pygame.Rect(panel.left + margin, content_top, preview_size, preview_size)

    side_left = preview.right + margin
    side_width = panel.right - margin - side_left
    circle_size = min(side_width, max(190, preview_size // 2))
    circle = pygame.Rect(0, 0, circle_size, circle_size)
    circle.center = (side_left + side_width // 2, preview.centery - preview_size // 10)

    button_width = min(max(190, panel.width // 5), (panel.width - margin * 3) // 2)
    confirm = pygame.Rect(0, 0, button_width, button_height)
    cancel = pygame.Rect(0, 0, button_width, button_height)
    confirm.midbottom = (panel.centerx - button_width // 2 - margin // 2, panel.bottom - margin)
    cancel.midbottom = (panel.centerx + button_width // 2 + margin // 2, panel.bottom - margin)

    return {
        "panel": panel,
        "title": title_rect,
        "preview": preview,
        "circle": circle,
        "confirm": confirm,
        "cancel": cancel,
    }


def get_account_crop_image_rect(game, preview_rect):
    surface = getattr(game, "account_crop_surface", None)
    if surface is None or surface.get_width() <= 0 or surface.get_height() <= 0:
        return pygame.Rect(preview_rect)

    scale = min(preview_rect.width / surface.get_width(), preview_rect.height / surface.get_height())
    width = max(1, int(surface.get_width() * scale))
    height = max(1, int(surface.get_height() * scale))
    rect = pygame.Rect(0, 0, width, height)
    rect.center = preview_rect.center
    return rect


def get_account_crop_screen_rect(game, preview_rect):
    box = getattr(game, "account_crop_box", None)
    surface = getattr(game, "account_crop_surface", None)
    if not box or surface is None:
        return pygame.Rect(preview_rect)

    image_rect = get_account_crop_image_rect(game, preview_rect)
    scale = image_rect.width / max(1, surface.get_width())
    left, top, side = box
    return pygame.Rect(
        int(image_rect.left + left * scale),
        int(image_rect.top + top * scale),
        max(1, int(side * scale)),
        max(1, int(side * scale)),
    )


def draw_account_crop_preview(game, preview_rect):
    surface = getattr(game, "account_crop_surface", None)
    if surface is None:
        return

    pygame.draw.rect(game.screen, (8, 8, 8), preview_rect, border_radius=4)
    image_rect = get_account_crop_image_rect(game, preview_rect)
    draw_image_contain_in_rect(game, surface, preview_rect)
    crop_rect = get_account_crop_screen_rect(game, preview_rect)

    shade_color = (0, 0, 0, 150)
    shade_rects = (
        pygame.Rect(image_rect.left, image_rect.top, image_rect.width, max(0, crop_rect.top - image_rect.top)),
        pygame.Rect(image_rect.left, crop_rect.bottom, image_rect.width, max(0, image_rect.bottom - crop_rect.bottom)),
        pygame.Rect(image_rect.left, crop_rect.top, max(0, crop_rect.left - image_rect.left), crop_rect.height),
        pygame.Rect(crop_rect.right, crop_rect.top, max(0, image_rect.right - crop_rect.right), crop_rect.height),
    )
    for rect in shade_rects:
        if rect.width > 0 and rect.height > 0:
            shade = pygame.Surface(rect.size, pygame.SRCALPHA)
            shade.fill(shade_color)
            game.screen.blit(shade, rect)

    pygame.draw.rect(game.screen, (255, 218, 112), crop_rect, 3, border_radius=6)
    pygame.draw.ellipse(game.screen, (255, 235, 164), crop_rect.inflate(-4, -4), 2)
    pygame.draw.rect(game.screen, (85, 56, 20), preview_rect, 2, border_radius=4)


def draw_account_crop_circle_preview(game, circle_rect):
    surface = getattr(game, "account_crop_surface", None)
    box = getattr(game, "account_crop_box", None)
    if surface is None or not box:
        return

    left, top, side = [int(value) for value in box]
    source_rect = pygame.Rect(left, top, side, side)
    source_rect.clamp_ip(surface.get_rect())
    source_rect.width = min(source_rect.width, surface.get_width() - source_rect.left)
    source_rect.height = min(source_rect.height, surface.get_height() - source_rect.top)
    if source_rect.width <= 0 or source_rect.height <= 0:
        return

    cropped = surface.subsurface(source_rect).copy()
    scaled = pygame.transform.smoothscale(cropped, circle_rect.size)
    circle = pygame.Surface(circle_rect.size, pygame.SRCALPHA)
    circle.blit(scaled, (0, 0))
    mask = pygame.Surface(circle_rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(mask, (255, 255, 255, 255), mask.get_rect())
    circle.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    game.screen.blit(circle, circle_rect)
    pygame.draw.ellipse(game.screen, (255, 220, 112), circle_rect, 3)
    pygame.draw.ellipse(game.screen, (90, 58, 18), circle_rect.inflate(10, 10), 2)


def draw_account_profile_crop(game, draw_sea_background):
    draw_account_background(game, draw_sea_background)
    layout_info = get_account_profile_crop_layout(game)
    panel = layout_info["panel"]

    panel_surface = pygame.Surface(panel.size, pygame.SRCALPHA)
    panel_surface.fill((8, 9, 10, 238))
    game.screen.blit(panel_surface, panel)
    pygame.draw.rect(game.screen, (229, 176, 72), panel, 3, border_radius=8)
    pygame.draw.rect(game.screen, (86, 55, 21), panel.inflate(-18, -18), 1, border_radius=6)

    draw_text_fit_in_rect(game, "프로필 사진 편집", 42, (246, 218, 150), layout_info["title"], True, True, get_right_ui_font)
    draw_account_crop_preview(game, layout_info["preview"])
    draw_account_crop_circle_preview(game, layout_info["circle"])

    focus_index = max(0, min(getattr(game, "account_crop_focus_index", 0), 1))
    draw_menu_mode_button(
        game,
        layout_info["confirm"],
        "업로드",
        focus_index == 0,
        layout_info["confirm"].collidepoint(pygame.mouse.get_pos()),
    )
    draw_menu_mode_button(
        game,
        layout_info["cancel"],
        "취소",
        focus_index == 1,
        layout_info["cancel"].collidepoint(pygame.mouse.get_pos()),
    )


def get_account_focus_patch(game, image, source_rect, size, shape="border"):
    cache = getattr(game, "account_focus_patch_cache", None)
    if cache is None:
        cache = {}
        game.account_focus_patch_cache = cache

    width, height = max(1, int(size[0])), max(1, int(size[1]))
    key = (id(image), source_rect.x, source_rect.y, source_rect.width, source_rect.height, width, height, shape)
    if key in cache:
        return cache[key]

    source_rect = source_rect.clip(image.get_rect())
    if source_rect.width <= 0 or source_rect.height <= 0:
        return None

    patch = image.subsurface(source_rect).copy()
    raw = pygame.image.tostring(patch, "RGBA")
    patch_image = Image.frombytes("RGBA", patch.get_size(), raw)
    highlight = Image.new("RGBA", patch_image.size, (0, 0, 0, 0))
    highlight_pixels = []
    source_width, source_height = patch_image.size
    border_margin = max(6, min(source_width, source_height) // 9)
    center_x = source_width / 2
    center_y = source_height / 2
    ring_radius = min(source_width, source_height) * 0.4
    ring_width = max(14, min(source_width, source_height) * 0.09)
    for index, (red, green, blue, alpha) in enumerate(patch_image.getdata()):
        x = index % source_width
        y = index // source_width
        if shape == "profile":
            distance = math.hypot(x - center_x, y - center_y)
            in_focus_band = abs(distance - ring_radius) <= ring_width
        else:
            in_focus_band = (
                x < border_margin
                or x >= source_width - border_margin
                or y < border_margin
                or y >= source_height - border_margin
            )

        gold_score = min(red - blue, green - blue, red - green + 80)
        if in_focus_band and alpha > 8 and red > 58 and green > 42 and gold_score > 20 and red + green > 130:
            highlight_alpha = max(34, min(130, int((red + green) * 0.2 + gold_score * 0.8)))
            highlight_pixels.append((255, 205, 86, highlight_alpha))
        else:
            highlight_pixels.append((0, 0, 0, 0))
    highlight.putdata(highlight_pixels)
    highlight = pygame.image.fromstring(highlight.tobytes(), highlight.size, "RGBA").convert_alpha()
    scaled = pygame.transform.smoothscale(highlight, (width, height))
    if len(cache) >= 64:
        cache.clear()
    cache[key] = scaled
    return scaled


def draw_account_image_light(game, layout_info, source_rect, draw_rect, selected, hovered, shape="border"):
    image = game.images.get(layout_info.get("image_key", ""))
    if image is None or source_rect is None or draw_rect is None:
        return False

    patch = get_account_focus_patch(game, image, source_rect, draw_rect.size, shape)
    if patch is None:
        return False

    pulse = int(24 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180)))
    alpha = 188 + pulse if selected else 112
    offsets = ((0, 0),)
    if selected:
        offsets = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))

    for offset_x, offset_y in offsets:
        lit = patch.copy()
        lit.set_alpha(alpha if offset_x == 0 and offset_y == 0 else max(28, alpha // 4))
        game.screen.blit(lit, draw_rect.move(offset_x, offset_y))
    return True


def draw_account_focus_rect(game, rect, selected, hovered):
    pulse = int(14 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180)))
    alpha = 70 + pulse if selected else 42
    width = 3 if selected else 2
    border_radius = max(6, min(12, rect.height // 5))
    glow_rect = rect.inflate(2, 2)
    glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(glow, (255, 220, 112, alpha), glow.get_rect(), width, border_radius=border_radius)
    game.screen.blit(glow, glow_rect)


def draw_account_focus_indicators(game, layout_info, state):
    items = get_account_focus_items(layout_info, state)
    if not items:
        return

    focus_index = max(0, min(getattr(game, "account_focus_index", 0), len(items) - 1))
    hovered_index = get_account_hovered_focus_index(layout_info, state, pygame.mouse.get_pos(), items)
    for index, item in enumerate(items):
        selected = index == focus_index
        hovered = index == hovered_index
        if not selected and not hovered:
            continue
        drew_image_light = False
        source_shapes = item.get("source_shapes", ())
        for light_index, (source_rect, draw_rect) in enumerate(zip(item.get("source_rects", ()), item.get("draw_rects", ()))):
            shape = source_shapes[light_index] if light_index < len(source_shapes) else "border"
            drew_image_light = draw_account_image_light(game, layout_info, source_rect, draw_rect, selected, hovered, shape) or drew_image_light
        if not drew_image_light:
            draw_account_focus_rect(game, item["rect"], selected, hovered)


def draw_account_login(game, draw_sea_background):
    layout_info = draw_account_panel(game, "account_login", draw_sea_background)
    draw_account_form_fields(game, layout_info)
    draw_account_message(game, layout_info)
    draw_account_focus_indicators(game, layout_info, "account_login")


def draw_account_signup(game, draw_sea_background):
    layout_info = draw_account_panel(game, "account_signup", draw_sea_background)
    draw_account_profile_image(game, layout_info)
    draw_account_form_fields(game, layout_info)
    draw_account_message(game, layout_info)
    draw_account_focus_indicators(game, layout_info, "account_signup")


def draw_account_mypage(game, draw_sea_background):
    layout_info = draw_account_panel(game, "account_mypage", draw_sea_background)
    draw_account_profile_image(game, layout_info)
    user = account_store.current_user(game)
    if not user:
        draw_account_message(game, layout_info)
        return

    values = {
        "nickname": user["nickname"],
        "login_id": user["login_id"],
        "best_score": f"{int(user.get('best_score', 0)):,}",
        "stage": f"{int(user.get('unlocked_stage_count', 1))}단계 해금",
    }
    for key, value in values.items():
        rect = layout_info["values"].get(key)
        if rect:
            value_rect = rect.inflate(-max(22, rect.width // 24), -max(10, rect.height // 7))
            value_size = max(20, min(30, int(rect.height * 0.44)))
            draw_text_fit_visual_center_in_rect(game, value, value_size, (246, 218, 150), value_rect, True, get_right_ui_font)
    draw_account_focus_indicators(game, layout_info, "account_mypage")


def draw_account_edit(game, draw_sea_background):
    layout_info = draw_account_panel(game, "account_edit", draw_sea_background)
    draw_account_profile_image(game, layout_info)
    draw_account_form_fields(game, layout_info)
    draw_account_message(game, layout_info)
    draw_account_focus_indicators(game, layout_info, "account_edit")


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
    hovered_index = get_hovered_choice_index(game, len(choices), mouse_pos)
    focused_index = hovered_index if hovered_index is not None else selected_index
    for index, rect in enumerate(rects):
        augment_id = choices[index]
        data = augments.AUGMENTS[augment_id]
        current_stack = getattr(game, "augment_stacks", {}).get(augment_id, 0)
        hovered = hovered_index == index
        draw_augment_card(game, rect, index, augment_id, data, current_stack, hovered, index == focused_index)


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
    hovered_index = get_hovered_choice_index(game, len(choices), mouse_pos)
    focused_index = hovered_index if hovered_index is not None else selected_index
    for index, rect in enumerate(rects):
        choice = choices[index]
        image_key = choice.get("image_key") or choice.get("id", "")
        data = {
            "title": choice.get("title", ""),
            "description": choice.get("description", ""),
            "max_stack": 1,
        }
        hovered = hovered_index == index
        draw_augment_card(game, rect, index, image_key, data, 0, hovered, index == focused_index)


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
    hovered_index = get_hovered_choice_index(game, len(choices), mouse_pos)
    focused_index = hovered_index if hovered_index is not None else selected_index
    for index, rect in enumerate(rects):
        choice = choices[index]
        image_key = choice.get("image_key", choice.get("id", ""))
        hovered = hovered_index == index
        data = {
            "title": choice["title"],
            "description": choice["description"],
            "max_stack": 1,
        }
        draw_augment_card(game, rect, index, image_key, data, 0, hovered, index == focused_index)


# 선택지 개수 안에서 현재 키보드 선택 위치를 안전하게 가져옵니다.
# 화면을 그리는 도중 선택지 수가 바뀌어도 인덱스 오류가 나지 않게 막습니다.
def get_safe_choice_index(game, choice_count):
    if choice_count <= 0:
        game.choice_select_index = 0
        return 0

    game.choice_select_index = max(0, min(getattr(game, "choice_select_index", 0), choice_count - 1))
    return game.choice_select_index


def get_hovered_choice_index(game, choice_count, mouse_pos):
    for index, rect in enumerate(layout.get_choice_visual_rects(game, choice_count)):
        if rect.collidepoint(mouse_pos):
            game.choice_select_index = index
            return index
    return None


# 증강 카드 하나를 그립니다.
# title/description은 augments.py의 AUGMENTS 딕셔너리에서 가져옵니다.
def draw_augment_card(game, rect, index, augment_id, data, current_stack, hovered, selected=False):
    # 마우스 hover와 키보드 selected를 같은 강조 계열로 보여주어 현재 선택 위치를 한눈에 알 수 있게 합니다.
    active = hovered or selected
    image = game.images.get(augment_id)

    if image is None:
        return

    image_box = rect.inflate(*layout.CHOICE_IMAGE_INFLATE)
    if active:
        image_box.inflate_ip(56, 72)
    image_box.center = rect.center

    draw_image_contain_in_rect(game, image, image_box)


def get_stage_ready_card_image(game, stage_index):
    stage_number = stage_index + 1
    return game.images.get(f"출전 준비_{stage_number}") or game.images.get(f"출전 준비{stage_number}")


def get_stage_select_card_image(game, stage_index, unlocked, cleared, focused):
    stage_number = stage_index + 1
    if not unlocked:
        return game.images.get(f"잠금_{stage_number}")

    ready_img = get_stage_ready_card_image(game, stage_index)
    cleared_img = game.images.get(f"완료_{stage_number}")
    if focused:
        return ready_img or cleared_img
    if cleared:
        return cleared_img or ready_img
    return ready_img or cleared_img


def get_stage_card_draw_rect(game, rect, focused):
    if not focused:
        return rect

    draw_rect = rect.inflate(max(24, rect.width // 10), max(30, rect.height // 10))
    draw_rect.clamp_ip(game.screen.get_rect().inflate(-8, -8))
    return draw_rect


def get_stage_card_visual_rect(rect, card_img):
    if not card_img:
        return rect

    image_ratio = card_img.get_width() / max(1, card_img.get_height())
    draw_rect = rect.copy()
    draw_rect.height = int(draw_rect.width / image_ratio)
    if draw_rect.height > rect.height:
        draw_rect.height = rect.height
        draw_rect.width = int(draw_rect.height * image_ratio)
    draw_rect.center = rect.center
    return draw_rect


def get_focused_stage_card_rect(game, rect, card_img):
    draw_rect = get_stage_card_visual_rect(rect, card_img)
    draw_rect.inflate_ip(max(18, int(draw_rect.width * 0.12)), max(24, int(draw_rect.height * 0.12)))
    draw_rect.clamp_ip(game.screen.get_rect().inflate(-8, -8))
    return draw_rect


def draw_stage_card_glow(game, rect):
    for expand, alpha, width in ((34, 42, 7), (22, 78, 5), (10, 132, 3)):
        glow_rect = rect.inflate(expand, expand)
        glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            glow,
            (255, 218, 109, alpha),
            glow.get_rect().inflate(-width, -width),
            width,
            border_radius=14,
        )
        game.screen.blit(glow, glow_rect)

    edge_rect = rect.inflate(4, 4)
    pygame.draw.rect(game.screen, (255, 235, 154), edge_rect, 3, border_radius=10)


def draw_stage_card_focus_frame(game, rect):
    glow = pygame.Surface(rect.size, pygame.SRCALPHA)
    glow.fill((255, 221, 122, 26))
    game.screen.blit(glow, rect)
    pygame.draw.rect(game.screen, (255, 225, 137), rect, 3, border_radius=8)


def get_stage_select_screen_image_key(game, focused_index):
    cleared_count = campaign.get_cleared_stage_count(game)
    stage_number = focused_index + 1
    if cleared_count >= STAGE_MAX:
        return f"stage_select_complete_s{stage_number}"

    unlocked_count = campaign.get_unlocked_stage_count(game)
    stage_number = min(stage_number, unlocked_count)
    return f"stage_select_u{unlocked_count}_s{stage_number}"


def draw_stage_select_message(game):
    if game.message_timer <= 0 or not game.message_text:
        return

    message_rect = pygame.Rect(0, 0, min(720, int(game.pad_width * 0.84)), 46)
    message_rect.center = (game.pad_width // 2, game.pad_height - 64)
    message_layer = pygame.Surface(message_rect.size, pygame.SRCALPHA)
    message_layer.fill((20, 18, 16, 210))
    game.screen.blit(message_layer, message_rect)
    pygame.draw.rect(game.screen, (226, 186, 96), message_rect, 1, border_radius=8)
    draw_text(game, game.message_text, 18, YELLOW, message_rect.centerx, message_rect.centery, True, True)


def get_hovered_stage_select_index(game, rects):
    mouse_pos = pygame.mouse.get_pos()
    for stage_index, rect in enumerate(rects):
        if rect.collidepoint(mouse_pos) and campaign.is_stage_unlocked(game, stage_index):
            return stage_index
    return None


def draw_stage_select_focus_overlay(game, rects, focused_index):
    if focused_index < 0 or focused_index >= len(rects):
        return

    unlocked = campaign.is_stage_unlocked(game, focused_index)
    cleared = campaign.is_stage_cleared(game, focused_index)
    card_img = get_stage_select_card_image(game, focused_index, unlocked, cleared, True)
    if not card_img:
        return

    draw_rect = get_focused_stage_card_rect(game, rects[focused_index], card_img)
    draw_stage_card_glow(game, draw_rect)
    draw_image_contain_in_rect(game, card_img, draw_rect)
    pygame.draw.rect(game.screen, (255, 226, 126), draw_rect, 2, border_radius=8)


# 캠페인 스테이지 선택 화면을 그립니다.
# 제공된 이미지 카드와 하단 글귀 이미지를 그대로 쓰고, 현재 포커스 카드는 확대합니다.
def draw_stage_select(game, draw_sea_background):
    stage_count = len(story.STAGE_STORIES)
    selectable_count = campaign.get_unlocked_stage_count(game)
    rects = layout.get_stage_select_card_rects(game, stage_count)
    if not rects:
        return

    focused_index = max(0, min(getattr(game, "stage_select_index", 0), min(stage_count, selectable_count) - 1))
    hovered_index = get_hovered_stage_select_index(game, rects)
    if hovered_index is not None:
        focused_index = hovered_index
    game.stage_select_index = focused_index

    screen_image = game.images.get(get_stage_select_screen_image_key(game, focused_index))
    if screen_image:
        layout.draw_cover(game, screen_image)
        draw_stage_select_focus_overlay(game, rects, focused_index)
        draw_stage_select_message(game)
        return

    bg = game.images.get("배경")
    if bg:
        layout.draw_cover(game, bg)
    else:
        fallback_bg = assets.get_stage_select_image(game, "background")
        if fallback_bg:
            layout.draw_cover(game, fallback_bg)
        else:
            draw_sea_background(game)

    card_entries = []
    for index, rect in enumerate(rects):
        unlocked = campaign.is_stage_unlocked(game, index)
        cleared = campaign.is_stage_cleared(game, index)
        focused = index == focused_index
        card_img = get_stage_select_card_image(game, index, unlocked, cleared, focused)
        card_entries.append((focused, rect, card_img))

    for focused, rect, card_img in sorted(card_entries, key=lambda entry: entry[0]):
        draw_rect = get_stage_card_draw_rect(game, rect, focused)
        if card_img:
            draw_image_cover_in_rect(game, card_img, draw_rect)
            if focused:
                draw_stage_card_focus_frame(game, draw_rect)
        else:
            locked_surf = pygame.Surface(draw_rect.size, pygame.SRCALPHA)
            locked_surf.fill((12, 14, 18, 210))
            game.screen.blit(locked_surf, draw_rect)
            pygame.draw.rect(game.screen, (70, 74, 86), draw_rect, 1, border_radius=6)

    quote_img = game.images.get(f"글귀_{focused_index + 1}")
    if quote_img:
        draw_image_contain_in_rect(game, quote_img, layout.get_stage_select_quote_rect(game))

    draw_stage_select_message(game)


# 난중일기/해전 브리핑 화면을 그립니다.
# 실제 문장 데이터는 story.py에 있고, 여기서는 보기 좋게 배치만 합니다.
def draw_story(game, draw_sea_background):
    diary_image = game.images.get("story_diary_horizontal")
    game.screen.fill((8, 6, 4))
    # story_stage1_page1.png, story_stage1.png, story_background.png 순서로 스토리 배경을 찾습니다.
    if getattr(game, "story_id", "intro") == "intro":
        story_background = assets.get_story_image(game, "intro")
    else:
        story_background = assets.get_story_image(game, "background")

    if story_background:
        layout.draw_cover(game, story_background)
    elif not diary_image:
        fallback = pygame.Surface((game.pad_width, game.pad_height))
        fallback.fill((28, 22, 16))
        game.screen.blit(fallback, (0, 0))

    # 배경 위에 어두운 반투명 막을 덮어 글자가 잘 보이게 합니다.
    shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 120))
    game.screen.blit(shade, (0, 0))

    data = story.get_current_story(game)
    # 가로 일기지 이미지가 있으면 더 넓은 편지지 비율로 패널을 잡습니다.
    # 없으면 기존 어두운 패널 크기를 사용합니다.
    if diary_image:
        panel = game.screen.get_rect()
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

    draw_text(game, data["kicker"], 17, accent_color, x, y, False, True, get_story_font)
    # 여러 편 스토리 구조일 때 현재 몇 편을 보고 있는지 작게 표시합니다.
    page_text = f"{story.get_current_story_page_index(game) + 1}/{story.get_story_page_count(game)}"
    draw_text(game, page_text, 15, sub_color, panel.right - margin - 42, y + 1, False, True, get_story_font)
    y += 28
    draw_text(game, data["title"], title_size, main_color, x, y, False, True, get_story_font)
    y += title_size + 18
    draw_text(game, data["date"], 18, accent_color if diary_image else BLUE, x, y, False, True, get_story_font)
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
    quote_y = draw_wrapped_text(game, visible_quote, quote_size, main_color, quote_rect, 4, True, get_story_font)
    y = max(y + 82, quote_y + 12)

    for line in visible_lines:
        line_rect = pygame.Rect(x, y, content_width, 90)
        y = draw_wrapped_text(game, line, body_size, sub_color, line_rect, 5, False, get_story_font)
        y += 10

    footer_y = panel.bottom - margin - 48
    next_text = story.get_story_next_text(game)
    draw_text(game, next_text, 18, main_color, x, footer_y, False, True, get_story_font)
    prompt_font = get_story_font(game, 16, True)
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
    result = getattr(game, "stage_result", {}) or {}
    if result_background:
        drawn_rect, _ = layout.draw_cover(game, result_background)
        draw_stage_result_image_values(game, result, drawn_rect, result_background.get_size())
        return
    else:
        draw_sea_background(game)

    # 배경 위에 반투명 어두운 막을 깔아 결과 글자가 잘 보이게 합니다.
    shade = pygame.Surface((game.pad_width, game.pad_height), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 132))
    game.screen.blit(shade, (0, 0))

    # 결과 데이터가 없더라도 화면이 깨지지 않게 빈 딕셔너리를 기본값으로 사용합니다.
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


def draw_stage_result_image_values(game, result, drawn_rect, source_size):
    values = {
        "score": f"{int(result.get('score', 0)):,}점",
        "play_time": format_result_time(result.get("play_time_seconds", 0)),
        "shots": f"{int(result.get('shots_fired', 0)):,}회",
        "hits": f"{int(result.get('hits_taken', 0)):,}회",
        "total_score": f"{int(result.get('total_score', result.get('score', 0))):,}점",
    }
    value_color = (250, 218, 149)
    shadow_color = (25, 16, 8)
    font_size = max(24, int(drawn_rect.height * 0.043))
    total_font_size = max(32, int(drawn_rect.height * 0.056))

    for key, text in values.items():
        rect = scale_source_rect(drawn_rect, source_size, STAGE_RESULT_VALUE_RECTS[key])
        size = total_font_size if key == "total_score" else font_size
        shadow_rect = rect.move(max(1, drawn_rect.width // 900), max(1, drawn_rect.height // 900))
        draw_text_fit_visual_center_in_rect(game, text, size, shadow_color, shadow_rect, True, get_story_font)
        draw_text_fit_visual_center_in_rect(game, text, size, value_color, rect, True, get_story_font)


def format_result_time(seconds):
    try:
        total_seconds = max(0, int(round(float(seconds))))
    except (TypeError, ValueError):
        total_seconds = 0
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


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


def get_leaderboard_background(game):
    if game.pad_width >= game.pad_height:
        return game.images.get("leaderboard_background") or game.images.get("leaderboard_background_vertical")
    return game.images.get("leaderboard_background_vertical") or game.images.get("leaderboard_background")


def get_horizontal_leaderboard_background(game):
    return game.images.get("leaderboard_background") or game.images.get("leaderboard_background_vertical")


def get_vertical_leaderboard_background(game):
    return game.images.get("leaderboard_background_vertical") or game.images.get("leaderboard_background")


def scale_source_rect(drawn_rect, source_size, rect):
    source_w, source_h = source_size
    x, y, width, height = rect
    scale_x = drawn_rect.width / source_w
    scale_y = drawn_rect.height / source_h
    return pygame.Rect(
        drawn_rect.left + int(x * scale_x),
        drawn_rect.top + int(y * scale_y),
        max(1, int(width * scale_x)),
        max(1, int(height * scale_y)),
    )


def get_leaderboard_layout(game, drawn_rect, source_size):
    if source_size[0] >= source_size[1]:
        row_centers = [320, 389, 456, 518, 575, 631, 688, 746, 802, 862]
        return {
            "name_rects": [scale_source_rect(drawn_rect, source_size, (575, y - 22, 315, 44)) for y in row_centers],
            "score_rects": [scale_source_rect(drawn_rect, source_size, (940, y - 22, 190, 44)) for y in row_centers],
            "row_rects": [scale_source_rect(drawn_rect, source_size, (370, y - 25, 790, 50)) for y in row_centers],
            "status": scale_source_rect(drawn_rect, source_size, (450, 910, 640, 44)),
            "font_name": max(18, int(drawn_rect.height * 0.031)),
            "font_score": max(18, int(drawn_rect.height * 0.031)),
            "font_status": max(14, int(drawn_rect.height * 0.021)),
        }

    row_centers = [491, 586, 679, 764, 844, 922, 999, 1075, 1151, 1229]
    return {
        "name_rects": [scale_source_rect(drawn_rect, source_size, (360, y - 28, 280, 56)) for y in row_centers],
        "score_rects": [scale_source_rect(drawn_rect, source_size, (675, y - 28, 170, 56)) for y in row_centers],
        "row_rects": [scale_source_rect(drawn_rect, source_size, (158, y - 35, 706, 70)) for y in row_centers],
        "status": scale_source_rect(drawn_rect, source_size, (210, 1360, 604, 52)),
        "font_name": max(16, int(drawn_rect.height * 0.023)),
        "font_score": max(16, int(drawn_rect.height * 0.023)),
        "font_status": max(13, int(drawn_rect.height * 0.017)),
    }


def refresh_leaderboard_entries(game, force=False):
    now = pygame.time.get_ticks() / 1000.0
    interval = max(30.0, float(getattr(game, "leaderboard_sync_interval", 300.0)))
    cached_entries = getattr(game, "leaderboard_entries", [])
    next_sync_at = float(getattr(game, "leaderboard_next_sync_at", 0.0))
    if force or not cached_entries or now >= next_sync_at:
        cached_entries = scoreboard.load_scores()
        game.leaderboard_entries = cached_entries
        game.leaderboard_next_sync_at = now + interval
    return cached_entries


def draw_leaderboard_entries(game, drawn_rect, source_size, show_status=True, entries=None, allow_refresh=True):
    if entries is None:
        entries = refresh_leaderboard_entries(game) if allow_refresh else getattr(game, "leaderboard_entries", [])
    layout_info = get_leaderboard_layout(game, drawn_rect, source_size)
    last_rank = getattr(game, "leaderboard_last_rank", None)

    for index in range(scoreboard.MAX_ENTRIES):
        rank = index + 1
        if rank == last_rank:
            highlight = pygame.Surface(layout_info["row_rects"][index].size, pygame.SRCALPHA)
            highlight.fill((255, 214, 103, 46))
            game.screen.blit(highlight, layout_info["row_rects"][index])

        if index >= len(entries):
            continue
        entry = entries[index]
        draw_text_fit_in_rect(game, entry["nickname"], layout_info["font_name"], DIARY_INK, layout_info["name_rects"][index], True, True, get_story_font)
        draw_text_fit_in_rect(game, f"{entry['score']:,}", layout_info["font_score"], DIARY_INK, layout_info["score_rects"][index], True, True, get_story_font)

    if not show_status:
        return

    nickname = getattr(game, "score_nickname", scoreboard.DEFAULT_NICKNAME)
    score = int(getattr(game, "score", 0))
    if last_rank:
        status = f"{nickname}  {score:,}점  {last_rank}위"
    else:
        status = f"{nickname}  {score:,}점"
    draw_text_fit_in_rect(game, status, layout_info["font_status"], DIARY_MUTED_INK, layout_info["status"], True, True, get_story_font)


def draw_leaderboard(game, draw_sea_background, background=None, show_status=True):
    background = background or get_leaderboard_background(game)
    if background:
        drawn_rect, _ = layout.draw_cover(game, background)
        source_size = background.get_size()
    else:
        draw_sea_background(game)
        drawn_rect = game.screen.get_rect()
        source_size = (game.pad_width, game.pad_height)

    draw_leaderboard_entries(game, drawn_rect, source_size, show_status)


def get_score_leaderboard_start_button_rect(game):
    background = get_horizontal_leaderboard_background(game)
    if background:
        drawn_rect, _ = layout.get_cover_rect(game, background)
        return scale_source_rect(drawn_rect, background.get_size(), SCORE_LEADERBOARD_START_BUTTON_SOURCE_RECT)

    rect = pygame.Rect(0, 0, min(420, int(game.pad_width * 0.48)), 76)
    rect.center = (game.pad_width // 2, int(game.pad_height * 0.88))
    return rect


def draw_score_leaderboard_start(game, draw_sea_background):
    draw_leaderboard(game, draw_sea_background, get_horizontal_leaderboard_background(game), show_status=False)

    button_rect = get_score_leaderboard_start_button_rect(game)
    start_button = game.images.get("menu_start_button")
    if start_button:
        image_rect = button_rect.inflate(-max(14, button_rect.width // 14), -max(6, button_rect.height // 8))
        draw_image_content_contain_in_rect(game, start_button, image_rect)
    else:
        pygame.draw.rect(game.screen, (128, 76, 34), button_rect, border_radius=8)
        draw_text_fit_in_rect(game, "게임 시작", max(24, button_rect.height // 2), WHITE, button_rect, True, True, get_story_font)

    hovered = button_rect.collidepoint(pygame.mouse.get_pos())
    overlay = pygame.Surface(button_rect.size, pygame.SRCALPHA)
    overlay.fill((255, 224, 145, 36 if hovered else 18))
    game.screen.blit(overlay, button_rect)
    pygame.draw.rect(game.screen, (255, 225, 137), button_rect, 4 if hovered else 2, border_radius=8)


# 게임오버 또는 클리어 화면을 그립니다.
# clear 값에 따라 제목과 안내 문구가 달라집니다.
def draw_end_screen(game, clear, draw_sea_background):
    # end_result는 actors.end_game()에서 results.py가 만든 최종 전투 기록입니다.
    result = getattr(game, "end_result", {}) or {}
    result_background = assets.get_stage_result_image(game, "background")
    if result_background:
        drawn_rect, _ = layout.draw_cover(game, result_background)
        draw_stage_result_image_values(game, result, drawn_rect, result_background.get_size())
        return

    draw_sea_background(game)
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
    else:
        draw_top_hud(game)

    draw_boss_hp_bar(game)


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


# 보스 전용 HP바를 플레이 영역 상단에 고정해서 그립니다.
def draw_boss_hp_bar(game):
    if game.boss is None:
        return

    frame_rect = layout.get_boss_hp_bar_rect(game)
    frame_image = assets.get_stage_image(game, "boss_hp")
    hp_ratio = max(0.0, min(1.0, game.boss["hp"] / max(1, game.boss["maxHp"])))
    fill_rect = get_boss_hp_fill_rect(game, frame_rect)

    if frame_image:
        scaled_frame = assets.get_scaled_image(game, frame_image, frame_rect.size)
        game.screen.blit(scaled_frame, frame_rect)
        missing_width = fill_rect.width - int(fill_rect.width * hp_ratio)
        if missing_width > 0:
            missing_rect = pygame.Rect(fill_rect.right - missing_width, fill_rect.top, missing_width, fill_rect.height)
            overlay = pygame.Surface(missing_rect.size, pygame.SRCALPHA)
            overlay.fill((7, 5, 5, 205))
            game.screen.blit(overlay, missing_rect)
    else:
        fill_image = assets.get_stage_image(game, "boss_hp_fill")
        pygame.draw.rect(game.screen, (10, 11, 15), frame_rect, border_radius=max(6, frame_rect.height // 4))
        pygame.draw.rect(game.screen, (202, 151, 62), frame_rect, 2, border_radius=max(6, frame_rect.height // 4))
        pygame.draw.rect(game.screen, (11, 8, 8), fill_rect, border_radius=max(2, fill_rect.height // 3))
        visible_width = int(fill_rect.width * hp_ratio)
        if visible_width > 0:
            if fill_image:
                scaled_fill = assets.get_scaled_image(game, fill_image, fill_rect.size)
                fill_crop = scaled_fill.subsurface(pygame.Rect(0, 0, visible_width, fill_rect.height)).copy()
                game.screen.blit(fill_crop, fill_rect.topleft)
            else:
                active_rect = fill_rect.copy()
                active_rect.width = visible_width
                pygame.draw.rect(game.screen, RED, active_rect, border_radius=max(2, fill_rect.height // 3))

    if game.boss.get("maxShield", 0) > 0:
        shield_ratio = max(0.0, min(1.0, game.boss.get("shield", 0) / max(1, game.boss["maxShield"])))
        shield_rect = pygame.Rect(fill_rect.left, frame_rect.bottom + 2, fill_rect.width, max(4, frame_rect.height // 13))
        pygame.draw.rect(game.screen, (12, 24, 34), shield_rect, border_radius=shield_rect.height // 2)
        shield_fill = shield_rect.copy()
        shield_fill.width = int(shield_rect.width * shield_ratio)
        pygame.draw.rect(game.screen, BLUE, shield_fill, border_radius=shield_rect.height // 2)


# 이미지별 장식 폭이 달라서 HP색이 들어갈 중앙 슬롯만 따로 계산합니다.
def get_boss_hp_fill_rect(game, frame_rect):
    stage_index = getattr(game, "stage_index", 0)
    stage_phase = getattr(game, "stage_phase", 0)
    ratio_by_stage = {
        (0, 0): (0.14, 0.39, 0.80, 0.26),
        (0, 1): (0.235, 0.41, 0.69, 0.23),
        (1, None): (0.205, 0.42, 0.70, 0.21),
        (2, None): (0.255, 0.42, 0.64, 0.22),
        (3, None): (0.245, 0.42, 0.65, 0.22),
        (4, None): (0.235, 0.42, 0.68, 0.22),
    }
    left_ratio, top_ratio, width_ratio, height_ratio = ratio_by_stage.get(
        (stage_index, stage_phase),
        ratio_by_stage.get((stage_index, None), (0.235, 0.43, 0.68, 0.20)),
    )

    height = max(10, int(frame_rect.height * height_ratio))
    rect = pygame.Rect(
        frame_rect.left + int(frame_rect.width * left_ratio),
        frame_rect.top + int(frame_rect.height * top_ratio),
        int(frame_rect.width * width_ratio),
        height,
    )
    rect.centery = frame_rect.top + int(frame_rect.height * (top_ratio + height_ratio * 0.5))
    return rect


# 넓은 화면용 사이드 HUD입니다.
# 중앙 플레이 영역을 가리지 않도록 오른쪽 바깥 영역에 핵심 정보를 모아 표시합니다.
# 왼쪽 바깥 영역은 다음 UI 확장을 위해 비워 둡니다.
def draw_side_hud(game):
    left_area, right_area = layout.get_side_areas(game)
    if augments.is_score_mode(game):
        draw_score_mode_left_leaderboard(game, left_area)
    else:
        draw_story_summary_panel(game, left_area)
    draw_right_status_panel(game, right_area)


def draw_score_mode_left_leaderboard(game, left_area):
    if left_area.width < 120 or left_area.height < 160:
        return

    panel = left_area.copy()
    snapshot_entries = getattr(game, "score_mode_leaderboard_snapshot", []) or getattr(game, "leaderboard_entries", [])
    background = get_vertical_leaderboard_background(game)
    if background:
        old_clip = game.screen.get_clip()
        game.screen.set_clip(panel)
        drawn_rect = get_image_cover_rect_in_rect(background, panel)
        scaled = assets.get_scaled_image(game, background, drawn_rect.size)
        game.screen.blit(scaled, drawn_rect)
        draw_leaderboard_entries(game, drawn_rect, background.get_size(), show_status=True, entries=snapshot_entries, allow_refresh=False)
        game.screen.set_clip(old_clip)
    else:
        draw_side_panel(game, panel)
        entries = snapshot_entries
        title_rect = pygame.Rect(panel.left + 12, panel.top + 12, panel.width - 24, 28)
        draw_text_fit_in_rect(game, "명예의 기록", 20, YELLOW, title_rect, True, True, get_story_font)
        y = title_rect.bottom + 8
        row_height = max(22, (panel.height - 70) // scoreboard.MAX_ENTRIES)
        for index, entry in enumerate(entries[:scoreboard.MAX_ENTRIES]):
            row = pygame.Rect(panel.left + 10, y + index * row_height, panel.width - 20, row_height)
            draw_text_fit_in_rect(game, f"{index + 1}. {entry['nickname']} {entry['score']:,}", 14, WHITE, row, True, True, get_story_font)


def draw_right_status_panel(game, right_area):
    if right_area.width < 80 or right_area.height < 160:
        return

    panel = right_area.copy()
    if panel.width <= 0 or panel.height <= 0:
        return

    game.screen.fill((5, 9, 17), panel)

    ui_image = game.images.get("right_ui_panel")
    if ui_image:
        drawn_rect = draw_right_ui_background(game, ui_image, panel)
        source_size = ui_image.get_size()
    else:
        draw_side_panel(game, panel)
        drawn_rect = panel
        source_size = RIGHT_UI_SOURCE_SIZE

    sections = {
        name: scale_right_ui_rect(drawn_rect, source_size, source_rect, panel)
        for name, source_rect in RIGHT_UI_SECTIONS.items()
    }
    fonts = get_right_ui_fonts(drawn_rect, source_size)
    draw_right_ui_header_section(game, sections["header"], fonts)
    draw_stage_info_section(game, sections["stage"], fonts)
    draw_score_section(game, sections["score"], fonts)
    draw_hp_section(game, sections["hp"], fonts)
    draw_skill_icon_section(game, drawn_rect, source_size, panel, fonts)
    draw_acquired_augments_section(game, sections["augments"], fonts)
    draw_current_stats_section(game, sections["stats"], fonts)


def draw_right_ui_background(game, image, panel):
    # 좌우 장식이 잘리지 않도록 cover crop 대신 패널 크기에 맞춰 전체 UI를 그립니다.
    scaled = assets.get_scaled_image(game, image, panel.size)
    game.screen.blit(scaled, panel)
    return panel


def scale_right_ui_rect(drawn_rect, source_size, source_rect, clip_rect):
    return scale_source_rect(drawn_rect, source_size, source_rect).clip(clip_rect)


def get_right_ui_fonts(drawn_rect, source_size):
    scale = min(drawn_rect.width / source_size[0], drawn_rect.height / source_size[1])
    return {
        "label": max(16, int(42 * scale)),
        "body": max(24, int(66 * scale)),
        "value": max(28, int(76 * scale)),
        "small": max(18, int(46 * scale)),
        "tiny": max(14, int(34 * scale)),
        "stat": max(16, int(36 * scale)),
    }


def draw_right_ui_header_section(game, rect, fonts):
    old_clip = game.screen.get_clip()
    game.screen.set_clip(rect)
    inner = rect.inflate(-max(6, rect.width // 18), -max(2, rect.height // 8))
    draw_hud_text_in_rect(game, "전투 현황", min(fonts["small"], max(16, int(inner.height * 0.72))), YELLOW, inner, True)
    game.screen.set_clip(old_clip)


def draw_stage_info_section(game, rect, fonts):
    old_clip = game.screen.get_clip()
    game.screen.set_clip(rect)

    inner = rect.inflate(-max(4, rect.width // 22), -max(2, rect.height // 10))
    stage = game.current_stage()
    kills_to_boss = get_kills_to_boss(stage, get_stage_phase(game))
    title = get_stage_display_name(game)
    progress = "보스전 진행 중" if game.boss is not None else f"격침 {game.kill_count}/{kills_to_boss}"

    line_gap = max(1, inner.height // 16)
    title_size = min(fonts["small"], max(16, int(inner.height * 0.46)))
    progress_size = min(fonts["tiny"], max(13, int(inner.height * 0.34)))
    title_height = title_size + 6
    progress_height = progress_size + 4
    total_height = title_height + progress_height + line_gap
    y = inner.centery - total_height // 2

    draw_hud_text_in_rect(game, title, title_size, WHITE, pygame.Rect(inner.left, y, inner.width, title_height), True)
    y += title_height + line_gap
    draw_hud_text_in_rect(game, progress, progress_size, YELLOW, pygame.Rect(inner.left, y, inner.width, progress_height), True)

    game.screen.set_clip(old_clip)


def draw_score_section(game, rect, fonts):
    old_clip = game.screen.get_clip()
    game.screen.set_clip(rect)
    inner = rect.inflate(-max(4, rect.width // 18), -max(3, rect.height // 9))
    value_size = min(fonts["value"], max(22, int(inner.height * 0.62)))
    draw_hud_text_in_rect(game, f"{game.score:,}", value_size, YELLOW, inner, True)
    game.screen.set_clip(old_clip)


def draw_hp_section(game, rect, fonts):
    old_clip = game.screen.get_clip()
    game.screen.set_clip(rect)

    inner = rect.inflate(-max(4, rect.width // 18), -max(2, rect.height // 8))
    hp = game.player.get("hp", 0)
    max_hp = game.player.get("maxHp", 1)
    hp_ratio = max(0, min(1, hp / max(1, max_hp)))
    bar_height = max(8, min(max(16, inner.height - 4), int(inner.height * 0.72)))
    bar_rect = pygame.Rect(inner.left, 0, inner.width, bar_height)
    bar_rect.centery = inner.centery
    draw_hp_gauge(game, bar_rect, hp_ratio)

    hp_size = min(fonts["small"], max(18, int(inner.height * 0.9)))
    text_rect = inner.inflate(-max(8, inner.width // 11), -max(1, inner.height // 9))
    text_color = (255, 242, 205) if hp_ratio > 0.25 else (255, 196, 168)
    draw_hud_text_in_rect(game, f"HP {int(hp)}/{max_hp}", hp_size, text_color, text_rect, True)

    game.screen.set_clip(old_clip)


def draw_skill_icon_section(game, drawn_rect, source_size, panel, fonts):
    slots = [scale_right_ui_rect(drawn_rect, source_size, source_rect, panel) for source_rect in RIGHT_UI_SKILL_SLOTS]
    skill_specs = [
        {
            "key": "Z",
            "image": "skill_icon_q",
            "timer": getattr(game, "hakikjin_timer", 0),
            "duration": skills.HAKIKJIN_DURATION,
            "cooldown": getattr(game, "hakikjin_cooldown", 0),
            "cooldown_max": skills.HAKIKJIN_COOLDOWN,
            "available": getattr(game, "hakikjin_unlocked", False),
            "color": YELLOW,
        },
        {
            "key": "X",
            "image": "skill_icon_z",
            "timer": getattr(game, "tanker_guard_timer", 0),
            "duration": skills.TANKER_DURATION + getattr(game, "augment_guard_bonus", 0),
            "cooldown": getattr(game, "tanker_guard_cooldown", 0),
            "cooldown_max": skills.TANKER_COOLDOWN,
            "available": getattr(game, "tanker_skill_unlocked", False),
            "color": BLUE,
        },
        {
            "key": "C",
            "image": "skill_icon_x",
            "timer": getattr(game, "healer_timer", 0),
            "duration": skills.HEALER_DURATION,
            "cooldown": getattr(game, "healer_cooldown", 0),
            "cooldown_max": skills.HEALER_COOLDOWN,
            "available": getattr(game, "healer_skill_unlocked", False),
            "color": GREEN,
        },
    ]

    for rect, spec in zip(slots, skill_specs):
        draw_skill_icon_slot(game, rect, spec, fonts)


def draw_skill_icon_slot(game, rect, spec, fonts):
    old_clip = game.screen.get_clip()
    game.screen.set_clip(rect)

    icon_size = max(1, int(min(rect.width, rect.height) * 0.74))
    icon_rect = pygame.Rect(0, 0, icon_size, icon_size)
    icon_rect.center = rect.center
    icon = game.images.get(spec["image"])
    if icon:
        draw_image_contain_in_rect(game, icon, icon_rect)
    else:
        pygame.draw.rect(game.screen, (12, 24, 38), icon_rect, border_radius=max(3, icon_size // 14))
        pygame.draw.rect(game.screen, spec["color"], icon_rect, 2, border_radius=max(3, icon_size // 14))
        draw_text_in_rect(game, spec["key"], fonts["body"], WHITE, icon_rect, True, True, get_right_ui_font)

    pygame.draw.rect(game.screen, (255, 222, 126), icon_rect, max(1, icon_size // 40), border_radius=max(3, icon_size // 12))
    key_rect = pygame.Rect(icon_rect.left, icon_rect.top, max(22, icon_size // 3), max(18, icon_size // 4))
    draw_text_in_rect(game, spec["key"], fonts["tiny"], WHITE, key_rect, True, True, get_right_ui_font)
    draw_skill_key_badge(game, icon_rect, spec["key"], fonts)

    if not spec["available"]:
        draw_skill_disabled_overlay(game, icon_rect, fonts)
    elif spec["cooldown"] > 0:
        draw_skill_cooldown_overlay(game, icon_rect, spec["cooldown"], spec["cooldown_max"], fonts)
    elif spec["timer"] > 0:
        draw_skill_active_ring(game, icon_rect, spec["timer"], spec["duration"], spec["color"], fonts)

    game.screen.set_clip(old_clip)


def draw_skill_key_badge(game, icon_rect, key, fonts):
    badge_size = max(24, int(icon_rect.width * 0.34))
    badge_rect = pygame.Rect(0, 0, badge_size, badge_size)
    badge_rect.bottomright = (icon_rect.right - max(3, icon_rect.width // 28), icon_rect.bottom - max(3, icon_rect.height // 28))

    badge = pygame.Surface(badge_rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(badge, (10, 12, 16, 232), badge.get_rect())
    pygame.draw.ellipse(badge, (255, 222, 126, 245), badge.get_rect(), max(2, badge_size // 15))
    game.screen.blit(badge, badge_rect)
    draw_text_fit_visual_center_in_rect(game, key, max(18, int(badge_size * 0.68)), (255, 238, 182), badge_rect, True, get_right_ui_font)


def draw_skill_disabled_overlay(game, rect, fonts):
    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    game.screen.blit(overlay, rect)
    draw_centered_skill_text(game, "잠김", fonts["small"], GRAY, rect)


def draw_skill_cooldown_overlay(game, rect, cooldown, cooldown_max, fonts):
    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
    center = (rect.width // 2, rect.height // 2)
    radius = int(max(rect.width, rect.height) * 0.86)
    points = [center]
    remaining_ratio = max(0, min(1, cooldown / max(0.1, cooldown_max)))
    elapsed_ratio = 1 - remaining_ratio
    start_angle = -90 + 360 * elapsed_ratio
    end_angle = start_angle + 360 * remaining_ratio
    steps = max(8, int(64 * remaining_ratio))
    for step in range(steps + 1):
        angle = math.radians(start_angle + (end_angle - start_angle) * step / max(1, steps))
        points.append((center[0] + math.cos(angle) * radius, center[1] + math.sin(angle) * radius))
    if len(points) >= 3:
        pygame.draw.polygon(overlay, (12, 17, 23, 178), points)
    game.screen.blit(overlay, rect)
    number_size = max(14, min(fonts["body"], int(rect.height * 0.38)))
    draw_centered_skill_text(game, format_skill_cooldown_text(cooldown), number_size, WHITE, rect)


def format_skill_cooldown_text(cooldown):
    if cooldown < 1:
        return f"{max(0.1, cooldown):.1f}"
    return f"{math.ceil(cooldown)}"


def draw_skill_active_ring(game, rect, timer, duration, color, fonts):
    ratio = max(0, min(1, timer / max(0.1, duration)))
    radius = max(9, min(rect.width, rect.height) // 2 - 4)
    pygame.draw.circle(game.screen, color, rect.center, radius, max(2, rect.width // 26))
    draw_centered_skill_text(game, f"{math.ceil(timer)}", fonts["small"], color, rect.inflate(0, -rect.height // 2))
    if ratio < 1:
        cover = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.circle(cover, (0, 0, 0, int(90 * (1 - ratio))), (rect.width // 2, rect.height // 2), radius)
        game.screen.blit(cover, rect)


def draw_centered_skill_text(game, text, size, color, rect):
    shadow_rect = rect.move(1, 1)
    draw_text_fit_visual_center_in_rect(game, text, size, BLACK, shadow_rect, True, get_right_ui_font, min_size=10)
    draw_text_fit_visual_center_in_rect(game, text, size, color, rect, True, get_right_ui_font, min_size=10)


def draw_hud_text_in_rect(game, text, size, color, rect, bold=True):
    offset = max(1, size // 18)
    draw_text_fit_visual_center_in_rect(game, text, size, BLACK, rect.move(offset, offset), bold, get_right_ui_font, min_size=10)
    draw_text_fit_visual_center_in_rect(game, text, size, color, rect, bold, get_right_ui_font, min_size=10)


def draw_acquired_augments_section(game, rect, fonts):
    old_clip = game.screen.get_clip()
    game.screen.set_clip(rect)
    inner = rect.inflate(-max(5, rect.width // 24), -max(4, rect.height // 14))
    title_size = min(fonts["small"], max(16, int(inner.height * 0.22)))
    draw_hud_text_in_rect(game, "획득한 증강", title_size, YELLOW, pygame.Rect(inner.left, inner.top, inner.width, title_size + 6), True)
    body_rect = pygame.Rect(inner.left, inner.top + title_size + 8, inner.width, inner.height - title_size - 8)
    lines = get_acquired_augment_summary(game)
    y = body_rect.top
    line_count = max(1, min(4, len(lines)))
    line_height = max(18, body_rect.height // line_count)
    line_size = min(fonts["stat"], max(14, line_height - 6))
    for line in lines[:4]:
        draw_hud_text_in_rect(game, line, line_size, WHITE, pygame.Rect(body_rect.left, y, body_rect.width, line_height), True)
        y += line_height
    game.screen.set_clip(old_clip)


def get_acquired_augment_summary(game):
    stacks = getattr(game, "augment_stacks", {}) or {}
    acquired = []
    for augment_id, count in stacks.items():
        if count <= 0:
            continue
        title = augments.AUGMENTS.get(augment_id, {}).get("title", augment_id)
        acquired.append(f"{title} x{count}")
    if not acquired:
        return ["없음"]
    return acquired


def draw_current_stats_section(game, rect, fonts):
    old_clip = game.screen.get_clip()
    game.screen.set_clip(rect)
    inner = rect.inflate(-max(6, rect.width // 22), -max(6, rect.height // 14))
    title_size = min(fonts["small"], max(16, int(inner.height * 0.16)))
    draw_hud_text_in_rect(game, "현재 능력치", title_size, YELLOW, pygame.Rect(inner.left, inner.top, inner.width, title_size + 6), True)

    lines = [
        f"무기 {augments.get_weapon_tier_name(game)}",
        f"공격 {augments.get_current_bullet_damage(game)}  이동 {augments.get_current_move_speed(game)}",
        f"탄크기 {augments.get_current_bullet_radius(game) // 3}  연사 {augments.get_current_fire_cooldown(game):.2f}s",
        f"레벨 {getattr(game, 'run_level', 1)}",
    ]

    body_rect = pygame.Rect(inner.left, inner.top + title_size + 9, inner.width, inner.height - title_size - 9)
    line_height = max(18, body_rect.height // len(lines))
    line_size = min(fonts["stat"], max(14, line_height - 5))
    y = body_rect.top
    for line in lines:
        draw_hud_text_in_rect(game, line, line_size, WHITE, pygame.Rect(body_rect.left, y, body_rect.width, line_height), True)
        y += line_height

    game.screen.set_clip(old_clip)


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


def draw_hp_gauge(game, rect, hp_ratio):
    gauge = game.images.get("hp_gauge")
    if not gauge:
        color = GREEN if hp_ratio > 0.45 else YELLOW if hp_ratio > 0.25 else RED
        draw_bar(game, rect, hp_ratio, 1, color)
        return

    scaled = assets.get_scaled_image(game, gauge, rect.size)
    empty = scaled.copy()
    empty.fill((70, 42, 42, 112), special_flags=pygame.BLEND_RGBA_MULT)
    game.screen.blit(empty, rect)

    fill_rect = rect.copy()
    fill_rect.width = int(rect.width * max(0, min(1, hp_ratio)))
    if fill_rect.width > 0:
        old_clip = game.screen.get_clip()
        game.screen.set_clip(fill_rect.clip(old_clip))
        game.screen.blit(scaled, rect)
        game.screen.set_clip(old_clip)
