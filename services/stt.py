import os
import tempfile
from core.config import get_settings

settings = get_settings()

class SttService:
    def __init__(self):
        self.model = None
        self.initialized = False
        
        # Load faster-whisper only if NOT in mock mode
        if not settings.MOCK_EXTERNAL:
            try:
                from faster_whisper import WhisperModel
                # Menggunakan CPU secara default karena dijalankan secara lokal di PC pengguna
                self.model = WhisperModel(settings.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
                self.initialized = True
            except Exception as e:
                print(f"Gagal menginisialisasi faster-whisper: {e}. STT berjalan dalam mode mock.")
                self.initialized = False

    def transkrip(self, audio_bytes: bytes) -> str:
        """
        Menerjemahkan berkas audio (bytes) menjadi teks menggunakan faster-whisper.
        Jika MOCK_EXTERNAL=true atau inisialisasi gagal, kembalikan teks tiruan yang relevan.
        """
        if settings.MOCK_EXTERNAL or not self.initialized or self.model is None:
            return (
                "Saya hari ini melaut sejauh sepuluh kilometer ke arah barat daya "
                "dan berhasil menangkap ikan kembung sekitar dua puluh lima kilogram. "
                "Cuaca di laut cukup berombak."
            )

        try:
            # Simpan bytes ke file temporer agar bisa dibaca oleh faster-whisper
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                temp_audio.write(audio_bytes)
                temp_audio_path = temp_audio.name

            try:
                segments, info = self.model.transcribe(temp_audio_path, beam_size=5, language="id")
                teks_hasil = " ".join([segment.text for segment in segments])
                return teks_hasil.strip()
            finally:
                # Pastikan file temporer dihapus setelah selesai
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
                    
        except Exception as e:
            print(f"Gagal melakukan transkripsi Whisper: {e}")
            return "Gagal merekam suara. Mohon gunakan input teks manual."
        
        return ""
