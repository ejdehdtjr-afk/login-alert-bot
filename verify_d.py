"""D1-D5: real local API requests and a direct, read-only MySQL query."""
import argparse
import json
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values
from sqlalchemy import create_engine, text


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=Path, default=Path(__file__).parent / "_7_board_test" / ".env")
    args = parser.parse_args()
    config = dotenv_values(args.env)
    student = (config.get("STUDENT") or "").strip()
    key = config.get("SECURITY_API_KEY")
    database = config.get("DATABASE_URL")
    if not all((student, key, database)):
        print("Missing STUDENT, SECURITY_API_KEY or DATABASE_URL in local .env")
        return 1
    endpoint = "http://127.0.0.1:5000/api/security/events"
    payload = {"student": student, "src_ip": "203.0.113.10", "decision": "deny",
               "severity": "High", "reason": "D evidence: level 10 -> deny",
               "fail_count": 1, "source": "submission_api_check"}
    print(f"D1-D5 LIVE CHECK | student={student}")
    print("This run adds two API-test records; it is not an n8n execution.")

    def post(label, data, auth, expected):
        response = requests.post(endpoint, json=data,
                                 headers={"X-API-Key": auth} if auth else {},
                                 timeout=10, allow_redirects=False)
        print(f"{label}: HTTP {response.status_code} (expected {expected})")
        if response.status_code != expected:
            raise ValueError("Unexpected HTTP status")
        return response.json()

    post("D1 POST no key", payload, None, 401)
    post("D1 POST wrong key", payload, "invalid-evidence-key", 401)
    post("D2 POST missing student", {k: v for k, v in payload.items() if k != "student"}, key, 400)
    deny = post("D3 POST deny", payload, key, 201)
    allow_payload = dict(payload, src_ip="203.0.113.11", decision="allow",
                         severity="Low", reason="D evidence: level 3 -> allow")
    allow = post("D3 POST allow", allow_payload, key, 201)
    ids = [deny["id"], allow["id"]]
    print(f"D3 returned IDs: deny={ids[0]}, allow={ids[1]}")
    query = ("SELECT id, student, src_ip, decision, severity FROM security_events "
             "WHERE student=:student AND id IN (:deny_id,:allow_id) ORDER BY id")
    engine = create_engine(database, hide_parameters=True)
    try:
        if engine.dialect.name != "mysql":
            raise ValueError("MySQL required")
        with engine.connect() as conn:
            rows = conn.execute(text(query), {"student": student, "deny_id": ids[0],
                                              "allow_id": ids[1]}).mappings().all()
        print("D4 MYSQL SQL: " + query)
        print(f"   params: student={student}, deny_id={ids[0]}, allow_id={ids[1]}")
        print("id | student | src_ip | decision | severity")
        for row in rows:
            print(" | ".join(str(row[k]) for k in ["id", "student", "src_ip", "decision", "severity"]))
        if len(rows) != 2 or {r["decision"] for r in rows} != {"allow", "deny"}:
            raise ValueError("SQL result mismatch")
    finally:
        engine.dispose()
    response = requests.get(endpoint, params={"student": student, "limit": 100}, timeout=10)
    if response.status_code != 200:
        raise ValueError("GET failed")
    data = response.json()
    selected = [{k: e[k] for k in ["id", "student", "decision", "severity"]}
                for e in data["events"] if e["id"] in ids]
    if len(selected) != 2:
        raise ValueError("GET result mismatch")
    print(f"D5 GET /api/security/events?student={student}: HTTP {response.status_code}")
    print("GET response excerpt (only this run's IDs; other fields omitted):")
    print(json.dumps({"count": data["count"], "events_excerpt": selected}, ensure_ascii=False))
    print("PASS: D1-D5 | Keep the separate n8n 201 screenshot for D6.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAILED ({type(exc).__name__}). Details withheld to protect credentials.")
        raise SystemExit(1)
