from ai_extracted_data_cleaner.units import normalize_value


def test_d002_angstrom_to_nm():
    value, corr = normalize_value("d002_nm", "3.72 Å")
    assert abs(value - 0.372) < 1e-9
    assert corr is not None


def test_current_density_ma_to_a():
    value, corr = normalize_value("current_density_A_g", "100 mA/g")
    assert abs(value - 0.1) < 1e-9
    assert corr is not None


def test_capacity_mah_is_not_converted_as_ah():
    value, corr = normalize_value("capacity_mAh_g", "310 mAh/g")
    assert value == 310
    assert corr is None


def test_capacity_ah_to_mah():
    value, corr = normalize_value("capacity_mAh_g", "0.31 Ah/g")
    assert abs(value - 310) < 1e-9
    assert corr is not None
