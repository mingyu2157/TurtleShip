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
import subprocess
import sys

import pygame

import actors
import account_store
import augments
import assets
import campaign
import combat
import layout
import scoreboard
import skills
import ui
from settings import MIN_PAD_HEIGHT, MIN_PAD_WIDTH
from stages import STAGE_MAX
from text_utils import normalize_korean_text


ACCOUNT_MOUSE_BLOCK_MS = 280
MENU_TRANSITION_MOUSE_BLOCK_MS = 450
MENU_BUTTON_ORDER = ("start", "login")


TEXT_INPUT_STATES = {"score_name_input", "account_login", "account_signup", "account_edit"}
MODE_SELECT_MOUSE_GUARD_MS = 260
MOUSE_TRANSITION_GUARD_MS = 420


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

    if event.type == pygame.TEXTINPUT:
        handle_text_input(game, event.text)
        sync_text_input_state(game)
        return

    if event.type == pygame.TEXTEDITING:
        game.text_editing_text = event.text
        sync_text_input_state(game)
        return

    if event.type == pygame.KEYDOWN:
        handle_key_down(game, event)
        sync_text_input_state(game)
        return

    if event.type == pygame.KEYUP:
        handle_key_up(game, event)
        sync_text_input_state(game)
        return

    if event.type == pygame.MOUSEMOTION:
        handle_mouse_motion(game, event.pos)
        sync_text_input_state(game)
        return

    if event.type == pygame.MOUSEWHEEL:
        handle_mouse_wheel(game, event.y)
        sync_text_input_state(game)
        return

    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        handle_mouse_up(game, event.pos)
        sync_text_input_state(game)
        return

    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1:
            if is_mouse_click_blocked(game):
                return
            handle_mouse_down(game, event.pos)
        elif event.button in (4, 5):
            handle_mouse_wheel(game, 1 if event.button == 4 else -1)
        sync_text_input_state(game)


def sync_text_input_state(game):
    should_enable = getattr(game, "game_state", "") in TEXT_INPUT_STATES
    if getattr(game, "text_input_active", False) == should_enable:
        return

    try:
        if should_enable:
            pygame.key.start_text_input()
        else:
            pygame.key.stop_text_input()
            game.text_editing_text = ""
    except pygame.error:
        return
    game.text_input_active = should_enable


def guard_mouse_after_transition(game, duration_ms=MOUSE_TRANSITION_GUARD_MS):
    game.mouse_input_guard_until = pygame.time.get_ticks() + duration_ms


def is_mouse_transition_guard_active(game):
    return pygame.time.get_ticks() < getattr(game, "mouse_input_guard_until", 0)


# 마우스가 움직일 때 메뉴/선택 화면의 포커스 인덱스를 갱신합니다.
def handle_mouse_motion(game, pos):
    if game.game_state == "account_profile_crop":
        handle_account_crop_mouse_motion(game, pos)
        return

    if ui.should_draw_profile_button(game) and ui.get_profile_button_rect(game).collidepoint(pos):
        set_menu_cursor(True)
        return

    if game.game_state in ("account_login", "account_signup", "account_mypage", "account_edit"):
        layout_info = ui.get_account_layout(game, game.game_state)
        items = ui.get_account_focus_items(layout_info, game.game_state)
        hovered_index = ui.get_account_hovered_focus_index(layout_info, game.game_state, pos, items)
        hovered_item = items[hovered_index] if hovered_index is not None else None
        if hovered_index is not None:
            game.account_focus_index = hovered_index
        set_account_cursor(
            hovered_item is not None and hovered_item["kind"] in ("button", "profile"),
            hovered_item is not None and hovered_item["kind"] == "field",
        )
        return

    if game.game_state == "menu":
        hovered_button = get_menu_button_at(game, pos)
        if hovered_button:
            game.menu_select_index = get_menu_button_index(hovered_button)
        set_menu_cursor(hovered_button is not None)
        return

    if game.game_state == "mode_select":
        _, buttons = layout.get_mode_select_layout(game)
        over_clickable = False
        for index, rect in enumerate(buttons):
            if rect.collidepoint(pos):
                game.mode_select_index = index
                over_clickable = True
                break
        set_menu_cursor(over_clickable)
        return

    if game.game_state == "stage_select":
        over_clickable = False
        for stage_index, rect in enumerate(layout.get_stage_select_card_rects(game, STAGE_MAX)):
            if rect.collidepoint(pos) and campaign.is_stage_unlocked(game, stage_index):
                game.stage_select_index = stage_index
                over_clickable = True
                break
        set_menu_cursor(over_clickable)
        return

    if game.game_state == "score_leaderboard":
        set_menu_cursor(ui.get_score_leaderboard_start_button_rect(game).collidepoint(pos))
        return

    if game.game_state == "augment_select":
        update_choice_focus_from_mouse(game, pos, layout.get_choice_visual_rects(game, len(getattr(game, "augment_choices", []))))
        return

    if game.game_state == "ability_select":
        update_choice_focus_from_mouse(
            game,
            pos,
            layout.get_choice_visual_rects(game, len(getattr(game, "basic_ability_choices", []))),
        )
        return

    if game.game_state == "last_stand_select":
        update_choice_focus_from_mouse(game, pos, layout.get_choice_visual_rects(game, len(skills.LAST_STAND_CHOICES)))


