# story.py
# 역할:
#   게임의 역사 흐름, 난중일기 문구, 스테이지 브리핑 문장을 모아둡니다.
#   전투 수치와 분리해두면 나중에 스토리 문장만 고치고 싶을 때 이 파일만 보면 됩니다.
#
# 초보자 포인트:
#   아래 INTRO_STORY_PAGES와 STAGE_STORIES는 "딕셔너리" 데이터입니다.
#   pygame 화면에 직접 그리는 코드는 ui.py가 담당하고,
#   이 파일은 어떤 제목과 문장을 보여줄지만 알려주는 안내서 역할을 합니다.
#
# 공부 순서:
#   INTRO_STORY_PAGES는 게임 시작 도입부입니다.
#   STAGE_STORIES는 각 스테이지 전 브리핑입니다.
#   한 스테이지에 여러 편의 난중일기를 넣고 싶으면 "pages" 리스트를 추가하면 됩니다.
#   get_current_story()는 현재 화면에 보여줄 스토리 데이터를 고르는 함수입니다.


# 게임을 처음 시작했을 때 보여줄 난중일기 도입부입니다.
# 사용자가 요청한 대로 화면에 보일 문구는 일기 문장만 담습니다.
INTRO_STORY_PAGES = [
    {
        "kicker": "난중일기",
        "title": "4월 13일",
        "date": "4월 13일 맑다",
        "quote": "동헌에 나가 공무를 본 뒤에 활 열다섯 순을 쏘았다.",
        "lines": [],
        "next": "4월 14일 기록",
        "prompt": "다음",
    },
    {
        "kicker": "난중일기",
        "title": "4월 14일",
        "date": "4월 14일 맑다",
        "quote": "동헌에 나가 공무를 본 뒤에 활 열 순을 쏘았다.",
        "lines": [],
        "next": "4월 15일 기록",
        "prompt": "다음",
    },
    {
        "kicker": "난중일기",
        "title": "4월 15일",
        "date": "4월 15일 맑다",
        "quote": "맑다.",
        "lines": [],
        "next": "사천포 기록",
        "prompt": "다음",
    },
]

# 1단계는 사천포해전과 당포해전으로 내부 전투가 2번 이어집니다.
# stage_phase가 0이면 사천포, 1이면 당포 브리핑을 보여줍니다.
STAGE1_PHASE_STORIES = [
    {
        "kicker": "1-1단계",
        "title": "사천포해전",
        "date": "1592년 5월 29일",
        "quote": "왜적들은 지금 사천선창에 있다.",
        "lines": [
            "바로 거기로 가보았더니 왜놈들은 벌써 뭍으로 올라가서 산 위에 진을 치고, 배는 그 산 아래에 줄지어 매어 놓고 항전하는 태세가 재빨리 튼튼해졌다.",
            "나는 장수들을 독려하여 일제히 달려 들며 화살을 비 퍼붓듯이 쏘고, 각종 총포들을 우레 같이 쏘아대니, 적들이 무서워서 물러났다.",
            "적선 열세 척을 불 태워버리고 물러나 머물렀다.",
        ],
        "next": "사천포 앞바다로 출전",
        "prompt": "출전",
    },
    {
        "kicker": "1-2단계",
        "title": "당포해전",
        "date": "1592년 6월 2일",
        "quote": "적선 중에 큰 배 한 척은 우리나라 판옥선만 하다.",
        "lines": [
            "아침에 떠나 곧장 당포 선창에 이르니, 적선 스무여 척이 줄지어 머물러 있다.",
            "배 위에 다락이 있는데, 높이가 두 길은 되겠고, 그 누각 위에는 왜장이 떡 버티고 우뚝 앉아 끄덕도 아니 하였다.",
            "모조리 섬멸하고 한 놈도 남겨두지 않았다.",
        ],
        "next": "당포 앞바다로 출전",
        "prompt": "출전",
    },
]


