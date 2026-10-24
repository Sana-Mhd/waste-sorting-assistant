import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
# data_rules is only imported by the contract test (categories must match).
sys.path.insert(0, str(ROOT.parent / "data_rules" / "src"))
