# combat.py
# 역할:
#   발사 명령, 충돌 판정, 체력 감소처럼 "전투 결과"를 처리합니다.
#   탄환의 실제 이동과 생성 데이터는 projectiles.py에 있고,
#   적을 잡았을 때 보상 처리는 rewards.py에 연결해 둡니다.
#
# 초보자 포인트:
#   게임에서는 보통 "무엇이 닿았는지"를 먼저 찾고,
#   닿았다면 체력 감소, 점수 증가, 삭제 같은 결과를 처리합니다.
#
# 공부 순서:
#   1. shoot_player_bullet()로 플레이어 발사 구조를 봅니다.
#   2. check_collisions()에서 어떤 충돌 검사를 어떤 순서로 하는지 봅니다.
#   3. damage_boss(), damage_player()에서 체력 감소 규칙을 봅니다.
import actors
import assets
import obstacles
import projectiles
import rewards
import results
import skills


# 현재 무기 진화 단계에 맞춰 대포 기본 수치를 계산합니다.
# 일반 증강 피해/크기와 PDF 설정의 총통 진화 보너스를 함께 더합니다.
def get_player_weapon_stats(game):
    # weapon_tier는 augments.py에서 관리하며, 0은 기본 황자총통입니다.
    tier = max(0, min(3, getattr(game, "weapon_tier", 0)))
    # 단계별 피해 보너스입니다. 현자총통부터 피해가 조금씩 커집니다.
    tier_damage_bonus = (0, 4, 8, 13)[tier]
    # 지자총통부터는 광역 느낌을 주기 위해 탄환 충돌 반지름도 키웁니다.
    tier_radius_bonus = (0, 0, 2, 4)[tier]
    # 이미지 포탄은 판정보다 조금 크게 보이므로 단계가 높을수록 padding도 커집니다.
    tier_image_padding = (6, 7, 8, 9)[tier]
    # 기존 화포 강화 증강과 무기 진화 보너스를 합쳐 최종 피해량을 만듭니다.
    damage = 18 + getattr(game, "augment_bullet_damage", 0) + tier_damage_bonus
    damage *= getattr(game, "augment_allied_attack_multiplier", 1.0)
    if getattr(game, "last_stand_damage_timer", 0) > 0:
        damage *= getattr(game, "last_stand_damage_multiplier", 1.0)
    elif getattr(game, "last_stand_revive_penalty_timer", 0) > 0:
        damage *= (1.0 - skills.LAST_STAND_REVIVE_PENALTY)
    # 기존 대형 포환 증강과 무기 진화 보너스를 합쳐 최종 탄환 크기를 만듭니다.
    radius = 3 + getattr(game, "augment_bullet_radius", 0) + tier_radius_bonus
    return tier, damage, radius, tier_image_padding


# 무기 진화 단계별 발사 패턴입니다.
# 반환값의 첫 번째 값은 가로 속도이고, 두 번째 값은 피해량 배율입니다.
def get_player_weapon_pattern(tier):
    if tier >= 3:
        # 천자총통은 중앙 1발과 좌우 4발을 함께 쏘는 강한 광역 포격입니다.
        return [(0, 1.0), (-120, 0.74), (120, 0.74), (-220, 0.55), (220, 0.55)]
    if tier >= 2:
        # 지자총통은 중앙 1발과 좌우 2발을 함께 쏘는 기본 광역 포격입니다.
        return [(0, 1.0), (-115, 0.68), (115, 0.68)]
    # 황자총통/현자총통은 한 줄로 곧게 나가는 일자 포격입니다.
    return [(0, 1.0)]


# 플레이어가 발사 버튼을 눌렀을 때 호출됩니다.
# shoot_cooldown이 남아 있으면 아직 다음 탄환을 쏠 수 없으므로 바로 return 합니다.
def shoot_player_bullet(game):
    if not game.player or game.shoot_cooldown > 0:
        return

    # 스테이지마다 총알 색상/이미지가 달라질 수 있어서 현재 스테이지 데이터를 가져옵니다.
    stage = game.current_stage()
    rect = game.player["rect"]
    speed = -620
    color = stage["bullet_color"]
    # PDF 설정의 총통 진화 단계와 현재 판 증강을 합쳐 탄환 수치를 계산합니다.
    tier, damage, radius, image_padding = get_player_weapon_stats(game)

    # 무기 단계별 패턴만큼 탄환을 생성합니다.
    for vx, damage_scale in get_player_weapon_pattern(tier):
        projectiles.make_player_bullet(
            game,
            rect.centerx,
            rect.top - 8,
            vx,
            speed,
            max(1, damage * damage_scale),
            radius,
            color,
            image_padding=image_padding,
        )

    # 결과 화면에 보여줄 대포 발사 횟수를 기록합니다.
    # 여러 발이 나가는 무기여도 사용자가 Space를 한 번 누른 것은 한 번의 발사로 셉니다.
    results.record_shot(game)

    # 장전 훈련 증강이 있으면 다음 발사까지 기다리는 시간이 짧아집니다.
    base_cooldown = 0.65
    total_reload_bonus = getattr(game, "augment_reload_bonus", 0) + getattr(game, "augment_perma_reload_speed_bonus", 0)
    game.shoot_cooldown = max(0.08, base_cooldown * (1 - min(0.8, total_reload_bonus)))
    assets.play_stage_sound(game, "shoot", 0.5)


