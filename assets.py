# assets.py
# 역할:
#   이미지와 효과음을 파일에서 읽어와 game.images, game.sounds에 넣습니다.
#   파일이 없으면 게임이 멈추지 않고 기본 도형/배경으로 대체되도록 설계했습니다.
#
# 파일 이름 규칙:
#   skins.py에 적힌 이름을 기준으로 assets/images, assets/audio 폴더에서 찾습니다.
#   예를 들어 enemy_stage1.png가 있으면 1스테이지 적 이미지로 자동 사용됩니다.
#
# 공부 순서:
#   load_assets()가 시작할 때 파일을 모두 읽어오고,
#   get_stage_image()/play_stage_sound()가 현재 스테이지에 맞는 파일을 골라줍니다.
import pygame

from settings import AUDIO_DIR, AUDIO_EXTENSIONS, BASE_DIR, IMAGE_DIR, IMAGE_EXTENSIONS
from skins import (
    ALLY_IMAGE_NAMES,
    COMMON_IMAGE_NAMES,
    COMMON_SOUND_NAMES,
    SKILL_IMAGE_NAMES,
    stage_image_names,
    stage_sound_names,
)
from stages import STAGE_MAX


# 이미지 확대/축소 캐시에 보관할 최대 개수입니다.
# 너무 많이 보관하면 메모리를 많이 쓰므로, 일정 개수를 넘으면 한 번 비웁니다.
MAX_SCALED_IMAGE_CACHE = 280

# 과거 프로젝트 폴더 구조(sound effect/)도 자동으로 읽어오도록 검색 폴더를 둘 다 유지합니다.
AUDIO_SEARCH_DIRS = (AUDIO_DIR, BASE_DIR / "sound effect")

# 영어 키 이름과 실제 파일 이름이 다를 수 있어 별칭 목록을 둡니다.
# 예: typing 키는 typing.mp3 또는 타이핑.mp3를 모두 허용합니다.
SOUND_NAME_ALIASES = {
    "typing": ("typing", "타이핑"),
}

# 스토리 타자음은 전용 채널 하나를 루프 재생해서 자연스럽게 들리게 합니다.
STORY_TYPING_CHANNEL_INDEX = 14


# 같은 이미지를 같은 크기로 계속 smoothscale()하지 않도록 캐시에서 꺼내는 함수입니다.
# pygame.transform.smoothscale()은 예쁘게 줄이고 키우지만 매 프레임 반복하면 성능을 많이 씁니다.
def get_scaled_image(game, image, size):
    if image is None:
        # 이미지가 없으면 호출한 쪽에서 기본 도형으로 그릴 수 있게 None을 돌려줍니다.
        return None

    # pygame은 Surface 크기에 정수가 필요하므로 안전하게 int로 맞춥니다.
    width = max(1, int(size[0]))
    height = max(1, int(size[1]))
    # game 객체에 캐시 딕셔너리가 없을 수도 있으므로 없으면 새로 만듭니다.
    cache = getattr(game, "scaled_image_cache", None)
    if cache is None:
        cache = {}
        game.scaled_image_cache = cache

    # 이미지 객체 id와 목표 크기를 함께 키로 써야 서로 다른 이미지가 섞이지 않습니다.
    key = (id(image), width, height)
    if key in cache:
        # 이미 같은 크기로 만든 이미지가 있으면 다시 계산하지 않고 바로 재사용합니다.
        return cache[key]

    # 캐시가 너무 커졌으면 한 번 비워서 오래된 랜덤 크기 이미지를 정리합니다.
    if len(cache) >= MAX_SCALED_IMAGE_CACHE:
        cache.clear()

    # 여기서만 실제 확대/축소를 수행합니다.
    scaled = pygame.transform.smoothscale(image, (width, height))
    # 다음 프레임부터 재사용할 수 있게 저장합니다.
    cache[key] = scaled
    return scaled


# 창 크기를 바꾸거나 메모리를 정리하고 싶을 때 이미지 캐시를 비웁니다.
def clear_image_cache(game):
    cache = getattr(game, "scaled_image_cache", None)
    if cache is not None:
        cache.clear()


