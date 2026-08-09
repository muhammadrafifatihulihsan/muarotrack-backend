import hashlib
from core.config import get_settings

settings = get_settings()

class GeeClient:
    def __init__(self):
        self.initialized = False
        if not settings.MOCK_EXTERNAL:
            try:
                import ee
                # Coba inisialisasi GEE menggunakan credential default
                if settings.GEE_PROJECT_ID:
                    ee.Initialize(project=settings.GEE_PROJECT_ID)
                else:
                    ee.Initialize()
                self.initialized = True
            except Exception as e:
                print(f"Gagal menginisialisasi Google Earth Engine API: {e}. Mengaktifkan fallback mock data.")
                self.initialized = False

    def fetch_satellite_data(self, lat: float, lng: float) -> dict:
        """
        Mengambil data satelit SST, klorofil-a, dan NDTI (turbiditas) untuk koordinat tertentu.
        Jika MOCK_EXTERNAL=True atau inisialisasi gagal, gunakan data mock deterministik.
        """
        if settings.MOCK_EXTERNAL or not self.initialized:
            return self._get_deterministic_mock(lat, lng)
            
        try:
            import ee
            # GEE pipeline untuk SST (MODIS Aqua/Terra)
            # Karena kueri spasial GEE membutuhkan waktu dan setup project, kita buat draft pipeline dasar
            point = ee.Geometry.Point([lng, lat])
            
            # 1. SST (Suhu Permukaan Laut)
            sst_col = ee.ImageCollection("NASA/OCEANDATA/MODIS-Aqua/L3SMI") \
                .filterBounds(point) \
                .sort("system:time_start", False)
            sst_img = sst_col.first().select("sst")
            sst_val = sst_img.reduceRegion(ee.Reducer.mean(), point, 1000).get("sst").getInfo()
            
            # 2. Chlorophyll-a
            chlor_img = sst_col.first().select("chlor_a")
            chlor_val = chlor_img.reduceRegion(ee.Reducer.mean(), point, 1000).get("chlor_a").getInfo()
            
            # 3. Turbiditas NDTI (Sentinel-2)
            # Indeks NDTI = (Red - Green) / (Red + Green) -> Sentinel-2: B4 (Red) dan B3 (Green)
            s2_col = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
                .filterBounds(point) \
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30)) \
                .sort("system:time_start", False)
            
            s2_img = s2_col.first()
            ndti_img = s2_img.normalizedDifference(["B4", "B3"])
            ndti_val = ndti_img.reduceRegion(ee.Reducer.mean(), point, 10).getInfo()
            ndti = ndti_val.get("nd") if ndti_val else 0.0
            
            return {
                "sst": float(sst_val) if sst_val else 28.0,
                "klorofil": float(chlor_val) if chlor_val else 0.8,
                "turbiditas_ndti": float(ndti) if ndti else -0.1,
                "source": "gee"
            }
        except Exception as e:
            print(f"Error saat memanggil GEE API: {e}. Fallback ke mock data.")
            return self._get_deterministic_mock(lat, lng)

    def _get_deterministic_mock(self, lat: float, lng: float) -> dict:
        """
        Menghasilkan data satelit tiruan yang stabil (deterministik) berdasarkan koordinat GPS.
        """
        hash_input = f"{round(lat, 4)},{round(lng, 4)}".encode()
        h = int(hashlib.md5(hash_input).hexdigest(), 16)
        
        # SST: ~26.0 sampai 31.0 °C
        sst = 26.0 + (h % 51) / 10.0
        # Klorofil: ~0.1 sampai 4.0 mg/m³
        klorofil = 0.1 + (h % 40) / 10.0
        # NDTI (Turbiditas): ~-0.4 sampai 0.4
        ndti = -0.4 + (h % 81) / 100.0
        
        return {
            "sst": round(sst, 2),
            "klorofil": round(klorofil, 2),
            "turbiditas_ndti": round(ndti, 3),
            "source": "mock"
        }