def set_menu_cursor(over_clickable):
    if not hasattr(pygame, "SYSTEM_CURSOR_HAND"):
        return

    try:
        cursor = pygame.SYSTEM_CURSOR_HAND if over_clickable else pygame.SYSTEM_CURSOR_ARROW
        pygame.mouse.set_cursor(cursor)
    except pygame.error:
        pass


def set_account_cursor(over_clickable, over_text=False):
    try:
        if over_text and hasattr(pygame, "SYSTEM_CURSOR_IBEAM"):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_IBEAM)
        elif over_clickable and hasattr(pygame, "SYSTEM_CURSOR_HAND"):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        elif hasattr(pygame, "SYSTEM_CURSOR_ARROW"):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
    except pygame.error:
        pass


def block_mouse_clicks(game, duration_ms=ACCOUNT_MOUSE_BLOCK_MS):
    game.mouse_click_block_until_ms = pygame.time.get_ticks() + duration_ms


def is_mouse_click_blocked(game):
    return pygame.time.get_ticks() < getattr(game, "mouse_click_block_until_ms", 0)


def update_choice_focus_from_mouse(game, pos, rects):
    for index, rect in enumerate(rects):
        if rect.collidepoint(pos):
            game.choice_select_index = index
            return


# 선택지 화면에서 방향키로 현재 선택 카드를 움직입니다.
# 방향키와 WASD를 같이 받으므로 한글 입력 상태가 아니면 키보드만으로도 고를 수 있습니다.
def move_choice_selection(game, direction, choice_count):
    if choice_count <= 0:
        game.choice_select_index = 0
        return

    current = getattr(game, "choice_select_index", 0)
    game.choice_select_index = (current + direction) % choice_count


def move_stage_selection(game, direction):
    unlocked_count = campaign.get_unlocked_stage_count(game)
    current = max(0, min(getattr(game, "stage_select_index", 0), unlocked_count - 1))
    game.stage_select_index = (current + direction) % unlocked_count


def activate_stage_selection(game, stage_index):
    stage_index = max(0, min(stage_index, STAGE_MAX - 1))
    game.stage_select_index = stage_index
    if campaign.is_stage_unlocked(game, stage_index):
        assets.play_stage_sound(game, "shoot", 0.45)
        actors.start_stage(game, stage_index)
    else:
        actors.show_locked_stage_message(game, stage_index)


def open_mode_select(game):
    game.game_state = "mode_select"
    game.mode_select_index = 0
    game.mode_select_ignore_mouse_until = pygame.time.get_ticks() + MODE_SELECT_MOUSE_GUARD_MS
    guard_mouse_after_transition(game)
    game.message_text = ""
    game.message_timer = 0
    assets.play_menu_music(game)
    block_mouse_clicks(game, MENU_TRANSITION_MOUSE_BLOCK_MS)


def get_menu_button_index(button_name):
    try:
        return MENU_BUTTON_ORDER.index(button_name)
    except ValueError:
        return 0


def get_selected_menu_button(game):
    index = max(0, min(getattr(game, "menu_select_index", 0), len(MENU_BUTTON_ORDER) - 1))
    game.menu_select_index = index
    return MENU_BUTTON_ORDER[index]


def move_menu_selection(game, direction):
    game.menu_select_index = (getattr(game, "menu_select_index", 0) + direction) % len(MENU_BUTTON_ORDER)


def activate_mode_selection(game, index):
    game.mode_select_index = max(0, min(index, 2))
    assets.play_stage_sound(game, "shoot", 0.45)
    if game.mode_select_index == 0:
        actors.open_stage_select(game)
    elif game.mode_select_index == 1:
        actors.open_score_name_input(game)
    else:
        game.game_state = "menu"
        assets.play_menu_music(game)
    guard_mouse_after_transition(game)