# 폴더 안에서 여러 확장자 중 실제 존재하는 파일을 찾습니다.
# 예: ["shoot"], [".mp3", ".ogg", ".wav"]를 넣으면 shoot.mp3부터 차례로 찾습니다.
def find_asset(folder, names, extensions):
    # 같은 이름이라도 png/jpg/mp3/ogg처럼 여러 확장자를 허용하기 위해 이중 반복문을 사용합니다.
    for name in names:
        for extension in extensions:
            path = folder / f"{name}{extension}"
            if path.exists():
                return path
    return None


# 여러 폴더를 순서대로 돌며 실제 존재하는 파일을 찾습니다.
def find_asset_in_folders(folders, names, extensions):
    for folder in folders:
        path = find_asset(folder, names, extensions)
        if path:
            return path
    return None


# 게임 시작 시 이미지와 효과음을 한 번에 불러옵니다.
# 불러온 이미지는 images 딕셔너리, 효과음은 sounds 딕셔너리에 저장됩니다.
def load_assets():
    images = {}
    sounds = {}
    audio_enabled = False

    # skins.py에서 사용할 수 있는 이미지 이름 목록을 가져와 전부 한 번씩 찾아봅니다.
    image_names = COMMON_IMAGE_NAMES + ALLY_IMAGE_NAMES + SKILL_IMAGE_NAMES + stage_image_names(STAGE_MAX)
    for name in image_names:
        path = find_asset(IMAGE_DIR, [name], IMAGE_EXTENSIONS)
        if not path:
            continue
        try:
            # convert_alpha()는 PNG 투명 배경을 빠르게 그릴 수 있게 변환합니다.
            images[name] = pygame.image.load(str(path)).convert_alpha()
        except pygame.error:
            print(f"이미지를 불러오지 못했습니다: {path}")

    try:
        # 컴퓨터에 오디오 장치가 없거나 권한 문제가 있으면 mixer 초기화가 실패할 수 있습니다.
        pygame.mixer.init()
        # 기본 채널 수가 적으면 효과음이 겹칠 때 sound.play()가 실패할 수 있습니다.
        # 채널을 넉넉히 늘려 대포/피격/폭발음/번개가 동시에 나도 빠지는 일을 줄입니다.
        pygame.mixer.set_num_channels(64)
        # 앞쪽 14개 채널은 중요한 효과음 전용으로 예약합니다.
        # 대포처럼 자주 나는 소리는 여러 채널을 돌려 써서 앞 소리를 덜 자릅니다.
        pygame.mixer.set_reserved(15)
        audio_enabled = True
    except pygame.error:
        audio_enabled = False

    if not audio_enabled:
        # 소리가 안 되는 환경이어도 이미지만으로 게임은 실행되게 합니다.
        return images, sounds, audio_enabled

    # 효과음도 이미지와 같은 방식으로 이름 목록을 돌며 불러옵니다.
    sound_names = COMMON_SOUND_NAMES + stage_sound_names(STAGE_MAX)
    for name in sound_names:
        candidate_names = SOUND_NAME_ALIASES.get(name, (name,))
        path = find_asset_in_folders(AUDIO_SEARCH_DIRS, candidate_names, AUDIO_EXTENSIONS)
        if not path:
            continue
        try:
            sounds[name] = pygame.mixer.Sound(str(path))
        except pygame.error:
            print(f"효과음을 불러오지 못했습니다: {path}")

    return images, sounds, audio_enabled


# 게임 플레이 배경음악 bgm 파일을 찾아 반복 재생합니다.
# 오디오 장치가 없거나 파일이 없으면 조용히 넘어가서 게임 실행을 방해하지 않습니다.
def play_menu_music(game):
    # 대기화면 BGM
    play_named_music(game, ["pagebgm"], "menu_bgm", 0.4)


def play_music(game):
    # 전투화면 BGM
    play_named_music(game, ["bgm"], "battle_bgm", 0.4)

# 스테이지 선택 화면용 배경음악을 재생합니다.
# assets/audio/stage_select_bgm.mp3 파일을 넣으면 자동으로 사용합니다.
def play_stage_select_music(game):
    # stage_select_bgm이 가장 명확한 이름이고, campaign_bgm은 예비 별칭입니다.
    play_named_music(game, ["stage_select_bgm", "campaign_bgm"], "stage_select_bgm", 0.36)


