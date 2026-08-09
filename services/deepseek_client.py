import re
import json
from typing import Dict, Any, Tuple
from core.config import get_settings

settings = get_settings()

class DeepSeekClient:
    def __init__(self):
        self.client = None
        if not settings.MOCK_EXTERNAL and settings.DEEPSEEK_API_KEY:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url="https://api.deepseek.com/v1"  # DeepSeek standard base URL
                )
            except Exception as e:
                print(f"Gagal menginisialisasi OpenAI SDK untuk DeepSeek: {e}. Mengaktifkan fallback lokal.")

    def parse_laporan(self, teks: str) -> Tuple[Dict[str, Any], bool]:
        """
        Menganalisis teks laporan nelayan (transkripsi) menggunakan DeepSeek API
        untuk mengonversinya menjadi data terstruktur (jenis_ikan, estimasi_kg, catatan).
        Mengembalikan tuple: (data_parsed, perlu_review).
        """
        if settings.MOCK_EXTERNAL or self.client is None:
            return self._parse_laporan_lokal(teks)

        system_prompt = (
            "Anda adalah AI yang bertugas mengekstrak laporan tangkapan nelayan pesisir Padang "
            "menjadi format JSON terstruktur. "
            "Ekstrak kunci berikut:\n"
            "- jenis_ikan (String: nama ikan dalam bahasa Indonesia, misal: Tongkol, Kembung, Tuna)\n"
            "- estimasi_kg (Number: angka berat tangkapan dalam kilogram saja)\n"
            "- catatan (String: keluhan, cuaca, atau catatan operasional penting)\n\n"
            "Format output HARUS berupa JSON murni dengan format:\n"
            "{\n"
            "  \"jenis_ikan\": \"NamaIkan\",\n"
            "  \"estimasi_kg\": 25.0,\n"
            "  \"catatan\": \"Teks catatan\"\n"
            "}\n"
            "Jika jenis ikan atau berat tidak ditemukan, beri nilai null."
        )

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat", # deepseek-v4-flash alias chat
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": teks}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            parsed = json.loads(content)
            
            jenis_ikan = parsed.get("jenis_ikan")
            estimasi_kg = parsed.get("estimasi_kg")
            catatan = parsed.get("catatan") or teks
            
            # Tentukan apakah perlu ditinjau ulang (jika salah satu parameter utama kosong)
            perlu_review = jenis_ikan is None or estimasi_kg is None
            
            return {
                "jenis_ikan": jenis_ikan,
                "estimasi_kg": float(estimasi_kg) if estimasi_kg is not None else None,
                "catatan": catatan
            }, perlu_review

        except Exception as e:
            print(f"Error memanggil DeepSeek API: {e}. Mengaktifkan fallback parsing lokal.")
            return self._parse_laporan_lokal(teks)

    def _parse_laporan_lokal(self, teks: str) -> Tuple[Dict[str, Any], bool]:
        """
        Parser lokal sederhana berbasis kata kunci dan regex untuk transkripsi audio.
        """
        teks_lower = teks.lower()
        
        # 1. Ekstrak Jenis Ikan (Bahasa Indonesia / Dialek Lokal Padang)
        daftar_ikan = ["kembung", "tongkol", "tuna", "tenggiri", "kakap", "kerapu", "teri", "selar", "layang", "sarden"]
        jenis_ikan = None
        for ikan in daftar_ikan:
            if ikan in teks_lower:
                jenis_ikan = ikan.capitalize()
                break

        # 2. Ekstrak Berat dalam kg
        # Cari angka terdekat sebelum kata kg/kilo/kilogram
        estimasi_kg = None
        match = re.search(r'(\d+)\s*(?:kg|kilo|kilogram)', teks_lower)
        if match:
            estimasi_kg = float(match.group(1))
        else:
            # Fallback pencarian kata bilangan bahasa Indonesia.
            # Urutkan dari kata TERPANJANG dulu agar frasa seperti "dua puluh lima"
            # dicocokkan sebelum "dua" (karena "dua" adalah substring dari frasa tersebut).
            angka_map = {
                "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5,
                "enam": 6, "tujuh": 7, "delapan": 8, "sembilan": 9, "sepuluh": 10,
                "sebelas": 11, "dua puluh": 20, "dua puluh lima": 25, "tiga puluh": 30,
                "empat puluh": 40, "lima puluh": 50, "seratus": 100
            }
            # Sortir berdasarkan panjang kata (descending) agar frasa multi-kata menang
            for kata in sorted(angka_map, key=len, reverse=True):
                if kata in teks_lower:
                    estimasi_kg = float(angka_map[kata])
                    break

        perlu_review = jenis_ikan is None or estimasi_kg is None
        
        return {
            "jenis_ikan": jenis_ikan,
            "estimasi_kg": estimasi_kg,
            "catatan": teks
        }, perlu_review
