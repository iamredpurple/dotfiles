#!/usr/bin/env python3
import json
import urllib.request
import subprocess
from datetime import datetime

# Weather icons mapping
WEATHER_CODES_DAY = {
    "113": "", "116": "󰖕", "119": "󰖐", "122": "󰖐",
    "143": "󰖑", "176": "󰼳", "179": "󰼶", "182": "󰼶",
    "185": "󰼶", "200": "󰙾", "227": "󰼶", "230": "",
    "248": "󰖑", "260": "󰖑", "263": "󰼳", "266": "󰼳",
    "281": "󰼶", "284": "󰼶", "293": "󰼳", "296": "󰼳",
    "299": "󰖖", "302": "󰖖", "305": "󰖖", "308": "󰖖",
    "311": "󰼶", "314": "󰼶", "317": "󰼶", "320": "󰼶",
    "323": "", "326": "", "329": "", "332": "",
    "335": "", "338": "", "350": "󰼶", "353": "󰼳",
    "356": "󰖖", "359": "󰖖", "362": "󰼶", "365": "󰼶",
    "368": "", "371": "", "374": "󰼶", "377": "󰼶",
    "386": "󰙾", "389": "󰙾", "392": "", "395": "",
    "149": "󰖑"
}
WEATHER_CODES_NIGHT = {
    "113": "", "116": "", "119": "󰖐", "122": "󰖐",
    "143": "󰖑", "176": "", "179": "󰼶", "182": "󰼶",
    "185": "󰼶", "200": "󰙾", "227": "󰼶", "230": "",
    "248": "󰖑", "260": "󰖑", "263": "", "266": "",
    "281": "󰼶", "284": "󰼶", "293": "", "296": "",
    "299": "󰖖", "302": "󰖖", "305": "󰖖", "308": "󰖖",
    "311": "󰼶", "314": "󰼶", "317": "󰼶", "320": "󰼶",
    "323": "", "326": "", "329": "", "332": "",
    "335": "", "338": "", "350": "󰼶", "353": "",
    "356": "󰖖", "359": "󰖖", "362": "󰼶", "365": "󰼶",
    "368": "", "371": "", "374": "󰼶", "377": "󰼶",
    "386": "󰙾", "389": "󰙾", "392": "", "395": "",
    "149": "󰖑"
}

try:
    # req = urllib.request.Request("https://wttr.in/?format=j1", headers={"User-Agent": "Mozilla/5.0"})
    # with urllib.request.urlopen(req) as response:
    #     data = json.loads(response.read().decode())

    command = ["curl", "wttr.in/?format=j1"]
    response = subprocess.run(command, capture_output=True, text=True)
    data = json.loads(response.stdout)
    
    current = data["current_condition"][0]
    astronomy = data['weather'][0]['astronomy'][0]
    temp_c = current["temp_C"]
    weather_code = current["weatherCode"]
    #icon = WEATHER_CODES.get(weather_code, "✨")
    desc = current["weatherDesc"][0]["value"]
    feel_c = current["FeelsLikeC"]
    humidity = current["humidity"]

    local_time_str = current["observation_time"] #['localObsDateTime']
    #current_dt = datetime.strptime(local_time_str, "%Y-%m-%d %I:%M %p")
    current_time = datetime.now().time()
    sunrise_time = datetime.strptime(astronomy['sunrise'], "%I:%M %p").time()
    sunset_time = datetime.strptime(astronomy['sunset'], "%I:%M %p").time()
        
    if sunrise_time <= current_time < sunset_time:
        icon = WEATHER_CODES_DAY.get(weather_code, "󱁞")
    else:
        icon = WEATHER_CODES_NIGHT.get(weather_code, "󱠩")

    # Waybar format output
    out = {
        "text": f"{icon} {temp_c}°C",
        "tooltip": f"{desc}\nFeels like: {feel_c}°C\nHumidity: {humidity}%"
    }
    print(json.dumps(out))

except Exception:
    print(json.dumps({"text": " ", "tooltip": "Radar Down Temporarily"}))
