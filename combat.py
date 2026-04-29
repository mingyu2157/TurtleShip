# combat.py
# 역할:
#   발사 명령, 충돌 판정, 체력 감소처럼 "전투 결과"를 처리합니다.
#   탄환의 실제 이동과 생성 데이터는 projectiles.py에 있고,
#   적을 잡았을 때 보상 처리는 rewards.py에 연결해 둡니다.
#
# 초보자 포인트:
#   게임에서는 보통 "무엇이 닿았는지"를 먼저 찾고,
#   닿았다면 체력 감소, 점수 증가, 삭제 같은 결과를 처리합니다.
import actors
import assets
import projectiles
import rewards


# 플레이어가 발사 버튼을 눌렀을 때 호출됩니다.
# shoot_cooldown이 남아 있으면 아직 다음 탄환을 쏠 수 없으므로 바로 return 합니다.
def shoot_player_bullet(game):
    if not game.player or game.shoot_cooldown > 0:
        return

    stage = game.current_stage()
    rect = game.player["rect"]
    speed = -620
    level = getattr(game, "bullet_level", 0)
    damage = 18 + level * 4
    color = stage["bullet_color"]
    radius = 7 + min(3, level)

    projectiles.make_player_bullet(game, rect.centerx, rect.top - 8, 0, speed, damage, radius, color)

    game.shoot_cooldown = 0.12 if getattr(game, "rapid_fire_timer", 0) > 0 else 0.28
    assets.play_stage_sound(game, "shoot", 0.5)


# 예전 구조와 호환하기 위한 함수입니다.
# 실제 탄환 이동은 projectiles.update_player_bullets()가 처리합니다.
def update_bullets(game, dt):
    projectiles.update_player_bullets(game, dt)


# 한 프레임 동안 필요한 모든 충돌 검사를 호출합니다.
# 플레이어 탄환 vs 적, 플레이어 탄환 vs 보스, 플레이어 vs 적, 플레이어 vs 적 탄환 순서입니다.
def check_collisions(game):
    check_bullet_enemy_collisions(game)
    check_bullet_boss_collisions(game)
    check_player_enemy_collisions(game)
    check_player_projectile_collisions(game)


# 플레이어 탄환이 일반 적과 닿았는지 검사합니다.
# 적 체력이 0 이하가 되면 적을 제거하고 점수/격침 수/보상 처리를 합니다.
def check_bullet_enemy_collisions(game):
    for bullet in game.bullets[:]:
        bullet_rect = get_circle_rect(bullet["x"], bullet["y"], bullet["radius"])
        hit_enemy = None

        for enemy in game.enemies:
            if enemy["rect"].colliderect(bullet_rect):
                hit_enemy = enemy
                break

        if hit_enemy is None:
            continue

        if bullet in game.bullets:
            game.bullets.remove(bullet)

        hit_enemy["hp"] -= bullet["damage"]
        if hit_enemy["hp"] <= 0:
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

        if game.boss is not None and game.boss["hp"] <= 0:
            game.score += 1200 + game.stage_index * 400
            actors.next_stage(game)
            return


# 플레이어 배가 적 배와 직접 충돌했는지 검사합니다.
# 충돌하면 적은 사라지고 플레이어 체력이 감소합니다.
def check_player_enemy_collisions(game):
    for enemy in game.enemies[:]:
        if enemy["rect"].colliderect(game.player["rect"]):
            game.enemies.remove(enemy)
            damage_player(game, enemy["damage"])


# 적 탄환이 플레이어와 닿았는지 검사합니다.
# 닿은 탄환은 제거하고 플레이어에게 피해를 줍니다.
def check_player_projectile_collisions(game):
    for projectile in game.enemy_projectiles[:]:
        rect = get_circle_rect(projectile["x"], projectile["y"], projectile["radius"])
        if game.player["rect"].colliderect(rect):
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
        shield_damage = min(game.boss["shield"], remain)
        game.boss["shield"] -= shield_damage
        remain -= shield_damage
        if game.boss["shield"] <= 0:
            game.boss["restoreTimer"] = 0

    if remain > 0:
        game.boss["hp"] = max(0, game.boss["hp"] - remain)


# 플레이어에게 피해를 줍니다.
# 필살기 무적 시간이 남아 있으면 피해를 무시합니다.
def damage_player(game, amount):
    if getattr(game, "ultimate_invincible_timer", 0) > 0:
        return

    game.player["hp"] = max(0, game.player["hp"] - amount)
    assets.play_stage_sound(game, "hit", 0.65)
