import time
import player_service
import match_service


def main():
    while True:
        print("\n" + "=" * 50)
        print("⚡ Riot Data Pipeline Manager (Production Ver.)")
        print("=" * 50)
        print("1. [초기화] 텍스트 파일(challenger_player.txt) 유저 DB 적재")
        print("2. [1단계] DB 유저 기반 Match ID 대기열 채우기 (멀티스레드)")
        print("3. [2단계] 매치 상세 수집 및 DB 저장 (유저 자동추가 + 멀티스레드)")
        print("4. [자동화] 3번 작업을 무한 루프로 실행 (서버 켜두기용)")
        print("5. 종료")

        choice = input("\n원하는 작업 번호를 입력하세요: ")

        if choice == '1':
            player_service.run_initial_player_load("challenger_player.txt")

        elif choice == '2':
            match_service.collect_match_ids_fast(max_workers=10)

        elif choice == '3':
            try_count = input("한 번에 몇 개의 매치를 처리할까요? (기본 1000): ")
            limit = int(try_count) if try_count.isdigit() else 1000
            match_service.process_matches_fast(limit=limit, max_workers=20)

        elif choice == '4':
            print("\n🚨 [무한 수집 모드] 시작합니다. (중단하려면 Ctrl+C)")
            try:
                while True:
                    match_service.process_matches_fast(limit=1000, max_workers=20)
                    time.sleep(2)  # DB 및 CPU 휴식
            except KeyboardInterrupt:
                print("\n🛑 무한 수집 모드를 안전하게 중단했습니다.")

        elif choice == '5':
            print("프로그램을 종료합니다.")
            break

        else:
            print("잘못된 입력입니다. 1~5 사이의 숫자를 입력해 주세요.")


if __name__ == "__main__":
    main()