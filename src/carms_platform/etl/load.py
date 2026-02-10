# src/carms_platform/etl/load.py
from __future__ import annotations

import json, zipfile, hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, SQLModel

from carms_platform.db import engine
from carms_platform.models import Discipline, ProgramStream, ProgramDescriptionArtifact

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()

def read_json_from_zip(zip_path: Path, member: str):
    with zipfile.ZipFile(zip_path) as zf:
        raw = zf.read(member).decode("utf-8", errors="replace")
    return json.loads(raw)

def ensure_tables() -> None:
    SQLModel.metadata.create_all(engine)

def upsert_rows(session: Session, table, rows: list[dict], conflict_cols: list[str], update_cols: list[str]) -> None:
    if not rows:
        return

    ins = pg_insert(table).values(rows)
    update_map = {c: getattr(ins.excluded, c) for c in update_cols}

    stmt = ins.on_conflict_do_update(
        index_elements=conflict_cols,
        set_=update_map,
    )
    session.exec(stmt)

def load_core(match_cycle_id: int, data_raw: Path) -> None:
    """Load discipline + program_stream from Excel."""
    discipline_df = pd.read_excel(data_raw / "1503_discipline.xlsx")
    program_df = pd.read_excel(data_raw / "1503_program_master.xlsx")

    row_index_col = next((c for c in program_df.columns if str(c).strip().lower().startswith("unnamed")), None)

    disc_rows = [
        {"discipline_id": int(r["discipline_id"]), "discipline": str(r["discipline"])}
        for _, r in discipline_df.iterrows()
    ]

    prog_rows = []
    for _, r in program_df.iterrows():
        prog_rows.append({
            "program_stream_id": int(r["program_stream_id"]),
            "match_cycle_id": match_cycle_id,
            "discipline_id": int(r["discipline_id"]) if pd.notna(r["discipline_id"]) else None,
            "discipline_name": str(r["discipline_name"]) if pd.notna(r["discipline_name"]) else None,
            "school_id": int(r["school_id"]) if pd.notna(r["school_id"]) else None,
            "school_name": str(r["school_name"]) if pd.notna(r["school_name"]) else None,
            "program_stream_name": str(r["program_stream_name"]) if pd.notna(r["program_stream_name"]) else None,
            "program_site": str(r["program_site"]) if pd.notna(r["program_site"]) else None,
            "program_stream": str(r["program_stream"]) if pd.notna(r["program_stream"]) else None,
            "program_name": str(r["program_name"]) if pd.notna(r["program_name"]) else None,
            "program_url": str(r["program_url"]) if pd.notna(r["program_url"]) else None,
            "row_index": int(r[row_index_col]) if row_index_col and pd.notna(r[row_index_col]) else None,
        })

    with Session(engine) as session:
        upsert_rows(session, Discipline.__table__, disc_rows, ["discipline_id"], ["discipline"])
        upsert_rows(
            session,
            ProgramStream.__table__,
            prog_rows,
            ["program_stream_id"],
            [
                "match_cycle_id","discipline_id","discipline_name","school_id","school_name",
                "program_stream_name","program_site","program_stream","program_name","program_url","row_index"
            ],
        )
        session.commit()

def load_representation_markdown_v2(match_cycle_id: int, data_raw: Path) -> int:
    zip_path = data_raw / "1503_markdown_program_descriptions_v2.zip"
    records = read_json_from_zip(zip_path, "1503_markdown_program_descriptions_v2.json")

    rows = []
    for rec in records:
        vid = rec.get("id")
        if not vid:
            continue
        doc_id = vid.replace("|", "-")
        program_stream_id = int(doc_id.split("-")[1])
        content = rec.get("page_content", "")
        rows.append({
            "doc_id": doc_id,
            "match_cycle_id": match_cycle_id,
            "program_stream_id": program_stream_id,
            "representation": "markdown_v2",
            "source_file": zip_path.name,
            "content": content,
            "content_sha256": sha256_text(content),
            "ingested_at": datetime.now(timezone.utc),
        })

    with Session(engine) as session:
        upsert_rows(
            session,
            ProgramDescriptionArtifact.__table__,
            rows,
            ["doc_id","representation"],
            ["match_cycle_id","program_stream_id","source_file","content","content_sha256","ingested_at"],
        )
        session.commit()
    return len(rows)

