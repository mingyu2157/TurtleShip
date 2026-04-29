# PyShooting

사용자 기본 코드의 `initGame()` / `runGame()` 구조에 맞춰 만든 pygame 2D 슈팅게임입니다. 화면 아래의 플레이어를 움직이며 위에서 내려오는 적을 피하거나 쏴서 격파합니다.

## 실행

```bash
pip install -r requirements.txt
python3 main.py
```

프로젝트의 가상환경을 사용할 때는:

```bash
source venv/bin/activate
python main.py
```

macOS에서는 `run_game.command`를 더블클릭하거나 터미널에서 실행해도 됩니다.

기본 실행은 전체화면이 아니라 최대화된 창입니다. 기본 코드 크기인 `480 x 640` 창으로 테스트하려면:

```bash
python3 main.py --windowed
```

## 조작

- 이동: `WASD` / 한글 입력 상태의 같은 물리 키 / 방향키
- 발사: `Space` 또는 마우스 왼쪽 버튼 연타
- 일시정지: `P`
- 메뉴/일시정지: `Esc`

## 스테이지

총 5스테이지입니다. 각 스테이지마다 적선 45척을 격침하면 미니보스가 등장합니다. 적선은 위, 왼쪽, 오른쪽에서 나타나며, 화면 밖으로 지나가도 체력은 감소하지 않습니다.

- 1단계: 안개 해협, 공격 없이 적선이 많이 몰려오는 물량공세
- 2단계: 소용돌이 해역, 좌우 확산 탄막 미니보스
- 3단계: 화공선 돌파, 화염 분열탄 미니보스
- 4단계: 검은 함대, 추적 저격 미니보스
- 5단계: 대장선 결전, 방어막 재생과 폭풍 탄막 최종 보스

## 코드 구조

- `main.py`: pygame 시작, 최대화 창 생성, 메인 게임 루프
- `settings.py`: 화면 크기, FPS, 색상, 경로, 이동 키 설정
- `assets.py`: 이미지/효과음 로딩, BGM, 스테이지별 사운드 재생
- `input.py`: 키보드/마우스 입력 처리
- `actors.py`: 플레이어, 일반 적, 미니보스 생성과 이동
- `projectiles.py`: 플레이어 탄환, 적 탄환, 보스 탄환, 분열탄 이동
- `combat.py`: 충돌, 피해 처리, 플레이어 발사 호출
- `allies.py`: 동료 종류, 동료 이동/자동 발사, 동료 드롭 준비
- `items.py`: 탄환 강화, 연사, 필살기 충전 아이템 준비
- `skills.py`: 필살기 입력, 폭탄/무적 효과 준비
- `rewards.py`: 적 격침 보상 훅, 동료/아이템/필살기 충전 연결
- `ui.py`: 폰트, 메인 메뉴, HUD, 게임오버/클리어 화면
- `render.py`: 배경, 플레이어, 적, 보스, 탄환 그리기
- `layout.py`: 화면 배율, 플레이 영역, 버튼 위치 계산
- `stages.py`: 스테이지 순서와 공통 색상, 보스 등장 조건
- `enemies.py`: 스테이지별 일반 적 이름, 체력, 속도, 등장 간격
- `bosses.py`: 스테이지별 미니보스 이름, 체력, 보호막, 공격 패턴
- `skins.py`: 플레이어 크기, 배경 플레이 영역, 이미지/효과음 파일 이름 규칙

스테이지별 일반 적 이미지와 효과음은 모두 다르게 넣을 수 있습니다. 예를 들어 `enemy_stage1.png`, `enemy_stage2.png`처럼 넣으면 각 스테이지에서 자동으로 해당 파일을 우선 사용합니다.

동료, 아이템, 필살기 기능은 확장하기 쉽게 모듈과 파일 이름만 먼저 잡아두었습니다. 현재는 `ALLY_DROP_ENABLED`, `ITEM_DROP_ENABLED`, `ULTIMATE_ENABLED`가 꺼져 있어서 기존 플레이에는 영향을 주지 않습니다.

## 교체 가능한 에셋

아래 파일을 넣으면 게임이 자동으로 사용합니다. 없는 파일은 기본 도형/배경으로 대체됩니다.

### 공통 이미지

`assets/images/`

- `splash.png`: 실행 직후 화면
- `main_menu.png`: 메인 화면 배경
- `game_background.png`: 모든 스테이지에서 기본으로 쓰는 게임 배경
- `player.png`: 플레이어
- `bullet.png`: 공통 플레이어 총탄
- `enemy.png`: 공통 일반 적 이미지
- `mini_boss.png`: 공통 미니보스 이미지
- `boss_room.png`: 미니보스 등장 시 배경
- `ally_support_ship.png`, `ally_guard_ship.png`, `ally_rapid_ship.png`: 동료 배
- `ally_support_bullet.png`, `ally_guard_bullet.png`, `ally_rapid_bullet.png`: 동료 탄환
- `item_bullet_upgrade.png`: 탄환 강화 아이템
- `item_rapid_fire.png`: 연사 아이템
- `item_ultimate_charge.png`: 필살기 충전 아이템
- `ultimate_flash.png`: 필살기 연출 이미지

### 스테이지별 이미지

`N`은 1부터 5까지의 스테이지 번호입니다.

- `stageN.png`: 스테이지 배경
- `enemy_stageN.png`: 스테이지별 일반 적선
- `mini_boss_stageN.png` 또는 `boss_stageN.png`: 스테이지별 미니보스
- `bullet_stageN.png`: 스테이지별 플레이어 총탄
- `projectile_stageN.png`: 스테이지별 적/미니보스 탄

PNG, JPG, JPEG 파일을 사용할 수 있습니다. 위 이름을 우선으로 찾습니다.

### 오디오

`assets/audio/`

- `bgm.mp3`: 배경음악
- `shoot.mp3`, `hit.mp3`: 공통 효과음
- `shoot_stageN.mp3`: 스테이지별 발사음
- `hit_stageN.mp3`: 스테이지별 피격음
- `boss_stageN.mp3`: 스테이지별 미니보스 등장음
- `destroy_stageN.mp3`: 스테이지별 적 격침음
- `ally_stageN.mp3`: 스테이지별 동료 획득음
- `item_stageN.mp3`: 스테이지별 아이템 획득음
- `ultimate_stageN.mp3`: 스테이지별 필살기 효과음

MP3가 환경에 따라 재생되지 않으면 같은 이름의 `.ogg` 또는 `.wav`로 넣어도 됩니다.
