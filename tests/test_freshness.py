"""Checks that saved prices and SEC data are thrown away when they are not from today (no network)."""
import sys, pathlib, types, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.modules["yfinance"] = types.SimpleNamespace()
import prices
import sec


def main():
    with tempfile.TemporaryDirectory() as tmp:
        folder = pathlib.Path(tmp)
        (folder / "AAA.csv.gz").write_text("x")
        (folder / "_downloaded_on.txt").write_text("2026-11-13")
        prices._clear_if_stale(folder, "2026-11-14")
        assert not (folder / "AAA.csv.gz").exists()
        assert (folder / "_downloaded_on.txt").read_text().strip() == "2026-11-14"
        (folder / "BBB.csv.gz").write_text("x")
        prices._clear_if_stale(folder, "2026-11-14")
        assert (folder / "BBB.csv.gz").exists()
    assert sec._fresh({"_date": "2026-11-13", "1": {}}, "2026-11-14") == {"_date": "2026-11-14"}
    assert sec._fresh({"_date": "2026-11-14", "1": {}}, "2026-11-14") == {"_date": "2026-11-14", "1": {}}
    assert sec._fresh({"1": {}}, "2026-11-14") == {"_date": "2026-11-14"}
    print("freshness test passed")


main()
