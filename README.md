# AI-Based Disaster Relief Management System — Review 4 Demo

## Run
1. Open a terminal in this folder.
2. Run: `python server.py`
3. Open: http://127.0.0.1:8000
4. Login: `admin` / `admin123`

## Demonstrated workflow
Login → Dashboard → Add Incident → Assess Incident → Inventory → Allocation/Dispatch → Audit Log.

The demo is intentionally zero-dependency and uses SQLite so the reviewer can run it immediately. The project architecture and Review-3 specification use Python/Flask and MySQL/InnoDB; the API and relational schema mirror that design and can be migrated to MySQL for deployment.
