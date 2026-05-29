from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.stream import Stream
from app.schemas.stream import StreamCreate, StreamResponse, StreamUpdate
from app.services.momentum_engine import refresh_all_stream_momentum

router = APIRouter(prefix="/streams", tags=["streams"])


@router.get("", response_model=list[StreamResponse])
def list_streams(db: Session = Depends(get_db)) -> list[Stream]:
    return db.query(Stream).order_by(Stream.name).all()


@router.post("", response_model=StreamResponse, status_code=status.HTTP_201_CREATED)
def create_stream(payload: StreamCreate, db: Session = Depends(get_db)) -> Stream:
    data = payload.model_dump()

    if payload.parent_id is not None:
        parent = db.get(Stream, payload.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent stream not found")
        if parent.parent_id is not None:
            raise HTTPException(status_code=400, detail="Sub-streams can only be added to main streams")
        data["category"] = parent.category
        data["type"] = parent.type

    stream = Stream(**data)
    db.add(stream)
    db.commit()
    db.refresh(stream)
    refresh_all_stream_momentum(db)
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

    updates = payload.model_dump(exclude_unset=True)

    if stream.parent_id is not None:
        updates.pop("category", None)
        updates.pop("parent_id", None)

    if "parent_id" in updates and updates["parent_id"] is not None:
        if stream.parent_id is None:
            has_children = db.query(Stream).filter(Stream.parent_id == stream.id).count() > 0
            if has_children:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot reparent a stream that has sub-streams",
                )
        parent = db.get(Stream, updates["parent_id"])
        if not parent:
            raise HTTPException(status_code=404, detail="Parent stream not found")
        if parent.parent_id is not None:
            raise HTTPException(status_code=400, detail="Sub-streams can only be added to main streams")

    category_changed = "category" in updates and stream.parent_id is None

    for key, value in updates.items():
        setattr(stream, key, value)

    if category_changed:
        children = db.query(Stream).filter(Stream.parent_id == stream.id).all()
        for child in children:
            child.category = stream.category

    refresh_all_stream_momentum(db)
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
