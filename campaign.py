# campaign.py
# 역할:
#   1~5스테이지 캠페인 진행도를 저장하고 불러옵니다.
#   "1단계를 깨면 2단계 해금" 같은 잠금/해금 규칙은 이 파일에서 관리합니다.
#
# 초보자 포인트:
#   게임을 껐다 켜도 해금 상태가 유지되려면 파일에 저장해야 합니다.
#   여기서는 campaign_progress.json 파일에 현재 열린 스테이지 수와 클리어한 스테이지 수를 저장합니다.
#
# 공부 순서:
#   1. load_progress()는 저장 파일을 읽습니다.
#   2. save_progress()는 저장 파일에 씁니다.
#   3. unlock_stage_after_clear()는 스테이지를 깼을 때 다음 스테이지를 열어줍니다.
import json

from settings import BASE_DIR
from stages import STAGE_MAX


# 저장 파일 이름입니다.
# 프로젝트 폴더 안에 생기므로, 같은 컴퓨터에서 다시 실행해도 캠페인 진행도가 유지됩니다.
SAVE_PATH = BASE_DIR / "campaign_progress.json"

# 저장 파일이 없거나 깨졌을 때 사용할 기본값입니다.
# 처음 시작하면 1스테이지만 열려 있고, 아직 클리어한 스테이지는 없습니다.
DEFAULT_PROGRESS = {
    "unlocked_stage_count": 1,
    "cleared_stage_count": 0,
}


# 숫자가 너무 작거나 커지지 않게 안전한 범위로 잘라줍니다.
def clamp(value, low, high):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = low
    return max(low, min(high, number))


# 저장 데이터가 올바른 형태인지 정리합니다.
# 혹시 사용자가 파일을 직접 고쳤거나, 예전 버전 데이터가 있어도 게임이 멈추지 않게 합니다.
def normalize_progress(progress):
    if not isinstance(progress, dict):
        progress = {}

    unlocked = clamp(progress.get("unlocked_stage_count", 1), 1, STAGE_MAX)
    cleared = clamp(progress.get("cleared_stage_count", 0), 0, STAGE_MAX)
    # 클리어한 스테이지보다 열린 스테이지가 적으면 이상하므로 자동으로 맞춥니다.
    unlocked = max(unlocked, min(STAGE_MAX, cleared + 1 if cleared < STAGE_MAX else STAGE_MAX))

    return {
        "unlocked_stage_count": unlocked,
        "cleared_stage_count": cleared,
    }


# campaign_progress.json을 읽어서 진행도를 돌려줍니다.
# 파일이 없으면 기본값을 사용합니다.
def load_progress():
    if not SAVE_PATH.exists():
        return DEFAULT_PROGRESS.copy()

    try:
        with SAVE_PATH.open("r", encoding="utf-8") as file:
            return normalize_progress(json.load(file))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        # 저장 파일이 깨져도 게임은 처음 상태로 안전하게 시작합니다.
        return DEFAULT_PROGRESS.copy()


# 현재 진행도를 campaign_progress.json에 저장합니다.
def save_progress(progress):
    normalized = normalize_progress(progress)
    tmp_path = SAVE_PATH.with_name(f"{SAVE_PATH.name}.tmp")
    try:
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(normalized, file, ensure_ascii=False, indent=2)
        tmp_path.replace(SAVE_PATH)
    except OSError:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
    return normalized


# 저장된 진행도를 game 객체에 적용합니다.
# UI와 입력 처리는 game.unlocked_stage_count 값을 보고 스테이지 잠금 여부를 판단합니다.
def apply_progress_to_game(game):
    progress = load_progress()
    game.unlocked_stage_count = progress["unlocked_stage_count"]
    game.cleared_stage_count = progress["cleared_stage_count"]
    game.stage_select_index = clamp(getattr(game, "stage_select_index", 0), 0, game.unlocked_stage_count - 1)
    return progress


# 현재 열린 스테이지 개수를 안전하게 가져옵니다.
def get_unlocked_stage_count(game):
    return clamp(getattr(game, "unlocked_stage_count", 1), 1, STAGE_MAX)


# 현재 클리어한 스테이지 개수를 안전하게 가져옵니다.
def get_cleared_stage_count(game):
    return clamp(getattr(game, "cleared_stage_count", 0), 0, STAGE_MAX)


# stage_index가 플레이 가능한 상태인지 확인합니다.
# stage_index는 0부터 시작하므로 0은 1스테이지, 1은 2스테이지입니다.
def is_stage_unlocked(game, stage_index):
    return 0 <= stage_index < get_unlocked_stage_count(game)


# stage_index가 이미 클리어된 스테이지인지 확인합니다.
def is_stage_cleared(game, stage_index):
    return 0 <= stage_index < get_cleared_stage_count(game)


# 스테이지를 클리어했을 때 다음 스테이지를 열고 저장합니다.
# 반환값은 이번 클리어로 새 스테이지가 열렸는지 여부입니다.
def unlock_stage_after_clear(game, stage_index):
    old_unlocked = get_unlocked_stage_count(game)
    cleared = max(get_cleared_stage_count(game), clamp(stage_index + 1, 0, STAGE_MAX))
    unlocked = max(old_unlocked, min(STAGE_MAX, stage_index + 2))

    progress = save_progress(
        {
            "unlocked_stage_count": unlocked,
            "cleared_stage_count": cleared,
        }
    )
    game.unlocked_stage_count = progress["unlocked_stage_count"]
    game.cleared_stage_count = progress["cleared_stage_count"]
    return progress["unlocked_stage_count"] > old_unlocked
