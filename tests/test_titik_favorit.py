import uuid
from models.nelayan import Nelayan
from models.titik_favorit import TitikFavorit

def test_titik_favorit_flow(client, db):
    # Buat nelayan
    nelayan = Nelayan(nama="Nelayan Uji", konsumsi_bbm_per_km=0.5)
    db.add(nelayan)
    db.commit()
    db.refresh(nelayan)
    
    # 1. Simpan Titik Favorit
    payload = {
        "nelayan_id": str(nelayan.id),
        "nama_label": "Sarang Ikan Layur",
        "lat": -0.8988,
        "lng": 100.3444,
        "catatan": "Kedalaman sedang, banyak karang"
    }
    
    response = client.post("/titik-favorit", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["nama_label"] == "Sarang Ikan Layur"
    assert data["lat"] == -0.8988
    assert data["lng"] == 100.3444
    assert data["catatan"] == "Kedalaman sedang, banyak karang"
    
    # 2. Ambil Daftar Titik Favorit Nelayan
    list_response = client.get(f"/titik-favorit?nelayan_id={nelayan.id}")
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert len(list_data) == 1
    assert list_data[0]["nama_label"] == "Sarang Ikan Layur"
