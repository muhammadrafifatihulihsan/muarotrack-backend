import uuid
from models.nelayan import Nelayan
from models.sos import SosSignal, PushToken

def test_sos_signal_and_push_token_flow(client, db):
    # Buat dua nelayan: pengirim SOS (Pak A) dan penerima SOS (Pak B)
    nelayan_a = Nelayan(nama="Pak A", konsumsi_bbm_per_km=0.5)
    nelayan_b = Nelayan(nama="Pak B", konsumsi_bbm_per_km=0.5)
    db.add_all([nelayan_a, nelayan_b])
    db.commit()
    db.refresh(nelayan_a)
    db.refresh(nelayan_b)
    
    # Daftarkan push token untuk Pak B
    token_payload = {
        "nelayan_id": str(nelayan_b.id),
        "expo_push_token": "ExponentPushToken[12345Test]"
    }
    token_response = client.post("/push-token", json=token_payload)
    assert token_response.status_code == 200
    
    # Seeding Laporan Tangkapan terakhir untuk Pak B sebagai penentu lokasi terbarunya (agar masuk radius SOS)
    from models.laporan import LaporanTangkapan
    laporan_b = LaporanTangkapan(
        nelayan_id=nelayan_b.id,
        lokasi="SRID=4326;POINT(100.3508 -0.8972)",  # Dekat dengan lokasi SOS
        jenis_ikan="Tuna",
        estimasi_kg=10.0,
        synced=True
    )
    db.add(laporan_b)
    db.commit()

    # 1. Pak A Mengirim Sinyal SOS Darurat di koordinat yang dekat
    sos_payload = {
        "nelayan_id": str(nelayan_a.id),
        "lat": -0.8972,
        "lng": 100.3508,
        "pesan": "Kapal bocor di muara!",
        "waktu_kejadian": "2026-08-08T09:00:00Z"
    }
    
    sos_response = client.post("/sos", json=sos_payload)
    assert sos_response.status_code == 201
    sos_data = sos_response.json()
    assert sos_data["status"] == "terkirim"
    assert sos_data["pesan"] == "Kapal bocor di muara!"
    
    # 2. Pak B Mengambil SOS Aktif di Peta
    aktif_response = client.get("/sos/aktif?lat=-0.8972&lng=100.3508&radius_km=10")
    assert aktif_response.status_code == 200
    aktif_data = aktif_response.json()
    assert len(aktif_data) == 1
    assert aktif_data[0]["pesan"] == "Kapal bocor di muara!"
