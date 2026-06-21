from pathlib import Path

import pandas as pd

from ai_extracted_data_cleaner.cleaner import clean_table


def test_cleaner_outputs(tmp_path):
    input_path = tmp_path / "raw.csv"
    pd.DataFrame({
        "paper": ["P1", "P1"],
        "Sample Name": ["A", "B"],
        "BET": ["1200 m2/g", "12300 m2/g"],
        "d002": ["3.72 Å", "0.371 nm"],
        "ICE": ["86%", "105%"],
        "source": ["Table 1", "Table 1"],
    }).to_csv(input_path, index=False)
    result = clean_table(input_path, tmp_path / "out")
    assert result["n_rows"] == 2
    assert (tmp_path / "out" / "cleaned_database.csv").exists()
    flags = pd.read_csv(tmp_path / "out" / "flagged_records.csv")
    assert "P0" in set(flags["risk_level"])


def test_cleaner_empty_flags_has_headers(tmp_path):
    input_path = tmp_path / "clean.csv"
    pd.DataFrame({
        "paper": ["P1"],
        "sample id": ["S1"],
        "Sample Name": ["A"],
        "BET": ["1200 m2/g"],
        "d002": ["0.372 nm"],
        "ICE": ["86%"],
        "source": ["Table 1"],
    }).to_csv(input_path, index=False)
    result = clean_table(input_path, tmp_path / "out")
    assert result["decision"] == "PASS_WITH_NOTES"
    flags = pd.read_csv(tmp_path / "out" / "flagged_records.csv")
    assert list(flags.columns) == ["row_index", "paper_id", "sample_id", "field", "value", "risk_level", "reason", "required_action"]
    assert flags.empty
