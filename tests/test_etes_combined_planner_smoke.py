import importlib.util
import sys
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "external" / "etes-werkstattplaner" / "source" / "app"
sys.path.insert(0, str(APP))

spec = importlib.util.spec_from_file_location("etes_combined_server", APP / "server.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

def test_combined_planner_initializes_database():
    with tempfile.TemporaryDirectory() as td:
        server.DB_PATH = Path(td) / "planner.sqlite"
        server.init_db()
        con = server.db_connect()
        names = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        con.close()
        assert "users" in names
        assert "appointments" in names
        assert "personnel_employees" in names
        assert "personnel_entries" in names
        assert "personnel_imports" in names
