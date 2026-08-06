# rewards.py
# 역할:
#   "적을 파괴했을 때 무엇을 보상으로 줄지"를 한곳에서 연결합니다.
#   캠페인과 점수 경쟁 모두 현재 판 전용 경험치를 지급합니다.
#
# 초보자 포인트:
#   기능이 많아질수록 한 파일에 다 넣으면 찾기 어려워집니다.
#   그래서 combat.py는 "적이 파괴됨"만 알려주고,
#   rewards.py가 어떤 보상을 줄지 각각의 기능 파일에 전달합니다.
#
# 공부 순서:
#   on_enemy_destroyed() 하나만 보면 적 격침 후 점수/경험치/충전이 어떻게 연결되는지 보입니다.
import augments
import skills


# 게임을 새로 시작할 때 보상 관련 상태를 모두 초기화합니다.
# 필살기 충전량과 전술 스킬 타이머를 정리합니다.
def reset_rewards(game):
    # 증강 초기화는 actors.py가 스테이지/점수 경쟁 시작 시점에 한 번만 처리합니다.
    # 여기서 다시 끄면 전투 중 선택한 증강까지 사라질 수 있으므로 건드리지 않습니다.
    # 새 게임에서는 전술 스킬과 필살기 충전량을 초기 상태로 되돌립니다.
    skills.reset_skills(game)


# 보상 관련 기능들을 매 프레임 업데이트합니다.
# 스킬 타이머 감소가 여기서 호출됩니다.
def update_rewards(game, dt):
    # 전술 스킬은 지속시간과 재사용 대기시간이 있으므로 매 프레임 업데이트가 필요합니다.
    skills.update_skills(game, dt)


# 적이 파괴되었을 때 호출되는 함수입니다.
# 나중에 확장할 때도 combat.py를 많이 고치지 않고 이 함수 안에서 보상 규칙을 바꾸면 됩니다.
def on_enemy_destroyed(game, enemy):
    # 새로운 보상 시스템을 추가하려면 이 함수에 한 줄을 더 연결하면 됩니다.
    # 캠페인과 점수 경쟁 모두 현재 판 전용 경험치를 얻습니다.
    augments.add_experience(game, 12 + game.stage_index * 4)
    skills.add_ultimate_charge(game, 5)


# 보스를 격파했을 때 현재 판 레벨업용 큰 경험치를 지급합니다.
def on_boss_destroyed(game):
    augments.add_experience(game, 80 + game.stage_index * 35)
    skills.add_ultimate_charge(game, 25)
