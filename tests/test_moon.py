from datetime import date
from services.moon import hitung_fase_bulan, fraksi_iluminasi_bulan, skor_fase_bulan

def test_moon_phase_ranges():
    # Menguji fase bulan untuk beberapa tanggal berbeda, nilainya harus berada dalam rentang 0-1
    dates_to_test = [
        date(2026, 8, 8),
        date(2026, 8, 20),
        date(2026, 9, 1),
        date(2026, 12, 25)
    ]
    for d in dates_to_test:
        phase = hitung_fase_bulan(d)
        fraction = fraksi_iluminasi_bulan(d)
        score = skor_fase_bulan(d)
        
        assert 0.0 <= phase <= 1.0
        assert 0.0 <= fraction <= 1.0
        assert 0.0 <= score <= 1.0
