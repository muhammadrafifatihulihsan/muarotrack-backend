from datetime import date
import math

def hitung_fase_bulan(tgl: date) -> float:
    """
    Menghitung fase bulan (0.0 - 1.0).
    0.0 atau 1.0 = Bulan Baru (New Moon)
    0.25 = Kuartal Awal (First Quarter)
    0.5 = Bulan Purnama (Full Moon)
    0.75 = Kuartal Akhir (Last Quarter)
    """
    # Referensi Bulan Baru: 6 Januari 2000
    ref_date = date(2000, 1, 6)
    diff_days = (tgl - ref_date).days
    
    synodic_cycle = 29.530588853
    phase = (diff_days % synodic_cycle) / synodic_cycle
    return phase

def fraksi_iluminasi_bulan(tgl: date) -> float:
    """
    Menghitung fraksi iluminasi bulan (0.0 - 1.0).
    0.0 = Gelap total (Bulan Baru)
    1.0 = Terang total (Bulan Purnama)
    """
    phase = hitung_fase_bulan(tgl)
    # Formula pendekatan ilmiah: (1 - cos(2 * pi * phase)) / 2
    fraction = (1.0 - math.cos(2 * math.pi * phase)) / 2.0
    return fraction

def skor_fase_bulan(tgl: date) -> float:
    """
    Mengembalikan skor fase bulan untuk scoring.
    """
    return fraksi_iluminasi_bulan(tgl)
