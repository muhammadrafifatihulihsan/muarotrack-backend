import math
from typing import Dict, Tuple
from services.geo import haversine_km

# Koordinat muara terdampak galodo/sedimentasi di Padang.
# Dipakai sebagai PENANDA (penjelasan) area sedimentasi pasca-banjir,
# bukan sebagai jangkar grid. Skor tetap dihitung dinamis dari posisi nelayan.
MUARA_TERDAMPAK = [
    {"nama": "Batang Kuranji", "lat": -0.8972, "lng": 100.3508},
    {"nama": "Koto Tangah", "lat": -0.8256, "lng": 100.3167},
    {"nama": "Ulak Karang", "lat": -0.8988, "lng": 100.3444},
]

# Radius (km) di sekitar muara yang dianggap terdampak sedimen.
# Gunanya hanya untuk penanda/catatan penjelas, bukan pembatas grid.
RADIUS_SEDIMEN_KM = 5.0


def clamp(val: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, val))


def normalisasi_sst(sst: float) -> float:
    """
    Suhu Permukaan Laut (SST) - Rentang ideal perairan tropis untuk ikan ~24-31 C.
    """
    return clamp((sst - 24.0) / 7.0, 0.0, 1.0)


def normalisasi_klorofil(klorofil: float) -> float:
    """
    Klorofil-a - Indikator kelimpahan fitoplankton. Logaritmik 0.1 - 10 mg/m3.
    """
    if klorofil <= 0:
        return 0.0
    return clamp(math.log10(klorofil / 0.1) / 2.0, 0.0, 1.0)


def normalisasi_turbiditas(ndti: float) -> float:
    """
    NDTI (Turbiditas) - Nilai NDTI rendah = air jernih = baik untuk penangkapan.
    """
    return 1.0 - clamp((ndti + 1.0) / 2.0, 0.0, 1.0)


def normalisasi_batimetri(depth_m: float) -> float:
    """
    Batimetri - Kontur kedalaman. Skor tertinggi pada kedalaman ideal nelayan tradisional (10-40 m).
    """
    abs_depth = abs(depth_m)
    if 10.0 <= abs_depth <= 40.0:
        return 1.0
    elif abs_depth < 10.0:
        return max(0.0, abs_depth / 10.0)
    else:
        return max(0.0, 1.0 - (abs_depth - 40.0) / 60.0)


def normalisasi_fase_bulan(illumination_fraction: float) -> float:
    """
    Fase Bulan - Diambil dari fraksi iluminasi (0.0 - 1.0).
    """
    return clamp(illumination_fraction, 0.0, 1.0)


def hitung_jarak_muara_terdekat_km(lat: float, lng: float) -> float:
    """
    Jarak terdekat dari suatu titik ke salah satu muara terdampak sedimen.
    """
    min_dist = float("inf")
    for muara in MUARA_TERDAMPAK:
        dist = haversine_km(lat, lng, muara["lat"], muara["lng"])
        if dist < min_dist:
            min_dist = dist
    return min_dist


def normalisasi_jarak_muara(distance_km: float) -> float:
    """
    Jarak ke muara terdampak - Makin jauh makin baik untuk menghindari sedimentasi.
    Jenuh di 5 km.
    """
    return clamp(distance_km / 5.0, 0.0, 1.0)


def faktor_hemat_bbm(jarak_km: float) -> float:
    """
    Faktor efisiensi BBM/waktu (0..1).

    Semakin dekat semakin hemat (faktor mendekati 1). Titik di radius maksimum
    diberi faktor rendah (mendekati 0) agar tidak menang hanya karena potensi ikan
    besar yang terlalu jauh sehingga boros BBM.
    """
    return clamp(1.0 - jarak_km / 25.0, 0.0, 1.0)


def tanda_sedimen(lat: float, lng: float) -> Dict[str, object]:
    """
    Menentukan apakah titik berada di area terdampak sedimen pasca-banjir.

    Hanya bersifat penjelas (flag + catatan). Tidak mengganti formula skor utama,
    namun informasi ini ditampilkan di respons agar nelayan tahu struktur dasar
    laut di area tersebut berubah.
    """
    jarak = hitung_jarak_muara_terdekat_km(lat, lng)
    if jarak <= RADIUS_SEDIMEN_KM:
        return {
            "terdampak_sedimen": True,
            "catatan_sedimen": (
                "Area terdampak sedimen pasca-banjir (dekat muara). "
                "Struktur dasar laut dapat berubah - hati-hati & hindari jika memungkinkan."
            ),
        }
    return {"terdampak_sedimen": False, "catatan_sedimen": None}


def hitung_skor_zona(
    sst: float,
    klorofil: float,
    turbiditas_ndti: float,
    depth_m: float,
    fase_bulan_illum: float,
    lat: float,
    lng: float,
    jarak_km_dari_titik_mulai: float = 0.0,
    laporan_dalam_500m: int = 0,
) -> Tuple[float, Dict[str, float], float]:
    """
    Menghitung skor gabungan (skor_zona) rule-based v1, DINAMIS dari posisi nelayan.

    Args:
        lat/lng: koordinat titik zona (bukan titik mulai).
        jarak_km_dari_titik_mulai: jarak titik zona dari posisi nelayan mulai melaut.
            Dipakai untuk skor efisiensi BBM/waktu serta penalti jarak.

    Returns:
        (skor_mentah, detail_skor, skor_efektif)
    """
    skor_sst = normalisasi_sst(sst)
    skor_klorofil = normalisasi_klorofil(klorofil)
    skor_turbiditas = normalisasi_turbiditas(turbiditas_ndti)
    skor_batimetri = normalisasi_batimetri(depth_m)
    skor_fase_bulan = normalisasi_fase_bulan(fase_bulan_illum)

    jarak_muara = hitung_jarak_muara_terdekat_km(lat, lng)
    skor_jarak_muara = normalisasi_jarak_muara(jarak_muara)

    # Formula pembobotan:
    # SST 20%, Klorofil 15%, Turbiditas 25%, Batimetri 15%, Fase Bulan 10%, Jarak Muara 15%
    skor_dasar = (
        0.20 * skor_sst
        + 0.15 * skor_klorofil
        + 0.25 * skor_turbiditas
        + 0.15 * skor_batimetri
        + 0.10 * skor_fase_bulan
        + 0.15 * skor_jarak_muara
    )

    # Bonus komunitas: jika ada >= 3 laporan dalam 500m, tambah 10% (0.10)
    bonus = 0.10 if laporan_dalam_500m >= 3 else 0.0
    skor_mentah = clamp(skor_dasar + bonus, 0.0, 1.0)

    # Skor efektif: menyeimbangkan potensi tangkapan (skor_mentah) dengan
    # efisiensi BBM/waktu (faktor jarak). Ini yang dipakai untuk PENGURUTAN.
    skor_efektif = round(
        skor_mentah * (0.6 + 0.4 * faktor_hemat_bbm(jarak_km_dari_titik_mulai)), 4
    )

    detail_skor = {
        "sst": round(skor_sst, 4),
        "klorofil": round(skor_klorofil, 4),
        "turbiditas": round(skor_turbiditas, 4),
        "batimetri": round(skor_batimetri, 4),
        "fase_bulan": round(skor_fase_bulan, 4),
        "jarak_muara": round(skor_jarak_muara, 4),
        "bonus_komunitas": round(bonus, 4),
        "faktor_hemat_bbm": round(faktor_hemat_bbm(jarak_km_dari_titik_mulai), 4),
    }

    return round(skor_mentah, 4), detail_skor, skor_efektif