# 난중일기/스토리 화면용 배경음악을 재생합니다.
# 더 구체적인 파일이 있으면 우선 사용하고, 없으면 공통 story_bgm을 사용합니다.
def play_story_music(game):
    if getattr(game, "story_id", "stage") == "intro":
        # 도입부는 4월 13일, 14일, 15일처럼 날짜별 페이지를 따로 가질 수 있습니다.
        intro_page_number = getattr(game, "story_page_index", 0) + 1
        names = [
            f"story_intro_page{intro_page_number}_bgm",
            "story_intro_bgm",
            "story_bgm",
            "nanjung_bgm",
        ]
        play_named_music(game, names, f"story_intro_bgm_{intro_page_number}", 0.38)
        return

    # stage_number는 1부터 시작하는 번호입니다. game.stage_index가 0이면 1스테이지입니다.
    stage_number = getattr(game, "stage_index", 0) + 1
    # page_number도 1부터 시작하도록 +1 합니다.
    page_number = getattr(game, "story_page_index", 0) + 1
    # phase_number는 1단계 사천포/당포처럼 내부 전투별 스토리 BGM을 나눌 때 씁니다.
    phase_number = getattr(game, "stage_phase", 0) + 1
    # names 앞쪽에 있는 파일일수록 우선순위가 높습니다.
    # 예: story_stage2_page3_bgm.mp3가 있으면 2단계 3편에서 그 곡을 사용합니다.
    names = [
        f"story_stage{stage_number}_phase{phase_number}_page{page_number}_bgm",
        f"story_stage{stage_number}_phase{phase_number}_bgm",
        f"story_stage{stage_number}_page{page_number}_bgm",
        f"story_stage{stage_number}_bgm",
        "story_bgm",
        "nanjung_bgm",
    ]
    play_named_music(game, names, f"story_bgm_{stage_number}_{phase_number}_{page_number}", 0.38)


# pygame.mixer.music으로 배경음악 파일 1개를 반복 재생합니다.
# 효과음은 pygame.mixer.Sound를 쓰지만, 배경음악은 긴 파일이라 music 채널 하나를 공유합니다.
def play_named_music(game, names, music_key, volume):
    if not game.audio_enabled:
        return

    # 이미 같은 음악이 재생 중이면 처음부터 다시 틀지 않습니다.
    # 이 조건이 없으면 화면을 다시 열 때 음악이 매번 끊겨 들릴 수 있습니다.
    if getattr(game, "current_music_key", None) == music_key:
        return

    # 여러 이름 후보 중 실제 존재하는 파일을 찾습니다.
    path = find_asset_in_folders(AUDIO_SEARCH_DIRS, names, AUDIO_EXTENSIONS)
    if not path:
        # 해당 화면 전용 음악이 없으면 이전 전투 음악이 계속 흐르지 않도록 멈춥니다.
        stop_music(game)
        return

    try:
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)
        game.current_music_key = music_key
    except pygame.error:
        print(f"배경음악을 재생하지 못했습니다: {path}")


# 게임 플레이가 끝났거나 메뉴로 돌아갈 때 배경음악을 멈춥니다.
def stop_music(game):
    if not game.audio_enabled:
        return

    try:
        pygame.mixer.music.stop()
        game.current_music_key = None
    except pygame.error:
        pass


# 중요한 효과음이 사용할 전용 채널 번호 묶음입니다.
# 한 효과음에 여러 채널을 주면 동시에 여러 번 재생되어도 소리가 덜 씹힙니다.
DEDICATED_SOUND_CHANNELS = {
    "shoot": (0, 1, 2, 3),
    "hit": (4, 5),
    "destroy": (6, 7),
    "weather_lightning": (8, 9),
    "boss": (10,),
    "skill": (11, 12),
    "ultimate": (13,),
}


