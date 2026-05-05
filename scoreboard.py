# scoreboard.py
# 역할:
#   점수 경쟁 모드의 닉네임/점수를 JSON 파일에 저장하고 상위 10명만 유지합니다.
import json
from datetime import datetime

from settings import BASE_DIR


SCOREBOARD_PATH = BASE_DIR / "scoreboard.json"
MAX_ENTRIES = 10
MAX_NICKNAME_LENGTH = 12
DEFAULT_NICKNAME = "무명"


# 공백과 너무 긴 이름을 정리해서 저장/표시 규칙을 한곳에서 맞춥니다.
def clean_nickname(nickname):
    text = str(nickname or "").strip()
    text = " ".join(text.split())
    if not text:
        text = DEFAULT_NICKNAME
    return text[:MAX_NICKNAME_LENGTH]


# 저장 파일 안의 이상한 데이터도 안전한 점수 기록 형태로 고쳐줍니다.
def normalize_entry(entry):
    if not isinstance(entry, dict):
        return None

    nickname = clean_nickname(entry.get("nickname", ""))
    try:
        score = int(entry.get("score", 0))
    except (TypeError, ValueError):
        score = 0
    if score < 0:
        score = 0

    return {
        "nickname": nickname,
        "score": score,
        "date": str(entry.get("date", ""))[:24],
    }


# 점수는 높은 순, 동점이면 닉네임 순으로 정렬하고 상위 10개만 남깁니다.
def sort_entries(entries):
    return sorted(entries, key=lambda entry: (-entry["score"], entry["nickname"]))[:MAX_ENTRIES]


# scoreboard.json을 읽되, 파일이 없거나 깨졌으면 빈 점수판으로 시작합니다.
def load_scores():
    if not SCOREBOARD_PATH.exists():
        return []

    try:
        with SCOREBOARD_PATH.open("r", encoding="utf-8") as file:
            raw_entries = json.load(file)
    except (OSError, json.JSONDecodeError, TypeError):
        return []

    if not isinstance(raw_entries, list):
        return []

    best_by_name = {}
    for raw_entry in raw_entries:
        entry = normalize_entry(raw_entry)
        if entry is None:
            continue
        # 같은 닉네임은 가장 높은 점수 1개만 남겨 점수판이 중복으로 채워지지 않게 합니다.
        current = best_by_name.get(entry["nickname"])
        if current is None or entry["score"] > current["score"]:
            best_by_name[entry["nickname"]] = entry

    return sort_entries(best_by_name.values())


# 저장 중 게임이 꺼져도 JSON이 반쯤 깨지지 않도록 임시 파일을 만든 뒤 교체합니다.
def save_scores(entries):
    normalized = []
    for entry in entries:
        fixed = normalize_entry(entry)
        if fixed is not None:
            normalized.append(fixed)

    top_entries = sort_entries(normalized)
    tmp_path = SCOREBOARD_PATH.with_name(f"{SCOREBOARD_PATH.name}.tmp")
    try:
        SCOREBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(top_entries, file, ensure_ascii=False, indent=2)
        tmp_path.replace(SCOREBOARD_PATH)
    except OSError:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
    return top_entries


# 게임이 끝났을 때 새 점수를 제출하고, 저장된 상위 10명과 이번 순위를 돌려줍니다.
def submit_score(nickname, score):
    try:
        score_value = int(score)
    except (TypeError, ValueError):
        score_value = 0

    entry = {
        "nickname": clean_nickname(nickname),
        "score": max(0, score_value),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    entries = load_scores()
    replaced = False
    accepted = False
    for index, old_entry in enumerate(entries):
        if old_entry["nickname"] != entry["nickname"]:
            continue
        replaced = True
        if entry["score"] > old_entry["score"]:
            entries[index] = entry
            accepted = True
        break

    if not replaced:
        entries.append(entry)
        accepted = True

    top_entries = sort_entries(entries)
    save_scores(top_entries)

    rank = None
    if accepted:
        for index, top_entry in enumerate(top_entries):
            if top_entry["nickname"] == entry["nickname"] and top_entry["score"] == entry["score"]:
                rank = index + 1
                break
    return top_entries, rank
