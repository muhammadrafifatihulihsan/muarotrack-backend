import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from core.deps import get_db
from models.laporan import LaporanTangkapan
from schemas.laporan import (
    LaporanTeksCreate,
    LaporanOut,
    LaporanSuaraOut,
    LaporanBatchRequest,
)
from services.stt import SttService
from services.deepseek_client import DeepSeekClient

router = APIRouter(tags=["Laporan Tangkapan"])

# Inisialisasi service singleton/klien
stt_service = SttService()
deepseek_client = DeepSeekClient()

@router.post("/laporan/teks", response_model=LaporanOut, status_code=status.HTTP_201_CREATED)
def laporan_teks(schema: LaporanTeksCreate, db: Session = Depends(get_db)):
    """
    Mengirim laporan tangkapan nelayan menggunakan input teks manual dari form.
    """
    lokasi_wkt = f"SRID=4326;POINT({schema.lng} {schema.lat})"
    laporan = LaporanTangkapan(
        nelayan_id=schema.nelayan_id,
        lokasi=lokasi_wkt,
        jenis_ikan=schema.jenis_ikan,
        estimasi_kg=schema.estimasi_kg,
        catatan=schema.catatan,
        perlu_review=schema.jenis_ikan is None or schema.estimasi_kg is None,
        synced=True
    )
    
    db.add(laporan)
    db.commit()
    db.refresh(laporan)
    
    # Konversi untuk response
    point = to_shape(laporan.lokasi)
    return LaporanOut(
        id=laporan.id,
        nelayan_id=laporan.nelayan_id,
        lat=point.y,
        lng=point.x,
        jenis_ikan=laporan.jenis_ikan,
        estimasi_kg=laporan.estimasi_kg,
        catatan=laporan.catatan,
        perlu_review=laporan.perlu_review,
        waktu=laporan.waktu,
        synced=laporan.synced
    )

@router.post("/laporan/suara", response_model=LaporanSuaraOut, status_code=status.HTTP_201_CREATED)
async def laporan_suara(
    file: UploadFile = File(..., description="Berkas rekaman audio laporan suara"),
    nelayan_id: Optional[uuid.UUID] = Form(None),
    lat: float = Form(..., ge=-90, le=90),
    lng: float = Form(..., ge=-180, le=180),
    db: Session = Depends(get_db)
):
    """
    Mengunggah berkas suara laporan tangkapan nelayan.
    Backend akan menjalankan STT (Whisper) -> parsing AI (DeepSeek) -> menyimpan data terstruktur.
    Jika parsing gagal mendeteksi ikan/berat, laporan ditandai dengan perlu_review=true.
    """
    try:
        audio_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gagal membaca file audio: {e}"
        )
        
    # 1. Transkripsi suara ke teks menggunakan Whisper
    teks_transkripsi = stt_service.transkrip(audio_bytes)
    
    # 2. Parsing teks menjadi JSON terstruktur menggunakan DeepSeek
    parsed_data, perlu_review = deepseek_client.parse_laporan(teks_transkripsi)
    
    # 3. Simpan laporan ke database
    lokasi_wkt = f"SRID=4326;POINT({lng} {lat})"
    laporan = LaporanTangkapan(
        nelayan_id=nelayan_id,
        lokasi=lokasi_wkt,
        jenis_ikan=parsed_data.get("jenis_ikan"),
        estimasi_kg=parsed_data.get("estimasi_kg"),
        catatan=parsed_data.get("catatan"),
        perlu_review=perlu_review,
        synced=True
    )
    
    db.add(laporan)
    db.commit()
    db.refresh(laporan)
    
    return LaporanSuaraOut(
        id=laporan.id,
        jenis_ikan=laporan.jenis_ikan,
        estimasi_kg=laporan.estimasi_kg,
        catatan=laporan.catatan,
        perlu_review=laporan.perlu_review
    )

@router.post("/sync/laporan-batch", response_model=List[LaporanOut])
def laporan_batch(schema: LaporanBatchRequest, db: Session = Depends(get_db)):
    """
    Sinkronisasi massal untuk laporan-laporan offline yang tertunda di SQLite lokal.
    """
    saved_laporans = []
    for item in schema.laporan:
        # Jika id dikirim dari klien, gunakan id tersebut, jika tidak biarkan default uuid
        laporan_id = item.id if item.id else uuid.uuid4()
        lokasi_wkt = f"SRID=4326;POINT({item.lng} {item.lat})"
        
        laporan = LaporanTangkapan(
            id=laporan_id,
            nelayan_id=item.nelayan_id,
            lokasi=lokasi_wkt,
            jenis_ikan=item.jenis_ikan,
            estimasi_kg=item.estimasi_kg,
            catatan=item.catatan,
            perlu_review=item.perlu_review if item.perlu_review is not None else (item.jenis_ikan is None or item.estimasi_kg is None),
            synced=True
        )
        if item.waktu:
            laporan.waktu = item.waktu
            
        db.add(laporan)
        saved_laporans.append(laporan)
        
    db.commit()
    
    response_list = []
    for l in saved_laporans:
        db.refresh(l)
        point = to_shape(l.lokasi)
        response_list.append(LaporanOut(
            id=l.id,
            nelayan_id=l.nelayan_id,
            lat=point.y,
            lng=point.x,
            jenis_ikan=l.jenis_ikan,
            estimasi_kg=l.estimasi_kg,
            catatan=l.catatan,
            perlu_review=l.perlu_review,
            waktu=l.waktu,
            synced=l.synced
        ))
        
    return response_list
