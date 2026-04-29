#!/bin/zsh
cd "$(dirname "$0")"

if [ ! -x "venv/bin/python" ]; then
  echo "venv/bin/python을 찾을 수 없습니다."
  echo "먼저 가상환경을 만들고 pygame을 설치하세요:"
  echo "  python3 -m venv venv"
  echo "  venv/bin/pip install -r requirements.txt"
  read -k "?아무 키나 누르면 닫습니다..."
  exit 1
fi

echo "PyShooting 실행 중..."
echo "로그 파일: $(pwd)/last_run.log"

venv/bin/python main.py > last_run.log 2>&1
status=$?

if [ "$status" -ne 0 ]; then
  echo ""
  echo "게임 실행 중 오류가 발생했습니다. 종료 코드: $status"
  echo "아래 로그를 확인하세요:"
  tail -40 last_run.log
  read -k "?아무 키나 누르면 닫습니다..."
fi