# 각 스테이지에 들어가기 전에 보여줄 역사 브리핑입니다.
# stage_index는 0부터 시작하므로 리스트의 첫 번째 값이 1단계입니다.
#
# 나중에 한 스테이지에 스토리 1편~9편을 넣고 싶을 때는 아래처럼 쓰면 됩니다.
# {
#     "pages": [
#         {"kicker": "난중일기 1편", "title": "...", "date": "...", "quote": "...", "lines": [...], "prompt": "다음"},
#         {"kicker": "난중일기 2편", "title": "...", "date": "...", "quote": "...", "lines": [...], "prompt": "출전"},
#     ]
# }
# pages가 없으면 지금처럼 스테이지 딕셔너리 1개를 1편으로 사용합니다.
STAGE_STORIES = [
    {
        "kicker": "1단계",
        "title": "사천포·당포해전",
        "date": "1592년 5월 29일 - 6월 2일",
        "quote": "적선 중에 큰 배 한 척은 우리나라 판옥선만 하다.",
        "lines": [
            "왜적들은 지금 사천선창에 있다.",
            "모조리 섬멸하고 한 놈도 남겨두지 않았다.",
        ],
        "next": "사천포 앞바다로 출전",
        "prompt": "출전",
    },
    {
        "kicker": "2단계",
        "title": "한산도해전",
        "date": "1592년 7월 8일",
        "quote": "한산도 바다 가운데로 유인하여 모조리 잡아버릴 계획을 세웠다.",
        "lines": [
            "대선 서른 여섯 척과 중선 스무 네 척, 소선 열세 척이 대열을 벌려서 정박하고 있었다.",
            "그때야 여러 장수들에게 명령하여 학익진을 펼쳐 일시에 진격하였다.",
            "그 형세가 마치 바람같고 우레같아, 적의 배를 불태우고 적을 사살하기를 일시에 다 해치워 버렸다.",
        ],
        "next": "한산도 앞바다로 출전",
        "prompt": "출전",
    },
    {
        "kicker": "3단계",
        "title": "부산포해전",
        "date": "1592년 9월 1일",
        "quote": "대개 오백 여 척이 선창 동쪽 산기슭의 언덕 아래 줄지어 대었다.",
        "lines": [
            "낮 여덟 시에 몰운대를 지날 무렵 샛바람이 갑자기 일고 파도가 크게 일어 간신히 배를 저어 화준구미에 이르렀다.",
            "우리 군사의 위세로써 만일 지금 공격하지 않고 군사를 돌이킨다면 반드시 적이 우리를 멸시하는 마음이 생길 것이다.",
            "여러 장수들은 한층 더 분개하여 죽음을 무릅쓰고 다투어 돌진하였다.",
        ],
        "next": "부산포로 진격",
        "prompt": "출전",
    },
    {
        "kicker": "4단계",
        "title": "명량해전",
        "date": "1597년 7월 18일 - 9월 16일",
        "quote": "반드시 죽고자 하면 살고 살려고만 하면 죽는다.",
        "pages": [
            {
                "kicker": "스토리",
                "title": "칠천량해전",
                "date": "1597년 7월 18일",
                "quote": "수군이 몰래 기습공격을 받아 수군이 대패했다.",
                "lines": [
                    "통제사 원균, 전라우수사 이억기, 충청수사 및 여러 장수와 많은 사람들이 해를 입었고, 수군이 대패했다.",
                    "듣자하니 통곡함을 참지 못했다.",
                    "내가 직접 연해안 지방으로 가서 보고 듣고난 뒤에 이를 결정하는 것이 어떻겠는가.",
                ],
                "next": "삼도수군통제사 재임명",
                "prompt": "다음",
            },
            {
                "kicker": "스토리",
                "title": "삼도수군통제사 재임명",
                "date": "1597년 8월 3일",
                "quote": "명령은 곧 삼도수군통제사의 임명이다.",
                "lines": [
                    "이른 아침에 선전관 양호가 뜻밖에 교유서를 가지고 왔다.",
                    "숙배를 한 뒤에 다만 받들어 받았다는 글월을 써서 봉하고, 곧 떠나 두치로 가는 길로 곧 바로 갔다.",
                ],
                "next": "명량해전 전날",
                "prompt": "다음",
            },
            {
                "kicker": "난중일기",
                "title": "명량해전 전날",
                "date": "1597년 9월 15일",
                "quote": "반드시 죽고자 하면 살고 살려고만 하면 죽는다.",
                "lines": [
                    "또 한 사람이 길목을 지키면, 천 사람이라도 두렵게 한다고 했음은 지금 우리를 두고 한 말이다.",
                    "너희 여러 장수들이 살려는 생각은 하지 마라.",
                    "이 날 밤 신인이 꿈에 나타나, 이렇게 하면 크게 이기고 이렇게 하면 지게 된다고 일러 주었다.",
                ],
                "next": "명량 울돌목으로 출전",
                "prompt": "출전",
            },
        ],
    },
    {
        "kicker": "5단계",
        "title": "노량해전",
        "date": "1598년 11월 19일",
        "quote": "오늘 진실로 죽음을 각오하오니, 하늘에 바라옵건대 반드시 이 적을 섬멸하게 하여 주소서.",
        "lines": [
            "노량해전의 난중일기 기록은 전하지 않습니다.",
            "오늘 진실로 죽음을 각오하오니, 하늘에 바라옵건대 반드시 이 적을 섬멸하게 하여 주소서.",
        ],
        "next": "노량의 마지막 바다로 출전",
        "prompt": "출전",
    },
]


