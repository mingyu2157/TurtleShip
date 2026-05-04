# results.py
# 역할:
#   한 스테이지 안에서 점수, 피격 횟수, 받은 피해량, 스킬 사용 횟수를 모읍니다.
#   스테이지 보스를 잡으면 이 기록을 바탕으로 결과 화면에 보여줄 데이터를 만듭니다.
#
# 초보자 포인트:
#   게임 결과는 전투 중에 조금씩 기록해야 마지막에 보여줄 수 있습니다.
#   예를 들어 플레이어가 맞을 때마다 record_player_hit()을 호출해 두면,
#   클리어 시점에 "몇 번 맞았는지"를 바로 알 수 있습니다.
#
# 공부 순서:
#   1. reset_stage_stats()에서 새 스테이지 기록이 어떻게 초기화되는지 봅니다.
#   2. record_player_hit(), record_skill_use()에서 전투 중 기록을 쌓는 방식을 봅니다.
#   3. build_stage_result()/build_end_result()에서 결과 화면용 딕셔너리를 만드는 방식을 봅니다.
from stages import get_stage_display_name


# 결과 화면에 표시할 스킬 이름입니다.
# 코드 내부 키는 영어로 두고, 화면에는 한국어 이름으로 바꿔 보여줍니다.
SKILL_LABELS = {
    "hakikjin": "학익진",
    "tanker": "몸빵",
    "healer": "치유",
    "ultimate": "필살기",
    "last_stand": "생즉사 사즉생",
}


# 새 스테이지를 시작할 때 전적 기록을 초기화합니다.
def reset_stage_stats(game):
    # current_stage_stats는 지금 플레이 중인 스테이지의 기록입니다.
    game.current_stage_stats = {
        # shots_fired는 플레이어가 대포를 몇 번 쐈는지 세는 값입니다.
        "shots_fired": 0,
        # hits_taken은 실제로 체력이 줄어든 피격 횟수입니다.
        "hits_taken": 0,
        # damage_taken은 이번 스테이지에서 실제로 잃은 체력 총합입니다.
        "damage_taken": 0,
        # skill_uses는 스킬별 사용 횟수를 모아두는 딕셔너리입니다.
        "skill_uses": {
            "hakikjin": 0,
            "tanker": 0,
            "healer": 0,
            "ultimate": 0,
            "last_stand": 0,
        },
    }


# 혹시 기록 딕셔너리가 아직 없으면 안전하게 만들어 줍니다.
def ensure_stage_stats(game):
    # getattr()은 속성이 없을 때 기본값을 돌려주므로, 예전 상태에서도 안전합니다.
    if not getattr(game, "current_stage_stats", None):
        reset_stage_stats(game)


# 플레이어가 대포를 한 번 발사했을 때 호출합니다.
def record_shot(game):
    # 기록 저장소가 없으면 먼저 만들어 둡니다.
    ensure_stage_stats(game)
    # shots_fired 값을 1 올려서 결과 화면에서 발사 횟수를 보여줄 수 있게 합니다.
    game.current_stage_stats["shots_fired"] += 1


# 플레이어가 실제로 피해를 받았을 때 호출합니다.
def record_player_hit(game, damage_amount):
    # 무적 등으로 피해가 0이면 피격으로 세지 않습니다.
    if damage_amount <= 0:
        return

    # 기록 저장소가 없으면 먼저 만들어 둡니다.
    ensure_stage_stats(game)
    # 맞은 횟수를 1 올립니다.
    game.current_stage_stats["hits_taken"] += 1
    # 받은 피해량은 정수로 누적해서 결과 화면이 읽기 쉽게 합니다.
    game.current_stage_stats["damage_taken"] += int(round(damage_amount))


# 스킬이 성공적으로 발동했을 때 호출합니다.
def record_skill_use(game, skill_key):
    # 기록 저장소가 없으면 먼저 만들어 둡니다.
    ensure_stage_stats(game)
    # skill_uses 딕셔너리를 가져옵니다.
    skill_uses = game.current_stage_stats["skill_uses"]
    # 아직 없는 스킬 키가 들어와도 결과 화면이 깨지지 않도록 기본값 0을 넣습니다.
    skill_uses.setdefault(skill_key, 0)
    # 해당 스킬 사용 횟수를 1 올립니다.
    skill_uses[skill_key] += 1


# 결과 화면에서 보여줄 스킬 사용 문장을 만듭니다.
def format_skill_summary(skill_uses):
    # 화면에 보여줄 문장을 차곡차곡 담을 리스트입니다.
    parts = []
    # SKILL_LABELS 순서대로 표시하면 결과 화면 순서가 항상 일정합니다.
    for key, label in SKILL_LABELS.items():
        # 없는 키는 0회로 처리합니다.
        count = skill_uses.get(key, 0)
        # "학익진 1회" 같은 짧은 문장을 만듭니다.
        parts.append(f"{label} {count}회")
    # 여러 문장을 쉼표로 이어서 한 줄 요약으로 만듭니다.
    return ", ".join(parts)


