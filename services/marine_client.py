import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List
from core.config import get_settings

settings = get_settings()

class MarineClient:
    def __init__(self):
        self.url = "https://marine-api.open-meteo.com/v1/marine"

    def fetch_gelombang(self, lat: float, lng: float) -> Dict[str, List[Dict[str, Any]]]:
        """
        Mengambil data ramalan gelombang laut dari Open-Meteo Marine API.
        Mencakup gelombang gabungan, gelombang angin, dan gelombang swell.
        """
        if settings.MOCK_EXTERNAL:
            return self._generate_mock_waves()

        params = {
            "latitude": lat,
            "longitude": lng,
            "hourly": [
                "wave_height", "wave_direction", "wave_period",
                "wind_wave_height", "wind_wave_direction", "wind_wave_period",
                "swell_wave_height", "swell_wave_direction", "swell_wave_period"
            ],
            "timezone": "Asia/Jakarta",
            "forecast_days": 7
        }

        try:
            response = httpx.get(self.url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return self._parse_open_meteo_marine(data)
        except Exception as e:
            print(f"Error memanggil Open-Meteo Marine API: {e}. Fallback ke mock data.")
            return self._generate_mock_waves()

    def _parse_open_meteo_marine(self, data: dict) -> Dict[str, List[Dict[str, Any]]]:
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        
        gabungan = []
        angin = []
        swell = []

        for i, t in enumerate(times):
            # Parse gelombang gabungan
            gabungan.append({
                "waktu": t,
                "tinggi_m": hourly.get("wave_height", [])[i],
                "arah_derajat": hourly.get("wave_direction", [])[i],
                "periode_detik": hourly.get("wave_period", [])[i]
            })
            # Parse gelombang angin
            angin.append({
                "waktu": t,
                "tinggi_m": hourly.get("wind_wave_height", [])[i],
                "arah_derajat": hourly.get("wind_wave_direction", [])[i],
                "periode_detik": hourly.get("wind_wave_period", [])[i]
            })
            # Parse gelombang swell
            swell.append({
                "waktu": t,
                "tinggi_m": hourly.get("swell_wave_height", [])[i],
                "arah_derajat": hourly.get("swell_wave_direction", [])[i],
                "periode_detik": hourly.get("swell_wave_period", [])[i]
            })

        return {
            "gelombang_gabungan": gabungan,
            "gelombang_angin": angin,
            "gelombang_swell": swell
        }

    def _generate_mock_waves(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Menghasilkan ramalan gelombang tiruan selama 7 hari (168 jam).
        """
        now = datetime.now()
        start_time = datetime(now.year, now.month, now.day)
        
        gabungan = []
        angin = []
        swell = []

        for hour_offset in range(168):
            current_time = start_time + timedelta(hours=hour_offset)
            time_str = current_time.strftime("%Y-%m-%dT%H:00")
            
            # Buat fluktuasi menggunakan gelombang sinus agar terlihat alami
            wave_factor = 0.5 + 0.3 * (1.0 + (hour_offset % 24) / 12.0)
            
            gabungan.append({
                "waktu": time_str,
                "tinggi_m": round(1.0 * wave_factor, 2),
                "arah_derajat": (180 + hour_offset * 2) % 360,
                "periode_detik": round(6.5 + (hour_offset % 5) / 2.0, 1)
            })
            
            angin.append({
                "waktu": time_str,
                "tinggi_m": round(0.4 * wave_factor, 2),
                "arah_derajat": (170 + hour_offset * 3) % 360,
                "periode_detik": round(3.5 + (hour_offset % 3) / 2.0, 1)
            })
            
            swell.append({
                "waktu": time_str,
                "tinggi_m": round(0.8 * wave_factor, 2),
                "arah_derajat": (190 + hour_offset * 1) % 360,
                "periode_detik": round(8.5 + (hour_offset % 4) / 2.0, 1)
            })

        return {
            "gelombang_gabungan": gabungan,
            "gelombang_angin": angin,
            "gelombang_swell": swell
        }
