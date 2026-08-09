from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from core.config import get_settings
from models.sos import SosSignal, PushToken
from models.laporan import LaporanTangkapan

settings = get_settings()

class SosDispatch:
    def __init__(self):
        self.client = None
        self.initialized = False
        
        if not settings.MOCK_EXTERNAL and settings.EXPO_ACCESS_TOKEN:
            try:
                from exponent_server_sdk import PushClient
                # Inisialisasi Expo Push client
                self.client = PushClient(access_token=settings.EXPO_ACCESS_TOKEN)
                self.initialized = True
            except Exception as e:
                print(f"Gagal menginisialisasi Expo Push SDK: {e}. Notifikasi SOS berjalan dalam mode mock log.")

    def notify_nearby(self, sos: SosSignal, db: Session) -> int:
        """
        Mengirim notifikasi darurat SOS ke nelayan lain dalam radius tertentu (mis. 10km)
        dari lokasi kejadian. Lokasi nelayan lain dinilai dari laporan tangkapan terakhir mereka.
        """
        # 1. Cari lokasi laporan terakhir dari setiap nelayan
        # Subquery untuk mendapatkan waktu laporan terakhir per nelayan
        subq = db.query(
            LaporanTangkapan.nelayan_id,
            func.max(LaporanTangkapan.waktu).label("max_waktu")
        ).group_by(LaporanTangkapan.nelayan_id).subquery()

        # Query token dari nelayan yang laporan terakhirnya berada dalam radius SOS_RADIUS_KM (meter = km * 1000)
        query = db.query(PushToken.expo_push_token).join(
            LaporanTangkapan, LaporanTangkapan.nelayan_id == PushToken.nelayan_id
        ).join(
            subq, 
            (LaporanTangkapan.nelayan_id == subq.c.nelayan_id) & 
            (LaporanTangkapan.waktu == subq.c.max_waktu)
        ).filter(
            # ST_DWithin menerima geography/geometry dan jarak dalam meter
            func.ST_DWithin(LaporanTangkapan.lokasi, sos.lokasi, settings.SOS_RADIUS_KM * 1000.0)
        )
        
        if sos.nelayan_id:
            query = query.filter(PushToken.nelayan_id != sos.nelayan_id)
            
        nearby_tokens = [r[0] for r in query.all()]
        
        # Fallback jika tidak ada laporan spasial, broadcast ke seluruh nelayan terdaftar (kecuali pengirim) untuk keselamatan
        if not nearby_tokens:
            fallback_query = db.query(PushToken.expo_push_token)
            if sos.nelayan_id:
                fallback_query = fallback_query.filter(PushToken.nelayan_id != sos.nelayan_id)
            nearby_tokens = [r[0] for r in fallback_query.all()]

        if not nearby_tokens:
            print("Tidak ada push token nelayan lain ditemukan untuk menerima SOS.")
            return 0

        # Judul & Pesan SOS
        pesan_sos = sos.pesan or "Membutuhkan bantuan darurat segera!"
        judul = "🚨 SINYAL SOS DARURAT"
        body = f"Nelayan di koordinat terdekat memerlukan bantuan: {pesan_sos}"

        # 2. Kirim Notifikasi via Expo
        count = 0
        if settings.MOCK_EXTERNAL or not self.initialized or self.client is None:
            # Mode mock: Cukup log saja
            print(f"[SOS MOCK PUSH] Mengirim push ke {len(nearby_tokens)} token.")
            print(f"Detail: {judul} - {body}")
            return len(nearby_tokens)
            
        try:
            from exponent_server_sdk import PushMessage, PushServerError
            
            messages = []
            for token in nearby_tokens:
                messages.append(PushMessage(
                    to=token,
                    title=judul,
                    body=body,
                    data={"sos_id": str(sos.id), "lat": -0.899, "lng": 100.354} # dummy data GPS untuk trigger peta
                ))
            
            # Kirim notifikasi secara batch
            response = self.client.publish_multiple(messages)
            count = len(messages)
            print(f"Sukses mengirim {count} notifikasi SOS.")
        except Exception as e:
            print(f"Error saat mengirim Expo Push notification: {e}")
            
        return count