# 이미 불러온 Sound 객체를 실제로 재생합니다.
# channel_name이 있으면 전용 채널을 써서 중요한 효과음이 묻히지 않게 합니다.
def play_loaded_sound(game, sound, volume=0.65, channel_name=None):
    if not game.audio_enabled:
        return

    if sound is None:
        # 파일이 없어도 게임이 멈추지 않게 조용히 넘어갑니다.
        return

    sound.set_volume(volume)
    channel_indexes = DEDICATED_SOUND_CHANNELS.get(channel_name)
    if channel_indexes is not None:
        # 대포 발사음처럼 짧고 중요한 소리는 전용 채널 묶음에서 빈 채널을 먼저 찾습니다.
        # 모두 바쁠 때만 첫 번째 채널을 강제로 써서 최신 효과음이 완전히 빠지지 않게 합니다.
        channel = find_available_dedicated_channel(channel_indexes)
        channel.set_volume(volume)
        channel.play(sound)
        return

    channel = sound.play()
    if channel is None:
        # 모든 일반 채널이 바쁘면 강제로 빈 채널을 확보해서 소리를 재생합니다.
        fallback_channel = pygame.mixer.find_channel(True)
        if fallback_channel is not None:
            fallback_channel.set_volume(volume)
            fallback_channel.play(sound)


# 전용 채널 묶음 안에서 지금 비어 있는 채널을 찾습니다.
def find_available_dedicated_channel(channel_indexes):
    for channel_index in channel_indexes:
        channel = pygame.mixer.Channel(channel_index)
        if not channel.get_busy():
            return channel

    return pygame.mixer.Channel(channel_indexes[0])


# 공통 효과음 이름으로 사운드를 재생합니다.
# name은 "shoot", "hit", "weather_lightning" 같은 키이고, volume은 0.0부터 1.0 사이 볼륨입니다.
def play_sound(game, name, volume=0.65):
    # name에 맞는 Sound 객체를 딕셔너리에서 꺼냅니다.
    sound = game.sounds.get(name)
    # shoot/hit/destroy 같은 중요 효과음은 전용 채널을 사용합니다.
    play_loaded_sound(game, sound, volume, name)


# 스테이지별 효과음을 먼저 재생하고, 없으면 공통 효과음을 대신 재생합니다.
# 예: kind="shoot", 2스테이지면 shoot_stage2를 먼저 찾고 없으면 shoot를 사용합니다.
def play_stage_sound(game, kind, volume=0.65):
    # 예: 2스테이지 발사음이면 shoot_stage2를 먼저 찾습니다.
    stage_number = game.stage_index + 1
    stage_key = f"{kind}_stage{stage_number}"
    # 스테이지별 사운드가 있으면 그것을 쓰고, 없으면 공통 사운드를 씁니다.
    sound = game.sounds.get(stage_key) or game.sounds.get(kind)
    # kind가 shoot이면 전용 대포 채널을 쓰므로, 빠른 발사 중에도 소리가 안정적으로 납니다.
    play_loaded_sound(game, sound, volume, kind)


# 스토리 타자 애니메이션 중 타이핑 효과음을 켜거나 끕니다.
# enabled=True면 루프 재생, False면 즉시 정지합니다.
def set_story_typing_sound_enabled(game, enabled):
    if not getattr(game, "audio_enabled", False):
        return

    try:
        channel = pygame.mixer.Channel(STORY_TYPING_CHANNEL_INDEX)
    except pygame.error:
        return

    if not enabled:
        if getattr(game, "story_typing_sound_active", False):
            channel.stop()
            game.story_typing_sound_active = False
        return

    sound = game.sounds.get("typing")
    if sound is None:
        return

    if not getattr(game, "story_typing_sound_active", False) or not channel.get_busy():
        sound.set_volume(0.26)
        channel.play(sound, loops=-1)
        game.story_typing_sound_active = True


# 현재 스테이지에 맞는 이미지를 가져옵니다.
# 스테이지 전용 이미지가 없으면 공통 이미지를 사용하거나 None을 돌려줍니다.
def get_stage_image(game, kind):
    stage_number = game.stage_index + 1

    # 스테이지 전용 이미지가 있으면 우선 사용하고, 없으면 공통 이미지를 대신 씁니다.
    if kind == "stage":
        return game.images.get(f"stage{stage_number}") or game.images.get("game_background")
    if kind == "enemy":
        return game.images.get(f"enemy_stage{stage_number}") or game.images.get("enemy")
    if kind == "boss":
        return (
            game.images.get(f"mini_boss_stage{stage_number}")
            or game.images.get(f"boss_stage{stage_number}")
            or game.images.get("mini_boss")
        )
    if kind == "bullet":
        return game.images.get(f"bullet_stage{stage_number}") or game.images.get("bullet")
    if kind == "projectile":
        return game.images.get(f"projectile_stage{stage_number}")

    return None


