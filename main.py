# main.py
# 역할:
#   pygame을 시작하고, 창을 만들고, 게임 전체 루프를 돌리는 "입구 파일"입니다.
#   이 파일은 게임의 큰 흐름만 담당하고, 실제 세부 기능은 다른 파일에 나눠져 있습니다.
#
# 실행 흐름:
#   1. initGame()으로 pygame과 화면, 이미지, 사운드를 준비합니다.
#   2. runGame()이 계속 반복되면서 입력 처리, 게임 업데이트, 화면 그리기를 합니다.
#   3. updateGame() 안에서 플레이어, 적, 탄환, 보상, 충돌 처리를 순서대로 호출합니다.
#
# 공부 순서:
#   처음 읽을 때는 Game 클래스 -> initGame() -> runGame() -> updateGame() 순서로 보면 됩니다.
#   pygame 게임은 대부분 "상태 저장 -> 입력 처리 -> 상태 변경 -> 화면 그리기" 구조로 되어 있습니다.
import sys


try:
    import pygame
except ModuleNotFoundError as exc:
    raise SystemExit(
        "pygame를 찾을 수 없습니다.\n"
        "가상환경을 켠 뒤 실행하세요:\n\n"
        "  source venv/bin/activate\n"
        "  python main.py\n"
    ) from exc

import actors
import assets
import augments
import campaign
import combat
import input as input_handler
import obstacles
import projectiles
import render
import rewards
import skills
import ui
import weather
from settings import DEFAULT_PAD_HEIGHT, DEFAULT_PAD_WIDTH, FPS
from stages import STAGES


# Game 클래스는 게임에서 계속 들고 다녀야 하는 상태를 한곳에 모아둔 상자입니다.
# 예를 들어 player, enemies, bullets, score처럼 여러 파일에서 같이 써야 하는 값들이 여기에 있습니다.
# 각 기능 파일은 game을 전달받아서 필요한 값만 읽거나 수정합니다.
class Game:
    def __init__(self):
        # 화면 크기와 pygame 기본 객체입니다.
        # pad_width/pad_height는 현재 창 크기이고, screen은 실제로 그림이 그려지는 도화지입니다.
        # clock은 초당 프레임 수를 일정하게 맞추기 위해 사용합니다.
        self.pad_width = DEFAULT_PAD_WIDTH
        self.pad_height = DEFAULT_PAD_HEIGHT
        self.screen = None
        self.clock = None

        # assets.py가 불러온 이미지, 효과음, 폰트를 저장합니다.
        # 딕셔너리를 쓰면 images["player"]처럼 이름으로 쉽게 꺼내 쓸 수 있습니다.
        self.images = {}
        self.sounds = {}
        self.fonts = {}
        self.scaled_image_cache = {}
        self.audio_enabled = False

        # 현재 게임 상태입니다. menu, mode_select, stage_select, story, play, gameover, clear 같은 문자열로 구분합니다.
        # stage_select는 캠페인 스테이지를 고르는 화면이고, story는 해전 브리핑 화면입니다.
        # stage_result는 스테이지 클리어 후 점수/피격/스킬 사용량을 보여주는 결과 화면입니다.
        # render.py와 input.py는 이 값을 보고 "어떤 화면을 그릴지", "키가 무슨 의미인지" 결정합니다.
        self.game_state = "menu"
        # game_mode는 현재 플레이 흐름을 구분합니다.
        # "campaign"은 이순신 시뮬레이션, "score"는 경험치/증강을 쓰는 점수 경쟁입니다.
        self.game_mode = "campaign"
        self.paused = False
        # held_scancodes는 한글 입력 상태에서도 WASD 물리 키를 인식하기 위한 보조 저장소입니다.
        self.held_scancodes = set()

        # 게임 안에 등장하는 주요 오브젝트 목록입니다.
        # 화면에 여러 개 나오는 것은 리스트로 저장하고, 하나만 있는 플레이어/보스는 딕셔너리로 저장합니다.
        self.player = {}
        self.bullets = []
        self.enemies = []
        self.enemy_projectiles = []
        self.obstacles = []
        self.weather_events = []
        self.boss = None

        # 점수, 스테이지, 타이머처럼 게임 진행에 필요한 값입니다.
        # 타이머는 대부분 "남은 시간" 또는 "다음 행동까지 기다린 시간"을 의미합니다.
        # updateGame()에서 매 프레임 dt만큼 줄이거나 늘립니다.
        self.stage_index = 0
        self.stage_phase = 0
        self.stage_total_kills = 0
        self.kill_count = 0
        self.score = 0
        # current_stage_stats는 이번 스테이지 전투 기록입니다.
        self.current_stage_stats = {}
        # stage_result는 방금 클리어한 스테이지 결과 화면에 표시할 데이터입니다.
        self.stage_result = {}
        self.enemy_spawn_timer = 0
        self.stage_banner_timer = 0
        self.message_timer = 0
        self.message_text = ""
        self.story_id = "intro"
        # 난중일기/스토리 페이지 번호입니다.
        # 0은 1편, 1은 2편처럼 사용하고, story.py가 현재 스테이지의 페이지 수에 맞춰 안전하게 제한합니다.
        self.story_page_index = 0
        # 스토리 화면 글자가 천천히 써지는 애니메이션에 필요한 상태입니다.
        self.story_typing_key = None
        self.story_typing_started_ms = 0
        self.story_typing_force_complete = False
        self.story_typing_complete = True
        # 캠페인 진행도입니다.
        # unlocked_stage_count는 현재 플레이 가능한 스테이지 개수이고,
        # cleared_stage_count는 이미 클리어한 스테이지 개수입니다.
        self.unlocked_stage_count = 1
        self.cleared_stage_count = 0
        self.mode_select_index = 0
        self.stage_select_index = 0
        self.menu_select_index = 0
        self.pause_select_index = 0
        self.hakikjin_unlocked = False
        self.shoot_cooldown = 0
        self.obstacle_spawn_timer = 0
        self.weather_spawn_timer = 0
        # 현재 플레이 중인 판에서만 쓰는 레벨/경험치/증강 상태입니다.
        self.run_level = 1
        self.run_xp = 0
        self.run_xp_to_next = 45
        self.augment_stacks = {}
        self.augment_choices = []
        self.augment_pending = False
        self.basic_ability_choices = []
        self.basic_ability_chosen = False
        self.basic_ability_augment_id = None
        # 선택지 화면에서 방향키로 움직이는 현재 카드 번호입니다.
        # 증강, 기본 능력, 생즉사 사즉생 화면이 같은 값을 함께 씁니다.
        self.choice_select_index = 0
        self.stage_handicap_timer = 0.0
        self.stage_effect_message = ""

        # 파도는 waves.py가 랜덤 방향과 다음 변화 시간을 관리합니다.
        # None으로 시작해두면 waves.py가 첫 호출 때 안전하게 초기값을 만들어 줍니다.
        self.wave_angle = None
        self.wave_target_angle = None
        self.wave_speed_current = 0
        self.wave_speed_target = 0
        self.wave_change_timer = 0
        self.wave_last_time = None

        # 나중에 확장할 필살기 상태입니다.
        # 기능을 여러 파일에 나눠도 실제 현재 값은 game 객체 안에 모아둡니다.
        augments.reset_augment_effects(self)
        self.ultimate_max = 100
        self.ultimate_charge = 0
        self.ultimate_invincible_timer = 0
        self.last_stand_used = False
        self.last_stand_choice = "damage"
        self.last_stand_choice_made = False
        self.last_stand_choice_version = 2
        self.last_stand_damage_timer = 0.0
        self.last_stand_damage_multiplier = 1.0
        self.last_stand_damage_active = False
        self.last_stand_damage_cooldown = 0.0
        self.last_stand_revive_cooldown = 0.0
        self.last_stand_revive_penalty_timer = 0.0
        self.revive_flash_timer = 0.0
        # 현재 재생 중인 배경음악 종류입니다.
        # assets.py가 같은 음악을 반복해서 처음부터 틀지 않도록 기억하는 값입니다.
        self.current_music_key = None

    def current_stage(self):
        # stage_index는 0부터 시작합니다. 0은 1스테이지, 1은 2스테이지입니다.
        return STAGES[self.stage_index]


