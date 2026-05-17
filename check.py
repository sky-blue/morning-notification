import requests

KEY = "571668b4449b4ba09ef972d847ee6022"
url = "https://open.neis.go.kr/hub/hisTimetable"
params = {
    "KEY": KEY,
    "Type": "json",
    "ATPT_OFCDC_SC_CODE": "B10",
    "SD_SCHUL_CODE": "7010965",
    "AY": "2026",
    "GRADE": "1",
    "CLASS_NM": "2",
    "TI_FROM_YMD": "20260520",
    "TI_TO_YMD": "20260520",
}
res = requests.get(url, params=params)
data = res.json()
print(data)
rows = data["hisTimetable"][1].get("row", [])
for row in rows:
    print(row.get("PERIO"), row.get("ITRT_CNTNT"))