"""
Pembangun grid zona rekomendasi secara DINAMIS dari posisi nelayan.

Berbeda dari implementasi lama yang meng-hardcode GRID_LAT/GRID_LNG global,
modul ini membangun titik-titik grid di sekitar titik tempat nelayan memulai
melaut (posisi GPS saat menyiapkan sampan di pantai) dengan sebaran jarak
bertingkat ke arah laut.

Prinsip:
- Titik terdekat dahulu (mis. 3 km) hingga radius maksimum (mis. 22 km = 12 mil laut).
- Titik yang terlalu jauh (di luar radius maksimum) TIDAK dibangkitkan,
  agar tidak memberi rekomendasi yang boros BBM.
- Jumlah titik dibatasi (default 5) agar panggilan GEE per-request tetap cepat.
"""
import math
from typing import List, Dict

# Radius bumi dalam kilometer (konsisten dengan services/geo.py)
R_BUMI_KM = 6371.0

# Bearing default ke arah laut untuk pesisir barat Sumatra (Padang).
# Dapat ditimpa lewat environment variable bila di-deploy di lokasi lain.
DEFAULT_BEARING_LAUT_DEG = 270.0  # Barat

# Tingkatan jarak laut (km) yang digunakan secara default.
# Dipilih agar ada opsi dekat (hemat BBM) dan alternatif lebih jauh (potensi besar).
DEFAULT_JARAK_LAUT_KM = [3.0, 7.0, 12.0, 17.0, 22.0]


def titik_dari_bearing(
    lat: float,
    lng: float,
    bearing_deg: float,
    jarak_km: float,
) -> Dict[str, float]:
    """
    Menghitung koordinat tujuan (lat, lng) dari titik awal ditambah jarak & bearing.

    Ini adalah inverse haversine (menggunakan rumus great-circle), murni matematika,
    tanpa API eksternal - sehingga jalan offline.
    """
    phi1 = math.radians(lat)
    lambda1 = math.radians(lng)
    theta = math.radians(bearing_deg)

    delta = jarak_km / R_BUMI_KM

    phi2 = math.asin(
        math.sin(phi1) * math.cos(delta)
        + math.cos(phi1) * math.sin(delta) * math.cos(theta)
    )
    lambda2 = lambda1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2),
    )

    return {
        "lat": math.degrees(phi2),
        "lng": math.degrees(lambda2),
    }


def bangun_grid(
    pusat_lat: float,
    pusat_lng: float,
    radius_km_maks: float = 22.0,
    jumlah_titik: int = 5,
    bearing_laut_deg: float = DEFAULT_BEARING_LAUT_DEG,
) -> List[Dict[str, float]]:
    """
    Membangun grid titik zona rekomendasi di sekitar posisi nelayan.

    Args:
        pusat_lat: Latitude posisi nelayan (GPS saat siapkan sampan).
        pusat_lng: Longitude posisi nelayan.
        radius_km_maks: Radius maksimum - titik di luar ini TIDAK dibangkitkan.
        jumlah_titik: Jumlah titik grid yang diinginkan (dibatasi agar GEE cepat).
        bearing_laut_deg: Arah laut relatif terhadap posisi nelayan (derajat).

    Returns:
        List dict berisi {"lat": ..., "lng": ..., "jarak_km": ...} diurutkan
        dari yang terdekat ke yang terjauh.
    """
    # Ambil jarak bertingkat sesuai jumlah titik yang diminta.
    jarak_bertahap = DEFAULT_JARAK_LAUT_KM[:jumlah_titik]

    # Pastikan tidak melebihi radius maksimum.
    jarak_bertahap = [j for j in jarak_bertahap if j <= radius_km_maks]

    # Jika semua jarak default > radius, hasilkan tingkatan proporsional dari 0..maks.
    if not jarak_bertahap:
        jarak_bertahap = [
            radius_km_maks * (i + 1) / jumlah_titik for i in range(jumlah_titik)
        ]

    # Variasi kecil bearing agar titik tidak segaris sempurna dengan pantai.
    variasi_bearing = [
        bearing_laut_deg - 15.0,
        bearing_laut_deg,
        bearing_laut_deg + 15.0,
    ]

    grid: List[Dict[str, float]] = []
    for i, jarak in enumerate(jarak_bertahap):
        # Titik utama lurus ke laut pada jarak bertingkat.
        titik_utama = titik_dari_bearing(pusat_lat, pusat_lng, bearing_laut_deg, jarak)
        grid.append({**titik_utama, "jarak_km": round(jarak, 2)})

        # Untuk titik di jarak menengah, tambahkan 2 variasi sisi agar grid menyebar.
        if i > 0 and i < len(jarak_bertahap) - 1:
            for var in variasi_bearing:
                if var == bearing_laut_deg:
                    continue  # sudah dibuat sebagai titik utama
                titik_sisi = titik_dari_bearing(pusat_lat, pusat_lng, var, jarak)
                grid.append({**titik_sisi, "jarak_km": round(jarak, 2)})

    # Potong bila terlalu banyak titik (jaga kecepatan GEE).
    grid = grid[:jumlah_titik]

    # Urutkan dari yang terdekat.
    grid.sort(key=lambda t: t["jarak_km"])
    return grid