def handle_text_input(game, text):
    if game.game_state in ("account_login", "account_signup", "account_edit"):
        handle_account_text_input(game, text)
        return

    if game.game_state != "score_name_input":
        return

    last_text = getattr(game, "score_last_key_text", "")
    last_ms = getattr(game, "score_last_key_text_ms", 0)
    if text and text == last_text and pygame.time.get_ticks() - last_ms < 80:
        game.score_last_key_text = ""
        return

    append_score_name_text(game, text)
    game.text_editing_text = ""


def append_score_name_text(game, text):
    if not text:
        return

    game.score_name_input = append_limited_text(
        getattr(game, "score_name_input", ""),
        text,
        scoreboard.MAX_NICKNAME_LENGTH,
        normalize=True,
    )


def remember_account_previous_state(game):
    if game.game_state not in ("account_login", "account_signup", "account_mypage", "account_edit"):
        game.account_previous_state = game.game_state


def open_account_login(game):
    remember_account_previous_state(game)
    user = account_store.current_user(game)
    game.account_form = {
        "login_id": user["login_id"] if user else "",
        "password": "",
        "nickname": user["nickname"] if user else "",
    }
    game.account_focus_index = 0
    game.account_message_text = ""
    game.account_message_ok = False
    game.game_state = "account_login"
    assets.play_menu_music(game)
    block_mouse_clicks(game)


def open_account_signup(game):
    clear_account_profile_crop(game)
    game.account_form = {"login_id": "", "password": "", "nickname": ""}
    game.account_focus_index = 0
    game.account_message_text = ""
    game.account_message_ok = False
    game.account_profile_upload_bytes = None
    game.account_profile_upload_mime = None
    game.account_profile_upload_changed = False
    game.game_state = "account_signup"
    block_mouse_clicks(game)


def open_account_mypage(game):
    remember_account_previous_state(game)
    game.account_focus_index = 0
    game.account_message_text = ""
    game.account_message_ok = False
    game.account_focus_index = 0
    game.game_state = "account_mypage"
    assets.play_menu_music(game)
    block_mouse_clicks(game)


def open_account_edit(game):
    user = account_store.current_user(game)
    if not user:
        open_account_login(game)
        return
    clear_account_profile_crop(game)
    game.account_form = {
        "login_id": user["login_id"],
        "password": "",
        "nickname": user["nickname"],
    }
    game.account_focus_index = 0
    game.account_message_text = ""
    game.account_message_ok = False
    game.account_profile_upload_bytes = None
    game.account_profile_upload_mime = None
    game.account_profile_upload_changed = False
    game.game_state = "account_edit"
    block_mouse_clicks(game)


def close_account_screen(game):
    block_mouse_clicks(game)
    destination = getattr(game, "account_previous_state", "menu")
    if destination in ("account_login", "account_signup", "account_mypage", "account_edit", "play"):
        destination = "menu"
    game.game_state = destination
    if destination == "stage_select":
        campaign.apply_progress_to_game(game)
        assets.play_stage_select_music(game)
        return
    if destination == "story":
        assets.play_story_music(game)
        return
    if destination == "mode_select":
        game.mode_select_index = 0
    if destination in ("menu", "mode_select", "score_name_input", "score_leaderboard"):
        assets.play_menu_music(game)


def handle_account_text_input(game, text):
    field = get_focused_account_field(game)
    if not field:
        return
    value = getattr(game, "account_form", {}).get(field, "")
    max_length = account_store.MAX_NICKNAME_LENGTH if field == "nickname" else account_store.MAX_LOGIN_ID_LENGTH
    if field == "password":
        max_length = 32
    game.account_form[field] = append_limited_text(value, text, max_length, normalize=field == "nickname")


def append_limited_text(value, text, max_length, normalize=False):
    value = str(value or "")
    for char in str(text or ""):
        if char in "\r\n\t":
            continue
        candidate = f"{value}{char}"
        if normalize:
            candidate = normalize_korean_text(candidate)
        if len(candidate) > max_length:
            break
        value = candidate
    return value


def move_account_focus(game, direction):
    items = get_account_focus_items(game)
    if not items:
        return
    game.account_focus_index = (getattr(game, "account_focus_index", 0) + direction) % len(items)


def get_account_focus_items(game):
    layout_info = ui.get_account_layout(game, game.game_state)
    return ui.get_account_focus_items(layout_info, game.game_state)


def get_account_focus_item(game):
    items = get_account_focus_items(game)
    if not items:
        return None
    return items[max(0, min(getattr(game, "account_focus_index", 0), len(items) - 1))]


def get_focused_account_field(game):
    item = get_account_focus_item(game)
    if item and item["kind"] == "field":
        return item["name"]
    return None


def activate_account_profile(game):
    assets.play_stage_sound(game, "shoot", 0.45)
    if game.game_state == "account_mypage":
        open_account_edit(game)
        return
    if game.game_state in ("account_signup", "account_edit"):
        select_account_profile_image(game)


