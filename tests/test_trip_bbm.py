import uuid
from models.trip_bbm import TripBbm
from models.nelayan import Nelayan

def test_trip_bbm_create_success(client, db):
    # Buat nelayan terlebih dahulu
    nelayan = Nelayan(nama="Pak Budiman", konsumsi_bbm_per_km=0.6)
    db.add(nelayan)
    db.commit()
    db.refresh(nelayan)
    
    payload = {
        "nelayan_id": str(nelayan.id),
        "jarak_km": 15.0,
        "prediksi_liter": 18.0,
        "liter_aktual": 20.0
    }
    
    response = client.post("/trip-bbm", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["jarak_km"] == 15.0
    assert data["prediksi_liter"] == 18.0
    assert data["liter_aktual"] == 20.0
    
    # Cek DB
    trip = db.query(TripBbm).filter(TripBbm.id == data["id"]).first()
    assert trip is not None
    assert trip.nelayan_id == nelayan.id
