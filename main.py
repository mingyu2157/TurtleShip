# main.py
# 역할:
#   pygame을 시작하고, 창을 만들고, 게임 전체 루프를 돌리는 "입구 파일"입니다.
#   이 파일은 게임의 큰 흐름만 담당하고, 실제 세부 기능은 다른 파일에 나눠져 있습니다.
#
# 실행 흐름:
#   1. initGame()으로 pygame과 화면, 이미지, 사운드를 준비합니다.
#   2. runGame()이 계속 반복되면서 입력 처리, 게임 업데이트, 화면 그리기를 합니다.
#   3. updateGame() 안에서 플레이어, 적, 탄환, 보상, 충돌 처리를 순서대로 호출합니다.
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
import combat
import input as input_handler
import projectiles
import render
import rewards
import ui
from settings import DEFAULT_PAD_HEIGHT, DEFAULT_PAD_WIDTH, FPS
from stages import STAGES


# Game 클래스는 게임에서 계속 들고 다녀야 하는 상태를 한곳에 모아둔 상자입니다.
# 예를 들어 player, enemies, bullets, score처럼 여러 파일에서 같이 써야 하는 값들이 여기에 있습니다.
# 각 기능 파일은 game을 전달받아서 필요한 값만 읽거나 수정합니다.
class Game:
    def __init__(self):
        # 화면 크기와 pygame 기본 객체입니다.
        self.pad_width = DEFAULT_PAD_WIDTH
        self.pad_height = DEFAULT_PAD_HEIGHT
        self.screen = None
        self.clock = None

        # assets.py가 불러온 이미지, 효과음, 폰트를 저장합니다.
        self.images = {}
        self.sounds = {}
        self.fonts = {}
        self.audio_enabled = False

        # 현재 게임 상태입니다. menu, play, gameover, clear 같은 문자열로 구분합니다.
        self.game_state = "menu"
        self.paused = False
        self.held_scancodes = set()

        # 게임 안에 등장하는 주요 오브젝트 목록입니다.
        self.player = {}
        self.bullets = []
        self.enemies = []
        self.enemy_projectiles = []
        self.allies = []
        self.items = []
        self.boss = None

        # 점수, 스테이지, 타이머처럼 게임 진행에 필요한 값입니다.
        self.stage_index = 0
        self.kill_count = 0
        self.score = 0
        self.enemy_spawn_timer = 0
        self.stage_banner_timer = 0
        self.message_timer = 0
        self.message_text = ""
        self.shoot_cooldown = 0

        # 나중에 확장할 강화/아이템/필살기 상태입니다.
        self.bullet_level = 0
        self.rapid_fire_timer = 0
        self.ultimate_max = 100
        self.ultimate_charge = 0
        self.ultimate_invincible_timer = 0

    def current_stage(self):
        return STAGES[self.stage_index]


# 전역 game 객체입니다.
# pygame 예제처럼 간단히 쓰기 위해 하나만 만들고, 다른 함수들이 이 객체를 공유합니다.
game = Game()


# 현재 모니터 크기를 기준으로 최대화 창 크기를 구합니다.
# 실패하면 기본 코드 베이스 크기인 480 x 640을 사용합니다.
def get_maximized_window_size():
    try:
        if hasattr(pygame.display, "get_desktop_sizes"):
            desktop_sizes = pygame.display.get_desktop_sizes()
            if desktop_sizes:
                width, height = desktop_sizes[0]
                return max(DEFAULT_PAD_WIDTH, width), max(DEFAULT_PAD_HEIGHT, height)

        display_info = pygame.display.Info()
        if display_info.current_w > 0 and display_info.current_h > 0:
            return max(DEFAULT_PAD_WIDTH, display_info.current_w), max(DEFAULT_PAD_HEIGHT, display_info.current_h)
    except pygame.error:
        pass

    return DEFAULT_PAD_WIDTH, DEFAULT_PAD_HEIGHT


# pygame, 키 반복 설정, 창 생성, 이미지/사운드 로딩을 담당합니다.
# "--windowed" 옵션이 없으면 전체화면이 아니라 "최대화된 창"으로 시작합니다.
def initGame():
    pygame.init()
    pygame.key.set_repeat(0)

    flags = pygame.RESIZABLE
    window_size = (game.pad_width, game.pad_height)
    if "--windowed" not in sys.argv:
        window_size = get_maximized_window_size()
        if hasattr(pygame, "MAXIMIZED"):
            flags = flags | pygame.MAXIMIZED

    game.screen = pygame.display.set_mode(window_size, flags)
    game.pad_width, game.pad_height = game.screen.get_size()
    pygame.display.set_caption("PyShooting")
    game.clock = pygame.time.Clock()

    game.images, game.sounds, game.audio_enabled = assets.load_assets()
    assets.play_music(game)
    ui.show_splash(game)


# 플레이 중일 때 한 프레임마다 호출되는 업데이트 함수입니다.
# 이동 -> 탄환 -> 적/보스 -> 보상 -> 충돌 순서로 처리합니다.
def updateGame(dt):
    game.stage_banner_timer = max(0, game.stage_banner_timer - dt)
    game.message_timer = max(0, game.message_timer - dt)
    game.shoot_cooldown = max(0, game.shoot_cooldown - dt)

    actors.update_player(game, dt)
    projectiles.update_player_bullets(game, dt)
    actors.update_enemies(game, dt)
    actors.update_boss(game, dt)
    projectiles.update_enemy_projectiles(game, dt)
    rewards.update_rewards(game, dt)
    combat.check_collisions(game)

    if game.player["hp"] <= 0:
        actors.end_game(game, False)


# 실제 게임 루프입니다.
# pygame 게임은 보통 "입력 처리 -> 상태 업데이트 -> 화면 그리기"를 계속 반복합니다.
def runGame():
    while True:
        dt = game.clock.tick(FPS) / 1000

        for event in pygame.event.get():
            input_handler.handle_event(game, event)

        if game.game_state == "play" and not game.paused:
            updateGame(dt)

        render.draw_screen(game)
        pygame.display.update()


if __name__ == "__main__":
    initGame()
    runGame()