def activate_account_button(game, button_name):
    assets.play_stage_sound(game, "shoot", 0.45)
    if game.game_state == "account_login":
        if button_name == "login":
            submit_account_login(game)
        elif button_name == "signup":
            open_account_signup(game)
        elif button_name == "back":
            close_account_screen(game)
        return

    if game.game_state == "account_signup":
        if button_name == "submit":
            submit_account_signup(game)
        elif button_name == "back":
            open_account_login(game)
        return

    if game.game_state == "account_mypage":
        if button_name == "edit":
            open_account_edit(game)
        elif button_name == "back":
            close_account_screen(game)
        return

    if game.game_state == "account_edit":
        if button_name == "save":
            submit_account_edit(game)
        elif button_name == "back":
            game.game_state = "account_mypage" if account_store.current_user(game) else "account_login"
            block_mouse_clicks(game)


def submit_account_from_focused_field(game):
    if game.game_state == "account_login":
        submit_account_login(game)
    elif game.game_state == "account_signup":
        submit_account_signup(game)
    elif game.game_state == "account_edit":
        submit_account_edit(game)


def activate_account_focus_item(game):
    item = get_account_focus_item(game)
    if not item:
        return
    if item["kind"] == "profile":
        activate_account_profile(game)
    elif item["kind"] == "button":
        activate_account_button(game, item["name"])
    elif item["kind"] == "field":
        submit_account_from_focused_field(game)


def submit_account_login(game):
    form = getattr(game, "account_form", {})
    profile, message = account_store.login_user(form.get("login_id", ""), form.get("password", ""))
    if profile:
        account_store.apply_profile_to_game(game, profile)
        game.account_message_text = "로그인 완료"
        game.account_message_ok = True
        close_account_screen(game)
        return
    game.account_message_text = message
    game.account_message_ok = False


def submit_account_signup(game):
    form = getattr(game, "account_form", {})
    profile, message = account_store.signup_user(
        form.get("login_id", ""),
        form.get("password", ""),
        form.get("nickname", ""),
        getattr(game, "account_profile_upload_bytes", None),
        getattr(game, "account_profile_upload_mime", None),
    )
    if profile:
        account_store.apply_profile_to_game(game, profile)
        game.account_message_text = "회원가입 완료"
        game.account_message_ok = True
        close_account_screen(game)
        return
    game.account_message_text = message
    game.account_message_ok = False


def submit_account_edit(game):
    user = account_store.current_user(game)
    if not user:
        open_account_login(game)
        return
    form = getattr(game, "account_form", {})
    old_nickname = user.get("nickname", "")
    profile, message = account_store.update_user_profile(
        user["id"],
        form.get("login_id", ""),
        form.get("password", ""),
        form.get("nickname", ""),
        getattr(game, "account_profile_upload_bytes", None),
        getattr(game, "account_profile_upload_mime", None),
        getattr(game, "account_profile_upload_changed", False),
    )
    if profile:
        account_store.apply_profile_to_game(game, profile)
        rename_cached_leaderboard_nickname(game, old_nickname, profile.get("nickname", ""))
        game.account_message_text = "저장 완료"
        game.account_message_ok = True
        game.game_state = "account_mypage"
        return
    game.account_message_text = message
    game.account_message_ok = False


def select_account_profile_image(game):
    path = pick_profile_image_file()
    if not path:
        game.account_message_text = "프로필 사진 파일을 선택하지 않았습니다."
        game.account_message_ok = False
        return

    raw, source_size, message = account_store.load_profile_image_preview(path)
    if not raw or not source_size:
        game.account_message_text = message or "프로필 사진을 선택하지 못했습니다."
        game.account_message_ok = False
        return

    try:
        surface = pygame.image.frombuffer(raw, source_size, "RGBA").convert_alpha()
    except pygame.error as error:
        game.account_message_text = f"이미지를 불러오지 못했습니다: {error}"
        game.account_message_ok = False
        return

    start_account_profile_crop(game, path, surface, source_size)


def start_account_profile_crop(game, path, surface, source_size):
    width, height = source_size
    side = min(width, height)
    game.account_crop_previous_state = game.game_state
    game.account_crop_path = path
    game.account_crop_surface = surface
    game.account_crop_source_size = source_size
    game.account_crop_box = [(width - side) / 2, (height - side) / 2, float(side)]
    game.account_crop_dragging = False
    game.account_crop_drag_last = None
    game.account_crop_focus_index = 0
    game.account_message_text = ""
    game.account_message_ok = False
    game.game_state = "account_profile_crop"
    block_mouse_clicks(game)


