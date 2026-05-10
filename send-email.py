import re
import logging
import os
import requests
from datetime import date, datetime
from zoneinfo import ZoneInfo

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

WEBHOOK_URL_ENV = "DISCORD_WEBHOOK"
NEIS_KEY_ENV = "NEIS_API_KEY"

OFFICE_CODE = "B10"
<<<<<<< HEAD
SCHOOL_CODE = "7010663"
=======
SCHOOL_CODE = "710965"  # 동양고등학교
>>>>>>> 169e97f (change cron time to 5:50 KST)
GRADE = "1"
CLASS_NM = "2"

KST = ZoneInfo("Asia/Seoul")

# 쉬는 날 키워드 - 추가하고 싶으면 여기에 넣으면 됨
HOLIDAY_KEYWORDS = [
    "휴업일",
    "재량휴업일",
    "방학",
    "수련활동"
    "수학여행"
]

TIMETABLE: dict[int, list[str]] = {
    0: ["공영짝(영어교실)", "미술", "한국사", "공수", "통과C", "공국", "통사D", "방과후영어"],
    1: ["통사B", "한국사", "체육", "정보A", "미술", "미술", "공국", "방과후수학"],
    2: ["과탐", "공영교과서(1-2)", "통과B", "공수"],
    3: ["한국사", "체육", "통사A", "공국", "통과A", "공수", "정보A", "방과후영어"],
    4: ["정보B", "공국", "진로", "통사C", "공수", "통과D", "공영홀(1-1)", "방과후수학"],
}

DAY_COLORS = {
    0: 0x3498DB,  # 월 - 파랑
    1: 0xE74C3C,  # 화 - 빨강
    2: 0x2ECC71,  # 수 - 초록
    3: 0xE67E22,  # 목 - 주황
    4: 0x9B59B6,  # 금 - 보라
}


def get_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise EnvironmentError(f"환경변수 {key} 가 설정되지 않았습니다.")
    return val


def is_neis_empty(data: dict, key: str) -> bool:
    """NEIS INFO-200 (데이터 없음) 응답 확인"""
    return "RESULT" in data and data["RESULT"].get("CODE") == "INFO-200" or key not in data


def is_holiday(session: requests.Session, key: str, today: date) -> bool:
    url = "https://open.neis.go.kr/hub/SchoolSchedule"
    params = {
        "KEY": key, "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "AA_FROM_YMD": today.strftime("%Y%m%d"),
        "AA_TO_YMD": today.strftime("%Y%m%d"),
    }
    try:
        res = session.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        if is_neis_empty(data, "SchoolSchedule"):
            return False
        rows = data["SchoolSchedule"][1].get("row", [])
        for row in rows:
            event = row.get("EVENT_NM", "")
            if any(keyword in event for keyword in HOLIDAY_KEYWORDS):
                log.info(f"쉬는 날 감지: {event}, 전송 생략")
                return True
        return False
    except Exception as e:
        log.warning(f"학사일정 조회 실패, 그냥 전송: {e}")
        return False


def fetch_meal(session: requests.Session, key: str, today: date, meal_code: str) -> str | None:
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": key, "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "MLSV_YMD": today.strftime("%Y%m%d"),
        "MMEAL_SC_CODE": meal_code,
    }
    try:
        res = session.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        if is_neis_empty(data, "mealServiceDietInfo"):
            return None
        raw = data["mealServiceDietInfo"][1]["row"][0]["DDISH_NM"]
        cleaned = re.sub(r'\(\d+(\.\d+)*\)', '', raw)
        meals = cleaned.replace("<br/>", "\n")
        return "\n".join(line.strip() for line in meals.splitlines() if line.strip())
    except Exception as e:
        log.warning(f"급식 조회 실패 (code={meal_code}): {e}")
        return None


def get_meals(session: requests.Session, key: str, today: date) -> list[dict]:
    fields = []

    lunch = fetch_meal(session, key, today, "2")
    fields.append({
        "name": "# 중식",
        "value": (lunch or "⚠️ 중식 정보 없음")[:1024],
        "inline": False,
    })

    if today.weekday() != 2:
        dinner = fetch_meal(session, key, today, "3")
        if dinner:
            fields.append({
                "name": "# 석식",
                "value": dinner[:1024],
                "inline": False,
            })

    return fields


def get_timetable_api(session: requests.Session, key: str, today: date) -> list[str] | None:
    url = "https://open.neis.go.kr/hub/hisTimetable"
    params = {
        "KEY": key, "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "AY": today.year,
        "GRADE": GRADE,
        "CLASS_NM": CLASS_NM,
        "TI_FROM_YMD": today.strftime("%Y%m%d"),
        "TI_TO_YMD": today.strftime("%Y%m%d"),
    }
    try:
        res = session.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        if is_neis_empty(data, "hisTimetable"):
            return None
        rows = data["hisTimetable"][1].get("row", [])
        if not rows:
            return None
        return [r["ITRT_CNTNT"] for r in sorted(rows, key=lambda x: x["PERIO"])]
    except Exception as e:
        log.warning(f"시간표 API 실패, 로컬로 대체: {e}")
        return None


def build_embed(today: date, subjects: list[str], source: str, meal_fields: list[dict]) -> dict:
    day_names = ["월", "화", "수", "목", "금"]
    day = day_names[today.weekday()]

    timetable_value = "\n".join(f"`{i+1}교시` {s}" for i, s in enumerate(subjects))

    fields = [
        {
            "name": f"# 시간표 ({source})",
            "value": timetable_value[:1024],
            "inline": False,
        },
        *meal_fields,
    ]

    return {
        "title": f"{today.strftime('%Y-%m-%d')} {day}요일 좋은 아침!",
        "color": DAY_COLORS.get(today.weekday(), 0x95A5A6),
        "fields": fields,
        "footer": {"text": "동양고등학교 1학년 2반"},
    }


def send_discord(session: requests.Session, webhook_url: str, embed: dict) -> None:
    try:
        res = session.post(webhook_url, json={"content": "@everyone", "embeds": [embed]}, timeout=10)
        res.raise_for_status()
        log.info("디스코드 전송 성공")
    except Exception as e:
        log.error(f"디스코드 전송 실패: {e}")
        try:
            session.post(webhook_url, json={"content": f"⚠️ 오류 발생: {e}"}, timeout=10)
        except Exception:
            pass


def main() -> None:
    today = datetime.now(KST).date()

    if today.weekday() >= 5:
        log.info("주말이므로 전송 생략")
        return

    try:
        webhook_url = get_env(WEBHOOK_URL_ENV)
        neis_key = get_env(NEIS_KEY_ENV)
    except EnvironmentError as e:
        log.error(e)
        return

    with requests.Session() as session:
        if is_holiday(session, neis_key, today):
            return

        subjects = get_timetable_api(session, neis_key, today)
        source = "NEIS"
        if not subjects:
            subjects = TIMETABLE.get(today.weekday(), [])
            source = "저장됨"

        meal_fields = get_meals(session, neis_key, today)
        embed = build_embed(today, subjects, source, meal_fields)
        send_discord(session, webhook_url, embed)


main()
