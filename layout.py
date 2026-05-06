# layout.py
# 역할:
#   화면 크기에 따라 배경 이미지, 전투 가능 영역, HUD 높이, 시작 버튼 위치를 계산합니다.
#   게임 창이 최대화되거나 크기가 바뀌어도 플레이 영역이 맞도록 도와줍니다.
#
# 초보자 포인트:
#   이미지를 화면에 꽉 채우려면 원본 비율과 현재 창 비율을 비교해서 scale을 구해야 합니다.
#   이 파일은 그런 위치 계산을 모아두어 다른 파일이 숫자 계산에 덜 신경 쓰게 합니다.
#
# 공부 순서:
#   get_play_area()는 "그려지는 바다 영역",
#   get_combat_area()는 "실제로 전투 가능한 영역",
#   get_side_areas()는 "좌우 예비/HUD 영역"을 계산합니다.
import pygame

import assets
from skins import GAME_BACKGROUND_PLAY_RECT


# 기존 480px 중앙 플레이 폭에서 왼쪽 20%, 오른쪽 20%씩 확장한 값입니다.
# 480 + 96 + 96 = 672라서, 전투 공간은 넓히되 좌우 HUD/대기 구역은 남겨둡니다.
MOBILE_PLAY_WIDTH = 672
SIDE_PANEL_MIN_WIDTH = 230
CHOICE_IMAGE_INFLATE = (164, 194)


