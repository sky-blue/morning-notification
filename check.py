import requests

KEY = "571668b4449b4ba09ef972d847ee6022"
url = "https://open.neis.go.kr/hub/SchoolSchedule"
params = {
    "KEY": KEY,
    "Type": "json",
    "ATPT_OFCDC_SC_CODE": "B10",
    "SD_SCHUL_CODE": "7010965",
    "AA_FROM_YMD": "20260511",
    "AA_TO_YMD": "20260511",
}
res = requests.get(url, params=params)
data = res.json()
print(data)
HOLIDAY_KEYWORDS = ["휴업일", "재량휴업일", "방학", "수련활동"]

rows = data["SchoolSchedule"][1].get("row", [])
for row in rows:
    event = row.get("EVENT_NM", "")
    print(f"EVENT_NM: '{event}'")
    print(any(keyword in event for keyword in HOLIDAY_KEYWORDS))