# 스테이지 선택 화면에서 사용할 이미지를 가져옵니다.
# kind가 background이면 전체 배경, card이면 선택 카드 안 대표 이미지입니다.
def get_stage_select_image(game, kind, stage_index=None):
    if kind == "background":
        # stage_select_background.png가 있으면 스테이지 선택 화면 전체 배경으로 사용합니다.
        return game.images.get("stage_select_background")

    if kind == "panel":
        # stage_select_panel.png는 나중에 선택 화면 전체 디자인을 덮는 용도로 쓸 수 있습니다.
        return game.images.get("stage_select_panel")

    if kind == "card" and stage_index is not None:
        # stage_select_stage1.png처럼 스테이지별 카드 이미지를 찾습니다.
        return game.images.get(f"stage_select_stage{stage_index + 1}")

    return None


# 난중일기/스토리 화면에서 사용할 이미지를 가져옵니다.
# 더 구체적인 이미지부터 찾고, 없으면 공통 이미지로 넘어갑니다.
def get_story_image(game, kind):
    stage_number = getattr(game, "stage_index", 0) + 1
    page_number = getattr(game, "story_page_index", 0) + 1
    phase_number = getattr(game, "stage_phase", 0) + 1

    if kind == "background":
        # story_stage1_page1.png:
        #   1스테이지 1편 스토리 전용 배경 이미지입니다.
        # story_stage1.png:
        #   1스테이지 스토리 공통 배경 이미지입니다.
        # story_background.png:
        #   모든 스토리 공통 배경 이미지입니다.
        return (
            game.images.get(f"story_stage{stage_number}_phase{phase_number}_page{page_number}")
            or game.images.get(f"story_stage{stage_number}_page{page_number}")
            or game.images.get(f"story_stage{stage_number}")
            or game.images.get("story_background")
        )

    if kind == "paper":
        # story_paper.png는 텍스트 패널 배경 장식 이미지입니다.
        return game.images.get("story_paper")

    if kind == "boss":
        # story_boss_stage1.png는 전투 중 왼쪽 세로 요약 패널에만 쓰는 보스 초상입니다.
        # 전용 이미지가 없으면 전투에서 쓰는 미니보스/보스 이미지를 대신 보여줍니다.
        return (
            game.images.get(f"story_boss_stage{stage_number}")
            or game.images.get(f"mini_boss_stage{stage_number}")
            or game.images.get(f"boss_stage{stage_number}")
            or game.images.get("mini_boss")
        )

    if kind == "intro":
        # story_intro.png는 도입부 전용 이미지입니다.
        page_number = getattr(game, "story_page_index", 0) + 1
        return (
            game.images.get(f"story_intro_page{page_number}")
            or game.images.get("story_intro")
            or game.images.get("story_background")
        )

    return None


# 스테이지 결과 화면에서 사용할 이미지를 가져옵니다.
# 나중에 결과 화면 UI 이미지를 넣으면 이 함수가 자동으로 찾아줍니다.
def get_stage_result_image(game, kind):
    # stage_number는 사람이 보는 1부터 시작하는 스테이지 번호입니다.
    stage_number = getattr(game, "stage_index", 0) + 1

    if kind == "background":
        # stage_result_stage1.png가 있으면 해당 스테이지 전용 결과 배경으로 사용합니다.
        # 없으면 stage_result_background.png 공통 결과 배경을 사용합니다.
        return game.images.get(f"stage_result_stage{stage_number}") or game.images.get("stage_result_background")

    if kind == "panel":
        # stage_result_panel.png는 결과 수치를 올릴 패널 디자인 이미지입니다.
        return game.images.get("stage_result_panel")

    return None
