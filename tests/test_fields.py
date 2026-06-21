from ai_extracted_data_cleaner.fields import build_column_map


def test_field_mapping_bet():
    column_map, unknown = build_column_map(["BET", "Sample Name", "random_col"])
    assert column_map["BET"] == "BET_m2_g"
    assert column_map["Sample Name"] == "sample_name"
    assert "random_col" in unknown
