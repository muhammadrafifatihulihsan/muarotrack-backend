import pytest
from models.nelayan import Nelayan

def test_pendaftaran_nelayan_success(client, db):
    payload = {
        "nama": "Pak Anto",
        "total_liter_biasa": 10.0,
        "jarak_km_biasa": 20.0
    }
    
    response = client.post("/nelayan", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["nama"] == "Pak Anto"
    # 10 / 20 = 0.5 bbm per km
    assert data["konsumsi_bbm_per_km"] == 0.5
    assert "id" in data
    
    # Pastikan data tersimpan di database
    nelayan = db.query(Nelayan).filter(Nelayan.id == data["id"]).first()
    assert nelayan is not None
    assert nelayan.nama == "Pak Anto"

def test_pendaftaran_nelayan_invalid_data(client):
    # Jarak 0 tidak diperbolehkan (ZeroDivision Error prevention)
    payload = {
        "nama": "Pak Anto",
        "total_liter_biasa": 10.0,
        "jarak_km_biasa": 0.0
    }
    response = client.post("/nelayan", json=payload)
    assert response.status_code == 422
