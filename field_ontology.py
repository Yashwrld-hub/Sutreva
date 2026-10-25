"""
field_ontology.py — Self-learning engineering field ontology & morphological matcher.

When a user introduces a new engineering field (e.g., "Vapour Pressure", "Suction
Pressure", "Impeller Material"), this module resolves its industry synonyms,
abbreviations, and negative collision cues from:
  1. A persistent local library (engineering_ontology.json)
  2. Universal UK/US spelling & engineering prefix-abbreviation rules (VAP. -> vapor)
  3. On-demand NVIDIA Nemotron synthesis, which caches newly learned fields into
     engineering_ontology.json for all future audits.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from ai_provider import DEFAULT_MODEL_NAME, get_model_provider

ONTOLOGY_PATH = Path(__file__).with_name("engineering_ontology.json")

# UK -> US and common morphological normalizations in engineering datasheets
_SPELLING_EQUIVALENTS = (
    ("vapour", "vapor"),
    ("aluminium", "aluminum"),
    ("sulphur", "sulfur"),
    ("meters", "metres"),
    ("meter", "metre"),
    ("liters", "litres"),
    ("liter", "litre"),
    ("centre", "center"),
    ("colour", "color"),
    ("gage", "gauge"),
)

# Standard engineering datasheet token abbreviations -> canonical full token
_ABBREV_MAP = {
    "vap": "vapor",
    "vapour": "vapor",
    "press": "pressure",
    "pr": "pressure",
    "pres": "pressure",
    "temp": "temperature",
    "tmp": "temperature",
    "suc": "suction",
    "suct": "suction",
    "disch": "discharge",
    "dis": "discharge",
    "del": "discharge",
    "diff": "differential",
    "cap": "capacity",
    "eff": "efficiency",
    "imp": "impeller",
    "dia": "diameter",
    "diam": "diameter",
    "mat": "material",
    "matl": "material",
    "moc": "material",
    "max": "maximum",
    "min": "minimum",
    "nom": "nominal",
    "req": "required",
    "reqd": "required",
    "avail": "available",
    "visc": "viscosity",
    "dens": "density",
    "sp": "specific",
    "grav": "gravity",
    "sg": "gravity",
    "freq": "frequency",
    "spd": "speed",
    "rot": "rotation",
    "lub": "lubrication",
    "lube": "lubrication",
    "conn": "connection",
    "hyd": "hydraulic",
    "atmos": "atmospheric",
    "atm": "atmospheric",
    "amb": "ambient",
}

# Built-in seed library covering common rotating & static equipment fields
BUILTIN_ONTOLOGY: dict[str, dict[str, Any]] = {
    "rated_power": {
        "aliases": [
            "power at rated conditions", "power, rated", "rated power",
            "nominal power", "brake power", "motor power", "absorbed power",
            "shaft power", "hp/kw",
        ],
        "negative_cues": [
            "calculated hydraulic power", "power, hydraulic", "hydraulic kw",
            "coupling rating", "power factor", "power at the end of the curve",
            "max. bkw", "maximum, rated diameter", "max. power of rated impeller",
            "minimum recommended motor rating", "required motor rating",
            "bhp @", "maximum viscocity", "maximum viscosity", "relief valve",
            "efficiency", "water",
        ],
    },
    "npsh_available": {
        "aliases": [
            "npsh available, rated", "npsh available", "npsha available",
            "npsha", "npsh r/a", "net positive suction head available",
        ],
        "negative_cues": [
            "npsh required", "npshr", "difference between npsha and npshr",
            "minimum 1 meter margin", "minimum i meter margin", "npsh test",
        ],
    },
    "npsh_required": {
        "aliases": [
            "npsh required", "npshr", "npsh (required", "npsh req.",
            "net positive suction head required",
        ],
        "negative_cues": [
            "npsh available", "npsha", "difference between npsha",
        ],
    },
    "vapour_pressure": {
        "aliases": [
            "vapour pressure", "vapor pressure", "vapor pressure, rated",
            "vap. pressure", "vap. pr.", "vap press", "vp at pt",
            "vapour press.", "vapor press.",
        ],
        "negative_cues": [
            "suction pressure", "discharge pressure", "differential pressure",
            "hydrotest pressure", "hydrostatic test pressure", "working pressure",
            "atm. pressure", "barometer", "seal chamber pressure",
        ],
    },
    "suction_pressure": {
        "aliases": [
            "suction pressure", "suction pressure, rated / max",
            "suction pr.", "suc. pressure", "suc. pr.", "inlet pressure",
        ],
        "negative_cues": [
            "maximum allowable suction pressure", "discharge pressure",
            "differential pressure", "vapour pressure", "vapor pressure",
        ],
    },
    "discharge_pressure": {
        "aliases": [
            "discharge pressure", "disch. pressure", "disch. pr.",
            "delivery pressure", "outlet pressure",
        ],
        "negative_cues": [
            "suction pressure", "differential pressure", "vapour pressure",
            "vapor pressure", "hydrotest pressure",
        ],
    },
    "differential_pressure": {
        "aliases": [
            "differential pressure", "diff. pressure", "diff. pr.",
            "differential head / pressure, rated (actual)",
            "differential head / pressure, rated",
        ],
        "negative_cues": [
            "suction pressure", "discharge pressure", "vapour pressure",
        ],
    },
    "rated_flow": {
        "aliases": [
            "flow, rated", "rated flow", "capacity: normal- rated-",
            "capacity @pt", "rated capacity", "capacity, rated", "flow rate",
        ],
        "negative_cues": [
            "min. continuous flow", "min. cont. stable flow", "min. cont. thermal flow",
            "flow, best eff. point", "bep flow", "flow ratio", "flushing",
        ],
    },
    "rated_head": {
        "aliases": [
            "rated head", "differential head", "head, rated",
            "total dynamic head", "tdh", "head:",
        ],
        "negative_cues": [
            "shut-off head", "shut off head", "head, maximum", "head rise",
            "head ratio", "npsh",
        ],
    },
    "operating_temperature": {
        "aliases": [
            "operating temperature", "temperature, max", "pumping temp.",
            "pumping temperature", "liquid temperature", "max operating temp",
        ],
        "negative_cues": [
            "design temperature", "range of amb. temperature",
            "range of ambient temps", "temp rise",
        ],
    },
    "fluid_density": {
        "aliases": [
            "fluid density, rated / max", "fluid density", "density",
            "specific gravity", "sp. gravity", "sg",
        ],
        "negative_cues": ["solids concentration"],
    },
    "viscosity": {
        "aliases": [
            "viscosity, rated", "viscosity", "viscosity (cp)", "kinematic viscosity",
        ],
        "negative_cues": ["viscosity factors", "bhp @ maximum viscocity"],
    },
    "rated_speed": {
        "aliases": [
            "speed, rated", "nominal/eff. speed", "pump speed (rated)",
            "rated speed", "rpm", "speed (syn)",
        ],
        "negative_cues": [
            "specific speed", "suction specific speed", "limiting speed",
            "maximum allowable speed", "minimum allowable speed", "speed criteria",
        ],
    },
    "efficiency": {
        "aliases": [
            "efficiency", "efficiency of pump", "pump efficiency",
            "mechanical efficiency",
        ],
        "negative_cues": [
            "efficiency class", "volumetric efficiency", "efficiency (water)",
        ],
    },
    "casing_material": {
        "aliases": [
            "casing / barrel material", "barrel / case", "volute casing",
            "casing material", "pump casing", "casing", "body material", "version",
        ],
        "negative_cues": [
            "casing type", "casing mounting", "casing split", "pump casing drain",
            "pump casing vent", "casing front", "casing back", "wear ring",
            "single volute", "double volute", "noted & updated", "mark casing type",
            "casing/gland stud",
        ],
    },
    "shaft_material": {
        "aliases": ["shaft material", "pump shaft", "shaft"],
        "negative_cues": [
            "prot sleeve", "protective sleeve", "shaft sleeve",
            "impeller fixing to shaft", "keyed threaded", "line shaft",
            "shaft dia", "shaft seal", "shaft sealing", "vibration switch",
        ],
    },
    "impeller_material": {
        "aliases": ["impeller material", "impeller"],
        "negative_cues": [
            "impeller dia", "impeller diameter", "impeller type",
            "impeller form", "impeller mounting", "impeller fixing",
            "impeller front", "impeller back", "max. power of rated impeller",
            "wear ring", "span b/w bearing and impeller",
        ],
    },
    "driver_type": {
        "aliases": [
            "driver type", "type of driver", "pump driven by",
            "prime mover", "motor manufacturer", "motor data", "driver",
        ],
        "negative_cues": [
            "driver item no", "driver data sheet", "driver fixing",
            "driver sizing", "gd2 value", "assembly of pumps",
            "electric supply", "weight",
        ],
    },
    "design_pressure": {
        "aliases": [
            "design pressure", "m.a.w.p", "mawp", "maximum allowable working pressure",
            "shell design pressure", "internal design pressure", "design pr.",
        ],
        "negative_cues": [
            "operating pressure", "normal pressure", "hydrotest pressure",
            "hydrostatic test pressure", "suction pressure", "vapour pressure",
        ],
    },
    "design_temperature": {
        "aliases": [
            "design temperature", "design temp.", "max design temp",
            "shell design temperature", "maximum allowable temperature",
        ],
        "negative_cues": [
            "operating temperature", "pumping temp", "ambient temperature",
            "mdmt", "minimum design metal temperature",
        ],
    },
    "hydrotest_pressure": {
        "aliases": [
            "hydrotest pressure", "hydrostatic test pressure", "shop test pressure",
            "hydraulic test pressure", "test pressure",
        ],
        "negative_cues": [
            "operating pressure", "design pressure", "mawp", "suction pressure",
        ],
    },
    "heat_duty": {
        "aliases": [
            "heat duty", "thermal duty", "heat exchanged", "total duty", "duty",
        ],
        "negative_cues": ["heavy duty", "continuous duty"],
    },
    "heat_transfer_area": {
        "aliases": [
            "heat transfer area", "effective surface area", "surface area",
            "bare tube area", "finned area", "total area",
        ],
        "negative_cues": ["hazardous area", "area classification", "area to be lubricated"],
    },
    "shell_material": {
        "aliases": [
            "shell material", "shell", "vessel shell", "column shell",
            "cylinder material", "reactor shell",
        ],
        "negative_cues": ["shell id", "shell dia", "shell thickness", "shell passes", "shell side"],
    },
    "tube_material": {
        "aliases": [
            "tube material", "tubes", "tube bundle material", "coil material",
        ],
        "negative_cues": ["tube od", "tube length", "tube pitch", "tube passes", "tube side"],
    },
    "corrosion_allowance": {
        "aliases": [
            "corrosion allowance", "c.a.", "shell corrosion allowance", "ca",
        ],
        "negative_cues": ["erosion"],
    },
}


@lru_cache(maxsize=4096)
def canonical_tokens(text: str) -> tuple[str, ...]:
    """Tokenize any label into canonical engineering roots (resolving abbreviations & UK/US spelling)."""
    lowered = str(text or "").lower()
    for uk, us in _SPELLING_EQUIVALENTS:
        lowered = lowered.replace(uk, us)
    raw_tokens = re.findall(r"[a-z0-9]+", lowered)
    result = []
    stop_words = {"of", "the", "at", "in", "for", "to", "by", "and", "or", "per", "a", "an"}
    for tok in raw_tokens:
        if tok in stop_words or tok.isdigit():
            continue
        mapped = _ABBREV_MAP.get(tok, tok)
        result.append(mapped)
    return tuple(result)


def canonical_concept_key(text: str) -> str:
    """Turn 'Vapour Pressure (bar)' or 'VAP. PR.' into 'vapor_pressure'."""
    tokens = canonical_tokens(text)
    return "_".join(tokens) if tokens else re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")


def load_ontology(path: Path = ONTOLOGY_PATH) -> dict[str, dict[str, Any]]:
    """Load the merged built-in + user-persisted ontology library."""
    merged = {k: dict(v) for k, v in BUILTIN_ONTOLOGY.items()}
    if path.is_file():
        try:
            custom = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(custom, dict):
                for k, v in custom.items():
                    if isinstance(v, dict):
                        merged[k] = v
        except (OSError, json.JSONDecodeError):
            pass
    return merged


def save_ontology_entry(
    concept_key: str,
    aliases: list[str],
    negative_cues: list[str] | None = None,
    *,
    path: Path = ONTOLOGY_PATH,
) -> None:
    """Persist a newly learned field profile into engineering_ontology.json."""
    existing: dict[str, Any] = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        except (OSError, json.JSONDecodeError):
            existing = {}

    clean_aliases = []
    for a in aliases:
        s = str(a).strip()
        if s and s.lower() not in {x.lower() for x in clean_aliases}:
            clean_aliases.append(s)

    clean_negatives = []
    for n in (negative_cues or []):
        s = str(n).strip()
        if s and s.lower() not in {x.lower() for x in clean_negatives}:
            clean_negatives.append(s)

    existing[concept_key] = {
        "aliases": clean_aliases,
        "negative_cues": clean_negatives,
    }
    try:
        path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def generate_morphological_aliases(label: str) -> list[str]:
    """Generate deterministic UK/US spelling and common abbreviation variants for any label."""
    base = str(label or "").strip()
    if not base:
        return []
    variants = {base, base.lower()}
    lowered = base.lower()

    # 1. UK <-> US spelling swaps
    for uk, us in _SPELLING_EQUIVALENTS:
        if uk in lowered:
            variants.add(lowered.replace(uk, us))
        if us in lowered:
            variants.add(lowered.replace(us, uk))

    # 2. Common engineering abbreviations (e.g., "vapor pressure" -> "vap. pressure", "vap. pr.")
    tokens = canonical_tokens(base)
    if tokens:
        canonical_phrase = " ".join(tokens)
        variants.add(canonical_phrase)
        abbrev_reverse = {
            "vapor": ["vap.", "vap", "vapour"],
            "pressure": ["pressure", "press.", "pr."],
            "temperature": ["temperature", "temp."],
            "suction": ["suction", "suc.", "suct."],
            "discharge": ["discharge", "disch.", "del."],
            "differential": ["differential", "diff."],
            "efficiency": ["efficiency", "eff."],
            "impeller": ["impeller", "imp."],
            "diameter": ["diameter", "dia."],
            "maximum": ["maximum", "max."],
            "minimum": ["minimum", "min."],
            "capacity": ["capacity", "cap."],
        }
        if len(tokens) == 2:
            t1_opts = abbrev_reverse.get(tokens[0], [tokens[0]])
            t2_opts = abbrev_reverse.get(tokens[1], [tokens[1]])
            for o1 in t1_opts:
                for o2 in t2_opts:
                    variants.add(f"{o1} {o2}")

    return sorted(variants, key=len, reverse=True)


def match_ontology_entry(field: dict[str, Any]) -> dict[str, Any]:
    """Find or synthesize aliases and negative cues for any schema field."""
    ontology = load_ontology()
    field_name = str(field.get("field_name") or "").strip().lower()
    label = str(field.get("label") or field_name).strip()
    concept_key = canonical_concept_key(label or field_name)

    matched_entry = (
        ontology.get(field_name)
        or ontology.get(concept_key)
    )
    if not matched_entry:
        # Check if canonical tokens match any ontology entry's key tokens
        target_tokens = set(canonical_tokens(f"{field_name} {label}"))
        for key, entry in ontology.items():
            key_tokens = set(canonical_tokens(key))
            if key_tokens and key_tokens.issubset(target_tokens):
                matched_entry = entry
                break

    aliases: list[str] = []
    for src in (
        [label, field_name],
        field.get("extraction_aliases") or [],
        field.get("deterministic_source_aliases") or [],
        (matched_entry or {}).get("aliases") or [],
        generate_morphological_aliases(label),
    ):
        for item in src:
            s = str(item).strip()
            if s and s.lower() not in {x.lower() for x in aliases}:
                aliases.append(s)

    negative_cues: list[str] = []
    for src in (
        field.get("negative_cues") or [],
        (matched_entry or {}).get("negative_cues") or [],
    ):
        for item in src:
            s = str(item).strip()
            if s and s.lower() not in {x.lower() for x in negative_cues}:
                negative_cues.append(s)

    return {
        "concept_key": concept_key,
        "aliases": aliases,
        "negative_cues": negative_cues,
    }


def enrich_field_with_nemotron(
    label: str,
    unit: str | None = None,
    equipment_context: str = "industrial pump / rotating equipment",
    *,
    model_name: str = DEFAULT_MODEL_NAME,
    persist: bool = True,
) -> dict[str, Any]:
    """Ask Nemotron to synthesize datasheet aliases and negative collision cues for a new field.

    Falls back gracefully to morphological aliases if offline or if no API key is set.
    """
    base_profile = match_ontology_entry({"field_name": canonical_concept_key(label), "label": label, "unit": unit})
    prompt = f"""You are an industrial engineering datasheet ontology builder for {equipment_context}.
