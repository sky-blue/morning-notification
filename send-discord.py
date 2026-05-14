import re
import logging
import os
import requests
from datetime import date, datetime
from zoneinfo import ZoneInfo

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

NEIS_KEY_ENV = "NEIS_API_KEY"
OFFICE_CODE = "B10"
SCHOOL_CODE = "7010965"
KST = ZoneInfo("Asia/Seoul")

# 쉬는 날 키워드 - 추가하고 싶으면 여기에 넣으면 됨
HOLIDAY_KEYWORDS = [
    "휴업일",
    "휴일",
    "재량휴업일",
    "방학",
    "수련활동",
    "대체휴업일",
    "졸업식",
    "종업식",
    "체육대회",
    "개학식",
    "기말고사",
    "중간고사",
    "학력평가",
    "수능"
    "수학능력시험"
    "모의고사"
]

DAY_COLORS = {
    0: 0x3498DB,  # 월 - 파랑
    1: 0xE74C3C,  # 화 - 빨강
    2: 0x2ECC71,  # 수 - 초록
    3: 0xE67E22,  # 목 - 주황
    4: 0x9B59B6,  # 금 - 보라
}

CLASSES = {
    (1, 1): {
        "webhook_env": "DISCORD_WEBHOOK_1_1",
        "role_id": "1504064435193647105",
        "timetable": {
            0: ["공영", "한국", "통사1", "공수", "정보", "공국", "통과"],
            1: ["한국", "미술", "공국", "체육1", "과탐1", "통과", "통사1"],
            2: ["공국", "공영", "통과", "공수"],
            3: ["정보", "통사1", "미술", "미술", "진로1", "공수", "한국"],
            4: ["통사1", "정보", "통과", "공국", "공수", "체육1", "공영"],
        },
    },
    (1, 2): {
        "webhook_env": "DISCORD_WEBHOOK_1_2",
        "role_id": "1504064479586160670",
        "timetable": {
            0: ["공영", "미술", "한국", "공수", "통과", "공국", "통사1"],
            1: ["통사1", "한국", "체육1", "정보", "미술", "미술", "공국"],
            2: ["과탐1", "공영", "통과", "공수"],
            3: ["한국", "체육1", "통사1", "공국", "통과", "공수", "정보"],
            4: ["정보", "공국", "진로1", "통사1", "공수", "통과", "공영"],
        },
    },
    (1, 3): {
        "webhook_env": "DISCORD_WEBHOOK_1_3",
        "role_id": "1504064500448366704",
        "timetable": {
            0: ["공수", "과탐1", "체육1", "공국", "미술", "통사1", "공영"],
            1: ["통사1", "공영", "공국", "통과", "한국", "정보", "공수"],
            2: ["통과", "통사1", "공수", "정보"],
            3: ["공영", "공국", "공수", "체육1", "한국", "진로1", "통과"],
            4: ["한국", "공국", "정보", "통과", "통사1", "미술", "미술"],
        },
    },
    (1, 4): {
        "webhook_env": "DISCORD_WEBHOOK_1_4",
        "role_id": "1504064519587233853",
        "timetable": {
            0: ["공수", "음악", "과탐1", "통과", "한국", "통사1", "공영"],
            1: ["체육1", "공영", "정보", "통사1", "진로1", "공국", "공수"],
            2: ["통사1", "통과", "공수", "공국"],
            3: ["공영", "한국", "공수", "정보", "통과", "통사1", "공국"],
            4: ["체육1", "정보", "한국", "공국", "통과", "음악", "음악"],
        },
    },
    (1, 5): {
        "webhook_env": "DISCORD_WEBHOOK_1_5",
        "role_id": "1504064539497599006",
        "timetable": {
            0: ["통사1", "공수", "공영", "통과", "정보", "진로1", "체육1"],
            1: ["정보", "통사1", "음악", "음악", "공수", "공국", "통과"],
            2: ["공국", "한국", "체육1", "공영"],
            3: ["공국", "공영", "통과", "한국", "공수", "정보", "통사1"],
            4: ["공국", "음악", "공수", "과탐1", "통사1", "한국", "통과"],
        },
    },
    (1, 6): {
        "webhook_env": "DISCORD_WEBHOOK_1_6",
        "role_id": "1504064560355741776",
        "timetable": {
            0: ["통사1", "공수", "공영", "공국", "음악", "통과", "정보"],
            1: ["공국", "통사1", "진로1", "체육1", "공수", "한국", "과탐1"],
            2: ["통과", "통사1", "한국", "공영"],
            3: ["공국", "공영", "음악", "음악", "공수", "통과", "정보"],
            4: ["체육1", "통사1", "공수", "한국", "정보", "공국", "통과"],
        },
    },
}


