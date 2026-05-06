# PyShooting

pygame으로 만든 거북선 전쟁 2D 슈팅게임입니다. 플레이어는 거북선을 조종하고, 위에서 내려오는 적 함선을 대포로 격침합니다.

## 실행

```bash
source venv/bin/activate
python main.py
```

가상환경을 새로 만들 때는:

```bash
pip install -r requirements.txt
python main.py
```

기본 실행은 전체화면이 아니라 최대화된 창입니다. 작은 창으로 테스트하려면:

```bash
python main.py --windowed
```

## 조작

- 이동: `WASD`, 방향키, 한글 입력 상태의 같은 물리 키
- 발사: `Space` 또는 마우스 왼쪽 버튼
- 스킬: `Q/ㅂ` 학익진, `Z/ㅋ` 몸빵, `X/ㅌ` 치유
- 일시정지: `P`
- 뒤로 가기: `Esc`

`Space`는 전투 중 발사 전용입니다. 메뉴, 스테이지 선택, 스토리, 결과 화면에서는 자동 선택되지 않습니다.

## 모드

캠페인 모드는 1~5단계가 순서대로 열리는 이순신 시뮬레이션입니다. 진행도는 `campaign_progress.json`에 저장되어 게임을 다시 켜도 이어서 할 수 있습니다.

점수 경쟁 모드는 한 판 안에서 경험치를 모아 증강을 고르는 도전 모드입니다. 증강은 영구 저장되지 않고 현재 판에서만 유지됩니다.

스토리 화면에는 난중일기/해전 기록 문장만 보여줍니다. 전투 중 왼쪽 세로 일기지 이미지는 왼쪽 영역을 꽉 채워 현재 출전 기록 요약을 표시합니다.

## 캠페인 흐름

1단계를 처음 시작하면 `4월 13일`, `4월 14일`, `4월 15일` 난중일기 도입부를 먼저 봅니다. 이후 `1-1 사천포해전`과 `1-2 당포해전` 두 전투로 이어집니다. 사천포 전투 전에 기본 능력 하나를 고르고, 사천포 보스를 격파하면 결과 화면 없이 당포 브리핑으로 넘어갑니다. 당포까지 클리어하면 2단계가 해금됩니다.

기본 능력/증강/생즉사 사즉생 선택 화면은 방향키 또는 WASD로 이동하고, Enter로 선택할 수 있습니다. 숫자키와 마우스 클릭도 그대로 사용할 수 있습니다.

2단계부터 캠페인에서는 학익진 전술을 확정으로 얻습니다. 3단계는 강한 샛바람과 높은 파도, 4단계는 칠천량해전 이후 체력 절반 상태와 초반 30초 고립 전투, 생즉사 사즉생 선택 이벤트를 핵심 압박으로 둡니다. 5단계는 어두운 새벽 바다와 자폭선을 핵심 압박으로 둡니다.

## 코드 구조

- `main.py`: pygame 시작, 최대화 창, 메인 루프, 전투 업데이트 순서
- `input.py`: 키보드/마우스 입력과 화면 상태별 조작
- `campaign.py`: 스테이지 잠금/해금과 저장 파일
- `story.py`: 난중일기, 브리핑, 스토리 페이지
- `stages.py`: 5단계 공통 정보와 1단계 내부 전투 phase 정보
- `enemies.py`: 일반 적 체력, 속도, 등장 간격, 자폭선 설정
- `bosses.py`: 미니보스 체력, 보호막, 탄막 패턴
- `actors.py`: 플레이어, 일반 적, 보스 생성과 캠페인 전투 흐름
- `combat.py`: 발사, 충돌, 피해, 보스 처치 처리
- `projectiles.py`: 플레이어/적/보스 탄환 이동
- `augments.py`: 경험치, 레벨업, 증강, 기본 능력 선택
- `skills.py`: 학익진, 몸빵, 치유, 생즉사 사즉생
- `waves.py`: 파도 방향, 파도 이동 보정, 순풍/역풍 속도 보정
- `weather.py`: 태풍, 비, 번개
- `obstacles.py`: 랜덤 지형지물
- `results.py`: 결과 화면용 점수, 피격, 스킬 사용량 기록
- `assets.py`: 이미지, 효과음, BGM 로딩과 재생
- `skins.py`: 이미지/효과음 파일 이름 규칙, 플레이어 크기
- `layout.py`: 중앙 플레이 영역, 좌우 HUD 영역, 버튼 위치
- `ui.py`: 메뉴, 스테이지 선택, 스토리, 증강, 결과, HUD
- `render.py`: 배경, 탄환, 적, 보스, 날씨, 파도 그리기

더 자세한 개발 구조와 확장 방법은 `GAME_STRUCTURE.txt`에 정리되어 있습니다.

## 에셋 슬롯

이미지 폴더는 `assets/images/`, 오디오 폴더는 `assets/audio/`입니다. 파일이 없으면 기본 도형이나 기본 배경으로 대체됩니다.

공통 이미지:

- `main_menu.png`, `splash.png`, `game_background.png`
- `menu_start_button.png`: 메인 메뉴의 게임 시작 버튼
- `player.png`, `bullet.png`, `enemy.png`, `mini_boss.png`
- `stage_select_background.png`, `stage_select_panel.png`
- `story_background.png`, `story_paper.png`, `story_intro.png`
- `story_diary_horizontal.png`: 스토리 화면의 가로 일기지
- `story_summary_vertical.png`: 전투 중 왼쪽 요약 패널의 세로 일기지
- `stage_result_background.png`, `stage_result_panel.png`
- `obstacle_rock1.png`, `obstacle_rock2.png`
- `weather_typhoon1.png`, `weather_typhoon2.png`, `weather_rain1.png`, `weather_lightning1.png`

스테이지별 이미지:

- `stageN.png`, `enemy_stageN.png`, `bullet_stageN.png`, `projectile_stageN.png`
- `mini_boss_stageN.png` 또는 `boss_stageN.png`
- `stage_select_stageN.png`
- `story_stageN.png`, `story_stageN_pageM.png`
- `story_stageN_phaseP_pageM.png`
- `story_intro_pageM.png`
- `stage_result_stageN.png`

오디오:

- `bgm.mp3`: 전투 BGM
- `stage_select_bgm.mp3`: 스테이지 선택 BGM
- `story_bgm.mp3`, `story_intro_bgm.mp3`, `story_intro_pageM_bgm.mp3`
- `story_stageN_bgm.mp3`, `story_stageN_pageM_bgm.mp3`
- `story_stageN_phaseP_bgm.mp3`, `story_stageN_phaseP_pageM_bgm.mp3`
- `shoot.mp3`, `hit.mp3`, `destroy.mp3`, `weather_lightning.mp3`
- `shoot_stageN.mp3`, `hit_stageN.mp3`, `destroy_stageN.mp3`, `boss_stageN.mp3`

`N`은 스테이지 번호, `P`는 내부 전투 번호, `M`은 스토리 페이지 번호입니다.