# 전역 game 객체입니다.
# pygame 예제처럼 간단히 쓰기 위해 하나만 만들고, 다른 함수들이 이 객체를 공유합니다.
game = Game()


# 현재 모니터 크기를 기준으로 최대화 창 크기를 구합니다.
# 실패하면 기본 코드 베이스 크기인 480 x 640을 사용합니다.
def get_maximized_window_size():
    try:
        # pygame 2에서는 get_desktop_sizes()로 모니터 해상도를 가져올 수 있습니다.
        if hasattr(pygame.display, "get_desktop_sizes"):
            desktop_sizes = pygame.display.get_desktop_sizes()
            if desktop_sizes:
                width, height = desktop_sizes[0]
                return max(DEFAULT_PAD_WIDTH, width), max(DEFAULT_PAD_HEIGHT, height)

        # 위 방법이 안 되면 pygame.display.Info()로 한 번 더 시도합니다.
        display_info = pygame.display.Info()
        if display_info.current_w > 0 and display_info.current_h > 0:
            return max(DEFAULT_PAD_WIDTH, display_info.current_w), max(DEFAULT_PAD_HEIGHT, display_info.current_h)
    except pygame.error:
        pass

    return DEFAULT_PAD_WIDTH, DEFAULT_PAD_HEIGHT