# 스테이지 클리어 시점에 결과 화면용 데이터를 만듭니다.
def build_stage_result(game, newly_unlocked, final_clear):
    # 기록 저장소가 없으면 먼저 만들어 둡니다.
    ensure_stage_stats(game)
    # 현재 스테이지 정보를 가져옵니다.
    stage = game.current_stage()
    # 현재 기록을 stats라는 짧은 이름으로 가져옵니다.
    stats = game.current_stage_stats
    # 스킬 사용 횟수 딕셔너리를 가져옵니다.
    skill_uses = stats.get("skill_uses", {})
    # stage_number는 사람이 보는 1부터 시작하는 번호입니다.
    stage_number = game.stage_index + 1

    # game.stage_result는 화면에 그대로 넘길 결과 데이터입니다.
    game.stage_result = {
        # stage_index는 코드가 쓰는 0부터 시작하는 번호입니다.
        "stage_index": game.stage_index,
        # stage_number는 화면에 보여줄 1부터 시작하는 번호입니다.
        "stage_number": stage_number,
        # stage_name은 결과 화면 제목에 씁니다.
        "stage_name": get_stage_display_name(game),
        # score는 현재 스테이지 점수입니다.
        "score": int(game.score),
        # kills는 이번 스테이지에서 격침한 일반 적 수입니다.
        "kills": int(getattr(game, "stage_total_kills", 0) + game.kill_count),
        # shots_fired는 플레이어 대포 발사 횟수입니다.
        "shots_fired": int(stats.get("shots_fired", 0)),
        # hits_taken은 체력이 실제로 줄어든 피격 횟수입니다.
        "hits_taken": int(stats.get("hits_taken", 0)),
        # damage_taken은 받은 피해량 총합입니다.
        "damage_taken": int(stats.get("damage_taken", 0)),
        # skill_uses는 스킬별 사용 횟수 원본입니다.
        "skill_uses": dict(skill_uses),
        # skill_summary는 화면에 바로 찍을 수 있는 스킬 사용 요약 문장입니다.
        "skill_summary": format_skill_summary(skill_uses),
        # newly_unlocked는 이번 클리어로 다음 스테이지가 새로 열렸는지 나타냅니다.
        "newly_unlocked": newly_unlocked,
        # final_clear는 5스테이지까지 끝냈는지 나타냅니다.
        "final_clear": final_clear,
    }

    # 다음 스테이지가 열렸으면 결과 화면에 보여줄 안내 문구를 넣습니다.
    if newly_unlocked and not final_clear:
        game.stage_result["unlock_text"] = f"{stage_number + 1}단계 해금"
    # 마지막 스테이지라면 캠페인 완료 문구를 넣습니다.
    elif final_clear:
        game.stage_result["unlock_text"] = "캠페인 최종 클리어"
    # 새로 열린 스테이지가 없으면 단순 클리어 문구를 넣습니다.
    else:
        game.stage_result["unlock_text"] = "스테이지 클리어"

    # 완성된 결과 딕셔너리를 돌려주면 테스트나 다른 코드에서 바로 확인할 수 있습니다.
    return game.stage_result


# 게임오버 또는 전체 클리어 화면에 보여줄 최종 결과 데이터를 만듭니다.
def build_end_result(game, clear):
    # 기록 저장소가 없으면 먼저 만들어 둡니다.
    ensure_stage_stats(game)
    # 현재 기록을 stats라는 짧은 이름으로 가져옵니다.
    stats = game.current_stage_stats
    # 스킬 사용 횟수 딕셔너리를 가져옵니다.
    skill_uses = stats.get("skill_uses", {})

    # 마지막 스테이지 클리어 후 전체 클리어 화면으로 넘어가는 경우에는
    # 이미 stage_result에 정확한 클리어 결과가 있으므로 그 값을 우선 재사용합니다.
    if clear and getattr(game, "stage_result", None):
        base_result = dict(game.stage_result)
    else:
        base_result = {
            # stage_index는 코드가 쓰는 0부터 시작하는 번호입니다.
            "stage_index": getattr(game, "stage_index", 0),
            # stage_number는 화면에 보여줄 1부터 시작하는 번호입니다.
            "stage_number": getattr(game, "stage_index", 0) + 1,
            # stage_name은 끝 화면의 보조 제목으로 씁니다.
            "stage_name": get_stage_display_name(game),
            # score는 현재 점수입니다.
            "score": int(getattr(game, "score", 0)),
            # kills는 현재 스테이지에서 격침한 일반 적 수입니다.
            "kills": int(getattr(game, "stage_total_kills", 0) + getattr(game, "kill_count", 0)),
            # shots_fired는 플레이어 대포 발사 횟수입니다.
            "shots_fired": int(stats.get("shots_fired", 0)),
            # hits_taken은 체력이 실제로 줄어든 피격 횟수입니다.
            "hits_taken": int(stats.get("hits_taken", 0)),
            # damage_taken은 받은 피해량 총합입니다.
            "damage_taken": int(stats.get("damage_taken", 0)),
            # skill_uses는 스킬별 사용 횟수 원본입니다.
            "skill_uses": dict(skill_uses),
            # skill_summary는 화면에 바로 찍을 수 있는 스킬 사용 요약 문장입니다.
            "skill_summary": format_skill_summary(skill_uses),
        }

    # 끝 화면 종류에 맞는 제목과 안내 문구를 추가합니다.
    base_result["clear"] = clear
    base_result["title"] = "승리했습니다" if clear else "게임 오버"
    base_result["detail"] = "5개의 스테이지를 모두 돌파했습니다." if clear else "전투 결과를 확인하고 다시 도전해보세요."
    # game.end_result는 ui.draw_end_screen()이 그대로 읽는 최종 결과입니다.
    game.end_result = base_result
    return base_result
