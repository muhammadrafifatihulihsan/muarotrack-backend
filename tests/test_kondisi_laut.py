from models.kondisi_laut import KondisiLaut

def test_ambil_kondisi_laut_success(client, db):
    # Seeding stasiun kondisi laut kustom di koordinat UNIK
    # (menghindari bentrok unique constraint dengan 3 stasiun default dari conftest:
    #  POINT(100.3508 -0.8972), POINT(100.3167 -0.8256), POINT(100.3444 -0.8988))
    stasiun = KondisiLaut(
        lokasi="SRID=4326;POINT(100.2800 -0.8600)",
        gelombang_gabungan=[{"tinggi_m": 1.2}],
        cuaca_per_jam=[{"suhu_c": 27.5}],
        pasang_surut=[{"tipe": "pasang"}]
    )
    db.add(stasiun)
    db.commit()
    
    # Ambil kondisi laut untuk titik terdekat stasiun (jarak ~0 meter)
    response = client.get("/kondisi-laut?lat=-0.86&lng=100.28")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["gelombang_gabungan"]) == 1
    assert data["gelombang_gabungan"][0]["tinggi_m"] == 1.2
    assert data["cuaca_per_jam"][0]["suhu_c"] == 27.5
    assert data["pasang_surut"][0]["tipe"] == "pasang"
    
def test_ambil_kondisi_laut_not_found(client, db):
    # Bersihkan seluruh DB agar tidak ada stasiun sama sekali
    db.query(KondisiLaut).delete()
    db.commit()
    
    response = client.get("/kondisi-laut?lat=-5.0&lng=100.0")
    assert response.status_code == 404