# 한 프레임 동안 필요한 모든 충돌 검사를 호출합니다.
# 플레이어 탄환 vs 적, 플레이어 탄환 vs 보스, 보스 몸통 접촉,
# 몸빵 방패선, 플레이어 vs 적, 적 탄환 vs 플레이어 순서입니다.
def check_collisions(game):
    # 지형지물이 탄환을 먼저 막아야 뒤에서 적/플레이어와 중복 충돌하지 않습니다.
    obstacles.block_projectiles(game)
    check_bullet_enemy_collisions(game)
    check_bullet_boss_collisions(game)
    check_boss_contact_collisions(game)
    check_guard_collisions(game)
    check_player_enemy_collisions(game)
    check_player_projectile_collisions(game)


# 플레이어 탄환이 일반 적과 닿았는지 검사합니다.
# 적 체력이 0 이하가 되면 적을 제거하고 점수/격침 수/보상 처리를 합니다.
def check_bullet_enemy_collisions(game):
    # 탄환 리스트를 돌다가 탄환을 지울 수 있으므로 복사본 game.bullets[:]를 사용합니다.
    for bullet in game.bullets[:]:
        # 탄환은 원처럼 보이지만 pygame 충돌은 Rect가 편해서 작은 사각형으로 바꿉니다.
        bullet_rect = get_circle_rect(bullet["x"], bullet["y"], bullet["radius"])
        hit_enemy = None

        # 이번 탄환이 맞춘 첫 번째 적만 찾습니다.
        for enemy in game.enemies:
            if enemy["rect"].colliderect(bullet_rect):
                hit_enemy = enemy
                break

        if hit_enemy is None:
            continue

        if bullet in game.bullets:
            # 적에게 닿은 탄환은 관통하지 않고 사라집니다.
            game.bullets.remove(bullet)

        hit_enemy["hp"] -= bullet["damage"]
        if hit_enemy["hp"] <= 0:
            # 적이 파괴되면 점수/격침 수를 올리고 rewards.py에 보상 처리를 맡깁니다.
            game.enemies.remove(hit_enemy)
            game.kill_count += 1
            game.score += 100 + game.stage_index * 25
            rewards.on_enemy_destroyed(game, hit_enemy)
            assets.play_stage_sound(game, "destroy", 0.45)


# 플레이어 탄환이 보스와 닿았는지 검사합니다.
# 보스는 보호막이 먼저 깎이고, 보호막이 없을 때 체력이 깎입니다.
def check_bullet_boss_collisions(game):
    if game.boss is None:
        return

    for bullet in game.bullets[:]:
        bullet_rect = get_circle_rect(bullet["x"], bullet["y"], bullet["radius"])
        if not game.boss["rect"].colliderect(bullet_rect):
            continue

        if bullet in game.bullets:
            game.bullets.remove(bullet)

        damage_boss(game, bullet["damage"])

        # 보스가 탄환으로 죽은 경우 현재 스테이지를 클리어하고 선택 화면으로 돌아갑니다.
        if game.boss is not None and game.boss["hp"] <= 0:
            game.score += 1200 + game.stage_index * 400
            actors.handle_boss_defeated(game)
            return


# 플레이어 배가 적 배와 직접 충돌했는지 검사합니다.
# 피해 판정은 이미지 전체가 아니라 actors.get_player_hitbox()의 작은 히트박스를 사용합니다.
def check_player_enemy_collisions(game):
    # 플레이어는 이미지 전체가 아니라 작은 hitbox로 맞았는지 판단합니다.
    player_hitbox = actors.get_player_hitbox(game)
    for enemy in game.enemies[:]:
        if enemy["rect"].colliderect(player_hitbox):
            # 적과 몸으로 부딪히면 적은 사라지고 플레이어만 피해를 받습니다.
            game.enemies.remove(enemy)
            damage_player(game, enemy["damage"])


