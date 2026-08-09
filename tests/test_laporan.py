import uuid
import pytest
from models.laporan import LaporanTangkapan

def test_laporan_teks_success(client, db):
    payload = {
        "nelayan_id": None,
        "lat": -0.8972,
        "lng": 100.3508,
        "jenis_ikan": "Tongkol",
        "estimasi_kg": 15.5,
        "catatan": "Melaut lancar"
    }
    
    response = client.post("/laporan/teks", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["jenis_ikan"] == "Tongkol"
    assert data["estimasi_kg"] == 15.5
    assert data["lat"] == -0.8972
    assert data["lng"] == 100.3508
    assert data["perlu_review"] is False
    
    # Cek DB
    lap = db.query(LaporanTangkapan).filter(LaporanTangkapan.id == data["id"]).first()
    assert lap is not None
    assert lap.jenis_ikan == "Tongkol"

def test_laporan_suara_success(client, db):
    # Buat file audio dummy
    audio_data = b"RIFF....WAVEfmt ....data...."
    
    form_data = {
        "lat": -0.8988,
        "lng": 100.3444
    }
    
    files = {
        "file": ("test_report.wav", audio_data, "audio/wav")
    }
    
    response = client.post("/laporan/suara", data=form_data, files=files)
    assert response.status_code == 201
    
    data = response.json()
    # Mock STT menghasilkan: kembung, 25 kg
    assert data["jenis_ikan"] == "Kembung"
    assert data["estimasi_kg"] == 25.0
    assert data["perlu_review"] is False

def test_laporan_batch_sync_success(client, db):
    payload = {
        "laporan": [
            {
                "id": str(uuid.uuid4()),
                "nelayan_id": None,
                "lat": -0.8256,
                "lng": 100.3167,
                "jenis_ikan": "Tuna",
                "estimasi_kg": 50.0,
                "catatan": "Offline report 1",
                "waktu": "2026-08-08T00:00:00Z"
            },
            {
                "id": str(uuid.uuid4()),
                "nelayan_id": None,
                "lat": -0.8972,
                "lng": 100.3508,
                "jenis_ikan": None,
                "estimasi_kg": None,
                "catatan": "Offline report 2 gagal tangkap",
                "waktu": "2026-08-08T01:00:00Z"
            }
        ]
    }
    
    response = client.post("/sync/laporan-batch", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2
    assert data[0]["jenis_ikan"] == "Tuna"
    assert data[0]["perlu_review"] is False
    assert data[1]["jenis_ikan"] is None
    assert data[1]["perlu_review"] is True
    
    # Pastikan kedua laporan masuk ke DB
    db_count = db.query(LaporanTangkapan).count()
    assert db_count >= 2
