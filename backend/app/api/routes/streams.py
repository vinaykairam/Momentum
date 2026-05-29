from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.stream import Stream
from app.schemas.stream import StreamCreate, StreamResponse, StreamUpdate
from app.services.momentum_engine import update_stream_momentum

router = APIRouter(prefix="/streams", tags=["streams"])


@router.get("", response_model=list[StreamResponse])
def list_streams(db: Session = Depends(get_db)) -> list[Stream]:
    return db.query(Stream).order_by(Stream.name).all()


@router.post("", response_model=StreamResponse, status_code=status.HTTP_201_CREATED)
def create_stream(payload: StreamCreate, db: Session = Depends(get_db)) -> Stream:
    stream = Stream(**payload.model_dump())
    update_stream_momentum(stream, db)
    db.add(stream)
    db.commit()
    db.refresh(stream)
    return stream


@router.get("/{stream_id}", response_model=StreamResponse)
def get_stream(stream_id: int, db: Session = Depends(get_db)) -> Stream:
    stream = db.get(Stream, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream


@router.patch("/{stream_id}", response_model=StreamResponse)
def update_stream(stream_id: int, payload: StreamUpdate, db: Session = Depends(get_db)) -> Stream:
    stream = db.get(Stream, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(stream, key, value)

    update_stream_momentum(stream, db)
    db.commit()
    db.refresh(stream)
    return stream


@router.delete("/{stream_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stream(stream_id: int, db: Session = Depends(get_db)) -> None:
    stream = db.get(Stream, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    db.delete(stream)
    db.commit()
