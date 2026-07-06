# -*- coding: utf-8 -*-
"""오케스트레이터: 데이터 수집 -> 대시보드 생성. 스케줄러가 이 파일을 실행한다."""
import update
import build

if __name__ == "__main__":
    update.main()
    build.build()