# pygame, 키 반복 설정, 창 생성, 이미지/사운드 로딩을 담당합니다.
# "--windowed" 옵션이 없으면 전체화면이 아니라 "최대화된 창"으로 시작합니다.
def initGame():
    # pygame.init()은 pygame의 화면, 키보드, 소리 같은 내부 기능을 준비합니다.
    pygame.init()
    # 키를 꾹 누를 때 KEYDOWN이 반복 발생하지 않게 해서 Space 연타 규칙을 유지합니다.
    pygame.key.set_repeat(0)

    flags = pygame.RESIZABLE
    window_size = (game.pad_width, game.pad_height)
    if "--windowed" not in sys.argv:
        window_size = get_maximized_window_size()
        if hasattr(pygame, "MAXIMIZED"):
            flags = flags | pygame.MAXIMIZED

    # set_mode()를 호출하면 실제 게임 창이 만들어지고, 이후 모든 그림은 game.screen에 그립니다.
    game.screen = pygame.display.set_mode(window_size, flags)
    game.pad_width, game.pad_height = game.screen.get_size()
    pygame.display.set_caption("PyShooting")
    game.clock = pygame.time.Clock()

    # 이미지/효과음은 게임 중 계속 쓰므로 시작할 때 한 번만 불러옵니다.
    game.images, game.sounds, game.audio_enabled = assets.load_assets()
    assets.play_menu_music(game)
    # 저장된 캠페인 진행도를 불러와서 스테이지 선택 화면에서 잠금 상태를 정확히 보여줍니다.
    campaign.apply_progress_to_game(game)
    ui.show_splash(game)


# 플레이 중일 때 한 프레임마다 호출되는 업데이트 함수입니다.
# 이동 -> 탄환 -> 적/보스 -> 보상 -> 충돌 순서로 처리합니다.
def updateGame(dt):
    # dt는 지난 프레임부터 이번 프레임까지 걸린 시간(초)입니다.
    # 속도 * dt 방식으로 계산하면 컴퓨터가 빠르거나 느려도 움직임이 비슷합니다.
    game.stage_banner_timer = max(0, game.stage_banner_timer - dt)
    game.message_timer = max(0, game.message_timer - dt)
    game.shoot_cooldown = max(0, game.shoot_cooldown - dt)
    if pygame.key.get_pressed()[pygame.K_SPACE]:
        combat.shoot_player_bullet(game)

    # 아래 순서가 중요합니다.
    # 먼저 위치/타이머를 갱신하고, 마지막에 충돌을 검사해야 이번 프레임 결과가 자연스럽습니다.
    obstacles.update_obstacles(game, dt)
    weather.update_weather(game, dt)
    actors.update_player(game, dt)
    projectiles.update_player_bullets(game, dt)
    actors.update_enemies(game, dt)
    actors.update_boss(game, dt)
    projectiles.update_enemy_projectiles(game, dt)
    rewards.update_rewards(game, dt)
    combat.check_collisions(game)

    # 보스 체력이 0이 되면 현재 스테이지를 클리어합니다.
    # combat.py에서도 보스 처치 처리가 있지만, 혹시 날씨 피해 등으로 죽는 경우까지 여기서 한 번 더 봅니다.
    if game.boss is not None and game.boss["hp"] <= 0:
        game.score += 900 + game.stage_index * 320
        actors.handle_boss_defeated(game)
        return

    # 필생즉사(damage) 선택 시: 체력 20% 이하에서 발동합니다.
    if (
        getattr(game, "last_stand_choice", "damage") == "damage"
        and game.player["hp"] > 0
        and game.player["hp"] <= game.player["maxHp"] * skills.LAST_STAND_TRIGGER_RATIO
        and skills.try_use_last_stand(game)
    ):
        return

    # 플레이어 체력이 0이 되었을 때 사망 처리합니다.
    if game.player["hp"] <= 0:
        # 필사즉생(revive) 선택 시: 사망 시 부활을 시도합니다.
        if getattr(game, "last_stand_choice", "damage") == "revive" and skills.try_use_last_stand(game):
            game.revive_flash_timer = 0.7
            return
        actors.end_game(game, False)


# 실제 게임 루프입니다.
# pygame 게임은 보통 "입력 처리 -> 상태 업데이트 -> 화면 그리기"를 계속 반복합니다.
def runGame():
    while True:
        # tick(FPS)는 최대 FPS를 제한하고, 반환값은 지난 프레임의 밀리초입니다.
        # /1000을 해서 초 단위 dt로 바꿉니다.
        dt = game.clock.tick(FPS) / 1000

        # pygame.event.get()은 마우스 클릭, 키 입력, 창 닫기 같은 사건을 모아서 돌려줍니다.
        for event in pygame.event.get():
            input_handler.handle_event(game, event)

        # 메뉴/스토리/결과 화면에서는 전투 계산을 멈추고 화면만 그립니다.
        # 그래도 스테이지 선택 화면의 안내 메시지는 시간이 지나면 사라져야 하므로 여기서 줄입니다.
        if game.game_state != "play":
            game.message_timer = max(0, game.message_timer - dt)

        if game.game_state == "play" and not game.paused:
            updateGame(dt)

        # 모든 계산이 끝난 뒤 현재 상태를 화면에 그립니다.
        render.draw_screen(game)
        pygame.display.update()


if __name__ == "__main__":
    initGame()
    runGame()
