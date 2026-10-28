import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
import panel as p

def test_names():
    assert p.name_keys("RTX CORPORATION AND AFFILIATES (FKA RAYTHEON TECHNOLOGIES CORPORATION)") == ["RTX", "RAYTHEON TECHNOLOGIES"]
    assert p.name_keys("RTX CORPORATION AND AFFILIATES(RAYTHEON TECHNOLOGIES CORPORATION AND AFFILIATES)")[0] == "RTX"
    assert p.norm("The Boeing Company") == "BOEING"
    assert p.norm("AT&T Inc.") == "AT T"
    assert p.norm("AT&amp;T INC") == "AT T"

def test_index_and_rollup():
    cos = [{"cik": 101829, "ticker": "RTX", "name": "RTX Corp", "former_names": ["RAYTHEON TECHNOLOGIES CORP", "UNITED TECHNOLOGIES CORP /DE/"]},
           {"cik": 6201, "ticker": "AAL", "name": "American Airlines Group Inc.", "former_names": []},
           {"cik": 1, "ticker": "X1", "name": "Acme Holdings", "former_names": []},
           {"cik": 2, "ticker": "X2", "name": "Acme Inc", "former_names": []}]
    idx = p.build_name_index(cos)
    assert idx["RTX"] == 101829 and idx["UNITED TECHNOLOGIES"] == 101829
    assert idx["AMERICAN AIRLINES"] == 6201
    assert "ACME" not in idx                      # ambiguous -> dropped
    spend = {"RTX CORPORATION AND AFFILIATES": 3260000, "RAYTHEON TECHNOLOGIES CORPORATION": 50000,
             "AMERICAN AIRLINES, INC.": 100000, "ACME INC": 5, "UNKNOWN LLC": 9}
    out, matched = p.company_spend(spend, idx)
    assert out[101829] == 3310000 and out[6201] == 100000 and len(out) == 2

def test_amendment_and_cutoff():
    f = {(2025, 4): [("1", "9", "RTX", "2026-01-20T10:00", 3110000.0),
                     ("1", "9", "RTX", "2026-02-15T10:00", 3260000.0),
                     ("2", "8", "RTX", "2026-01-19T10:00", 60000.0)]}
    assert p.spend_by_client(f, (2025, 4), "2026-01-22")["RTX"] == 3170000   # amendment not yet known
    assert p.spend_by_client(f, (2025, 4), "2026-03-01")["RTX"] == 3320000   # amendment replaces original

if __name__ == "__main__":
    test_names(); test_index_and_rollup(); test_amendment_and_cutoff(); print("panel tests passed")
