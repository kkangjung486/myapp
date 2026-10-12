@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo KCFM 기업 현금흐름 진단을 시작합니다...
echo (처음 실행 시 필요한 프로그램을 설치하느라 몇 분 걸릴 수 있습니다)
python -m pip install -r requirements.txt --quiet
python -m streamlit run app.py
pause
