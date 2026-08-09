import math
from typing import List, Dict

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Menghitung jarak lingkaran besar antara dua titik koordinat dalam kilometer.
    """
    R = 6371.0  # Radius bumi dalam kilometer
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_phi / 2.0) ** 2 + 
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Menghitung bearing awal (azimut) dari titik 1 ke titik 2 dalam derajat (0 - 360).
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lng2 - lng1)
    
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = (math.cos(phi1) * math.sin(phi2) - 
         math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda))
    
    theta = math.atan2(y, x)
    return (math.degrees(theta) + 360.0) % 360.0

def prediksi_bbm(jarak_km: float, konsumsi_per_km: float) -> float:
    """
    Memprediksi kebutuhan bahan bakar untuk perjalanan pulang-pergi.
    """
    return jarak_km * konsumsi_per_km * 2.0

def total_jarak_jalur(titik: List[Dict[str, float]]) -> float:
    """
    Menghitung total jarak dari rute yang terdiri dari beberapa titik koordinat.
    Setiap titik adalah dict yang mengandung 'lat' dan 'lng'.
    """
    total = 0.0
    for i in range(len(titik) - 1):
        total += haversine_km(
            titik[i]["lat"], titik[i]["lng"],
            titik[i + 1]["lat"], titik[i + 1]["lng"]
        )
    return total
