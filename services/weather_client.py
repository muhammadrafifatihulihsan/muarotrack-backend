import math
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any
from core.config import get_settings

settings = get_settings()

class WeatherClient:
    def __init__(self):
        self.url = "https://api.open-meteo.com/v1/forecast"

    def fetch_cuaca(self, lat: float, lng: float) -> List[Dict[str, Any]]:
        """
        Mengambil ramalan cuaca atmosfer dari Open-Meteo Forecast API.
        Mencakup 9 parameter cuaca esensial per jam selama 7 hari.
        """
        if settings.MOCK_EXTERNAL:
            return self._generate_mock_weather()

        params = {
            "latitude": lat,
            "longitude": lng,
            "hourly": [
                "temperature_2m", "relative_humidity_2m", "surface_pressure",
                "uv_index", "precipitation", "precipitation_probability",
                "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"
            ],
            "timezone": "Asia/Jakarta",
            "forecast_days": 7
        }

        try:
            response = httpx.get(self.url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return self._parse_open_meteo_weather(data)
        except Exception as e:
            print(f"Error memanggil Open-Meteo Forecast API: {e}. Fallback ke mock data.")
            return self._generate_mock_weather()

    def _parse_open_meteo_weather(self, data: dict) -> List[Dict[str, Any]]:
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        
        result = []
        for i, t in enumerate(times):
            result.append({
                "waktu": t,
                "suhu_c": hourly.get("temperature_2m", [])[i],
                "kelembapan_persen": hourly.get("relative_humidity_2m", [])[i],
                "tekanan_hpa": hourly.get("surface_pressure", [])[i],
                "uv_index": hourly.get("uv_index", [])[i],
                "presipitasi_mm": hourly.get("precipitation", [])[i],
                "probabilitas_presipitasi_persen": hourly.get("precipitation_probability", [])[i],
                "kecepatan_angin_kmh": hourly.get("wind_speed_10m", [])[i],
                "arah_angin_derajat": hourly.get("wind_direction_10m", [])[i],
                "hembusan_angin_kmh": hourly.get("wind_gusts_10m", [])[i]
            })
        return result

    def _generate_mock_weather(self) -> List[Dict[str, Any]]:
        """
        Menghasilkan ramalan cuaca tiruan selama 7 hari (168 jam) dengan fluktuasi siang-malam alami.
        """
        now = datetime.now()
        start_time = datetime(now.year, now.month, now.day)
        
        result = []
        for hour_offset in range(168):
            current_time = start_time + timedelta(hours=hour_offset)
            time_str = current_time.strftime("%Y-%m-%dT%H:00")
            hour = current_time.hour
            
            # Fluktuasi suhu: terpanas jam 14:00 (32 °C), terdingin jam 05:00 (24 °C)
            temp_diff = -math.cos((hour - 5) * 2 * math.pi / 24)
            suhu = 28.0 + 4.0 * temp_diff
            
            # Fluktuasi kelembapan: berkebalikan dengan suhu
            kelembapan = 80.0 - 15.0 * temp_diff
            
            # Fluktuasi tekanan
            tekanan = 1010.0 + 1.5 * math.sin(hour * 2 * math.pi / 12)
            
            # UV Index: hanya ada di siang hari (jam 6 sampai 18)
            if 6 <= hour <= 18:
                uv = max(0.0, 11.0 * math.sin((hour - 6) * math.pi / 12))
            else:
                uv = 0.0
                
            # Curah hujan tiruan (hujan kecil sesekali)
            presipitasi = 0.0
            prob_hujan = 10
            if hour_offset % 30 == 0:
                presipitasi = round(1.5 + (hour_offset % 3), 1)
                prob_hujan = 75
                
            # Angin
            wind_speed = round(12.0 + 5.0 * math.sin(hour_offset * 2 * math.pi / 24), 1)
            wind_dir = (240 + hour_offset * 2) % 360
            wind_gust = round(wind_speed * 1.5, 1)

            result.append({
                "waktu": time_str,
                "suhu_c": round(suhu, 1),
                "kelembapan_persen": int(kelembapan),
                "tekanan_hpa": round(tekanan, 1),
                "uv_index": round(uv, 1),
                "presipitasi_mm": presipitasi,
                "probabilitas_presipitasi_persen": prob_hujan,
                "kecepatan_angin_kmh": wind_speed,
                "arah_angin_derajat": wind_dir,
                "hembusan_angin_kmh": wind_gust
            })
            
        return result
