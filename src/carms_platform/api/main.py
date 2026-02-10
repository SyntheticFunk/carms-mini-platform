# src/carms_platform/api/main.py
from __future__ import annotations

from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import text

from carms_platform.db import engine

app = FastAPI(title="CaRMS Mini Platform", version="0.1.0")

@app.get("/health")
def health():
    with engine.begin() as conn:
        ok = conn.execute(text("select 1")).scalar()
        counts = conn.execute(text("""
            select
              (select count(*) from discipline) as disciplines,
              (select count(*) from program_stream) as program_streams,
              (select count(*) from program_description_artifact) as artifacts,
              (select count(*) from v_program_description_canonical) as canonical
        """)).mappings().one()
    return {"ok": bool(ok == 1), "counts": dict(counts)}

@app.get("/program-streams")
def list_program_streams(
    discipline_id: Optional[int] = None,
    school_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
):
    sql = """
    select program_stream_id, match_cycle_id, discipline_id, discipline_name, school_id, school_name, program_name, program_url
    from program_stream
    where (:discipline_id is null or discipline_id = :discipline_id)
      and (:school_id is null or school_id = :school_id)
    order by school_name, discipline_name, program_stream_id
    limit :limit
    """
    with engine.begin() as conn:
        rows = conn.execute(text(sql), {"discipline_id": discipline_id, "school_id": school_id, "limit": limit}).mappings().all()
    return {"items": [dict(r) for r in rows]}

@app.get("/program-streams/{program_stream_id}")
def get_program_stream(program_stream_id: int):
    with engine.begin() as conn:
        row = conn.execute(
            text("select * from program_stream where program_stream_id = :id"),
            {"id": program_stream_id}
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="program_stream_id not found")
    return dict(row)

@app.get("/program-streams/{program_stream_id}/description")
def get_description(program_stream_id: int):
    with engine.begin() as conn:
        row = conn.execute(
            text("""
            select program_stream_id, doc_id, representation, content
            from v_program_description_canonical
            where program_stream_id = :id
            """),
            {"id": program_stream_id}
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="description not found")
    return dict(row)

@app.get("/search")
def search(q: str = Query(..., min_length=2), limit: int = Query(25, ge=1, le=200)):
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
            select p.program_stream_id, p.school_name, p.discipline_name, p.program_name
            from program_stream p
            join v_program_description_canonical v using (program_stream_id)
            where v.content ilike :pattern
            order by p.school_name, p.discipline_name
            limit :limit
            """),
            {"pattern": f"%{q}%", "limit": limit}
        ).mappings().all()
    return {"q": q, "items": [dict(r) for r in rows]}
