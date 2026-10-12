#!/bin/bash
cd "$(dirname "$0")"
echo "KCFM 기업 현금흐름 진단을 시작합니다..."
python3 -m pip install -r requirements.txt --quiet
python3 -m streamlit run app.py
