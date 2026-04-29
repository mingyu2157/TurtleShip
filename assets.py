# assets.py
# 역할:
#   이미지와 효과음을 파일에서 읽어와 game.images, game.sounds에 넣습니다.
#   파일이 없으면 게임이 멈추지 않고 기본 도형/배경으로 대체되도록 설계했습니다.
#
# 파일 이름 규칙:
#   skins.py에 적힌 이름을 기준으로 assets/images, assets/audio 폴더에서 찾습니다.
#   예를 들어 enemy_stage1.png가 있으면 1스테이지 적 이미지로 자동 사용됩니다.
import pygame

from settings import AUDIO_DIR, AUDIO_EXTENSIONS, IMAGE_DIR, IMAGE_EXTENSIONS
from skins import (
    ALLY_IMAGE_NAMES,
    COMMON_IMAGE_NAMES,
    COMMON_SOUND_NAMES,
    ITEM_IMAGE_NAMES,
    SKILL_IMAGE_NAMES,
    stage_image_names,
    stage_sound_names,
)
from stages import STAGE_MAX


# 폴더 안에서 여러 확장자 중 실제 존재하는 파일을 찾습니다.
# 예: ["shoot"], [".mp3", ".ogg", ".wav"]를 넣으면 shoot.mp3부터 차례로 찾습니다.
def find_asset(folder, names, extensions):
    for name in names:
        for extension in extensions:
            path = folder / f"{name}{extension}"
            if path.exists():
                return path
    return None


# 게임 시작 시 이미지와 효과음을 한 번에 불러옵니다.
# 불러온 이미지는 images 딕셔너리, 효과음은 sounds 딕셔너리에 저장됩니다.
def load_assets():
    images = {}
    sounds = {}
    audio_enabled = False

    image_names = COMMON_IMAGE_NAMES + ALLY_IMAGE_NAMES + ITEM_IMAGE_NAMES + SKILL_IMAGE_NAMES + stage_image_names(STAGE_MAX)
    for name in image_names:
        path = find_asset(IMAGE_DIR, [name], IMAGE_EXTENSIONS)
        if not path:
            continue
        try:
            images[name] = pygame.image.load(str(path)).convert_alpha()
        except pygame.error:
            print(f"이미지를 불러오지 못했습니다: {path}")

    try:
        pygame.mixer.init()
        audio_enabled = True
    except pygame.error:
        audio_enabled = False

    if not audio_enabled:
        return images, sounds, audio_enabled

    sound_names = COMMON_SOUND_NAMES + stage_sound_names(STAGE_MAX)
    for name in sound_names:
        path = find_asset(AUDIO_DIR, [name], AUDIO_EXTENSIONS)
        if not path:
            continue
        try:
            sounds[name] = pygame.mixer.Sound(str(path))
        except pygame.error:
            print(f"효과음을 불러오지 못했습니다: {path}")

    return images, sounds, audio_enabled


# 배경음악 bgm 파일을 찾아 반복 재생합니다.
# 오디오 장치가 없거나 파일이 없으면 조용히 넘어가서 게임 실행을 방해하지 않습니다.
def play_music(game):
    if not game.audio_enabled:
        return

    path = find_asset(AUDIO_DIR, ["bgm"], AUDIO_EXTENSIONS)
    if not path:
        return

    try:
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(0.4)
        pygame.mixer.music.play(-1)
    except pygame.error:
        print(f"배경음악을 재생하지 못했습니다: {path}")


# 공통 효과음 이름으로 사운드를 재생합니다.
# name은 "shoot", "hit", "item" 같은 키이고, volume은 0.0부터 1.0 사이 볼륨입니다.
def play_sound(game, name, volume=0.65):
    if not game.audio_enabled:
        return

    sound = game.sounds.get(name)
    if sound is None:
        return

    sound.set_volume(volume)
    sound.play()


# 스테이지별 효과음을 먼저 재생하고, 없으면 공통 효과음을 대신 재생합니다.
# 예: kind="shoot", 2스테이지면 shoot_stage2를 먼저 찾고 없으면 shoot를 사용합니다.
def play_stage_sound(game, kind, volume=0.65):
    stage_number = game.stage_index + 1
    stage_key = f"{kind}_stage{stage_number}"
    play_sound(game, stage_key, volume)
    if stage_key not in game.sounds:
        play_sound(game, kind, volume)


# 현재 스테이지에 맞는 이미지를 가져옵니다.
# 스테이지 전용 이미지가 없으면 공통 이미지를 사용하거나 None을 돌려줍니다.
def get_stage_image(game, kind):
    stage_number = game.stage_index + 1

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