def clear_account_profile_crop(game):
    game.account_crop_path = ""
    game.account_crop_surface = None
    game.account_crop_source_size = (0, 0)
    game.account_crop_box = None
    game.account_crop_dragging = False
    game.account_crop_drag_last = None


def finish_account_profile_crop(game):
    image_data, image_mime, message = account_store.prepare_profile_image(
        getattr(game, "account_crop_path", ""),
        getattr(game, "account_crop_box", None),
    )
    previous_state = getattr(game, "account_crop_previous_state", "account_signup")
    clear_account_profile_crop(game)
    game.game_state = previous_state
    block_mouse_clicks(game)

    if not image_data:
        game.account_message_text = message or "프로필 사진을 선택하지 못했습니다."
        game.account_message_ok = False
        return

    game.account_profile_upload_bytes = image_data
    game.account_profile_upload_mime = image_mime
    game.account_profile_upload_changed = True
    game.account_message_text = "프로필 사진 선택 완료"
    game.account_message_ok = True


def cancel_account_profile_crop(game):
    previous_state = getattr(game, "account_crop_previous_state", "account_signup")
    clear_account_profile_crop(game)
    game.game_state = previous_state
    block_mouse_clicks(game)
    game.account_message_text = "프로필 사진 선택 취소"
    game.account_message_ok = False


def clamp_account_crop_box(game):
    box = getattr(game, "account_crop_box", None)
    surface = getattr(game, "account_crop_surface", None)
    if not box or surface is None:
        return

    width, height = surface.get_size()
    max_side = min(width, height)
    min_side = max(48, int(max_side * 0.12))
    side = max(min_side, min(float(box[2]), max_side))
    left = max(0, min(float(box[0]), width - side))
    top = max(0, min(float(box[1]), height - side))
    game.account_crop_box = [left, top, side]


def move_account_crop_box(game, dx, dy):
    box = getattr(game, "account_crop_box", None)
    if not box:
        return
    box[0] += dx
    box[1] += dy
    clamp_account_crop_box(game)


def zoom_account_crop_box(game, direction):
    box = getattr(game, "account_crop_box", None)
    surface = getattr(game, "account_crop_surface", None)
    if not box or surface is None or direction == 0:
        return

    width, height = surface.get_size()
    max_side = min(width, height)
    min_side = max(48, int(max_side * 0.12))
    factor = 0.88 if direction > 0 else 1.12
    old_side = float(box[2])
    new_side = max(min_side, min(max_side, old_side * factor))
    center_x = float(box[0]) + old_side / 2
    center_y = float(box[1]) + old_side / 2
    game.account_crop_box = [center_x - new_side / 2, center_y - new_side / 2, new_side]
    clamp_account_crop_box(game)


def get_account_crop_preview_scale(game):
    layout_info = ui.get_account_profile_crop_layout(game)
    image_rect = ui.get_account_crop_image_rect(game, layout_info["preview"])
    surface = getattr(game, "account_crop_surface", None)
    if surface is None:
        return 1
    return image_rect.width / max(1, surface.get_width())


def handle_account_crop_mouse_motion(game, pos):
    layout_info = ui.get_account_profile_crop_layout(game)
    over_clickable = layout_info["confirm"].collidepoint(pos) or layout_info["cancel"].collidepoint(pos)
    if layout_info["confirm"].collidepoint(pos):
        game.account_crop_focus_index = 0
    elif layout_info["cancel"].collidepoint(pos):
        game.account_crop_focus_index = 1
    crop_rect = ui.get_account_crop_screen_rect(game, layout_info["preview"])
    over_crop = crop_rect.collidepoint(pos) or layout_info["preview"].collidepoint(pos)
    set_menu_cursor(over_clickable or over_crop)

    if not getattr(game, "account_crop_dragging", False):
        return

    last = getattr(game, "account_crop_drag_last", None)
    game.account_crop_drag_last = pos
    if not last:
        return

    scale = get_account_crop_preview_scale(game)
    if scale <= 0:
        return
    move_account_crop_box(game, (pos[0] - last[0]) / scale, (pos[1] - last[1]) / scale)


def handle_account_crop_mouse_down(game, pos):
    layout_info = ui.get_account_profile_crop_layout(game)
    if layout_info["confirm"].collidepoint(pos):
        game.account_crop_focus_index = 0
        assets.play_stage_sound(game, "shoot", 0.45)
        finish_account_profile_crop(game)
        return
    if layout_info["cancel"].collidepoint(pos):
        game.account_crop_focus_index = 1
        assets.play_stage_sound(game, "shoot", 0.45)
        cancel_account_profile_crop(game)
        return
    if layout_info["preview"].collidepoint(pos):
        game.account_crop_dragging = True
        game.account_crop_drag_last = pos


