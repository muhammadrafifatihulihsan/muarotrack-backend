from services.scoring import (
    clamp,
    normalisasi_sst,
    normalisasi_klorofil,
    normalisasi_turbiditas,
    normalisasi_batimetri,
    normalisasi_fase_bulan,
    normalisasi_jarak_muara,
    hitung_skor_zona
)

def test_clamp():
    assert clamp(5.0, 0.0, 10.0) == 5.0
    assert clamp(-1.0, 0.0, 10.0) == 0.0
    assert clamp(12.0, 0.0, 10.0) == 10.0

def test_normalisasi_sst():
    # Ideal: suhu tinggi ~31 derajat -> skor 1.0
    assert normalisasi_sst(31.0) == 1.0
    # Minimum: suhu rendah ~24 derajat -> skor 0.0
    assert normalisasi_sst(24.0) == 0.0
    # Di luar rentang
    assert normalisasi_sst(20.0) == 0.0
    assert normalisasi_sst(35.0) == 1.0

def test_normalisasi_klorofil():
    # 0.1 -> skor 0.0
    assert abs(normalisasi_klorofil(0.1) - 0.0) < 0.001
    # 10.0 -> skor 1.0
    assert abs(normalisasi_klorofil(10.0) - 1.0) < 0.001
    # Di luar batas
    assert normalisasi_klorofil(0.0) == 0.0
    assert normalisasi_klorofil(-1.0) == 0.0

def test_normalisasi_turbiditas():
    # NDTI tinggi (air sangat keruh) -> NDTI=1 -> skor 0.0
    assert normalisasi_turbiditas(1.0) == 0.0
    # NDTI rendah (air jernih) -> NDTI=-1 -> skor 1.0
    assert normalisasi_turbiditas(-1.0) == 1.0

def test_normalisasi_batimetri():
    # Ideal (10m - 40m) -> skor 1.0
    assert normalisasi_batimetri(10.0) == 1.0
    assert normalisasi_batimetri(25.0) == 1.0
    assert normalisasi_batimetri(40.0) == 1.0
    # Terlalu dangkal (5m) -> skor 0.5
    assert normalisasi_batimetri(5.0) == 0.5
    # Terlalu dalam (70m) -> skor 0.5 (1.0 - (70 - 40)/60 = 0.5)
    assert normalisasi_batimetri(70.0) == 0.5

def test_normalisasi_jarak_muara():
    # Jauh (>=5km) -> skor 1.0
    assert normalisasi_jarak_muara(5.0) == 1.0
    assert normalisasi_jarak_muara(10.0) == 1.0
    # Sangat dekat muara (0km) -> skor 0.0
    assert normalisasi_jarak_muara(0.0) == 0.0

def test_hitung_skor_zona():
    # Titik uji
    sst = 27.5
    klorofil = 1.0
    turbiditas_ndti = 0.0
    depth_m = 25.0
    fase_bulan_illum = 0.5
    
    # Koordinat dekat muara Batang Kuranji (jarak ~0km)
    lat_dekat = -0.8972
    lng_dekat = 100.3508
    
    skor_dekat, detail_dekat, skor_efektif_dekat = hitung_skor_zona(
        sst, klorofil, turbiditas_ndti, depth_m, fase_bulan_illum, lat_dekat, lng_dekat,
        jarak_km_dari_titik_mulai=3.0
    )
    
    # Koordinat jauh di tengah laut (jarak >= 5km)
    lat_jauh = -0.9000
    lng_jauh = 100.2000
    
    skor_jauh, detail_jauh, skor_efektif_jauh = hitung_skor_zona(
        sst, klorofil, turbiditas_ndti, depth_m, fase_bulan_illum, lat_jauh, lng_jauh,
        jarak_km_dari_titik_mulai=20.0
    )
    
    # Skor jauh harus lebih tinggi dibanding dekat muara terdampak karena airnya bebas sedimentasi muara
    assert skor_jauh > skor_dekat
    
    # Skor efektif dekat > skor efektif jauh karena dekat lebih hemat BBM/waktu
    assert skor_efektif_dekat > skor_efektif_jauh
    
    # Menguji bonus komunitas (laporan_dalam_500m >= 3)
    skor_bonus, detail_bonus, _ = hitung_skor_zona(
        sst, klorofil, turbiditas_ndti, depth_m, fase_bulan_illum, lat_jauh, lng_jauh,
        jarak_km_dari_titik_mulai=20.0, laporan_dalam_500m=3
    )
    assert abs(skor_bonus - clamp(skor_jauh + 0.10, 0.0, 1.0)) < 0.001
