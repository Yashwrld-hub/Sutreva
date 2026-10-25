"""Conservative engineering unit normalization and conversion helpers.

The registry is deliberately explicit. Ambiguous or reference-dependent
conversions (for example gauge pressure to absolute pressure) require an
explicit pressure basis and are never silently guessed.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

_UNIT_ALIASES = {
    # Temperature
    "c": "degC", "°c": "degC", "degc": "degC", "deg c": "degC", "deg. c": "degC", "celsius": "degC",
    "f": "degF", "°f": "degF", "degf": "degF", "deg f": "degF", "deg. f": "degF", "fahrenheit": "degF",
    "k": "K", "kelvin": "K",
    # Generic pressure (reference unspecified)
    "pa": "Pa", "kpa": "kPa", "mpa": "MPa", "bar": "bar", "psi": "psi",
    "kg/cm2": "kg/cm2", "kg/cm²": "kg/cm2", "kgf/cm2": "kg/cm2", "kgf/cm²": "kg/cm2",
    # Gauge / absolute pressure families
    "barg": "barg", "bar(g)": "barg", "bar.g": "barg", "bar g": "barg",
    "bara": "bara", "bar(a)": "bara", "bar.a": "bara", "bar a": "bara",
    "kpag": "kPag", "kpa(g)": "kPag", "kpa-g": "kPag", "kpa g": "kPag",
    "kpaa": "kPaa", "kpa(a)": "kPaa", "kpa-a": "kPaa", "kpa a": "kPaa",
    "mpag": "MPag", "mpa(g)": "MPag", "mpaa": "MPaa", "mpa(a)": "MPaa",
    "psig": "psig", "psi(g)": "psig", "psia": "psia", "psi(a)": "psia",
    "kg/cm2g": "kg/cm2g", "kg/cm²g": "kg/cm2g", "kg/cm2(g)": "kg/cm2g", "kg/cm2.g": "kg/cm2g",
    "kg/cm2a": "kg/cm2a", "kg/cm²a": "kg/cm2a", "kg/cm2(a)": "kg/cm2a", "kg/cm2.a": "kg/cm2a", "kg/cm² a": "kg/cm2a",
    # Length
    "mm": "mm", "millimeter": "mm", "millimetre": "mm",
    "cm": "cm", "centimeter": "cm", "centimetre": "cm",
    "m": "m", "m.": "m", "meter": "m", "metre": "m", "meters": "m", "metres": "m",
    "in": "in", "inch": "in", "inches": "in",
    "ft": "ft", "foot": "ft", "feet": "ft",
    # Volume
    "l": "L", "litre": "L", "litres": "L", "liter": "L", "liters": "L", "ltrs": "L",
    "ml": "mL", "millilitre": "mL", "milliliter": "mL",
    "m3": "m3", "m³": "m3", "m^3": "m3", "cubic meter": "m3", "cubic metre": "m3",
    "us gal": "galUS", "us gallon": "galUS", "gallon (us)": "galUS", "gal": "galUS",
    "imp gal": "galImp", "imperial gallon": "galImp", "uk gallon": "galImp",
    # Flow
    "l/min": "L/min", "lpm": "L/min", "l/minute": "L/min",
    "l/s": "L/s", "lps": "L/s",
    "m3/h": "m3/h", "m³/h": "m3/h", "m3/hr": "m3/h", "m³/hr": "m3/h", "m3/ur": "m3/h",
    "m3/s": "m3/s", "m³/s": "m3/s",
    "gpm": "gpmUS", "us gpm": "gpmUS", "usgpm": "gpmUS",
    "imp gpm": "gpmImp", "uk gpm": "gpmImp",
    # Power
    "w": "W", "kw": "kW", "mw": "MW", "bkw": "kW",
    "hp": "hp", "bhp": "hp", "ps": "metric_hp",
    # Mass
    "g": "g", "kg": "kg", "lb": "lb", "lbs": "lb", "pound": "lb",
    # Speed
    "rpm": "rpm", "rad/s": "rad/s", "radian/s": "rad/s",
    # Torque
    "n.m": "N*m", "n·m": "N*m", "nm": "N*m", "kn.m": "kN*m", "kn·m": "kN*m",
    "lbf.ft": "lbf*ft", "lb-ft": "lbf*ft", "lb ft": "lbf*ft",
    # Viscosity & Density
    "cp": "cP", "mpas": "cP", "mpa.s": "cP",
    "cst": "cSt", "mm2/s": "cSt",
    "kg/m3": "kg/m3", "kg/m³": "kg/m3",
    "kg/dm3": "kg/dm3", "kg/dm³": "kg/dm3", "g/cm3": "kg/dm3", "sg": "SG",
}

_DIMENSIONS = {
    "degC": "temperature", "degF": "temperature", "K": "temperature",
    "Pa": "pressure", "kPa": "pressure", "MPa": "pressure", "bar": "pressure", "psi": "pressure", "kg/cm2": "pressure",
    "barg": "pressure_gauge", "kPag": "pressure_gauge", "MPag": "pressure_gauge", "psig": "pressure_gauge", "kg/cm2g": "pressure_gauge",
    "bara": "pressure_absolute", "kPaa": "pressure_absolute", "MPaa": "pressure_absolute", "psia": "pressure_absolute", "kg/cm2a": "pressure_absolute",
    "mm": "length", "cm": "length", "m": "length", "in": "length", "ft": "length",
    "mL": "volume", "L": "volume", "m3": "volume", "galUS": "volume", "galImp": "volume",
    "L/min": "flow", "L/s": "flow", "m3/h": "flow", "m3/s": "flow", "gpmUS": "flow", "gpmImp": "flow",
    "W": "power", "kW": "power", "MW": "power", "hp": "power", "metric_hp": "power",
    "g": "mass", "kg": "mass", "lb": "mass",
    "rpm": "speed", "rad/s": "speed",
    "N*m": "torque", "kN*m": "torque", "lbf*ft": "torque",
    "cP": "dynamic_viscosity", "cSt": "kinematic_viscosity",
    "kg/m3": "density", "kg/dm3": "density", "SG": "density",
}

_FACTORS = {
    # base units: K, Pa, mm, mL, L/s, W, g, rad/s, N*m
    "mm": ("length", 1.0), "cm": ("length", 10.0), "m": ("length", 1000.0),
    "in": ("length", 25.4), "ft": ("length", 304.8),
    "mL": ("volume", 1.0), "L": ("volume", 1000.0), "m3": ("volume", 1_000_000.0),
    "galUS": ("volume", 3785.411784), "galImp": ("volume", 4546.09),
    "L/min": ("flow", 1.0 / 60.0), "L/s": ("flow", 1.0),
    "m3/h": ("flow", 1_000.0 / 3600.0), "m3/s": ("flow", 1_000_000.0),
    "gpmUS": ("flow", 3.785411784 / 60.0), "gpmImp": ("flow", 4.54609 / 60.0),
    "W": ("power", 1.0), "kW": ("power", 1000.0), "MW": ("power", 1_000_000.0),
    "hp": ("power", 745.6998715822702), "metric_hp": ("power", 735.49875),
    "g": ("mass", 1.0), "kg": ("mass", 1000.0), "lb": ("mass", 453.59237),
    "rpm": ("speed", 1.0), "rad/s": ("speed", 1.0 / (2.0 * 3.141592653589793) * 60.0),
    "N*m": ("torque", 1.0), "kN*m": ("torque", 1000.0), "lbf*ft": ("torque", 1.3558179483314004),
    "cP": ("dynamic_viscosity", 1.0), "cSt": ("kinematic_viscosity", 1.0),
    "kg/m3": ("density", 1.0), "kg/dm3": ("density", 1000.0), "SG": ("density", 1000.0),
}

_NUMBER_RE = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def _unit_pattern_text():
    units = sorted((str(alias) for alias in _UNIT_ALIASES), key=len, reverse=True)
    return "|".join(re.escape(u) for u in units)


_UNIT_PATTERN_STR = _unit_pattern_text()
_PARSE_NUMERIC_UNIT_RE = re.compile(
    rf"^({_NUMBER_RE})\s*(?P<unit>{_UNIT_PATTERN_STR})?\s*$", re.IGNORECASE
)
_FIND_NUMERIC_UNIT_RE = re.compile(
    rf"({_NUMBER_RE})\s*(?P<unit>{_UNIT_PATTERN_STR})(?![a-zA-Z])", re.IGNORECASE
)


def canonical_unit(unit):
    if unit is None:
        return None
    key = str(unit).strip().lower().replace("µ", "u")
    return _UNIT_ALIASES.get(key, str(unit).strip())


def unit_dimension(unit):
    canonical = canonical_unit(unit)
    return _DIMENSIONS.get(canonical)


def are_compatible_units(from_unit, to_unit):
    src, dst = canonical_unit(from_unit), canonical_unit(to_unit)
    if src in _DIMENSIONS and dst in _DIMENSIONS:
        if _DIMENSIONS[src] == _DIMENSIONS[dst]:
            return True
        # Allow generic pressure target (e.g. "bar") to accept explicit source bar.a/bar.g when comparing magnitudes
        pressure_dims = {"pressure", "pressure_gauge", "pressure_absolute"}
        if _DIMENSIONS[src] in pressure_dims and _DIMENSIONS[dst] == "pressure":
            return True
    return False


def _pressure_reference(unit):
    canonical = canonical_unit(unit)
    if canonical in {"barg", "kPag", "MPag", "psig", "kg/cm2g"}:
        return "gauge"
    if canonical in {"bara", "kPaa", "MPaa", "psia", "kg/cm2a"}:
        return "absolute"
    return "generic"


def _pressure_to_pa(value, unit, ambient_pressure_pa: Optional[float] = None):
    unit = canonical_unit(unit)
    value = float(value)
    reference = _pressure_reference(unit)
    factors = {"Pa": 1.0, "kPa": 1000.0, "MPa": 1_000_000.0, "bar": 100_000.0, "psi": 6894.757293168, "kg/cm2": 98_066.5}
    gauge_factors = {"barg": 100_000.0, "kPag": 1000.0, "MPag": 1_000_000.0, "psig": 6894.757293168, "kg/cm2g": 98_066.5}
    abs_factors = {"bara": 100_000.0, "kPaa": 1000.0, "MPaa": 1_000_000.0, "psia": 6894.757293168, "kg/cm2a": 98_066.5}
    if reference == "generic":
        return value * factors[unit], "generic"
    if reference == "gauge":
        return value * gauge_factors[unit], "gauge"
    return value * abs_factors[unit], "absolute"


def _pressure_from_pa(value_pa, unit, source_reference, ambient_pressure_pa: Optional[float]):
    unit = canonical_unit(unit)
    target_reference = _pressure_reference(unit)
    if source_reference != target_reference and "generic" not in {source_reference, target_reference}:
        if ambient_pressure_pa is None:
            raise ValueError("Gauge/absolute pressure conversion requires ambient_pressure_pa context")
    if source_reference == "gauge" and target_reference == "absolute":
        value_pa += ambient_pressure_pa or 0.0
    elif source_reference == "absolute" and target_reference == "gauge":
        value_pa -= ambient_pressure_pa or 0.0
    factors = {
        "Pa": 1.0, "kPa": 1000.0, "MPa": 1_000_000.0, "bar": 100_000.0, "psi": 6894.757293168, "kg/cm2": 98_066.5,
        "barg": 100_000.0, "kPag": 1000.0, "MPag": 1_000_000.0, "psig": 6894.757293168, "kg/cm2g": 98_066.5,
        "bara": 100_000.0, "kPaa": 1000.0, "MPaa": 1_000_000.0, "psia": 6894.757293168, "kg/cm2a": 98_066.5,
    }
    return value_pa / factors[unit]


def convert_value(value, from_unit, to_unit, *, ambient_pressure_pa: Optional[float] = None):
    """Convert supported scalar engineering values; raise ValueError when unsafe."""
    src, dst = canonical_unit(from_unit), canonical_unit(to_unit)
    number = float(value)
    if src == dst:
        return number
    src_dim, dst_dim = unit_dimension(src), unit_dimension(dst)
    if {src_dim, dst_dim} <= {"pressure", "pressure_gauge", "pressure_absolute"}:
        src_ref, dst_ref = _pressure_reference(src), _pressure_reference(dst)
        if src_ref != dst_ref and dst_ref != "generic":
            if ambient_pressure_pa is None:
                raise ValueError("Gauge/absolute pressure conversion requires ambient_pressure_pa context")
    elif src_dim != dst_dim:
        raise ValueError(f"Incompatible unit dimensions: {src} ({src_dim}) -> {dst} ({dst_dim})")

    if src_dim == "temperature":
        if src == "degC":
            kelvin = number + 273.15
        elif src == "degF":
            kelvin = (number - 32) * 5 / 9 + 273.15
        else:
            kelvin = number
        if dst == "degC":
            return kelvin - 273.15
        if dst == "degF":
            return (kelvin - 273.15) * 9 / 5 + 32
        return kelvin

    if src_dim in {"pressure", "pressure_gauge", "pressure_absolute"}:
        pa, ref = _pressure_to_pa(number, src, ambient_pressure_pa)
        return _pressure_from_pa(pa, dst, ref, ambient_pressure_pa)

    if src not in _FACTORS or dst not in _FACTORS:
        raise ValueError(f"Unsupported or unsafe conversion: {src} -> {dst}")
    _, src_factor = _FACTORS[src]
    _, dst_factor = _FACTORS[dst]
    return number * src_factor / dst_factor


def _normalize_decimal_comma(text: str) -> str:
    """Convert European/OCR decimal commas ('75,07 hp') to dots while removing thousand commas ('1,200')."""
    def _repl(m: re.Match) -> str:
        int_part, frac_part = m.group(1), m.group(2)
        if len(frac_part) == 3 and int_part != "0":
            return int_part + frac_part
        return f"{int_part}.{frac_part}"
    return re.sub(r"(\d+),(\d+)", _repl, text)


def parse_numeric_with_unit(value) -> Tuple[float, Optional[str]]:
    """Parse strings such as '1000 kPa', '75,07 hp', or '0.074 kg/cm²' into (value, canonical_unit)."""
    if isinstance(value, bool):
        raise ValueError("Boolean is not a numeric engineering value")
    if isinstance(value, (int, float)):
        return float(value), None
    text = _normalize_decimal_comma(str(value).strip())
    match = _PARSE_NUMERIC_UNIT_RE.match(text)
    if not match:
        raise ValueError(f"Not a numeric value with a recognized unit: {value!r}")
    return float(match.group(1)), canonical_unit(match.group("unit")) if match.group("unit") else None


def find_numeric_unit_candidates(text, target_unit=None):
    """Return numeric/unit pairs on one line, filtered to target dimensionality."""
    if not text:
        return []
    candidates = []
    norm_text = _normalize_decimal_comma(str(text))
    for match in _FIND_NUMERIC_UNIT_RE.finditer(norm_text):
        unit = canonical_unit(match.group("unit"))
        if target_unit and not are_compatible_units(unit, target_unit):
            continue
        candidates.append((float(match.group(1)), unit))
    return candidates