A user added a new audit template field:
- Field Label: "{label}"
- Unit: "{unit or 'none'}"

Return ONLY one valid JSON object with:
1. "aliases": 6 to 12 common ways OEM datasheets (API 610, ISO, KSB, Sulzer, Ruhrpumpen, etc.) label or abbreviate this exact parameter (including UK/US spellings and standard abbreviations like "VAP. PRESSURE" or "SUC. PR.").
2. "negative_cues": 4 to 8 similar-sounding datasheet labels that refer to a DIFFERENT parameter and must NOT be confused with "{label}".

JSON structure:
{{
  "aliases": ["...", "..."],
  "negative_cues": ["...", "..."]
}}"""

    try:
        raw = get_model_provider().generate(prompt, model_name=model_name)
        cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.IGNORECASE | re.DOTALL).strip()
        start = cleaned.find("{")
        if start >= 0:
            payload, _ = json.JSONDecoder().raw_decode(cleaned[start:])
            if isinstance(payload, dict):
                llm_aliases = [str(x).strip() for x in (payload.get("aliases") or []) if str(x).strip()]
                llm_negatives = [str(x).strip() for x in (payload.get("negative_cues") or []) if str(x).strip()]
                merged_aliases = list(dict.fromkeys(base_profile["aliases"] + llm_aliases))
                merged_negatives = list(dict.fromkeys(base_profile["negative_cues"] + llm_negatives))
                if persist:
                    save_ontology_entry(base_profile["concept_key"], merged_aliases, merged_negatives)
                return {
                    "concept_key": base_profile["concept_key"],
                    "aliases": merged_aliases,
                    "negative_cues": merged_negatives,
                    "source": "nemotron_enriched",
                }
    except Exception:
        pass

    if persist:
        save_ontology_entry(base_profile["concept_key"], base_profile["aliases"], base_profile["negative_cues"])
    return {
        "concept_key": base_profile["concept_key"],
        "aliases": base_profile["aliases"],
        "negative_cues": base_profile["negative_cues"],
        "source": "deterministic_morphology",
    }


def line_matches_field_tokens(line: str, field_label: str) -> bool:
    """Universal token-root matcher: matches '17 VAP. PRESSURE : 0.25' to 'Vapour Pressure'."""
    target_roots = canonical_tokens(field_label)
    if not target_roots or len(target_roots) < 2:
        return False
    # Only check the label portion of the line (before a colon or number)
    label_part = re.split(r"[:=]|\s-?\d+\.\d+", line, maxsplit=1)[0]
    line_roots = set(canonical_tokens(label_part))
    return all(root in line_roots for root in target_roots)


# Strict Metallurgical Specification Families (ASTM / ASME / AISI / EN / DIN)
# Two material designations are considered equivalent ONLY if they belong to the
# exact same alloy composition family (e.g., A216 WCB and A216 WCC are both API 610
# Carbon Steel castings; A276-410 and A479 Type 410 Cl 2 are both 12% Cr Type 410
# Martensitic Stainless Steel bar). Distinct alloys (such as 316 SS vs 410 SS)
# are in separate sets and NEVER match each other.
_METALLURGICAL_GRADE_FAMILIES: tuple[tuple[str, set[str]], ...] = (
    (
        "carbon_steel_casting_a216",
        {"a216wcb", "a216grwcb", "sa216wcb", "a216wcc", "a216grwcc", "sa216wcc", "astma216wcb", "astma216wcc", "astma216grwcb", "astma216grwcc"},
    ),
    (
        "martensitic_ss_410",
        {"a276410", "a276type410", "a479410", "a479type410", "a479type410cl1", "a479type410cl2", "a479type410ci2", "aisi410", "ss410", "uns41000"},
    ),
    (
        "martensitic_ss_ca6nm",
        {"a487ca6nm", "a487grca6nm", "a487grca6nmclassa", "a743ca6nm", "ca6nm"},
    ),
    (
        "austenitic_ss_316_wrought_and_cast",
        {"a479316", "a479316l", "a276316", "a276type316", "a276type316l", "aisi316", "aisi316l", "ss316", "ss316l", "ssaisi316", "a743cf8m", "a743grcf8m", "astma743grcf8m", "a351cf8m", "cf8m", "sa240316", "sa240316l"},
    ),
    (
        "austenitic_ss_304",
        {"a479304", "a276304", "a276type304", "aisi304", "ss304", "a743cf8", "a351cf8", "cf8", "sa240304", "sa240304l"},
    ),
    (
        "carbon_steel_vessel_plate_516_70",
        {"sa51670", "sa516gr70", "a51670", "a516gr70", "astma516gr70", "asmesa516gr70", "sa516gr70n"},
    ),
    (
        "duplex_ss_2205",
        {"a182f51", "a182f60", "a240s31803", "a240s32205", "sa240s31803", "sa240s32205", "duplex2205", "uns31803", "uns32205", "a8904a", "cd3mn"},
    ),
    (
        "super_duplex_2507",
        {"a182f53", "a182f55", "a240s32750", "sa240s32750", "superduplex2507", "uns32750", "uns32760", "a8905a", "a8906a"},
    ),
)


def _norm_mat_token(value: str) -> str:
    text = re.sub(r"\b(?:astm|asme)\b", "", str(value or "").lower())
    return re.sub(r"[^a-z0-9]+", "", text)


def equivalent_material_grade(extracted_value: Any, expected_value: Any) -> bool:
    """Return True if extracted_value and expected_value belong to the same strict ASTM/ASME alloy family."""
    if extracted_value in (None, "") or expected_value in (None, ""):
        return False
    ext_norm = _norm_mat_token(str(extracted_value))
    exp_norm = _norm_mat_token(str(expected_value))
    if not ext_norm or not exp_norm:
        return False
    if ext_norm == exp_norm:
        return True
    for _family_name, members in _METALLURGICAL_GRADE_FAMILIES:
        if ext_norm in members and exp_norm in members:
            return True
    return False
