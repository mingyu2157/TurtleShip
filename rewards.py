# rewards.py
# 역할:
#   "적을 파괴했을 때 무엇을 보상으로 줄지"를 한곳에서 연결합니다.
#   동료 생성, 아이템 드롭, 필살기 충전은 서로 다른 파일에 있지만
#   combat.py가 여러 파일을 직접 다 알 필요는 없게 이 파일이 중간 다리 역할을 합니다.
#
# 초보자 포인트:
#   기능이 많아질수록 한 파일에 다 넣으면 찾기 어려워집니다.
#   그래서 combat.py는 "적이 파괴됨"만 알려주고,
#   rewards.py가 어떤 보상을 줄지 각각의 기능 파일에 전달합니다.
import allies
import items
import skills


# 게임을 새로 시작할 때 보상 관련 상태를 모두 초기화합니다.
# 탄환 강화 단계, 연사 시간, 동료 목록, 아이템 목록, 필살기 충전량을 정리합니다.
def reset_rewards(game):
    game.bullet_level = 0
    game.rapid_fire_timer = 0
    allies.reset_allies(game)
    items.reset_items(game)
    skills.reset_skills(game)


# 스테이지가 넘어갈 때 정리할 보상 상태입니다.
# 현재는 화면에 남아 있는 아이템만 지우고, 나중에 동료 유지 여부도 여기서 정할 수 있습니다.
def on_stage_change(game):
    items.reset_items(game)


# 보상 관련 기능들을 매 프레임 업데이트합니다.
# 동료 이동/발사, 아이템 이동/획득, 필살기 타이머 감소가 여기서 한꺼번에 호출됩니다.
def update_rewards(game, dt):
    game.rapid_fire_timer = max(0, getattr(game, "rapid_fire_timer", 0) - dt)
    allies.update_allies(game, dt)
    items.update_items(game, dt)
    skills.update_skills(game, dt)


# 적이 파괴되었을 때 호출되는 함수입니다.
# 나중에 확장할 때도 combat.py를 많이 고치지 않고 이 함수 안에서 보상 규칙을 바꾸면 됩니다.
def on_enemy_destroyed(game, enemy):
    allies.maybe_spawn_ally(game, enemy)
    items.maybe_spawn_item(game, enemy)
    skills.add_ultimate_charge(game, 5)
