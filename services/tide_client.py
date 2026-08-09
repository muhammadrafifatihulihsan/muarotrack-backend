import httpx
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any
from core.config import get_settings

settings = get_settings()

class TideClient:
    def __init__(self):
        self.tidecheck_url = "https://api.tidecheck.com/v1/tides"
        self.worldtides_url = "https://partner.worldtides.info/api/v3"

    def fetch_pasut(self, lat: float, lng: float) -> List[Dict[str, Any]]:
        """
        Mengambil ramalan pasang surut air laut.
        Mencoba memanggil TideCheck API terlebih dahulu, jika gagal atau jika MOCK_EXTERNAL=true,
        maka menghasilkan ramalan pasang surut menggunakan model harmonik matematis lokal (mock).
        """
        if settings.MOCK_EXTERNAL:
            return self._generate_mock_tides()

        # Cobalah TideCheck API
        if settings.TIDECHECK_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {settings.TIDECHECK_API_KEY}"}
                params = {"lat": lat, "lon": lng}
                response = httpx.get(self.tidecheck_url, headers=headers, params=params, timeout=10.0)
                if response.status_code == 200:
                    return self._parse_tidecheck(response.json())
            except Exception as e:
                print(f"Gagal memanggil TideCheck API: {e}. Mencoba WorldTides...")

        # Fallback ke WorldTides API jika ada key
        if settings.WORLDTIDES_API_KEY:
            try:
                params = {
                    "heights": "",
                    "extremes": "",
                    "lat": lat,
                    "lon": lng,
                    "key": settings.WORLDTIDES_API_KEY,
                    "days": 7
                }
                response = httpx.get(self.worldtides_url, params=params, timeout=10.0)
                if response.status_code == 200:
                    return self._parse_worldtides(response.json())
            except Exception as e:
                print(f"Gagal memanggil WorldTides API: {e}.")

        # Fallback terakhir ke mock data
        return self._generate_mock_tides()

    def _parse_tidecheck(self, data: dict) -> List[Dict[str, Any]]:
        # Parser TideCheck disesuaikan dengan response asli TideCheck API
        # (Sebagai demo, kita sesuaikan dengan format time-series standar kita)
        result = []
        for item in data.get("tides", []):
            result.append({
                "waktu": item.get("time"),
                "tinggi_m": round(item.get("height"), 2),
                "tipe": item.get("type")  # 'pasang' | 'surut' | 'sampel'
            })
        return result

    def _parse_worldtides(self, data: dict) -> List[Dict[str, Any]]:
        # Parser WorldTides
        result = []
        for item in data.get("extremes", []):
            dt = datetime.fromtimestamp(item.get("dt"))
            time_str = dt.strftime("%Y-%m-%dT%H:%M")
            tipe = "pasang" if item.get("type") == "High" else "surut"
            result.append({
                "waktu": time_str,
                "tinggi_m": round(item.get("height"), 2),
                "tipe": tipe
            })
        return result

    def _generate_mock_tides(self) -> List[Dict[str, Any]]:
        """
        Menghasilkan ramalan pasang surut tiruan selama 7 hari menggunakan rumus harmonik semi-diurnal.
        Siklus pasut semi-diurnal memiliki periode sekitar 12 jam 25 menit.
        """
        now = datetime.now()
        start_time = datetime(now.year, now.month, now.day)
        
        result = []
        # Menggenerasi titik ekstrem pasang dan surut (setiap 6 jam 12 menit bergantian)
        cycle_hours = 6.208  # ~6 jam 12.5 menit untuk pindah dari pasang ke surut
        
        is_high = True
        current_time = start_time
        
        for i in range(28):  # 4 kali per hari * 7 hari = 28 ekstrem
            time_str = current_time.strftime("%Y-%m-%dT%H:%M")
            
            # Tinggi pasang berkisar 1.5 - 2.0 meter, surut berkisar 0.1 - 0.4 meter
            if is_high:
                tinggi = 1.6 + 0.3 * math.sin(i * 0.5)
                tipe = "pasang"
            else:
                tinggi = 0.2 + 0.15 * math.sin(i * 0.5)
                tipe = "surut"
                
            result.append({
                "waktu": time_str,
                "tinggi_m": round(tinggi, 2),
                "tipe": tipe
            })
            
            # Tambahkan waktu untuk siklus berikutnya
            current_time += timedelta(hours=cycle_hours)
            is_high = not is_high

        return result
