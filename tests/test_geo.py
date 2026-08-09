from services.geo import haversine_km, bearing, prediksi_bbm, total_jarak_jalur

def test_haversine_km():
    # Jarak dari Padang ke Bukittinggi sekitar 70 - 75 km
    lat1, lng1 = -0.9471, 100.4172  # Padang
    lat2, lng2 = -0.3051, 100.3694  # Bukittinggi
    
    dist = haversine_km(lat1, lng1, lat2, lng2)
    assert 70.0 < dist < 75.0


def test_bearing():
    # Arah Utara harus ~0 derajat
    lat1, lng1 = 0.0, 0.0
    lat2, lng2 = 1.0, 0.0
    assert abs(bearing(lat1, lng1, lat2, lng2) - 0.0) < 0.01

    # Arah Timur harus ~90 derajat
    lat2, lng2 = 0.0, 1.0
    assert abs(bearing(lat1, lng1, lat2, lng2) - 90.0) < 0.01

def test_prediksi_bbm():
    # Kapal dengan konsumsi 0.5 liter/km melaju sejauh 10 km (PP = 20 km) -> Habis 10 liter
    assert prediksi_bbm(10.0, 0.5) == 10.0 * 0.5 * 2.0

def test_total_jarak_jalur():
    titik = [
        {"lat": -0.8972, "lng": 100.3508},
        {"lat": -0.8988, "lng": 100.3444},
        {"lat": -0.8256, "lng": 100.3167}
    ]
    
    jarak_segment_1 = haversine_km(titik[0]["lat"], titik[0]["lng"], titik[1]["lat"], titik[1]["lng"])
    jarak_segment_2 = haversine_km(titik[1]["lat"], titik[1]["lng"], titik[2]["lat"], titik[2]["lng"])
    
    assert abs(total_jarak_jalur(titik) - (jarak_segment_1 + jarak_segment_2)) < 0.001
