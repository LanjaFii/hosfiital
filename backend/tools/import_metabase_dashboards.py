#!/usr/bin/env python3
"""Import Metabase dashboards from JSON exports in `backend/db/metabase_exports`.

Usage:
  METABASE_URL=http://localhost:3000 METABASE_USER=you@example.com METABASE_PASSWORD=secret \
    python backend/tools/import_metabase_dashboards.py --path backend/db/metabase_exports

Supports `METABASE_API_TOKEN` to skip login.
"""
from __future__ import annotations

import argparse
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

import httpx


def get_session_token(client: httpx.Client, url: str) -> str:
    token = os.environ.get("METABASE_API_TOKEN")
    if token:
        return token
    user = os.environ.get("METABASE_USER")
    pwd = os.environ.get("METABASE_PASSWORD")
    if not user or not pwd:
        raise RuntimeError("METABASE_API_TOKEN or METABASE_USER+METABASE_PASSWORD must be set")
    r = client.post(f"{url.rstrip('/')}/api/session", json={"username": user, "password": pwd}, timeout=30.0)
    r.raise_for_status()
    return r.json().get("id")


def create_card(client: httpx.Client, url: str, token: str, database_id: int, card: Dict[str, Any], dry_run: bool = False) -> int:
    body = {
        "name": card.get("name"),
        "dataset_query": {
            "type": card.get("type", "native"),
            "native": {"query": card.get("query")},
            "database": database_id,
        },
        "display": card.get("display"),
        "visualization_settings": {},
        "description": card.get("notes") or card.get("description"),
    }
    if dry_run:
        print("DRY RUN create card:", body)
        return -1
    headers = {"X-Metabase-Session": token}
    r = client.post(f"{url.rstrip('/')}/api/card", json=body, headers=headers, timeout=30.0)
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError:
        print("Error response from Metabase (create card):", r.status_code, r.text)
        raise
    return r.json()["id"]


def create_dashboard(client: httpx.Client, url: str, token: str, dash: Dict[str, Any], dry_run: bool = False) -> int:
    body = {"name": dash.get("name"), "description": dash.get("description")}
    if dry_run:
        print("DRY RUN create dashboard:", body)
        return -1
    headers = {"X-Metabase-Session": token}
    # try to find existing dashboard with same name
    try:
        existing = client.get(f"{url.rstrip('/')}/api/dashboard", headers=headers, timeout=30.0)
        if existing.status_code == 200:
            for d in existing.json():
                if d.get("name") == body["name"]:
                    print(f"Reusing existing dashboard {body['name']} -> id={d.get('id')}")
                    return d.get("id")
    except Exception:
        pass

    r = client.post(f"{url.rstrip('/')}/api/dashboard", json=body, headers=headers, timeout=30.0)
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError:
        print("Error response from Metabase (create dashboard):", r.status_code, r.text)
        raise
    return r.json()["id"]


def add_card_to_dashboard(client: httpx.Client, url: str, token: str, dashboard_id: int, card_id: int, row: int, col: int, sizeX: int = 4, sizeY: int = 4, dry_run: bool = False) -> None:
    body = {"cardId": card_id, "row": row, "col": col, "sizeX": sizeX, "sizeY": sizeY, "parameter_mappings": []}
    if dry_run:
        print(f"DRY RUN add card to dashboard {dashboard_id}:", body)
        return
    headers = {"X-Metabase-Session": token}
    r = client.post(f"{url.rstrip('/')}/api/dashboard/{dashboard_id}/cards", json=body, headers=headers, timeout=30.0)
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError:
        print(f"Error response from Metabase (add card to dashboard {dashboard_id}):", r.status_code, r.text)
        raise


def import_from_file(client: httpx.Client, url: str, token: str, path: Path, dry_run: bool = False) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    database_id = data.get("database_id")
    dash = data.get("dashboard")
    if not dash:
        print(f"No dashboard found in {path}")
        return

    cards = dash.get("cards", [])
    created_card_ids = []
    for i, c in enumerate(cards):
        try:
            cid = create_card(client, url, token, database_id, c, dry_run=dry_run)
            created_card_ids.append(cid)
            print(f"Created card {c.get('name')} -> id={cid}")
        except Exception as e:
            print(f"Failed to create card {c.get('name')}: {e}")

    try:
        dashboard_id = create_dashboard(client, url, token, dash, dry_run=dry_run)
        print(f"Created dashboard {dash.get('name')} -> id={dashboard_id}")
    except Exception as e:
        print(f"Failed to create dashboard {dash.get('name')}: {e}")
        return

    # fetch and show dashboard JSON for debugging API shape
    try:
        headers = {"X-Metabase-Session": token}
        resp = client.get(f"{url.rstrip('/')}/api/dashboard/{dashboard_id}", headers=headers, timeout=30.0)
        print(f"Dashboard {dashboard_id} fetch status:", resp.status_code)
        print(resp.text)
    except Exception as e:
        print(f"Failed to fetch dashboard {dashboard_id}: {e}")

    # add cards to dashboard with a simple grid layout
    row = 0
    col = 0
    max_cols = 3
    for cid in created_card_ids:
        try:
            add_card_to_dashboard(client, url, token, dashboard_id, cid, row=row, col=col, dry_run=dry_run)
            print(f"Added card id={cid} to dashboard id={dashboard_id} at row={row} col={col}")
        except Exception as e:
            print(f"Failed to add card {cid} to dashboard {dashboard_id}: {e}")
        col += 1
        if col >= max_cols:
            col = 0
            row += 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:]) if argv is None else argv
    p = argparse.ArgumentParser(description="Import Metabase dashboards from JSON exports")
    p.add_argument("--path", default="backend/db/metabase_exports", help="Path to the folder with exported dashboards")
    p.add_argument("--dry-run", action="store_true", help="Do not create resources, only show actions")
    args = p.parse_args(argv)

    url = os.environ.get("METABASE_URL", "http://localhost:3000")
    folder = Path(args.path)
    if not folder.exists():
        print(f"Path not found: {folder}")
        return 2

    client = httpx.Client()
    try:
        token = get_session_token(client, url)
    except Exception as e:
        print(f"Auth error: {e}")
        return 3

    for f in sorted(folder.glob("*.json")):
        print(f"Importing {f}")
        import_from_file(client, url, token, f, dry_run=args.dry_run)

    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