def handle_account_crop_mouse_up(game, pos):
    game.account_crop_dragging = False
    game.account_crop_drag_last = None


def handle_account_crop_key_down(game, event):
    if event.key == pygame.K_ESCAPE:
        cancel_account_profile_crop(game)
        return
    if event.key == pygame.K_RETURN:
        assets.play_stage_sound(game, "shoot", 0.45)
        if getattr(game, "account_crop_focus_index", 0) == 1:
            cancel_account_profile_crop(game)
        else:
            finish_account_profile_crop(game)
        return
    if event.key == pygame.K_TAB:
        game.account_crop_focus_index = (getattr(game, "account_crop_focus_index", 0) + 1) % 2
        return
    plus_keys = (pygame.K_EQUALS, getattr(pygame, "K_PLUS", pygame.K_EQUALS), getattr(pygame, "K_KP_PLUS", pygame.K_EQUALS))
    minus_keys = (pygame.K_MINUS, getattr(pygame, "K_UNDERSCORE", pygame.K_MINUS), getattr(pygame, "K_KP_MINUS", pygame.K_MINUS))
    if event.key in plus_keys:
        zoom_account_crop_box(game, 1)
        return
    if event.key in minus_keys:
        zoom_account_crop_box(game, -1)
        return

    step = max(2, int(getattr(game, "account_crop_box", [0, 0, 100])[2] * 0.025))
    if event.key in (pygame.K_LEFT, pygame.K_a):
        move_account_crop_box(game, -step, 0)
    elif event.key in (pygame.K_RIGHT, pygame.K_d):
        move_account_crop_box(game, step, 0)
    elif event.key in (pygame.K_UP, pygame.K_w):
        move_account_crop_box(game, 0, -step)
    elif event.key in (pygame.K_DOWN, pygame.K_s):
        move_account_crop_box(game, 0, step)


def pick_profile_image_file():
    if sys.platform == "darwin":
        return pick_profile_image_file_macos()
    return pick_profile_image_file_tk()


def pick_profile_image_file_tk():
    if sys.platform == "darwin":
        return ""

    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return ""

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()
        return filedialog.askopenfilename(
            title="프로필 사진 선택",
            filetypes=(
                ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("All files", "*.*"),
            ),
        )
    except Exception:
        return ""
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