# 이미지를 화면에 꽉 차게 덮을 때 필요한 위치와 배율을 계산합니다.
# cover 방식이라 이미지가 잘릴 수 있지만, 화면에 빈 공간이 생기지 않습니다.
def get_cover_rect(game, image):
    # 화면과 이미지의 가로/세로 확대 비율 중 더 큰 값을 사용해야 빈 공간 없이 꽉 찹니다.
    scale = max(game.pad_width / image.get_width(), game.pad_height / image.get_height())
    # 소수점 버림 때문에 모서리에 1픽셀 빈틈이 생기지 않도록 한 픽셀 여유를 둡니다.
    width = max(game.pad_width, int(image.get_width() * scale) + 1)
    height = max(game.pad_height, int(image.get_height() * scale) + 1)
    rect = pygame.Rect(0, 0, width, height)
    rect.center = (game.pad_width // 2, game.pad_height // 2)
    return rect, scale


# get_cover_rect()로 계산한 크기에 맞춰 이미지를 실제 화면에 그립니다.
def draw_cover(game, image):
    rect, scale = get_cover_rect(game, image)
    # 같은 배경 이미지를 같은 창 크기로 매 프레임 다시 확대하지 않도록 캐시를 사용합니다.
    scaled = assets.get_scaled_image(game, image, rect.size)
    game.screen.blit(scaled, rect)
    return rect, scale


# HUD가 차지하는 위쪽 높이를 돌려줍니다.
# 작은 화면에서는 HUD가 조금 더 높아져 글자가 겹치지 않게 합니다.
def get_hud_height(game):
    return 98 if game.pad_width < 720 else 82


# 좌우에 HUD/추가 UI 공간을 둘 수 있을 만큼 화면이 넓은지 확인합니다.
# 이 함수는 get_play_area()를 부르지 않아서 재귀 호출 문제가 생기지 않습니다.
def can_use_side_panels(game):
    return game.pad_width >= MOBILE_PLAY_WIDTH + SIDE_PANEL_MIN_WIDTH * 2


# 넓은 화면에서도 실제 플레이는 중앙 모바일 폭 안에서만 진행되게 만듭니다.
# 양옆 영역은 추후 기능을 넣을 수 있도록 비워두고, 전투 판정에서는 제외합니다.
def fit_mobile_play_width(game, area):
    if area.width <= MOBILE_PLAY_WIDTH:
        return area

    # 큰 모니터에서도 전투 영역이 너무 넓어지지 않게 중앙 폭만 잘라 씁니다.
    width = min(MOBILE_PLAY_WIDTH, area.width)
    centered = pygame.Rect(0, area.top, width, area.height)
    centered.centerx = game.pad_width // 2
    return centered.clip(area)


# 전체 배경 이미지 중 실제 바다 전투 영역을 계산합니다.
# 맵 이미지 테두리처럼 플레이하면 안 되는 부분은 제외하고,
# 넓은 창에서는 중앙 모바일 폭으로 한 번 더 좁힙니다.
def get_play_area(game):
    background = assets.get_stage_image(game, "stage")
    if background:
        # 배경 이미지가 화면에 cover 방식으로 그려졌을 때,
        # 원본 이미지 안의 GAME_BACKGROUND_PLAY_RECT도 같은 배율/위치로 변환해야 합니다.
        drawn_rect, scale = get_cover_rect(game, background)
        source_x, source_y, source_w, source_h = GAME_BACKGROUND_PLAY_RECT
        area = pygame.Rect(
            drawn_rect.left + int(source_x * scale),
            drawn_rect.top + int(source_y * scale),
            int(source_w * scale),
            int(source_h * scale),
        )
        return fit_mobile_play_width(game, area.clip(pygame.Rect(0, 0, game.pad_width, game.pad_height)))

    # 배경 이미지가 없을 때는 화면 가장자리를 조금 남기고 플레이 영역을 만듭니다.
    top = 12 if can_use_side_panels(game) else get_hud_height(game) + 12
    area = pygame.Rect(8, top, game.pad_width - 16, game.pad_height - top - 12)
    return fit_mobile_play_width(game, area)


# 중앙 플레이 영역 바깥의 좌우 지원 공간을 돌려줍니다.
# 현재 왼쪽은 예비 UI 구역, 오른쪽은 HUD 구역으로 사용합니다.
def get_side_areas(game):
    play_area = get_play_area(game)
    # play_area 왼쪽은 추후 UI 확장, 오른쪽은 HUD 정보 표시 영역입니다.
    left = pygame.Rect(0, play_area.top, max(0, play_area.left), play_area.height)
    right = pygame.Rect(play_area.right, play_area.top, max(0, game.pad_width - play_area.right), play_area.height)
    return left, right


# 현재 화면에서 HUD를 위가 아니라 좌우 바깥 영역에 둘 수 있는지 확인합니다.
def has_side_panels(game):
    left, right = get_side_areas(game)
    return left.width >= SIDE_PANEL_MIN_WIDTH and right.width >= SIDE_PANEL_MIN_WIDTH


# 실제 전투 가능 영역입니다.
# 좌우 HUD가 가능한 넓은 화면에서는 위쪽 HUD 공간을 비우지 않고 중앙 플레이 영역 전체를 씁니다.
def get_combat_area(game):
    play_area = get_play_area(game)
    top = play_area.top + 8 if has_side_panels(game) else max(play_area.top, get_hud_height(game) + 10)
    height = max(80, play_area.bottom - top)
    return pygame.Rect(play_area.left, top, play_area.width, height)


# 보스 HP바는 전투 영역 안의 최상단에 고정하고, 보스 이동 제한도 같은 기준을 사용합니다.
def get_boss_hp_bar_rect(game):
    combat_area = get_combat_area(game)
    margin_x = max(10, int(combat_area.width * 0.035))
    width = max(260, combat_area.width - margin_x * 2)
    frame_image = assets.get_stage_image(game, "boss_hp")
    aspect_ratio = 0.12
    if frame_image and frame_image.get_width() > 0:
        aspect_ratio = frame_image.get_height() / frame_image.get_width()

    height = max(46, int(width * aspect_ratio))
    max_height = max(72, int(combat_area.height * 0.22))
    if height > max_height:
        height = max_height
        width = max(260, int(height / max(0.01, aspect_ratio)))

    rect = pygame.Rect(0, 0, width, height)
    rect.midtop = (combat_area.centerx, combat_area.top + max(6, int(combat_area.height * 0.012)))
    return rect


# 보스가 HP바와 겹치지 않도록 보스의 최상단 y좌표를 돌려줍니다.
def get_boss_reserved_top(game):
    hp_rect = get_boss_hp_bar_rect(game)
    return hp_rect.bottom + max(14, int(hp_rect.height * 0.24))


# 메인 메뉴 이미지 위의 "게임 시작" 버튼 위치를 계산합니다.
# 이미지가 없을 때는 화면 크기에 맞춘 기본 버튼 위치를 사용합니다.
def get_start_button_rect(game):
    menu_image = game.images.get("main_menu")
    if menu_image:
        # main_menu.png 안에 그려진 "게임 시작" 버튼의 전체 장식 영역입니다.
        # draw_cover()와 같은 cover 계산을 써서 배경/클릭/하이라이트가 같은 위치에 놓이게 합니다.
        source_rect = (878, 578, 415, 102)
        rect = get_cover_source_rect(game, menu_image, source_rect)
        if rect.colliderect(pygame.Rect(0, 0, game.pad_width, game.pad_height)):
            return rect

    rect = pygame.Rect(0, 0, min(380, int(game.pad_width * 0.72)), 68)
    rect.center = (game.pad_width // 2, int(game.pad_height * 0.60))
    return rect


# cover 방식으로 그려진 이미지 안의 원본 좌표 사각형을 현재 화면 좌표로 변환합니다.
def get_cover_source_rect(game, image, source_rect):
    drawn_rect, scale = get_cover_rect(game, image)
    return pygame.Rect(
        drawn_rect.left + int(source_rect[0] * scale),
        drawn_rect.top + int(source_rect[1] * scale),
        int(source_rect[2] * scale),
        int(source_rect[3] * scale),
    )


# 모드 선택 창과 그 안의 두 모드 버튼 위치를 계산합니다.
def get_mode_select_layout(game):
    mode_image = game.images.get("mode_back") or game.images.get("story_mode") or game.images.get("com_mode")
    if mode_image:
        # 원본 1672x941 모드 선택 이미지 안의 클릭 영역입니다.
        source_rects = (
            (330, 290, 520, 500),
            (830, 290, 520, 500),
            (1215, 792, 420, 120),
        )
        screen_rect = pygame.Rect(0, 0, game.pad_width, game.pad_height)
        buttons = [get_cover_source_rect(game, mode_image, source_rect).clip(screen_rect) for source_rect in source_rects]
        return screen_rect, buttons

    panel_width = min(760, int(game.pad_width * 0.78))
    panel_height = min(500, int(game.pad_height * 0.66))
    panel = pygame.Rect(0, 0, panel_width, panel_height)
    panel.center = (game.pad_width // 2, game.pad_height // 2)

    button_width = min(panel.width - 96, 520)
    button_height = max(66, min(90, panel.height // 5))
    gap = max(18, panel.height // 16)
    start_y = panel.centery - int(button_height * 1.55) - gap
    buttons = []
    for index in range(3):
        rect = pygame.Rect(0, start_y + index * (button_height + gap), button_width, button_height)
        rect.centerx = panel.centerx
        buttons.append(rect)
    return panel, buttons


# 증강 선택 화면에서 3개 카드 위치를 계산합니다.
def get_augment_choice_rects(game, choice_count):
    count = max(1, choice_count)
    gap = 42 if game.pad_width >= 980 else 24
    if game.pad_width >= 980:
        columns = count
    else:
        columns = 1

    content_width = min(1120, int(game.pad_width * 0.90))
    card_width = (content_width - gap * (columns - 1)) // columns
    card_height = 230 if columns > 1 else 176
    total_width = card_width * columns + gap * (columns - 1)
    start_x = (game.pad_width - total_width) // 2
    start_y = int(game.pad_height * 0.50)

    rects = []
    for index in range(choice_count):
        col = index % columns
        row = index // columns
        rects.append(
            pygame.Rect(
                start_x + col * (card_width + gap),
                start_y + row * (card_height + gap),
                card_width,
                card_height,
            )
        )
    return rects


def get_choice_visual_rects(game, choice_count):
    rects = []
    for rect in get_augment_choice_rects(game, choice_count):
        visual_rect = rect.inflate(*CHOICE_IMAGE_INFLATE)
        visual_rect.center = rect.center
        rects.append(visual_rect)
    return rects


# 기본 능력 선택 화면의 하단 선택 영역 위치를 계산합니다.
# 실제 화면에는 이미지만 보이므로, 마우스 선택을 위한 보이지 않는 전체 화면 분할 영역을 만듭니다.
def get_basic_ability_choice_rects(game, choice_count):
    rects = []
    if choice_count <= 0:
        return rects

    band_width = game.pad_width / choice_count
    for index in range(choice_count):
        left = int(round(index * band_width))
        right = int(round((index + 1) * band_width))
        rects.append(pygame.Rect(left, 0, max(1, right - left), game.pad_height))
    return rects


# 스테이지 선택 화면의 카드 위치를 계산합니다.
# 입력 처리(input.py)와 화면 그리기(ui.py)가 같은 위치를 써야 클릭 판정이 정확합니다.
def get_stage_select_card_rects(game, stage_count):
    # 하단 글귀 이미지 영역을 먼저 확보합니다.
    quote_height = get_stage_select_quote_height(game)
    available_height = game.pad_height - quote_height

    # 카드는 항상 5개를 한 줄로 표시하고, 창이 좁으면 2열/1열로 줄입니다.
    if game.pad_width >= 900:
        columns = min(stage_count, 5)
    elif game.pad_width >= 560:
        columns = 2
    else:
        columns = 1

    # 양쪽 끝단과의 여백 (화면 폭의 8%, 최소 64px)
    side_margin = max(64, int(game.pad_width * 0.08))
    gap_x = max(10, int(game.pad_width * 0.012))
    gap_y = 12

    # 카드 상단 여백: 사용 가능 높이의 30% 아래에서 시작합니다.
    top_margin = max(100, int(available_height * 0.30))

    content_width = game.pad_width - side_margin * 2
    card_width = (content_width - gap_x * (columns - 1)) // columns

    rows = (stage_count + columns - 1) // columns
    # 카드 높이: 남은 공간을 채우되 72% 이하로 제한합니다.
    card_height = min(
        max(130, int((available_height - top_margin - gap_y * (rows - 1)) // rows)),
        int(available_height * 0.72),
    )

    total_width = card_width * columns + gap_x * (columns - 1)
    start_x = (game.pad_width - total_width) // 2
    start_y = top_margin

    rects = []
    for index in range(stage_count):
        col = index % columns
        row = index // columns
        rect = pygame.Rect(
            start_x + col * (card_width + gap_x),
            start_y + row * (card_height + gap_y),
            card_width,
            card_height,
        )
        rects.append(rect)

    return rects


def get_stage_select_quote_height(game):
    # 글귀 이미지가 차지할 화면 하단 높이입니다.
    return min(280, max(140, int(game.pad_height * 0.24)))


def get_stage_select_quote_rect(game):
    # 화면 하단에 글귀 이미지를 표시할 영역을 반환합니다.
    h = get_stage_select_quote_height(game)
    return pygame.Rect(0, game.pad_height - h, game.pad_width, h)


# 일시정지 메뉴의 중앙 패널과 버튼 위치를 계산합니다.
# 화면이 작아도 버튼이 서로 겹치지 않도록 패널 높이와 버튼 간격을 함께 줄입니다.
def get_pause_menu_layout(game):
    panel_width = min(560, int(game.pad_width * 0.86))
    panel_height = min(520, int(game.pad_height * 0.74))
    panel = pygame.Rect(0, 0, panel_width, panel_height)
    panel.center = (game.pad_width // 2, game.pad_height // 2)

    button_width = int(panel.width * 0.78)
    button_height = max(54, min(72, panel.height // 7))
    gap = max(14, min(28, panel.height // 18))
    total_button_height = button_height * 3 + gap * 2
    start_y = panel.centery - total_button_height // 2 + int(panel.height * 0.11)

    buttons = []
    for index in range(3):
        rect = pygame.Rect(0, start_y + index * (button_height + gap), button_width, button_height)
        rect.centerx = panel.centerx
        buttons.append(rect)

    return panel, buttons
