# settings.py
# 역할:
#   게임 전체에서 공통으로 쓰는 설정값을 모아둡니다.
#   색상, 기본 화면 크기, FPS, 에셋 폴더 경로, 이동 키 scancode가 여기에 있습니다.
#
# 초보자 포인트:
#   여러 파일에서 같은 숫자나 색상을 직접 쓰면 나중에 수정하기 어렵습니다.
#   이렇게 설정 파일에 모아두면 한 곳만 바꿔도 전체 게임에 적용됩니다.
from pathlib import Path


# RGB 색상값입니다. pygame은 (빨강, 초록, 파랑) 튜플로 색을 표현합니다.
BLACK = (0, 0, 0)
WHITE = (245, 247, 255)
GRAY = (170, 178, 195)
RED = (235, 83, 83)
BLUE = (82, 173, 255)
GREEN = (100, 226, 160)
YELLOW = (255, 213, 92)

# 기본 창 크기와 최소 창 크기입니다.
DEFAULT_PAD_WIDTH = 480
DEFAULT_PAD_HEIGHT = 640
MIN_PAD_WIDTH = 420
MIN_PAD_HEIGHT = 560
FPS = 60

# 프로젝트 기준 경로와 이미지/오디오 폴더 위치입니다.
BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "assets" / "images"
AUDIO_DIR = BASE_DIR / "assets" / "audio"
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
AUDIO_EXTENSIONS = (".mp3", ".ogg", ".wav")

# 한글 입력 상태에서도 WASD 물리 키를 인식하기 위한 scancode 목록입니다.
# key 값은 문자 입력 상태에 영향을 받을 수 있지만, scancode는 키보드 위치에 가깝습니다.
MOVE_SCANCODES = {
    "left": {4, 80},
    "right": {7, 79},
    "up": {26, 82},
    "down": {22, 81},
}
