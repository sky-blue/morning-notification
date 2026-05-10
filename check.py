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
print(res.json())