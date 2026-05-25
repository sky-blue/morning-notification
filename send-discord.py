import re
import json
import logging
import os
import sys
import requests
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

NEIS_KEY_ENV = "NEIS_API_KEY"
ADMIN_WEBHOOK_ENV = "DISCORD_WEBHOOK_ADMIN"
ADMIN_ROLE_ID = "1503038580946108507"
OFFICE_CODE = "B10"
SCHOOL_CODE = "7010965"
KST = ZoneInfo("Asia/Seoul")

HOLIDAY_KEYWORDS = [
    "휴업일",
    "재량휴업일",
    "방학",
    "수련활동",
    "공휴일"
]

DAY_COLORS = {
    0: 0x3498DB,
    1: 0xE74C3C,
    2: 0x2ECC71,
    3: 0xE67E22,
    4: 0x9B59B6,
}

CLASSES = {
    (1, 1): {
        "webhook_env": "DISCORD_WEBHOOK_1_1",
        "role_id": "1504064435193647105",
        "timetable": {
            0: ["공통영어1", "한국사1", "통합사회1", "공통수학1", "정보", "공통국어1", "통합과학1"],
            1: ["한국사1", "미술", "공통국어1", "체육1", "과학탐구실험1", "통합과학1", "통합사회1"],
            2: ["공통국어1", "공통영어1", "통합과학1", "공통수학1"],
            3: ["정보", "통합사회1", "미술", "미술", "진로활동", "공통수학1", "한국사1"],
            4: ["통합사회1", "정보", "통합과학1", "공통국어1", "공통수학1", "체육1", "공통영어1"],
        },
    },
    (1, 2): {
        "webhook_env": "DISCORD_WEBHOOK_1_2",
        "role_id": "1504064479586160670",
        "timetable": {
            0: ["공통영어1", "미술", "한국사1", "공통수학1", "통합과학1", "공통국어1", "통합사회1"],
            1: ["통합사회1", "한국사1", "체육1", "정보", "공통국어1", "미술", "미술"],
            2: ["과학탐구실험1", "공통영어1", "통합과학1", "공통수학1"],
            3: ["한국사1", "체육1", "통합사회1", "공통국어1", "통합과학1", "공통수학1", "정보"],
            4: ["정보", "공통국어1", "진로활동", "통합사회1", "공통수학1", "통합과학1", "공통영어1"],
        },
    },
    (1, 3): {
        "webhook_env": "DISCORD_WEBHOOK_1_3",
        "role_id": "1504064500448366704",
        "timetable": {
            0: ["공통수학1", "과학탐구실험1", "체육1", "공통국어1", "미술", "통합사회1", "공통영어1"],
            1: ["통합사회1", "공통영어1", "공통국어1", "통합과학1", "한국사1", "정보", "공통수학1"],
            2: ["통합과학1", "통합사회1", "공통수학1", "정보"],
            3: ["공통영어1", "공통국어1", "공통수학1", "체육1", "한국사1", "진로활동", "통합과학1"],
            4: ["한국사1", "공통국어1", "정보", "통합과학1", "통합사회1", "미술", "미술"],
        },
    },
    (1, 4): {
        "webhook_env": "DISCORD_WEBHOOK_1_4",
        "role_id": "1504064519587233853",
        "timetable": {
            0: ["공통수학1", "음악", "과학탐구실험1", "통합과학1", "한국사1", "통합사회1", "공통영어1"],
            1: ["체육1", "공통영어1", "정보", "통합사회1", "진로활동", "공통국어1", "공통수학1"],
            2: ["통합사회1", "통합과학1", "공통수학1", "공통국어1"],
            3: ["공통영어1", "한국사1", "공통수학1", "정보", "통합과학1", "통합사회1", "공통국어1"],
            4: ["체육1", "정보", "한국사1", "공통국어1", "통합과학1", "음악", "음악"],
        },
    },
    (1, 5): {
        "webhook_env": "DISCORD_WEBHOOK_1_5",
        "role_id": "1504064539497599006",
        "timetable": {
            0: ["통합사회1", "공통수학1", "공통영어1", "통합과학1", "정보", "진로활동", "체육1"],
            1: ["정보", "통합사회1", "음악", "음악", "공통수학1", "공통국어1", "통합과학1"],
            2: ["공통국어1", "한국사1", "체육1", "공통영어1"],
            3: ["공통국어1", "공통영어1", "통합과학1", "한국사1", "공통수학1", "정보", "통합사회1"],
            4: ["공통국어1", "음악", "공통수학1", "과학탐구실험1", "통합사회1", "한국사1", "통합과학1"],
        },
    },
    (1, 6): {
        "webhook_env": "DISCORD_WEBHOOK_1_6",
        "role_id": "1504064560355741776",
        "timetable": {
            0: ["통합사회1", "공통수학1", "공통영어1", "공통국어1", "음악", "통합과학1", "정보"],
            1: ["공통국어1", "통합사회1", "진로활동", "체육1", "공통수학1", "한국사1", "과학탐구실험1"],
            2: ["통합과학1", "통합사회1", "한국사1", "공통영어1"],
            3: ["공통국어1", "공통영어1", "음악", "음악", "공통수학1", "통합과학1", "정보"],
            4: ["체육1", "통합사회1", "공통수학1", "한국사1", "정보", "공통국어1", "통합과학1"],
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


def load_override(target: date) -> dict:
    try:
        with open("override.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(target.strftime("%Y-%m-%d"), {})
    except FileNotFoundError:
        return {}
    except Exception as e:
        log.warning(f"override.json 읽기 실패: {e}")
        return {}


def get_schedule_events(session: requests.Session, key: str, target: date) -> list[str]:
    url = "https://open.neis.go.kr/hub/SchoolSchedule"
    params = {
        "KEY": key, "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "AA_FROM_YMD": target.strftime("%Y%m%d"),
        "AA_TO_YMD": target.strftime("%Y%m%d"),
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
            log.info(f"쉬는 날 감지: {event}")
            return True
    return False


def fetch_meal(session: requests.Session, key: str, target: date, meal_code: str) -> str | None:
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": key, "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "MLSV_YMD": target.strftime("%Y%m%d"),
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
        cleaned = re.sub(r'\*+', '', cleaned)
        meals = cleaned.replace("<br/>", "\n")
        return "\n".join(line.strip() for line in meals.splitlines() if line.strip())
    except Exception as e:
        log.warning(f"급식 조회 실패 (code={meal_code}): {e}")
        return None


def get_meals(session: requests.Session, key: str, today: date, override: dict) -> tuple[str, str | None] | None:
    lunch_api = fetch_meal(session, key, today, "2")

    if lunch_api:
        log.info("급식 API 성공")
        dinner = fetch_meal(session, key, today, "3") if today.weekday() != 2 else None
        return lunch_api, dinner

    log.warning("급식 API 실패, override 확인")
    meal_override = override.get("meal")
    if meal_override:
        log.info("급식 override 사용")
        lunch = meal_override.get("lunch")
        dinner = meal_override.get("dinner")
        return lunch, dinner

    log.warning("급식 정보 없음 (API + override 모두 없음)")
    return None


def get_timetable_api(session: requests.Session, key: str, target: date, grade: int, class_num: int) -> list[str] | None:
    url = "https://open.neis.go.kr/hub/hisTimetable"
    params = {
        "KEY": key, "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "AY": target.year,
        "GRADE": str(grade),
        "CLASS_NM": str(class_num),
        "TI_FROM_YMD": target.strftime("%Y%m%d"),
        "TI_TO_YMD": target.strftime("%Y%m%d"),
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
        seen = set()
        subjects = []
        for r in sorted(rows, key=lambda x: int(x.get("PERIO", 0))):
            perio = r.get("PERIO")
            if perio not in seen:
                seen.add(perio)
                subjects.append(r["ITRT_CNTNT"])
        return subjects if subjects else None
    except Exception as e:
        log.warning(f"{grade}학년 {class_num}반 시간표 API 실패: {e}")
        return None


def compare_timetable(local: list[str], api: list[str]) -> list[dict]:
    """로컬 시간표와 API 시간표 비교, 변동 내역 반환"""
    changes = []
    max_len = max(len(local), len(api))

    for i in range(max_len):
        local_s = local[i] if i < len(local) else None
        api_s = api[i] if i < len(api) else None

        if local_s == api_s:
            changes.append({"perio": i + 1, "subject": api_s, "type": "same"})
        elif local_s and api_s:
            changes.append({"perio": i + 1, "subject": api_s, "type": "changed", "from": local_s, "to": api_s})
        elif local_s and not api_s:
            changes.append({"perio": i + 1, "subject": None, "type": "removed", "from": local_s})
        elif not local_s and api_s:
            changes.append({"perio": i + 1, "subject": api_s, "type": "added", "to": api_s})

    return changes


def has_changes(changes: list[dict]) -> bool:
    return any(c["type"] != "same" for c in changes)


def format_timetable_student(changes: list[dict]) -> str:
    """학생 채널용 시간표 문자열"""
    lines = []
    for c in changes:
        perio = c["perio"]
        if c["type"] == "same":
            lines.append(f"`{perio}교시` {c['subject']}")
        elif c["type"] == "changed":
            lines.append(f"`{perio}교시` {c['to']} ({c['from']} → {c['to']})")
        elif c["type"] == "removed":
            lines.append(f"`{perio}교시` ~~{c['from']}~~ (없어짐)")
        elif c["type"] == "added":
            lines.append(f"`{perio}교시` {c['to']} (추가됨)")
    return "\n".join(lines)


def format_timetable_admin(changes: list[dict]) -> str:
    """관리자 채널용 변동 내역 문자열"""
    lines = []
    for c in changes:
        perio = c["perio"]
        if c["type"] == "changed":
            lines.append(f"{perio}교시 {c['from']} → {c['to']}")
        elif c["type"] == "removed":
            lines.append(f"{perio}교시 {c['from']} → 없어짐")
        elif c["type"] == "added":
            lines.append(f"{perio}교시 추가됨 → {c['to']}")
    return "\n".join(lines)


def summarize_meal(meal: str | None) -> str:
    if not meal:
        return "없음"
    lines = [l for l in meal.splitlines() if l.strip()]
    if len(lines) <= 1:
        return lines[0] if lines else "없음"
    return f"{lines[0]} 외 {len(lines)-1}종"


def build_embed(
    today: date,
    grade: int,
    class_num: int,
    subjects: list[str],
    local_subjects: list[str],
    source: str,
    lunch: str,
    dinner: str | None,
    events: list[str],
) -> dict:
    day_names = ["월", "화", "수", "목", "금"]
    day = day_names[today.weekday()]

    # 변동 비교 (API 또는 override일 때만)
    if source in ("NEIS", "override"):
        changes = compare_timetable(local_subjects, subjects)
        changed = has_changes(changes)
        timetable_value = format_timetable_student(changes)
        timetable_name = "시간표 (변동있음)" if changed else "시간표"
    else:
        timetable_value = "\n".join(f"`{i+1}교시` {s}" for i, s in enumerate(subjects))
        timetable_name = "시간표 (저장됨)"

    timetable_value += "\n\u200b"
    description = f"학사일정: {', '.join(events)}\n\u200b" if events else ""

    fields = [
        {
            "name": timetable_name,
            "value": timetable_value[:1024],
            "inline": False,
        },
        {
            "name": "🍱 중식",
            "value": lunch[:1024],
            "inline": True,
        },
    ]

    if dinner:
        fields.append({
            "name": "🌙 석식",
            "value": dinner[:1024],
            "inline": True,
        })

    return {
        "title": f"{today.strftime('%Y-%m-%d')} {day}요일 좋은 아침!",
        "description": description,
        "color": DAY_COLORS.get(today.weekday(), 0x95A5A6),
        "fields": fields,
        "footer": {"text": f"동양고등학교 {grade}학년 {class_num}반"},
    }


def build_admin_embed(
    target: date,
    events: list[str],
    holiday: bool,
    lunch: str | None,
    dinner: str | None,
    timetable_summary: list[dict],
) -> dict:
    day_names = ["월", "화", "수", "목", "금"]
    day = day_names[target.weekday()]

    has_any_timetable = any(t["subjects"] for t in timetable_summary)

    if holiday:
        send_status = f"❌ 알림 전송 안 함\n학사일정: {', '.join(events)}"
        color = 0xE74C3C
    elif lunch is None and not has_any_timetable:
        send_status = "❓ 전송 여부 불확실\n급식 + 시간표 API 모두 없음"
        color = 0xE67E22
    elif lunch is None:
        send_status = "⚠️ 급식 없음 (시간표는 정상)\noverride 입력 필요"
        color = 0xE67E22
    else:
        send_status = "✅ 알림 전송 예정"
        color = 0x2ECC71

    if events and not holiday:
        send_status += f"\n학사일정: {', '.join(events)}"

    timetable_lines = []
    timetable_warnings = []

    for t in timetable_summary:
        subjects = t["subjects"]
        local_subjects = t["local_subjects"]
        normal_count = t["normal_count"]
        label = f"{t['grade']}-{t['class_num']}"

        if not subjects:
            timetable_lines.append(f"{label}: 없음")
        else:
            count = len(subjects)
            first = subjects[0]
            last = subjects[-1]
            line = f"{label}: {count}교시 ({first} ~ {last})"
            if count != normal_count:
                line += f" ⚠️(평소 {normal_count}교시)"
            timetable_lines.append(line)

            # 변동 감지
            changes = compare_timetable(local_subjects, subjects)
            if has_changes(changes):
                admin_diff = format_timetable_admin(changes)
                timetable_warnings.append(f"{label}\n{admin_diff}")

    timetable_value = "\n".join(timetable_lines) + "\n\u200b"

    fields = [
        {
            "name": "시간표",
            "value": timetable_value[:1024],
            "inline": False,
        },
        {
            "name": "🍱 중식",
            "value": summarize_meal(lunch),
            "inline": True,
        },
        {
            "name": "🌙 석식",
            "value": summarize_meal(dinner),
            "inline": True,
        },
    ]

    if timetable_warnings:
        warning_value = f"\n\u200b\n".join(timetable_warnings)
        # warning_value += "\noverride.json 입력하거나 API가 맞으면 무시하세요"
        fields.append({
            "name": "⚠️ 시간표 확인 필요",
            "value": warning_value[:1024],
            "inline": False,
        })

    if lunch is None and not has_any_timetable:
        fields.append({
            "name": "📢 안내",
            "value": "휴일이거나 NEIS 장애입니다\n확인 후 판단하세요",
            "inline": False,
        })
    elif lunch is None:
        fields.append({
            "name": "📢 안내",
            "value": "override.json 에 급식 입력하세요",
            "inline": False,
        })

    return {
        "title": f"📋 {target.strftime('%Y-%m-%d')} ({day}요일) 내일 미리보기",
        "description": f"{send_status}\n\u200b",
        "color": color,
        "fields": fields,
        "footer": {"text": "동양고등학교 관리자"},
    }


def send_discord(session: requests.Session, webhook_url: str, content: str, embed: dict, label: str) -> None:
    try:
        res = session.post(webhook_url, json={"content": content, "embeds": [embed]}, timeout=10)
        res.raise_for_status()
        log.info(f"{label} 디스코드 전송 성공")
    except Exception as e:
        log.error(f"{label} 디스코드 전송 실패: {e}")
        try:
            session.post(webhook_url, json={"content": f"오류 발생: {e}"}, timeout=10)
        except Exception:
            pass


def send_admin(session: requests.Session, admin_webhook: str, embed: dict) -> None:
    send_discord(session, admin_webhook, f"<@&{ADMIN_ROLE_ID}>", embed, "관리자")


def main_morning() -> None:
    today = datetime.now(KST).date()

    if today.weekday() >= 5:
        log.info("주말이므로 전송 생략")
        return

    try:
        neis_key = get_env(NEIS_KEY_ENV)
        admin_webhook = get_env(ADMIN_WEBHOOK_ENV)
    except EnvironmentError as e:
        log.error(e)
        return

    with requests.Session() as session:
        events = get_schedule_events(session, neis_key, today)
        if is_holiday(events):
            log.info("휴일이므로 전송 생략")
            send_admin(session, admin_webhook, {
                "title": "❌ 오늘 알림 전송 안 함",
                "description": f"휴일 감지: {', '.join(events)}",
                "color": 0xE74C3C,
            })
            return

        override = load_override(today)
        meals = get_meals(session, neis_key, today, override)

        if meals is None:
            test_subjects = get_timetable_api(session, neis_key, today, 1, 1)
            if test_subjects:
                send_admin(session, admin_webhook, {
                    "title": "⚠️ 오늘 알림 전송 안 함",
                    "description": "급식 API 실패 + override 없음\n시간표 API는 정상\noverride.json 입력 후 수동 실행하세요",
                    "color": 0xE67E22,
                })
            else:
                send_admin(session, admin_webhook, {
                    "title": "❓ 오늘 알림 전송 안 함",
                    "description": "급식 + 시간표 API 모두 없음\n휴일이거나 NEIS 장애\n확인 후 판단하세요",
                    "color": 0xE74C3C,
                })
            return

        lunch, dinner = meals

        for (grade, class_num), info in CLASSES.items():
            webhook_url = os.environ.get(info["webhook_env"])
            if not webhook_url:
                log.warning(f"{grade}학년 {class_num}반 Webhook 없음, 건너뜀")
                continue

            local_subjects = info["timetable"].get(today.weekday(), [])
            timetable_key = f"{grade}-{class_num}"
            timetable_override = override.get("timetable", {}).get(timetable_key)

            if timetable_override:
                log.info(f"{grade}학년 {class_num}반 시간표 override 사용")
                subjects = timetable_override
                source = "override"
            else:
                api_subjects = get_timetable_api(session, neis_key, today, grade, class_num)
                if api_subjects:
                    subjects = api_subjects
                    source = "NEIS"
                else:
                    subjects = local_subjects
                    source = "저장됨"

            embed = build_embed(today, grade, class_num, subjects, local_subjects, source, lunch, dinner, events)
            send_discord(session, webhook_url, f"<@&{info['role_id']}>", embed, f"{grade}학년 {class_num}반")


def main_preview() -> None:
    today = datetime.now(KST).date()
    tomorrow = today + timedelta(days=1)

    if tomorrow.weekday() >= 5:
        log.info("내일 주말이므로 미리보기 생략")
        return

    try:
        neis_key = get_env(NEIS_KEY_ENV)
        admin_webhook = get_env(ADMIN_WEBHOOK_ENV)
    except EnvironmentError as e:
        log.error(e)
        return

    with requests.Session() as session:
        events = get_schedule_events(session, neis_key, tomorrow)
        holiday = is_holiday(events)

        lunch = fetch_meal(session, neis_key, tomorrow, "2")
        dinner = fetch_meal(session, neis_key, tomorrow, "3") if tomorrow.weekday() != 2 else None

        timetable_summary = []
        for (grade, class_num), info in CLASSES.items():
            subjects = get_timetable_api(session, neis_key, tomorrow, grade, class_num)
            local_subjects = info["timetable"].get(tomorrow.weekday(), [])
            normal_count = len(local_subjects)
            timetable_summary.append({
                "grade": grade,
                "class_num": class_num,
                "subjects": subjects or [],
                "local_subjects": local_subjects,
                "normal_count": normal_count,
            })

        embed = build_admin_embed(tomorrow, events, holiday, lunch, dinner, timetable_summary)
        send_admin(session, admin_webhook, embed)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    if mode == "preview":
        main_preview()
    else:
        main_morning()