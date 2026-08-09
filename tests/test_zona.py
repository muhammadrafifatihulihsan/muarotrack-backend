from models.zona import ZonaRekomendasi

def test_ambil_zona_rekomendasi_success(client, db):
    # Seed stasiun kondisi laut default sudah ada dari conftest.
    # Grid zona kini dibangun DINAMIS dari posisi nelayan (bukan hardcode 9 titik).
    #
    # Posisi di Pantai Gajah Padang (bukan salah satu muara hardcode) ->
    # endpoint harus tetap menghasilkan rekomendasi di sekitarnya.
    lat = -0.9000
    lng = 100.3600

    response = client.get(f"/zona-rekomendasi?lat={lat}&lng={lng}&radius_km=22")
    assert response.status_code == 200

    data = response.json()
    zonas = data["zonas"]
    assert len(zonas) > 0

    # Semua zona memiliki peringkat 1..N dan diurutkan berdasarkan skor efektif.
    peringkat_list = [z["peringkat"] for z in zonas]
    assert peringkat_list == sorted(peringkat_list)
    assert peringkat_list[0] == 1

    # Semua zona dalam radius maksimum.
    for z in zonas:
        assert z["jarak_km"] <= 22.0
        assert "terdampak_sedimen" in z

    # Urutan tidak boleh menurun pada skor_efektif.
    skor_efektif_list = [z["skor_efektif"] for z in zonas]
    assert skor_efektif_list == sorted(skor_efektif_list, reverse=True)

def test_ambil_zona_rekomendasi_dengan_estimasi_bbm(client, db):
    # Dapatkan rekomendasi sekaligus estimasi BBM pulang-pergi.
    lat = -0.9000
    lng = 100.3600

    response = client.get(
        f"/zona-rekomendasi?lat={lat}&lng={lng}&radius_km=22&konsumsi_bbm_per_km=0.5"
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["zonas"]) > 0

    # Estimasi BBM = jarak_km * 0.5 * 2 (pulang-pergi).
    for z in data["zonas"]:
        assert z["estimasi_bbm_liter"] is not None
        expected = round(z["jarak_km"] * 0.5 * 2.0, 2)
        assert abs(z["estimasi_bbm_liter"] - expected) < 0.01