# 도입부 스토리 페이지 목록을 돌려줍니다.
def get_intro_story_pages():
    return INTRO_STORY_PAGES


# 현재 game 상태에 맞는 스토리 페이지 목록을 돌려줍니다.
def get_story_pages_for_game(game):
    if getattr(game, "story_id", "intro") == "intro":
        return get_intro_story_pages()
    stage_index = max(0, min(getattr(game, "stage_index", 0), len(STAGE_STORIES) - 1))
    return get_stage_story_pages(stage_index, getattr(game, "stage_phase", 0))


# 스테이지 번호로 스토리 페이지 목록을 가져옵니다.
# pages가 있으면 그 목록을 쓰고, 없으면 기존 스테이지 딕셔너리 1개를 리스트처럼 감싸서 돌려줍니다.
def get_stage_story_pages(stage_index, phase=0):
    # stage_index가 범위를 벗어나도 게임이 멈추지 않도록 0~마지막 사이로 제한합니다.
    safe_index = max(0, min(stage_index, len(STAGE_STORIES) - 1))
    if safe_index == 0:
        safe_phase = max(0, min(int(phase), len(STAGE1_PHASE_STORIES) - 1))
        return [STAGE1_PHASE_STORIES[safe_phase]]

    stage_story = STAGE_STORIES[safe_index]

    # pages 키가 있고 비어 있지 않으면 여러 편 스토리 구조로 판단합니다.
    pages = stage_story.get("pages")
    if pages:
        return pages[:9]

    # pages가 없으면 현재 딕셔너리 전체를 1편짜리 스토리로 사용합니다.
    return [stage_story]


# 현재 스토리 페이지 번호를 안전한 범위로 가져옵니다.
# story_page_index는 0부터 시작하므로 0은 1편, 1은 2편입니다.
def get_current_story_page_index(game):
    page_count = len(get_story_pages_for_game(game))
    return max(0, min(getattr(game, "story_page_index", 0), page_count - 1))


# 현재 스테이지에 스토리 페이지가 몇 편 있는지 가져옵니다.
def get_story_page_count(game):
    return len(get_story_pages_for_game(game))


# 현재 보고 있는 스토리 페이지가 마지막 편인지 확인합니다.
def is_last_story_page(game):
    return get_current_story_page_index(game) >= get_story_page_count(game) - 1


# 스토리 화면에서 현재 보여줄 데이터를 가져옵니다.
# intro이면 INTRO_STORY_PAGES를, stage이면 현재 stage_index와 story_page_index에 맞는 페이지를 돌려줍니다.
def get_current_story(game):
    pages = get_story_pages_for_game(game)
    page_index = get_current_story_page_index(game)
    return pages[page_index]


# 전투 중 왼쪽 세로 일기지에 표시할 짧은 요약 문장을 만듭니다.
# 각 스토리 데이터에 summary 키를 넣으면 그 문장을 우선 사용하고,
# 없으면 현재 제목, 날짜, 인용문, 첫 번째 설명을 조합해서 자동 요약합니다.
def get_current_story_summary(game):
    current_story = get_current_story(game)
    if current_story.get("summary"):
        return current_story["summary"]

    parts = [
        current_story.get("title", ""),
        current_story.get("date", ""),
        current_story.get("quote", ""),
    ]
    lines = current_story.get("lines", [])
    if lines:
        parts.append(lines[0])

    return "\n".join(part for part in parts if part)


# 스토리 화면 하단의 진행 버튼 문구를 가져옵니다.
# 도입 화면에서는 다음 브리핑으로, 스테이지 화면에서는 실제 출전으로 이어집니다.
def get_story_prompt(game):
    current_story = get_current_story(game)
    if is_last_story_page(game):
        return current_story.get("prompt", "출전")

    return current_story.get("prompt", "다음")


# 스토리 패널 왼쪽 아래에 보여줄 다음 행동 문구입니다.
# 여러 편 스토리에서는 마지막 편 전까지 "다음 난중일기"로 보여주고, 마지막 편에서는 출전 문구를 보여줍니다.
def get_story_next_text(game):
    current_story = get_current_story(game)
    if is_last_story_page(game):
        return current_story.get("next", "출전")

    return current_story.get("next", "다음 난중일기")