# 보스 몸통이 플레이어와 직접 부딪혔는지 검사합니다.
# 보스는 사라지지 않으므로 접촉 쿨타임을 사용해서 피해가 일정 간격으로만 들어가게 합니다.
def check_boss_contact_collisions(game):
    if game.boss is None:
        return

    stage = game.current_stage()
    boss_rect = game.boss["rect"]
    cooldown = stage.get("boss_contact_cooldown", 0.85)

    if game.player and boss_rect.colliderect(actors.get_player_hitbox(game)):
        if game.boss.get("contactTimer", 0) <= 0:
            # 보스는 계속 남아 있으므로 접촉 피해가 매 프레임 들어가지 않도록 쿨타임을 둡니다.
            damage_player(game, stage.get("boss_contact_damage", 28 + game.stage_index * 8))
            game.boss["contactTimer"] = cooldown


# 몸빵 방패선이 켜져 있으면 적 배와 적 탄환을 먼저 막습니다.
def check_guard_collisions(game):
    guard_rect = getattr(game, "tanker_guard_rect", None)
    if guard_rect is None or getattr(game, "tanker_guard_timer", 0) <= 0:
        return

    for enemy in game.enemies[:]:
        if guard_rect.colliderect(enemy["rect"]):
            game.enemies.remove(enemy)

    for projectile in game.enemy_projectiles[:]:
        rect = get_circle_rect(projectile["x"], projectile["y"], projectile["radius"])
        if guard_rect.colliderect(rect):
            game.enemy_projectiles.remove(projectile)


# 적 탄환이 플레이어와 닿았는지 검사합니다.
# 탄환도 작은 히트박스에 닿았을 때만 피해를 줍니다.
def check_player_projectile_collisions(game):
    player_hitbox = actors.get_player_hitbox(game)
    for projectile in game.enemy_projectiles[:]:
        rect = get_circle_rect(projectile["x"], projectile["y"], projectile["radius"])
        if player_hitbox.colliderect(rect):
            # 플레이어에게 닿은 적 탄환은 한 번 피해를 주고 사라집니다.
            game.enemy_projectiles.remove(projectile)
            damage_player(game, projectile["damage"])


# 원형 탄환을 충돌 판정용 사각형으로 바꾸는 편의 함수입니다.
# 실제 계산은 projectiles.py의 같은 기능을 재사용합니다.
def get_circle_rect(x, y, radius):
    return projectiles.get_circle_rect(x, y, radius)


# 보스에게 피해를 줍니다.
# 보호막이 있으면 보호막부터 깎고, 남은 피해량만 체력에 적용합니다.
def damage_boss(game, amount):
    if game.boss is None:
        return

    remain = amount
    if game.boss["shield"] > 0:
        # 보호막이 있으면 체력보다 보호막을 먼저 깎습니다.
        shield_damage = min(game.boss["shield"], remain)
        game.boss["shield"] -= shield_damage
        remain -= shield_damage
        if game.boss["shield"] <= 0:
            game.boss["restoreTimer"] = 0

    if remain > 0:
        # 보호막을 다 깎고 남은 피해량만 실제 체력에 들어갑니다.
        game.boss["hp"] = max(0, game.boss["hp"] - remain)


# 플레이어에게 피해를 줍니다.
# 필살기 무적 시간이 남아 있으면 피해를 무시합니다.
def damage_player(game, amount):
    if getattr(game, "ultimate_invincible_timer", 0) > 0:
        # 무적 시간에는 맞아도 체력이 줄지 않습니다.
        return

    # 피해 적용 전 체력을 기억해 두면 실제로 얼마나 깎였는지 계산할 수 있습니다.
    before_hp = game.player["hp"]
    # max(0, ...)을 쓰면 체력이 음수로 내려가지 않습니다.
    # 필생즉사 활성 중에는 받는 피해를 50%로 줄입니다.
    if getattr(game, "last_stand_damage_active", False):
        amount = amount * skills.LAST_STAND_DAMAGE_REDUCTION
    amount = amount * getattr(game, "augment_allied_damage_taken_multiplier", 1.0)
    game.player["hp"] = max(0, game.player["hp"] - amount)
    # 실제 피해량은 이전 체력과 이후 체력의 차이입니다.
    actual_damage = before_hp - game.player["hp"]
    # 결과 화면에 보여줄 피격 횟수와 받은 피해량을 기록합니다.
    results.record_player_hit(game, actual_damage)
    assets.play_stage_sound(game, "hit", 0.65)