def pick_profile_image_file_macos():
    if sys.platform != "darwin":
        return ""

    script = (
        'set selectedFile to choose file with prompt "프로필 사진 선택" '
        'of type {"public.image"}\n'
        "POSIX path of selectedFile"
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""

    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_account_profile_click_rect(profile_rect):
    return ui.get_account_profile_hit_rect(profile_rect)


def is_account_profile_click(layout_info, pos):
    profile_button = layout_info.get("profile_button")
    if profile_button and profile_button.collidepoint(pos):
        return True

    profile_rect = layout_info.get("profile")
    return profile_rect is not None and get_account_profile_click_rect(profile_rect).collidepoint(pos)


def rename_cached_leaderboard_nickname(game, old_nickname, new_nickname):
    old_name = scoreboard.clean_nickname(old_nickname)
    new_name = scoreboard.clean_nickname(new_nickname)
    if old_name == new_name:
        return

    for attr_name in ("leaderboard_entries", "score_mode_leaderboard_snapshot"):
        entries = getattr(game, attr_name, None)
        if not entries:
            continue
        for entry in entries:
            if entry.get("nickname") == old_name:
                entry["nickname"] = new_name


def handle_account_key_down(game, event):
    if event.key == pygame.K_ESCAPE:
        close_account_screen(game)
        return
    if event.key == pygame.K_TAB:
        move_account_focus(game, -1 if getattr(event, "mod", 0) & pygame.KMOD_SHIFT else 1)
        return
    if event.key in (pygame.K_DOWN, pygame.K_RIGHT):
        move_account_focus(game, 1)
        return
    if event.key in (pygame.K_UP, pygame.K_LEFT):
        move_account_focus(game, -1)
        return
    if event.key == pygame.K_BACKSPACE:
        field = get_focused_account_field(game)
        if field:
            game.account_form[field] = getattr(game, "account_form", {}).get(field, "")[:-1]
        return
    if event.key == pygame.K_RETURN:
        activate_account_focus_item(game)
        return


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


# 키를 눌렀을 때 실행됩니다.
# 메뉴/결과 화면/플레이 화면마다 같은 키도 다른 의미로 쓰일 수 있어서 상태별로 나눠 처리합니다.
def handle_key_down(game, event):
    if getattr(event, "scancode", None) is not None:
        # scancode는 키보드의 물리 위치에 가까워서 한글 입력 상태에서도 WASD를 추적할 수 있습니다.
        game.held_scancodes.add(event.scancode)

    if game.game_state == "account_profile_crop":
        handle_account_crop_key_down(game, event)
        return

    if game.game_state in ("account_login", "account_signup", "account_mypage", "account_edit"):
        handle_account_key_down(game, event)
        return

    if game.game_state == "menu":
        if event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_a, pygame.K_w):
            move_menu_selection(game, -1)
            return
        if event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_d, pygame.K_s, pygame.K_TAB):
            move_menu_selection(game, 1)
            return
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            activate_menu_button(game, get_selected_menu_button(game))
            return
        if event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        return

    if game.game_state == "mode_select":
        current_mode_index = getattr(game, "mode_select_index", 0)
        if event.key in (pygame.K_LEFT, pygame.K_a):
            game.mode_select_index = 0 if current_mode_index == 1 else 1
            return
        if event.key in (pygame.K_RIGHT, pygame.K_d):
            game.mode_select_index = 1 if current_mode_index == 0 else 0
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            game.mode_select_index = 0 if current_mode_index == 2 else 2
            return
        if event.key in (pygame.K_DOWN, pygame.K_s):
            game.mode_select_index = 2
            return
        if event.key == pygame.K_1:
            activate_mode_selection(game, 0)
            return
        if event.key == pygame.K_2:
            activate_mode_selection(game, 1)
            return
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            activate_mode_selection(game, getattr(game, "mode_select_index", 0))
            return
        if event.key == pygame.K_ESCAPE:
            game.game_state = "menu"
            assets.play_menu_music(game)
            return
        return

    if game.game_state == "score_name_input":
        if event.key == pygame.K_ESCAPE:
            open_mode_select(game)
            return
        if event.key == pygame.K_BACKSPACE:
            game.score_name_input = getattr(game, "score_name_input", "")[:-1]
            game.text_editing_text = ""
            return
        if event.key == pygame.K_RETURN:
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.confirm_score_name(game)
            return
        text = getattr(event, "unicode", "")
        if text and text.isascii() and text.isprintable():
            append_score_name_text(game, text)
            game.score_last_key_text = text
            game.score_last_key_text_ms = pygame.time.get_ticks()
            return
        return

    if game.game_state == "score_leaderboard":
        if event.key == pygame.K_RETURN:
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.start_score_mode(game)
            return
        if event.key == pygame.K_ESCAPE:
            open_mode_select(game)
            return
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
        return

    if game.game_state == "stage_select":
        # 스테이지 선택 화면에서는 숫자키, 방향키, Enter를 사용합니다.
        # 잠긴 스테이지를 고르면 actors.py가 안내 메시지를 띄우고 시작하지 않습니다.
        if event.key == pygame.K_ESCAPE:
            open_mode_select(game)
            return

        if pygame.K_1 <= event.key <= pygame.K_5:
            activate_stage_selection(game, event.key - pygame.K_1)
            return

        if event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_a, pygame.K_w):
            move_stage_selection(game, -1)
            return

        if event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_d, pygame.K_s):
            move_stage_selection(game, 1)
            return

        if event.key == pygame.K_RETURN:
            activate_stage_selection(game, getattr(game, "stage_select_index", 0))
            return

        return

    if game.game_state == "story":
        # 스토리 화면에서는 Enter 또는 마우스 클릭으로 다음 스토리/전투 시작을 진행합니다.
        # Space는 메뉴 자동 선택을 막기 위해 전투 중 발사 전용으로만 사용합니다.
        if event.key == pygame.K_RETURN:
            actors.advance_story(game)
        if event.key == pygame.K_ESCAPE:
            actors.open_stage_select(game)
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

    if game.game_state == "leaderboard":
        if event.key == pygame.K_RETURN:
            assets.play_stage_sound(game, "shoot", 0.45)
            game.game_state = "menu"
            assets.play_menu_music(game)
        if event.key == pygame.K_ESCAPE:
            game.game_state = "menu"
            assets.play_menu_music(game)
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
    if skills.is_hakikjin_key(event):
        skills.try_use_hakikjin(game)
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
    if game.game_state == "account_profile_crop":
        handle_account_crop_mouse_down(game, pos)
        return

    if game.game_state != "play" and is_mouse_transition_guard_active(game):
        return

    if ui.should_draw_profile_button(game) and ui.get_profile_button_rect(game).collidepoint(pos):
        assets.play_stage_sound(game, "shoot", 0.45)
        if account_store.current_user(game):
            open_account_mypage(game)
        else:
            open_account_login(game)
        guard_mouse_after_transition(game)
        return

    if game.game_state in ("account_login", "account_signup", "account_mypage", "account_edit"):
        handle_account_mouse_down(game, pos)
        return

    if game.game_state == "menu":
        pressed_button = get_menu_button_at(game, pos)
        game.menu_pressed_button = pressed_button
        if pressed_button:
            game.menu_select_index = get_menu_button_index(pressed_button)
        return

    if game.game_state == "mode_select":
        if pygame.time.get_ticks() < getattr(game, "mode_select_ignore_mouse_until", 0):
            return
        _, buttons = layout.get_mode_select_layout(game)
        for index, rect in enumerate(buttons):
            if rect.collidepoint(pos):
                activate_mode_selection(game, index)
                break
        return

    if game.game_state == "score_name_input":
        return

    if game.game_state == "score_leaderboard":
        if ui.get_score_leaderboard_start_button_rect(game).collidepoint(pos):
            assets.play_stage_sound(game, "shoot", 0.45)
            actors.start_score_mode(game)
        return

    if game.game_state == "augment_select":
        for index, rect in enumerate(layout.get_choice_visual_rects(game, len(getattr(game, "augment_choices", [])))):
            if rect.collidepoint(pos):
                assets.play_stage_sound(game, "shoot", 0.45)
                game.choice_select_index = index
                augments.choose_augment(game, index)
                break
        return

    if game.game_state == "ability_select":
        visual_rects = layout.get_choice_visual_rects(game, len(getattr(game, "basic_ability_choices", [])))
        column_rects = layout.get_basic_ability_choice_rects(game, len(getattr(game, "basic_ability_choices", [])))
        for index, rect in enumerate(visual_rects):
            if rect.collidepoint(pos):
                assets.play_stage_sound(game, "shoot", 0.45)
                game.choice_select_index = index
                actors.choose_basic_ability(game, index)
                return
        for index, rect in enumerate(column_rects):
            if rect.collidepoint(pos):
                assets.play_stage_sound(game, "shoot", 0.45)
                game.choice_select_index = index
                actors.choose_basic_ability(game, index)
                return
        return

    if game.game_state == "last_stand_select":
        for index, rect in enumerate(layout.get_choice_visual_rects(game, len(skills.LAST_STAND_CHOICES))):
            if rect.collidepoint(pos):
                assets.play_stage_sound(game, "shoot", 0.45)
                game.choice_select_index = index
                actors.choose_last_stand(game, index)
                break
        return

    if game.game_state == "stage_select":
        # 스테이지 카드 안을 클릭하면 해당 스테이지를 선택하고, 해금된 스테이지이면 시작합니다.
        for stage_index, rect in enumerate(layout.get_stage_select_card_rects(game, STAGE_MAX)):
            if rect.collidepoint(pos):
                activate_stage_selection(game, stage_index)
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

    if game.game_state == "leaderboard":
        assets.play_stage_sound(game, "shoot", 0.45)
        game.game_state = "menu"
        assets.play_menu_music(game)
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


