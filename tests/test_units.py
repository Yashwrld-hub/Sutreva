import pytest

from core import normalize_numeric_value
from units import canonical_unit, convert_value


def test_temperature_conversion():
    assert convert_value(356, "F", "C") == pytest.approx(180)

def test_pressure_conversion():
    assert convert_value(1.2, "MPa", "bar") == pytest.approx(12)

def test_unsafe_conversion_is_rejected():
    with pytest.raises(ValueError):
        convert_value(10, "rpm", "bar")

def test_normalization_metadata():
    value, metadata = normalize_numeric_value(180, "C", "F")
    assert value == pytest.approx(356)
    assert metadata["converted"] is True
    assert canonical_unit("°C") == "degC"


def test_volume_litre_to_us_gallon():
    assert convert_value(3.785411784, "L", "US gallon") == pytest.approx(1.0, rel=1e-9)


def test_flow_lpm_to_m3h():
    assert convert_value(1000, "L/min", "m3/h") == pytest.approx(60.0)


def test_power_hp_to_kw():
    assert convert_value(1, "hp", "kW") == pytest.approx(0.7456998716)


def test_mass_kg_to_lb():
    assert convert_value(1, "kg", "lb") == pytest.approx(2.2046226218)


def test_gauge_absolute_conversion_requires_context():
    with pytest.raises(ValueError, match="ambient_pressure"):
        convert_value(5, "barg", "bara")
    assert convert_value(5, "barg", "bara", ambient_pressure_pa=101325) == pytest.approx(6.01325, rel=1e-5)


def test_parse_numeric_with_inline_unit():
    from units import parse_numeric_with_unit
    assert parse_numeric_with_unit("1000 kPa") == (1000.0, "kPa")
    assert parse_numeric_with_unit(12.5) == (12.5, None)