def get_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise EnvironmentError(f"환경변수 {key} 가 설정되지 않았습니다.")
    return val


def is_neis_empty(data: dict, key: str) -> bool:
    if key not in data:
        return True
    if "RESULT" in data and data["RESULT"].get("CODE") == "INFO-200":
        return True
    return False


def get_schedule_events(session: requests.Session, key: str, today: date) -> list[str]:
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
            return []
        rows = data["SchoolSchedule"][1].get("row", [])
        return [row.get("EVENT_NM", "") for row in rows if row.get("EVENT_NM")]
    except Exception as e:
        log.warning(f"학사일정 조회 실패: {e}")
        return []


def is_holiday(events: list[str]) -> bool:
    for event in events:
        if any(keyword in event for keyword in HOLIDAY_KEYWORDS):
            log.info(f"쉬는 날 감지: {event}, 전송 생략")
            return True
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
        "value": (lunch or "중식 정보 없음")[:1024],
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


def get_timetable_api(session: requests.Session, key: str, today: date, grade: int, class_num: int) -> list[str] | None:
    url = "https://open.neis.go.kr/hub/hisTimetable"
    params = {
        "KEY": key, "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "AY": today.year,
        "GRADE": str(grade),
        "CLASS_NM": str(class_num),
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
        log.warning(f"{grade}학년 {class_num}반 시간표 API 실패, 로컬로 대체: {e}")
        return None


def build_embed(today: date, grade: int, class_num: int, subjects: list[str], source: str, meal_fields: list[dict], events: list[str]) -> dict:
    day_names = ["월", "화", "수", "목", "금"]
    day = day_names[today.weekday()]

    timetable_value = "\n".join(f"`{i+1}교시` {s}" for i, s in enumerate(subjects))
    description = f"학사일정: {', '.join(events)}" if events else ""

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
        "description": description,
        "color": DAY_COLORS.get(today.weekday(), 0x95A5A6),
        "fields": fields,
        "footer": {"text": f"동양고등학교 {grade}학년 {class_num}반"},
    }


def send_discord(session: requests.Session, webhook_url: str, embed: dict, role_id: str, grade: int, class_num: int) -> None:
    try:
        res = session.post(webhook_url, json={"content": f"<@&{role_id}>", "embeds": [embed]}, timeout=10)
        res.raise_for_status()
        log.info(f"{grade}학년 {class_num}반 디스코드 전송 성공")
    except Exception as e:
        log.error(f"{grade}학년 {class_num}반 디스코드 전송 실패: {e}")
        try:
            session.post(webhook_url, json={"content": f"오류 발생: {e}"}, timeout=10)
        except Exception:
            pass


def main() -> None:
    today = datetime.now(KST).date()

    if today.weekday() >= 5:
        log.info("주말이므로 전송 생략")
        return

    try:
        neis_key = get_env(NEIS_KEY_ENV)
    except EnvironmentError as e:
        log.error(e)
        return

    with requests.Session() as session:
        events = get_schedule_events(session, neis_key, today)
        if is_holiday(events):
            return

        meal_fields = get_meals(session, neis_key, today)

        for (grade, class_num), info in CLASSES.items():
            webhook_url = os.environ.get(info["webhook_env"])
            if not webhook_url:
                log.warning(f"{grade}학년 {class_num}반 Webhook 없음, 건너뜀")
                continue

            subjects = get_timetable_api(session, neis_key, today, grade, class_num)
            source = "NEIS"
            if not subjects:
                subjects = info["timetable"].get(today.weekday(), [])
                source = "저장됨"

            embed = build_embed(today, grade, class_num, subjects, source, meal_fields, events)
            send_discord(session, webhook_url, embed, info["role_id"], grade, class_num)


main()