def handle_mouse_up(game, pos):
    if game.game_state == "account_profile_crop":
        handle_account_crop_mouse_up(game, pos)
        return

    if game.game_state == "menu":
        game.menu_pressed_button = None


def get_menu_button_at(game, pos):
    if layout.get_login_button_rect(game).collidepoint(pos):
        return "login"
    if layout.get_start_button_rect(game).collidepoint(pos):
        return "start"
    return None


def activate_menu_button(game, button_name):
    assets.play_stage_sound(game, "shoot", 0.45)
    game.menu_select_index = get_menu_button_index(button_name)
    if button_name == "login":
        open_account_login(game)
    elif button_name == "start":
        open_mode_select(game)
    guard_mouse_after_transition(game)


def handle_mouse_wheel(game, direction):
    if game.game_state == "account_profile_crop":
        zoom_account_crop_box(game, direction)


def handle_account_mouse_down(game, pos):
    layout_info = ui.get_account_layout(game, game.game_state)
    items = ui.get_account_focus_items(layout_info, game.game_state)
    hovered_index = ui.get_account_hovered_focus_index(layout_info, game.game_state, pos, items)
    if hovered_index is not None:
        game.account_focus_index = hovered_index

    if is_account_profile_click(layout_info, pos):
        activate_account_profile(game)
        return

    fields = layout_info.get("fields", [])
    for index, (_, rect) in enumerate(fields):
        if rect.collidepoint(pos):
            game.account_focus_index = hovered_index if hovered_index is not None else index
            return

    buttons = layout_info.get("buttons", {})
    for button_name, rect in buttons.items():
        if rect.collidepoint(pos):
            activate_account_button(game, button_name)
            return