def load_representation_html_v2(match_cycle_id: int, data_raw: Path) -> int:
    zip_path = data_raw / "1503_program_descriptions_v2.zip"
    records = read_json_from_zip(zip_path, "1503_program_descriptions_v2.json")

    rows = []
    for rec in records:
        vid = rec.get("id")
        if not vid:
            continue
        doc_id = vid.replace("|", "-")
        program_stream_id = int(doc_id.split("-")[1])
        content = rec.get("page_content", "")
        rows.append({
            "doc_id": doc_id,
            "match_cycle_id": match_cycle_id,
            "program_stream_id": program_stream_id,
            "representation": "html_v2",
            "source_file": zip_path.name,
            "content": content,
            "content_sha256": sha256_text(content),
            "ingested_at": datetime.now(timezone.utc),
        })

    with Session(engine) as session:
        upsert_rows(
            session,
            ProgramDescriptionArtifact.__table__,
            rows,
            ["doc_id","representation"],
            ["match_cycle_id","program_stream_id","source_file","content","content_sha256","ingested_at"],
        )
        session.commit()
    return len(rows)

def load_representation_markdown_enriched(match_cycle_id: int, data_raw: Path) -> int:
    zip_path = data_raw / "program_descriptions.zip"

    rows = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if not name.endswith(".md"):
                continue
            doc_id = name[:-3]
            program_stream_id = int(doc_id.split("-")[1])
            content = zf.read(name).decode("utf-8", errors="replace")
            rows.append({
                "doc_id": doc_id,
                "match_cycle_id": match_cycle_id,
                "program_stream_id": program_stream_id,
                "representation": "markdown_enriched",
                "source_file": zip_path.name,
                "content": content,
                "content_sha256": sha256_text(content),
                "ingested_at": datetime.now(timezone.utc),
            })

    with Session(engine) as session:
        upsert_rows(
            session,
            ProgramDescriptionArtifact.__table__,
            rows,
            ["doc_id","representation"],
            ["match_cycle_id","program_stream_id","source_file","content","content_sha256","ingested_at"],
        )
        session.commit()
    return len(rows)

def load_representation_x_section(match_cycle_id: int, data_raw: Path) -> int:
    zip_path = data_raw / "1503_program_descriptions_x_section.zip"
    with zipfile.ZipFile(zip_path) as zf:
        df = pd.read_csv(zf.open("1503_program_descriptions_x_section.csv"))

    rows = []
    for _, r in df.iterrows():
        doc_id = str(r["document_id"])
        program_stream_id = int(doc_id.split("-")[1])
        content = r.to_json()
        rows.append({
            "doc_id": doc_id,
            "match_cycle_id": match_cycle_id,
            "program_stream_id": program_stream_id,
            "representation": "x_section",
            "source_file": zip_path.name,
            "content": content,
            "content_sha256": sha256_text(content),
            "ingested_at": datetime.now(timezone.utc),
        })

    with Session(engine) as session:
        upsert_rows(
            session,
            ProgramDescriptionArtifact.__table__,
            rows,
            ["doc_id","representation"],
            ["match_cycle_id","program_stream_id","source_file","content","content_sha256","ingested_at"],
        )
        session.commit()
    return len(rows)

def create_or_replace_views() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
        create or replace view v_program_description_canonical as
        select distinct on (program_stream_id)
            program_stream_id,
            doc_id,
            match_cycle_id,
            representation,
            content
        from program_description_artifact
        where representation in ('markdown_v2', 'markdown_enriched', 'html_v2')
        order by
            program_stream_id,
            case representation
                when 'markdown_v2' then 1
                when 'markdown_enriched' then 2
                when 'html_v2' then 3
                else 99
            end;
        """))

def load_all(match_cycle_id: int, data_raw: Path) -> dict[str, int]:
    ensure_tables()
    load_core(match_cycle_id, data_raw)
    n_md = load_representation_markdown_v2(match_cycle_id, data_raw)
    n_html = load_representation_html_v2(match_cycle_id, data_raw)
    n_en = load_representation_markdown_enriched(match_cycle_id, data_raw)
    n_x = load_representation_x_section(match_cycle_id, data_raw)
    create_or_replace_views()
    return {"markdown_v2": n_md, "html_v2": n_html, "markdown_enriched": n_en, "x_section": n_x}
