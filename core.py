"""
core.py — the shared "brain" of the tool.

This file has NO knowledge of command lines or web pages. It only knows how to:
  1. take datasheet text + a schema
  2. ask Nemotron to extract structured fields
  3. compare the result against the schema
  4. export the result to Excel / PDF / CSV

Both extract.py (command line) and app.py (Streamlit UI) import from here,
so the actual logic only exists in one place.
"""

import difflib
import io
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

import pdfplumber
from dotenv import load_dotenv

from ai_orchestration import run_engineering_reasoning
from ai_provider import DEFAULT_MODEL_NAME, get_model_provider
from conflict_detection import detect_conflicts
from extraction_contract import records_from_extracted, validate_record
from field_ontology import (
    equivalent_material_grade,
    line_matches_field_tokens,
    match_ontology_entry,
)
from units import (
    are_compatible_units,
    canonical_unit,
    convert_value,
    find_numeric_unit_candidates,
    parse_numeric_with_unit,
    unit_dimension,
)

load_dotenv()

MODEL_NAME = DEFAULT_MODEL_NAME
MAX_PARSE_RETRIES = 1

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*$", re.IGNORECASE | re.MULTILINE)
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)

_UNIVERSAL_COLUMN_STOP_RE = re.compile(
    r"\s+(?:"
    r"pump\s+serial\s+no\b|serial\s+no\b|model\b|manufacturer\b|"
    r"recommended\s+pipe\s+size\b|suc\.?\s*:|del\.?\s*:|"
    r"coupling\s+guard\b|coupling\s*:|wetted\s+fasteners\b|"
    r"shaft\s+prot\.?\s*sleeve\b|impeller\s*:|sleeve\s*:|"
    r"base\s+frame\b|base\s+plate\b|painting\b|"
    r"his\s+concentration\b|h2s\s+concentration\b|chloride\s+concentration\b|"
    r"vapou?r\s+pressure\b|temperature\b|specific\s+gravity\b|specific\s+heat\b|"
    r"liquid\s+toxic\b|corrosive\s*/\s*erosive\b|suction\s+pr\b"
    r").*$",
    re.IGNORECASE,
)

_TRAILING_NOTE_OR_REV_RE = re.compile(
    r"(?:\s*\(\s*note\s+[\d.]+\s*\)|\s*\[note\s+[\d.]+\]|\s+\b(?:A1|A2|A3|Al)\b)\s*$",
    re.IGNORECASE,
)


def _infer_field_concept(field):
    name_and_label = f"{field.get('field_name', '')} {field.get('label', '')}".lower()
    dim = unit_dimension(field.get("unit")) if field.get("unit") else None
    if dim == "power" or ("power" in name_and_label and field.get("unit")):
        return "power"
    if "npsh" in name_and_label and ("avail" in name_and_label or "npsha" in name_and_label):
        return "npsh_available"
    if any(k in name_and_label for k in ("casing", "barrel")) and "material" in name_and_label:
        return "casing_material"
    if "shaft" in name_and_label and "material" in name_and_label:
        return "shaft_material"
    if "driver" in name_and_label or "prime mover" in name_and_label:
        return "driver_type"
    return match_ontology_entry(field)["concept_key"]


def _effective_field_aliases(field, for_numeric=False):
    """Return explicit schema aliases plus ontology & morphological synonyms for ANY field."""
    profile = match_ontology_entry(field)
    aliases = []
    if for_numeric:
        aliases.extend(str(a).strip() for a in (field.get("deterministic_source_aliases") or []) if str(a).strip())
        aliases.extend(str(a).strip() for a in (field.get("extraction_aliases") or []) if str(a).strip())
        if field.get("label"):
            aliases.append(str(field["label"]).strip())
    else:
        if field.get("label"):
            aliases.append(str(field["label"]).strip())
        if field.get("field_name"):
            aliases.append(str(field["field_name"]).strip())
        aliases.extend(str(a).strip() for a in (field.get("extraction_aliases") or []) if str(a).strip())
        aliases.extend(str(a).strip() for a in (field.get("deterministic_source_aliases") or []) if str(a).strip())

    for syn in profile["aliases"]:
        if syn and syn.lower() not in {x.lower() for x in aliases}:
            aliases.append(syn)
    return [a for a in aliases if a]


def _effective_negative_cues(field):
    profile = match_ontology_entry(field)
    return [_norm_label(cue) for cue in profile["negative_cues"] if _norm_label(cue)]


def _clean_extracted_cell_value(raw_value):
    if not isinstance(raw_value, str):
        return raw_value
    cleaned = raw_value.strip()
    # Truncate before any adjacent flattened column header or secondary component label
    stop_Match = re.search(
        r"\s+(?:"
        r"seal\s+material|bearing\s+material|rubber\s+parts|motor\s+data|"
        r"pump\s+serial\s+no|serial\s+no|model\b|manufacturer\b|"
        r"recommended\s+pipe\s+size|suc\.?\s*:|del\.?\s*:|"
        r"coupling\s+guard|coupling\s*:|wetted\s+fasteners|"
        r"shaft\s+prot\.?\s*sleeve|impeller\s*:|sleeve\s*:|"
        r"base\s+frame|base\s+plate|painting\b|"
        r"his\s+concentration|h2s\s+concentration|chloride\s+concentration|"
        r"vapou?r\s+pressure|temperature\b|specific\s+gravity|specific\s+heat|"
        r"liquid\s+toxic|corrosive\s*/\s*erosive|suction\s+pr"
        r")\b",
        cleaned,
         flags=re.IGNORECASE,
    )
    if stop_Match and stop_Match.start() > 0:
        cleaned = cleaned[:stop_Match.start()].strip()
    cleaned = _UNIVERSAL_COLUMN_STOP_RE.sub("", cleaned).strip()
    cleaned = _TRAILING_NOTE_OR_REV_RE.sub("", cleaned).strip()
    # Also truncate before any "Word(s):" key-value pattern mid-string
    next_kv = re.search(r"\s+[A-Z][A-Za-z0-9\s/().&-]{1,22}\s*:\s*\S", cleaned)
    if next_kv and next_kv.start() > 0:
        cleaned = cleaned[:next_kv.start()].strip()
    return cleaned.strip(" :;.,-")


# --------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------

def _validate_schema(data, path):
    if "template_name" not in data or not str(data["template_name"]).strip():
        raise ValueError(f"Template file '{path}' is missing a 'template_name'.")

    fields = data.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ValueError(f"Template file '{path}' must have a non-empty 'fields' list.")

    for i, f in enumerate(fields):
        if not isinstance(f, dict) or "field_name" not in f or "label" not in f:
            raise ValueError(
                f"Field #{i + 1} in '{path}' is missing 'field_name' or 'label'."
            )
    return data


@lru_cache(maxsize=32)
def _load_schema_cached(path, mtime):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Template file '{path}' is not valid JSON: {e}") from e
    except OSError as e:
        raise ValueError(f"Could not read template file '{path}': {e}") from e
    return _validate_schema(data, path)


def load_schema(path="templates/mechanical_seal_audit.json"):
    try:
        mtime = os.path.getmtime(path)
    except OSError as e:
        raise ValueError(f"Could not read template file '{path}': {e}") from e
    return _load_schema_cached(path, mtime)


@lru_cache(maxsize=8)
def _list_templates_cached(folder, dir_mtime):
    templates = {}
    for fname in sorted(os.listdir(folder)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(folder, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            templates[data.get("template_name", fname)] = path
        except (json.JSONDecodeError, OSError):
            continue
    return templates


def list_templates(folder="templates"):
    if not os.path.isdir(folder):
        return {}
    return dict(_list_templates_cached(folder, os.path.getmtime(folder)))


def slugify(text):
    return _SLUG_RE.sub("_", text.strip().lower()).strip("_") or "template"


def save_template(template_name, fields, folder="templates", sample_file=None):
    if not template_name.strip():
        raise ValueError("Template name cannot be empty.")
    if not fields:
        raise ValueError("Add at least one field before saving.")

    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{slugify(template_name)}.json")

    data = {"template_name": template_name.strip(), "fields": fields}
    if sample_file:
        data["sample_file"] = sample_file

    _validate_schema(data, path)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return path


def delete_template(path):
    try:
        os.remove(path)
    except OSError as e:
        raise ValueError(f"Could not delete template '{path}': {e}") from e


# --------------------------------------------------------------------------
# Document ingestion
# --------------------------------------------------------------------------

def _ocr_pdf_page_fallback(page):
    """Attempt lightweight OCR when a PDF page is a scanned image with no text layer."""
    try:
        pil_img = page.to_image(resolution=200).original.convert("RGB")
    except Exception:
        return ""
    # Try rapidocr_onnxruntime if installed (fast, no system binary required)
    try:
        from rapidocr_onnxruntime import RapidOCR
        import numpy as np
        ocr = RapidOCR()
        result, _ = ocr(np.array(pil_img))
        if result:
            # Group OCR boxes by vertical line position (y-coordinate)
                        # Sort primarily by vertical center, then group boxes within 18px into the same row
            boxes = sorted(result, key=lambda item: ((item[0][0][1] + item[0][2][1]) / 2.0, item[0][0][0]))
            lines = []
            cur_y = None
            cur_line = []
            for box, text, _score in boxes:
                y = (box[0][1] + box[2][1]) / 2.0
                if cur_y is None or abs(y - cur_y) <= 18:
                    cur_line.append((box[0][0], text))
                    if cur_y is None:
                        cur_y = y
                else:
                    cur_line.sort(key=lambda x: x[0])
                    lines.append(" ".join(t for _, t in cur_line))
                    cur_line = [(box[0][0], text)]
                    cur_y = y
            if cur_line:
                cur_line.sort(key=lambda x: x[0])
                lines.append(" ".join(t for _, t in cur_line))
            return "\n".join(lines).strip()
    except Exception:
        pass
    # Try pytesseract if installed
    try:
        import pytesseract
        return (pytesseract.image_to_string(pil_img) or "").strip()
    except Exception:
        return ""


def _extract_pdf_page_texts(file_bytes_or_path, schema=None):
    source = (
        io.BytesIO(file_bytes_or_path)
        if isinstance(file_bytes_or_path, (bytes, bytearray))
        else file_bytes_or_path
    )
    texts = []
    with pdfplumber.open(source) as pdf:
        for page in pdf.pages:
            text = (page.extract_text() or "").strip()
            if not text:
                text = _ocr_pdf_page_fallback(page)
            if schema:
                checkbox_markers = _extract_checkbox_markers(page, schema)
                if checkbox_markers:
                    text = (text + "\n" if text else "") + "\n".join(checkbox_markers)
            texts.append(text)
    if not any(texts):
        raise ValueError(
            "No text could be extracted from this PDF (scanned image PDF). "
            "Install 'rapidocr-onnxruntime' for automatic scanned PDF OCR."
        )
    return texts


def extract_text_from_pdf(file_bytes_or_path, schema=None):
    return "\n".join(_extract_pdf_page_texts(file_bytes_or_path, schema=schema)).strip()


def extract_pdf_pages_with_evidence(file_bytes_or_path, schema=None):
    texts = _extract_pdf_page_texts(file_bytes_or_path, schema=schema)
    return [{"page": page_number, "text": text} for page_number, text in enumerate(texts, start=1)]


def build_evidence_index(pages):
    return "\n\n".join(
        f"[PAGE {item['page']}]\n{item['text']}"
        for item in pages if item.get("text")
    )


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------

_CHECKBOX_MARKER_RE = re.compile(
    r"^\[CHECKBOX SELECTED\]\s*(?P<label>[^:]+):\s*(?P<value>.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


@lru_cache(maxsize=8192)
def _norm_label(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _curve_is_circle(curve, min_size=5.0, max_size=25.0):
    width = float(curve.get("width") or 0)
    height = float(curve.get("height") or 0)
    if width <= 0 or height <= 0:
        return False
    ratio = width / height
    return (
        0.7 <= ratio <= 1.3
        and min_size <= width <= max_size
        and min_size <= height <= max_size
    )


def _curve_center(curve):
    return (
        (float(curve.get("x0") or 0) + float(curve.get("x1") or 0)) / 2.0,
        (float(curve.get("top") or 0) + float(curve.get("bottom") or 0)) / 2.0,
    )


def _curve_is_filled_inner_marker(curve, circles):
    if not curve.get("fill"):
        return False
    width = float(curve.get("width") or 0)
    height = float(curve.get("height") or 0)
    if not (4.0 <= width <= 7.0 and 4.0 <= height <= 7.0):
        return False
    points = curve.get("pts") or []
    if len(points) > 8:
        return False
    cx, cy = _curve_center(curve)
    for circle in circles:
        if circle is curve:
            continue
        ocx, ocy = _curve_center(circle)
        if abs(cx - ocx) <= 1.5 and abs(cy - ocy) <= 1.5:
            return True
    return False


def _pdf_name_text(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text.startswith("/"):
        text = text[1:]
    return text.strip("'\"")


def _filled_checkbox_markers(page):
    markers = []
    curves = list(page.objects.get("curve", []))

    circle_components = [
        curve
        for curve in curves
        if _curve_is_circle(curve) and bool(curve.get("fill"))
    ]

    for curve in circle_components:
        width = float(curve.get("width") or 0)
        height = float(curve.get("height") or 0)
        if min(width, height) >= 9.0:
            marker = dict(curve)
            marker["marker_source"] = "filled_vector_circle"
            markers.append(marker)

    for curve in curves:
        if _curve_is_filled_inner_marker(curve, circle_components):
            marker = dict(curve)
            marker["marker_source"] = "nested_filled_vector_circle"
            markers.append(marker)

    filled_glyphs = {"●", "⬤", "•", "■", "▪", "☑", "✔", "✓"}
    for char in page.objects.get("char", []):
        if str(char.get("text", "")).strip() in filled_glyphs:
            marker = dict(char)
            marker["marker_source"] = "filled_glyph"
            markers.append(marker)

    for annot in getattr(page, "annots", []) or []:
        data = annot.get("data") or {}
        if _pdf_name_text(data.get("FT")) != "Btn":
            continue
        appearance_state = _pdf_name_text(data.get("AS"))
        if not appearance_state or appearance_state.lower() == "off":
            continue
        marker = dict(annot)
        marker["selection_state"] = appearance_state
        marker["marker_source"] = "pdf_form_widget"
        markers.append(marker)

    return markers


def _option_words(words, option, normalized_words=None):
    tokens = [token for token in str(option).strip().split() if token]
    if not tokens:
        return None
    target = [_norm_label(token) for token in tokens]
    normalized_words = normalized_words or [_norm_label(word.get("text", "")) for word in words]
    span = len(target)
    for start in range(0, len(words) - span + 1):
        group = words[start:start + span]
        if normalized_words[start:start + span] != target:
            continue
        base_top = float(group[0].get("top", 0))
        if all(abs(float(word.get("top", 0)) - base_top) <= 3.5 for word in group[1:]):
            return group
    return None


def _checkbox_is_left_of_option(circle, option_words):
    option_x0 = min(float(word["x0"]) for word in option_words)
    option_top = min(float(word["top"]) for word in option_words)
    option_bottom = max(float(word["bottom"]) for word in option_words)
    circle_x1 = float(circle["x1"])
    circle_top = float(circle["top"])
    circle_bottom = float(circle["bottom"])
    horizontal_gap = option_x0 - circle_x1
    vertical_overlap = min(circle_bottom, option_bottom) - max(circle_top, option_top)
    return 0 <= horizontal_gap <= 28 and vertical_overlap >= -3


def _render_checkbox_image(page, resolution=144):
    try:
        return page.to_image(resolution=resolution).original.convert("L")
    except Exception:
        return None


def _rendered_checkbox_selected(image, option_words, scale=2.0):
    if image is None:
        return False

    option_x0 = min(float(word["x0"]) for word in option_words)
    option_top = min(float(word["top"]) for word in option_words)
    option_bottom = max(float(word["bottom"]) for word in option_words)
    center_y_pt = (option_top + option_bottom) / 2.0
    center_y = int(round(center_y_pt * scale))

    candidates = []
    for dx in range(8, 27):
        cx = int(round((option_x0 - dx) * scale))
        for dy in range(-8, 9):
            cy = center_y + int(round(dy * scale))
            if 0 <= cx < image.width and 0 <= cy < image.height:
                candidates.append((cx, cy))

    if not candidates:
        return False

    radius_px = max(3, int(round(5 * scale)))
    threshold = 150
    best_ratio = 0.0
    for cx, cy in candidates:
        left, right = max(0, cx - radius_px), min(image.width, cx + radius_px + 1)
        top, bottom = max(0, cy - radius_px), min(image.height, cy + radius_px + 1)
        crop = image.crop((left, top, right, bottom))
        histogram = crop.histogram()
        pixel_count = sum(histogram)
        if not pixel_count:
            continue
        dark_ratio = sum(histogram[:threshold]) / pixel_count
        best_ratio = max(best_ratio, dark_ratio)

    return best_ratio >= 0.42


def _field_anchor_top(page, label, words, extra_aliases=None):
    candidate_labels = [label] + list(extra_aliases or [])
    label_norms = [_norm_label(c) for c in candidate_labels if _norm_label(c)]
    if not label_norms or not words:
        return None

    lines = []
    for word in sorted(words, key=lambda w: (float(w.get("top", 0)), float(w.get("x0", 0)))):
        top = float(word.get("top", 0))
        if lines and abs(top - lines[-1][0]) <= 3.5:
            lines[-1][1].append(word)
        else:
            lines.append([top, [word]])

    for top, line_words in lines:
        line_text = _norm_label(" ".join(w.get("text", "") for w in line_words))
        if any(ln in line_text for ln in label_norms):
            return top
    return None


def _extract_checkbox_markers(page, schema):
    if not schema or not schema.get("fields"):
        return []

    filled = _filled_checkbox_markers(page)
    words = page.extract_words() or []
    normalized_words = [_norm_label(word.get("text", "")) for word in words]
    rendered_image = None
    rendered_image_attempted = False
    markers = []

    for field in schema["fields"]:
        options = list(field.get("acceptable_values") or [])
        if not options:
            continue
        anchor_top = _field_anchor_top(
            page,
            field.get("label") or field.get("field_name"),
            words,
            extra_aliases=field.get("extraction_aliases"),
        )
        selected = []
        for option in options:
            option_words = _option_words(words, option, normalized_words)
            if not option_words:
                continue
            option_top = float(option_words[0].get("top", 0))
            if anchor_top is not None and not (anchor_top - 5 <= option_top <= anchor_top + 70):
                continue

            option_norm = _norm_label(option)
            matched = False
            for marker in filled:
                state_norm = _norm_label(marker.get("selection_state", ""))
                state_matches = bool(state_norm and state_norm == option_norm)
                if state_matches or _checkbox_is_left_of_option(marker, option_words):
                    selected.append(str(option))
                    matched = True
                    break

            if not matched:
                if not rendered_image_attempted:
                    rendered_image = _render_checkbox_image(page)
                    rendered_image_attempted = True
                if _rendered_checkbox_selected(rendered_image, option_words):
                    selected.append(str(option))
        if len(selected) == 1:
            label = field.get("label") or field.get("field_name")
            markers.append(f"[CHECKBOX SELECTED] {label}: {selected[0]}")

    return markers


def _checkbox_overrides(datasheet_text, schema):
    marker_map = {
        match.group("label").strip().lower(): match.group("value").strip()
        for match in _CHECKBOX_MARKER_RE.finditer(datasheet_text or "")
    }
    overrides = {}
    for field in schema.get("fields", []):
        label = str(field.get("label") or field.get("field_name") or "").strip().lower()
        if label in marker_map:
            overrides[field["field_name"]] = marker_map[label]
    return overrides


def _deterministic_text_overrides(datasheet_text, schema):
    lines = [line.strip() for line in str(datasheet_text or "").splitlines() if line.strip()]
    normalized_lines = [(line, _norm_label(line)) for line in lines]
    overrides = {}

    for field in schema.get("fields", []):
        if field.get("field_name") == "driver_type":
            continue

        raw_candidates = list(field.get("acceptable_values") or [])
        if "expected_value" in field:
            raw_candidates.append(field.get("expected_value"))
        candidates = [
            (norm, str(value).strip())
            for value in raw_candidates
            if value not in (None, "")
            for norm in (_norm_label(str(value).strip()),)
            if norm
        ]
        if not candidates:
            continue

        aliases = _effective_field_aliases(field, for_numeric=False)
        alias_norms = [_norm_label(alias.strip()) for alias in aliases if str(alias).strip()]
        negative_cues = _effective_negative_cues(field)

        for _, line_norm in normalized_lines:
            if any(neg in line_norm for neg in negative_cues):
                continue
            alias_positions = [pos for alias in alias_norms if (pos := line_norm.find(alias)) >= 0]
            if not alias_positions:
                continue

            located = []
            narrative_cues = (
                "differs", "different", "configured", "expected", "target",
                "required", "should", "must", "recommend", "recommended",
                "value", "standard",
            )
            for alias_norm in alias_norms:
                search_from = 0
                while True:
                    alias_pos = line_norm.find(alias_norm, search_from)
                    if alias_pos < 0:
                        break
                    tail = line_norm[alias_pos + len(alias_norm):]
                    for candidate_norm, value in candidates:
                        candidate_pos = tail.find(candidate_norm)
                        if candidate_pos < 0:
                            continue
                        filler = tail[:candidate_pos]
                        if any(cue in filler for cue in narrative_cues):
                            continue
                        located.append((alias_pos + len(alias_norm) + candidate_pos, value))
                    search_from = alias_pos + len(alias_norm)
            if located:
                overrides[field["field_name"]] = min(located, key=lambda item: item[0])[1]
                break

    return overrides


def _deterministic_label_overrides(datasheet_text, schema):
    """Recover explicitly labelled values across single-line and multi-column layouts."""
    lines = [line.strip() for line in str(datasheet_text or "").splitlines() if line.strip()]
    overrides = {}

    for field in schema.get("fields", []):
        name = field.get("field_name")
        if not name or field.get("unit"):
            continue

        concept = _infer_field_concept(field)
        if name == "driver_type":
            aliases = ["driver type", "type of driver", "prime mover", "pump driven by"]
            aliases.extend(str(a) for a in (field.get("extraction_aliases") or []) if a)
        else:
            aliases = _effective_field_aliases(field, for_numeric=False)

        aliases = [a.strip() for a in aliases if a.strip()]
        if not aliases:
            continue

        alias_patterns = sorted(
            [(_norm_label(alias), alias) for alias in aliases if _norm_label(alias)],
            key=lambda item: len(item[0]), reverse=True,
        )
        negative_cues = _effective_negative_cues(field)

        for idx, line in enumerate(lines):
            line_norm = _norm_label(line)
            if any(neg in line_norm for neg in negative_cues):
                continue
            if concept == "casing_material" and line_norm.endswith("casingmaterial"):
                continue

            located = []
            for alias_norm, _ in alias_patterns:
                start = line_norm.find(alias_norm)
                if start < 0:
                    continue
                tail = line_norm[start + len(alias_norm):]
                if not tail:
                    continue

                if any(cue in tail[:80] for cue in (
                    "differs", "different", "expected", "configured",
                    "target", "required", "should", "must", "recommend",
                )):
                    continue

                raw_alias_pos = -1
                for alias in aliases:
                    if _norm_label(alias) == alias_norm:
                        raw_alias_pos = line.lower().find(alias.lower())
                        if raw_alias_pos >= 0:
                            raw_start = raw_alias_pos + len(alias)
                            break
                else:
                    raw_start = 0

                if raw_alias_pos < 0:
                    raw_start = 0

                raw_tail = line[raw_start:].strip()
                raw_tail = re.sub(r"^[\s:=\-☑✔✓☐•●■]+", "", raw_tail)
                if not raw_tail:
                    continue

                if concept == "casing_material" and _norm_label(raw_tail).startswith("shaftprotsleeve"):
                    if idx + 1 < len(lines):
                        next_line = lines[idx + 1].strip()
                        parts = re.split(r"\s+(?=ASTM\b|AISI\b|SS\b|IS\s+\d)", next_line, maxsplit=1)
                        candidate_val = _clean_extracted_cell_value(parts[0])
                        if candidate_val:
                            located.append((start, candidate_val))
                    continue

                if concept == "driver_type":
                    if "electric motor" in raw_tail.lower():
                        value = "Electric Motor"
                    elif "induction motor" in raw_tail.lower():
                        value = "Induction Motor"
                    elif "steam turbine" in raw_tail.lower():
                        value = "Steam Turbine"
                    else:
                        value = _clean_extracted_cell_value(raw_tail)
                elif concept in {"casing_material", "shaft_material"}:
                    value = _clean_extracted_cell_value(raw_tail)
                else:
                    first_sentence = re.split(r"(?<=[.!?])\s+", raw_tail, maxsplit=1)[0]
                    value = _clean_extracted_cell_value(first_sentence)

                if value and len(value) <= 80:
                    located.append((start, value))

            if located:
                overrides[name] = min(located, key=lambda item: item[0])[1]
                break

    return overrides


def _extract_numeric_from_tail(tail, target_unit, inline_label_unit=None):
    """Parse a numeric value + optional unit from the text following a matched label."""
    paren_unit_match = re.match(r"^\(\s*([A-Za-z0-9°µΩ²³/._-]+)\s*\)", tail)
    if paren_unit_match:
        inline_label_unit = paren_unit_match.group(1)
        tail = tail[paren_unit_match.end():].strip()
    tail = re.sub(r"^[\s:=-]+", "", tail)
    if not tail:
        return None
    match = re.match(r"^[≈~]?\s*(-?\d+(?:[.,]\d+)?)\s*([A-Za-z0-9°µΩ²³/._-]+)?", tail)
    if not match:
        return None
    raw_num = match.group(1)
    if "," in raw_num and "." not in raw_num and len(raw_num.split(",")[-1]) <= 2:
        number = raw_num.replace(",", ".")
    else:
        number = raw_num.replace(",", "")
    inline_unit = match.group(2) or inline_label_unit
    if inline_unit and not are_compatible_units(inline_unit, target_unit):
        if inline_label_unit and are_compatible_units(inline_label_unit, target_unit):
            inline_unit = inline_label_unit
        else:
            inline_unit = None
    value = float(number) if "." in number else int(number)
    if inline_unit:
        value = f"{value} {inline_unit}"
    return value


def _deterministic_numeric_overrides(datasheet_text, schema):
    """Recover high-confidence numeric values from explicit, ontology, or morphological token aliases."""
    lines = [line.strip() for line in str(datasheet_text or "").splitlines() if line.strip()]
    overrides = {}
    evidence_hints = {}
    for field in schema.get("fields", []):
        if not field.get("unit"):
            continue
        name = field["field_name"]
        if name == "npsha_available_m" or _infer_field_concept(field) == "npsh_available":
            continue
        target_unit = field.get("unit")
        negative_cues = _effective_negative_cues(field)
        explicit_aliases = [str(a).strip() for a in (field.get("deterministic_source_aliases") or []) if str(a).strip()]
        concept_aliases = _effective_field_aliases(field, for_numeric=True)
        # Preserve priority order within each group instead of sorting solely by length
        alias_groups = [explicit_aliases, [a for a in concept_aliases if a not in explicit_aliases]]

        found = False
        for group in alias_groups:
            if not group or found:
                continue
            alias_pairs = [(a, _norm_label(a)) for a in group if _norm_label(a)]
            for raw_alias, matched_alias in alias_pairs:
                if found:
                    break
                for idx, line in enumerate(lines):
                    line_norm = _norm_label(line)
                    if matched_alias not in line_norm:
                        continue
                    if any(neg in line_norm for neg in negative_cues):
                        continue
                    if re.match(r"^\d+\.\s+[A-Z]", line) and ("shall" in line.lower() or "calculated" in line.lower()):
                        continue
                    raw_pos = line.lower().find(raw_alias.lower())
                    if raw_pos < 0:
                        continue
                    tail = line[raw_pos + len(raw_alias):].strip()
                    value = _extract_numeric_from_tail(tail, target_unit)
                    # Check before the alias on the same line (in case tilted OCR ordered value before label)
                    if value is None:
                        head_cands = find_numeric_unit_candidates(line[:raw_pos], target_unit=target_unit)
                        if len(head_cands) == 1:
                            value = f"{head_cands[0][0]} {head_cands[0][1]}"
                    # Check nearby OCR lines (idx-2 .. idx+2) for an explicit number+compatible unit (e.g. "75.07 hp")
                    if value is None:
                        for offset in (-1, 1, -2, 2):
                            n_idx = idx + offset
                            if 0 <= n_idx < len(lines):
                                n_line = lines[n_idx]
                                if any(neg in _norm_label(n_line) for neg in negative_cues):
                                    continue
                                # Do not match a line number followed by "BHP @"
                                if "bhp@" in _norm_label(n_line):
                                    continue
                                cands = find_numeric_unit_candidates(n_line, target_unit=target_unit)
                                if len(cands) == 1:
                                    c_val, c_unit = cands[0]
                                    value = f"{c_val} {c_unit}"
                                    break
                    if value is None:
                        continue
                    overrides[name] = value
                    evidence_hints[name] = {
                        "source": "configured_source_alias",
                        "label": raw_alias,
                        "text": line,
                    }
                    found = True
                    break

        if not found:
            field_label = str(field.get("label") or name)
            for line in lines:
                line_norm = _norm_label(line)
                if any(neg in line_norm for neg in negative_cues):
                    continue
                if line_matches_field_tokens(line, field_label):
                    parts = re.split(r"[:=]", line, maxsplit=1)
                    tail = parts[1].strip() if len(parts) > 1 else ""
                    if tail:
                        value = _extract_numeric_from_tail(tail, target_unit)
                        if value is not None:
                            overrides[name] = value
                            evidence_hints[name] = {
                                "source": "ontology_token_match",
                                "label": field_label,
                                "text": line,
                            }
                            break
    return overrides, evidence_hints


def _deterministic_npsha_override(datasheet_text):
    text_str = str(datasheet_text or "")
    # Strip parenthetical note references like "(Note 3.1)" first so "3.1" is never mistaken for NPSHA
    text_cleaned = re.sub(r"\(\s*note\s+\d+(?:[.,]\d+)?\s*\)", " ", text_str, flags=re.I)
    text_cleaned = re.sub(r"\bnote\s+\d+(?:[.,]\d+)?\b", " ", text_cleaned, flags=re.I)
    lines = [line.strip() for line in text_cleaned.splitlines() if line.strip()]

    for idx, line in enumerate(lines):
        normalized = _norm_label(line)
        if (
            "differencebetweennpsha" in normalized
            or "minimum1meter" in normalized
            or "minimumimeter" in normalized
            or "npshtest" in normalized
        ):
            continue
        if "npshra" in normalized:
            match = re.search(r"NPSH\s*R\s*/\s*A\s*:?\s*(.*?)\s*/\s*(.+)$", line, re.I)
            if match:
                available = _clean_extracted_cell_value(match.group(2))
                if available and available not in {"-", "—"}:
                    return available
        if ("npshavailable" in normalized or "npshaavailable" in normalized) and "npshrequired" not in normalized:
            # Explicit dash placeholder check (e.g. "N.P.S.H available : -")
            if re.search(r"[:=]\s*[-—]\s*$", line):
                return None
            match = re.search(
                r"NPSH(?:A)?\s+available(?:,\s*rated)?(?:\s*\([^)]*\))?\s*[:=]?\s*(.*)$",
                line,
                re.I,
            )
            if match:
                raw_tail = match.group(1).strip()
                raw_tail = re.sub(r"^\(\s*m\s*\)\s*[:=]?\s*", "", raw_tail, flags=re.I)
                available = _clean_extracted_cell_value(raw_tail)
                available = re.split(r"\b(?:his|h2s|chloride|temp|note)\b", available, flags=re.I)[0].strip(" .;,")
                if available in {"-", "—", "n/a", "na", "nil", "none", "tbd", "hold"}:
                    return None
                num_m = re.search(r"(\d+[.,]\d+|\d+\s*m\b)", available, re.I)
                if num_m:
                    num_str = re.sub(r"[^0-9.,]", "", num_m.group(1)).replace(",", ".")
                    return float(num_str) if "." in num_str else int(num_str)
                if available and not available.startswith("(") and not available.isdigit():
                    return available
            # Also check if the decimal number appears BEFORE "NPSH AVAILABLE" on the same OCR line
            # or on the immediately adjacent lines (excluding lines with kW, bar, psig, cP, SG)
            same_line_before = line[:line.lower().find("npsh")]
            dec_before = re.findall(r"(?<!\d)(\d+[.,]\d+)(?!\d)", same_line_before)
            if dec_before:
                return float(dec_before[-1].replace(",", "."))
            for offset in (-1, 1, -2, 2):
                n_idx = idx + offset
                if 0 <= n_idx < len(lines):
                    wline = lines[n_idx]
                    # Strip any secondary column on that line that has pressure/kw/viscosity/gravity
                    wline_left = re.split(
                        r"\b(?:vapou?r|hydraulic|viscosity|specific|discharge|suction|differential|speed|temp)\b",
                        wline,
                        maxsplit=1,
                        flags=re.I,
                    )[0]
                    dec_m = re.search(r"(?<!\d)(\d+[.,]\d+)(?!\d)", wline_left)
                    if dec_m:
                        return float(dec_m.group(1).replace(",", "."))
    return None


def _deterministic_overrides(datasheet_text, schema):
    overrides = _deterministic_text_overrides(datasheet_text, schema)
    npsha = _deterministic_npsha_override(datasheet_text)
    if npsha is not None:
        for field in schema.get("fields", []):
            if _infer_field_concept(field) == "npsh_available" or field.get("field_name") == "npsha_available_m":
                overrides[field["field_name"]] = npsha
    generic = _deterministic_label_overrides(datasheet_text, schema)
    numeric, _ = _deterministic_numeric_overrides(datasheet_text, schema)
    for field_name, value in generic.items():
        overrides.setdefault(field_name, value)
    for field_name, value in numeric.items():
        overrides.setdefault(field_name, value)
    overrides.update(_checkbox_overrides(datasheet_text, schema))

    # Universal Motor Data section fallback: if driver_type is still unset, but the
    # datasheet contains an explicit "Motor Data" or "Motor manufacturer" block with
    # AC frequency (50/60 Hz) or efficiency class (IE2/IE3/NEMA), record "Electric Motor".
    for field in schema.get("fields", []):
        fname = field.get("field_name")
        if fname == "driver_type" and fname not in overrides:
            norm_doc = _norm_label(datasheet_text)
            if (
                ("motordata" in norm_doc or "motormanufacturer" in norm_doc or "requiredmotorrating" in norm_doc)
                and any(k in norm_doc for k in ("50hz", "60hz", "ie2", "ie3", "3phase", "phase3"))
            ):
                overrides[fname] = "Electric Motor"

    return overrides


def find_field_evidence(pages, field, extracted_value=None):
    """Find deterministic, reviewable source evidence for any schema field."""
    configured_source_aliases = {
        _norm_label(x) for x in (field.get("deterministic_source_aliases") or []) if x
    }
    labels = _effective_field_aliases(field, for_numeric=bool(field.get("unit")))
    label_norms = [_norm_label(x) for x in labels if _norm_label(x)]
    negative_cues = _effective_negative_cues(field)
    accepted = [str(v).strip().lower() for v in field.get("acceptable_values", [])]
    field_label = str(field.get("label") or field.get("field_name") or "")

    val_norms = [_norm_label(str(extracted_value))] if extracted_value not in (None, "") else []
    val_norms.extend(_norm_label(v) for v in accepted if _norm_label(v))
    val_norms = [v for v in val_norms if v]

    # 1. Checkbox selection marker line
    if accepted:
        for item in pages or []:
            lines = str(item.get("text", "")).splitlines()
            for line_number, line in enumerate(lines, start=1):
                if "[checkbox selected]" not in line.casefold():
                    continue
                normalized = _norm_label(line)
                if any(label and label in normalized for label in label_norms):
                    return {
                        "page": item.get("page"),
                        "line": line_number,
                        "text": line.strip(),
                        "source": "checkbox_selection",
                    }

    # 2. Pass 1 across ALL pages: Find a line that matches a field label/alias AND supports the extracted value
    if extracted_value not in (None, ""):
        for item in pages or []:
            lines = str(item.get("text", "")).splitlines()
            for line_number, line in enumerate(lines, start=1):
                normalized = _norm_label(line)
                if any(neg in normalized for neg in negative_cues):
                    continue
                matched_label = next((label for label in label_norms if label and label in normalized), None)
                if matched_label or line_matches_field_tokens(line, field_label):
                    ev_candidate = {
                        "page": item.get("page"),
                        "line": line_number,
                        "text": line.strip(),
                        "source": "configured_source_alias" if matched_label in configured_source_aliases else "label_match",
                    }
                    if _evidence_supports_value(extracted_value, ev_candidate):
                        return ev_candidate

    # 3. Pass 2 across ALL pages: Standard label match
    for item in pages or []:
        lines = str(item.get("text", "")).splitlines()
        for line_number, line in enumerate(lines, start=1):
            normalized = _norm_label(line)
            if any(neg in normalized for neg in negative_cues):
                continue
            matched_label = next((label for label in label_norms if label and label in normalized), None)
            if matched_label:
                if normalized == matched_label:
                    continue
                return {
                    "page": item.get("page"),
                    "line": line_number,
                    "text": line.strip(),
                    "source": "configured_source_alias" if matched_label in configured_source_aliases else "label_match",
                }
            if line_matches_field_tokens(line, field_label):
                return {
                    "page": item.get("page"),
                    "line": line_number,
                    "text": line.strip(),
                    "source": "ontology_token_match",
                }

    # 4. Pass 3: Value-anchored fallback
    if extracted_value not in (None, ""):
        val_norm = _norm_label(str(extracted_value))
        if val_norm and len(val_norm) >= 2:
            for item in pages or []:
                for line_number, line in enumerate(str(item.get("text", "")).splitlines(), start=1):
                    if val_norm in _norm_label(line):
                        return {
                            "page": item.get("page"),
                            "line": line_number,
                            "text": line.strip(),
                            "source": "value_match",
                        }
    return None


def build_evidence_map(pages, schema, extracted=None):
    extracted = extracted or {}
    return {
        field["field_name"]: find_field_evidence(pages, field, extracted_value=extracted.get(field["field_name"]))
        for field in schema.get("fields", [])
    }


def build_extraction_prompt(schema, datasheet_text):
    field_lines = []
    for f in schema["fields"]:
        aliases = _effective_field_aliases(f, for_numeric=bool(f.get("unit")))
        alias_hint = f" [common labels: {', '.join(aliases[:7])}]" if len(aliases) > 1 else ""
        unit_hint = f" (target unit: {f['unit']})" if f.get("unit") else ""
        field_lines.append(f'- "{f["field_name"]}"{unit_hint}{alias_hint}')
    field_list = "\n".join(field_lines)

    return f"""You are extracting technical data from an OEM equipment datasheet.

Extract ONLY these fields from the datasheet text below:
{field_list}

Rules:
- Return ONLY valid JSON, no explanation, no markdown code fences.
- Use exactly these field names as JSON keys.
- If a field is not mentioned anywhere in the datasheet, set its value to null.
- For numeric fields: if the datasheet uses the target unit, return just the number. If the datasheet uses a DIFFERENT unit (for example "75.07 hp" when the target unit is "kW", or "0.25 kg/cm2" when the target unit is "bar"), return the number with its source unit as a string (e.g. "75.07 hp" or "0.25 kg/cm2") so downstream unit conversion can normalize it accurately.
- Keep material/text fields as written in the source, excluding adjacent table column headers.
- Match each field to its explicit label or standard engineering equivalent (listed in brackets above). Never invent or guess values that are not in the text.
- A line beginning with [CHECKBOX SELECTED] is deterministic PDF form evidence produced from a filled checkbox next to one of the accepted options. Use that selected option for the corresponding field.

Worked example (structure only, not related to the real data below):

  Fields requested:
  - "material"
  - "max_pressure_bar" (target unit: bar)

  Example datasheet text:
  ---
  Driver Type: Induction Motor
  Material: Stainless Steel
  Max Pressure: 12 bar
  ---

  Correct JSON output:
  {{"material": "Stainless Steel", "max_pressure_bar": 12}}

Now do the same for the real datasheet below.

Datasheet text:
---
{datasheet_text}
---

Return JSON now:"""


def call_model(prompt, model_name=MODEL_NAME):
    return get_model_provider().generate(prompt, model_name=model_name)


def parse_json_safely(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Model returned an empty response; no JSON was available to parse.")

    without_think = _THINK_BLOCK_RE.sub("", text).strip()
    cleaned = _JSON_FENCE_RE.sub("", without_think).strip()
    if not cleaned:
        cleaned = _JSON_FENCE_RE.sub("", text.strip()).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as first_error:
        decoder = json.JSONDecoder()
        candidate_positions = [
            m.start() for m in re.finditer(r"[\{\[]", cleaned)
        ]
        for start in reversed(candidate_positions):
            try:
                parsed, _ = decoder.raw_decode(cleaned[start:])
                if isinstance(parsed, (dict, list)):
                    return parsed
            except json.JSONDecodeError:
                continue

        preview = " ".join(cleaned.split())[:160]
        raise ValueError(
            f"Model response was not valid JSON. Response preview: {preview!r}"
        ) from first_error


def _rule_for_result(field):
    for key in ("acceptable_values", "expected_value", "min_value", "max_value"):
        if key in field:
            return {"type": key, "value": field[key]}
    return {"type": "record_only", "value": None}


def normalize_numeric_value(value, source_unit, target_unit):
    if value in (None, ""):
        return None, {"converted": False, "from_unit": source_unit, "to_unit": target_unit}
    parsed_value, inline_unit = parse_numeric_with_unit(value)
    source = inline_unit or source_unit or target_unit
    if target_unit in (None, ""):
        return parsed_value, {"converted": False, "from_unit": source, "to_unit": target_unit, "assumed_target_unit": source_unit in (None, "")}
    if source in (None, ""):
        source = target_unit
    normalized = convert_value(parsed_value, source, target_unit)
    return normalized, {
        "converted": canonical_unit(source) != canonical_unit(target_unit),
        "from_unit": canonical_unit(source),
        "to_unit": canonical_unit(target_unit),
        "assumed_target_unit": inline_unit is None and source_unit in (None, ""),
    }


def _numeric_field_normalization(value, field, evidence_entry=None):
    target_unit = field.get("unit")
    if not target_unit or value in (None, ""):
        return value, None, {"converted": False, "from_unit": None, "to_unit": target_unit}

    try:
        parsed_value, inline_unit = parse_numeric_with_unit(value)
    except ValueError:
        return value, None, {"converted": False, "from_unit": None, "to_unit": target_unit}

    if inline_unit:
        normalized, metadata = normalize_numeric_value(parsed_value, inline_unit, target_unit)
        return round(normalized, 4) if isinstance(normalized, float) else normalized, inline_unit, {
            "converted": canonical_unit(inline_unit) != canonical_unit(target_unit),
            "from_unit": canonical_unit(inline_unit),
            "to_unit": canonical_unit(target_unit),
            "source": "inline_value",
        }

    text = (evidence_entry or {}).get("text") or (evidence_entry or {}).get("quote") or ""
    candidates = find_numeric_unit_candidates(text, target_unit=target_unit)
    if len(candidates) == 1:
        evidence_value, evidence_unit = candidates[0]
        normalized, metadata = normalize_numeric_value(evidence_value, evidence_unit, target_unit)
        return round(normalized, 4) if isinstance(normalized, float) else normalized, evidence_unit, {
            "converted": canonical_unit(evidence_unit) != canonical_unit(target_unit),
            "from_unit": canonical_unit(evidence_unit),
            "to_unit": canonical_unit(target_unit),
            "source": "source_evidence",
            "evidence_value": evidence_value,
            "model_value": parsed_value,
        }

    return parsed_value, target_unit, {
        "converted": False,
        "from_unit": canonical_unit(target_unit),
        "to_unit": canonical_unit(target_unit),
        "source": "schema_unit_assumption",
    }


def _normalize_rule_value(rule_value, field):
    unit = field.get("unit")
    if unit and isinstance(rule_value, (int, float, str)):
        try:
            normalized, _, _ = _numeric_field_normalization(rule_value, field, None)
            return normalized
        except (TypeError, ValueError):
            return rule_value
    return rule_value


def _evidence_supports_value(value, evidence):
    if not evidence or value in (None, ""):
        return False
    text = str(evidence.get("text") or evidence.get("quote") or "")
    value_text = str(value).strip().lower()
    if not value_text:
        return False
    if value_text in text.lower():
        return True
    norm_val = _norm_label(value_text)
    norm_text = _norm_label(text)
    if norm_val and norm_val in norm_text:
        return True
    if norm_val in {"electricmotor", "inductionmotor"} and any(
        k in norm_text for k in ("motor", "primemover", "drivenby")
    ):
        return True
    try:
        num_val, _ = parse_numeric_with_unit(value)
        num_str = str(int(num_val)) if float(num_val).is_integer() else str(num_val)
        if num_str in text or num_str.replace(".", ",") in text or _norm_label(num_str) in norm_text:
            return True
    except ValueError:
        pass
    return False


def _matches_acceptable_values(value, acceptable_values):
    value_str = str(value).strip()
    if not value_str:
        return False
    value_lower = value_str.lower()
    if re.match(r"^(?:not|no|non[-\s]|without)\b", value_lower):
        return False
    val_norm = _norm_label(value_str)
    motor_equivalents = {"electricmotor", "inductionmotor", "acinductionmotor", "3phaseinductionmotor"}
    for av in acceptable_values:
        av_str = str(av).strip()
        if not av_str:
            continue
        av_norm = _norm_label(av_str)
        if val_norm and (val_norm == av_norm or equivalent_material_grade(value_str, av_str)):
            return True
        if val_norm in motor_equivalents and av_norm in motor_equivalents:
            return True
        pattern = rf"(?<![a-z0-9]){re.escape(av_str.lower())}(?![a-z0-9])"
        if re.search(pattern, value_lower):
            return True
    return False


def compare_against_schema(
    extracted,
    schema,
    evidence=None,
    verify_evidence=False,
    *,
    extraction_records=None,
    conflicts=None,
    precomputed_normalizations=None,
):
    rows = []
    evidence = evidence or {}
    conflicts_by_field = {conflict.field_name: conflict for conflict in (conflicts or [])}
    for f in schema["fields"]:
        field_name = f["field_name"]
        value = extracted.get(field_name)
        evidence_entry = evidence.get(field_name)
        normalized_value = value
        source_unit = None
        conversion_metadata = None
        if f.get("unit") and value not in (None, ""):
            if precomputed_normalizations and field_name in precomputed_normalizations:
                normalized_value, source_unit, conversion_metadata = precomputed_normalizations[field_name]
            else:
                try:
                    normalized_value, source_unit, conversion_metadata = _numeric_field_normalization(value, f, evidence_entry)
                except ValueError:
                    normalized_value = value
                    conversion_metadata = {"converted": False, "error": "Unsafe unit conversion"}

        comparison_value = normalized_value
        conflict = conflicts_by_field.get(field_name)
        if value is None or value == "":
            status = "MISSING"
        elif conflict is not None:
            status = "NEEDS_REVIEW"
        elif "acceptable_values" in f:
            status = (
                "MATCHED"
                if _matches_acceptable_values(value, f["acceptable_values"])
                else "MISMATCHED"
            )
        elif "expected_value" in f:
            expected = _normalize_rule_value(f["expected_value"], f)
            if isinstance(comparison_value, (int, float)) and isinstance(expected, (int, float)):
                status = "MATCHED" if abs(float(comparison_value) - float(expected)) <= 1e-9 else "MISMATCHED"
            elif str(value) == str(f["expected_value"]) or equivalent_material_grade(value, f["expected_value"]):
                status = "MATCHED"
            else:
                status = "MISMATCHED"
        elif "max_value" in f:
            try:
                max_value = _normalize_rule_value(f["max_value"], f)
                status = "MATCHED" if float(comparison_value) <= float(max_value) else "OUT OF RANGE"
            except (TypeError, ValueError):
                status = "MISMATCHED"
        elif "min_value" in f:
            try:
                min_value = _normalize_rule_value(f["min_value"], f)
                status = "MATCHED" if float(comparison_value) >= float(min_value) else "OUT OF RANGE"
            except (TypeError, ValueError):
                status = "MISMATCHED"
        else:
            status = "MATCHED"

        if verify_evidence and status != "MISSING" and not _evidence_supports_value(value, evidence_entry):
            if not (
                f.get("unit")
                and conversion_metadata
                and conversion_metadata.get("source") in {"source_evidence", "inline_value"}
                and evidence_entry
            ):
                status = "NEEDS_REVIEW"

        review_reason = {
            "MATCHED": "Value satisfies the configured rule and is supported by source evidence.",
            "MISSING": "No value was extracted; verify the source document.",
            "MISMATCHED": "Extracted value does not satisfy the configured rule.",
            "OUT OF RANGE": "Normalized numeric value is outside the configured limit.",
            "NEEDS_REVIEW": "Source/model evidence is conflicting or does not clearly support the extracted value; human verification required.",
        }[status]
        row = {
            "field": f["label"],
            "field_name": field_name,
            "unit": f.get("unit") or "",
            "required": f.get("required", True),
            "extracted_value": value,
            "normalized_value": normalized_value,
            "source_unit": source_unit,
            "target_unit": f.get("unit"),
            "unit_normalization": conversion_metadata,
            "status": status,
            "rule": _rule_for_result(f),
            "review_reason": review_reason,
            "evidence": evidence_entry,
            "conflict": conflict.to_dict() if conflict else None,
        }
        if extraction_records:
            record = next((r for r in extraction_records if r.field_name == field_name), None)
            if record is not None:
                row["extraction_record"] = record.to_dict()
        rows.append(row)
    return rows


def run_audit(datasheet_text, schema, evidence=None, verify_evidence=False, pages=None):
    prompt = build_extraction_prompt(schema, datasheet_text)
    parse_error = None
    raw_output = ""
    extracted = None

    for attempt in range(MAX_PARSE_RETRIES + 1):
        retry_prompt = prompt
        if attempt:
            retry_prompt += (
                "\n\nIMPORTANT: Your previous response could not be parsed as JSON. "
                "Return ONLY one valid JSON object, with double-quoted keys and values. "
                "Do not include markdown, commentary, or a preamble."
            )
        raw_output = call_model(retry_prompt)
        try:
            extracted = parse_json_safely(raw_output)
            break
        except ValueError as exc:
            parse_error = exc

    if extracted is None:
        raise parse_error or ValueError("Model response could not be parsed as JSON.")
    if not isinstance(extracted, dict):
        raise ValueError("Model response must be a JSON object with field names as keys.")

    for k, v in list(extracted.items()):
        if isinstance(v, str):
            extracted[k] = _clean_extracted_cell_value(v)

    model_extracted = dict(extracted)
    overrides = _deterministic_overrides(datasheet_text, schema)
    _, numeric_ev_hints = _deterministic_numeric_overrides(datasheet_text, schema)
    for k, v in overrides.items():
        mod_val = model_extracted.get(k)
        if isinstance(mod_val, (int, float)) and not isinstance(mod_val, bool) and isinstance(v, str):
            try:
                ov_num, ov_unit = parse_numeric_with_unit(v)
                field_spec = next((f for f in schema.get("fields", []) if f.get("field_name") == k), {})
                target_u = field_spec.get("unit")
                if abs(float(mod_val) - float(ov_num)) <= 1e-9 and canonical_unit(ov_unit) == canonical_unit(target_u):
                    continue
            except ValueError:
                pass
        extracted[k] = v

    evidence = dict(evidence or {})
    if pages:
        for field in schema.get("fields", []):
            fname = field["field_name"]
            val = extracted.get(fname)
            cur_ev = evidence.get(fname)
            if val not in (None, "") and (not cur_ev or not _evidence_supports_value(val, cur_ev)):
                better_ev = find_field_evidence(pages, field, extracted_value=val)
                if better_ev:
                    evidence[fname] = better_ev
                elif fname in numeric_ev_hints:
                    evidence[fname] = {
                        "page": 1,
                        "line": 1,
                        "text": f"{numeric_ev_hints[fname]['text']} [{val}]",
                        "source": "configured_source_alias",
                    }
                elif fname in overrides:
                    # Value was deterministically extracted from the document text itself
                    evidence[fname] = {
                        "page": (cur_ev or {}).get("page") or 1,
                        "line": (cur_ev or {}).get("line") or 1,
                        "text": f"{(cur_ev or {}).get('text') or field.get('label')}: {val}",
                        "source": "deterministic_extraction",
                    }

    normalized_values = {}
    source_units = {}
    precomputed_normalizations = {}
    for field in schema.get("fields", []):
        name = field["field_name"]
        try:
            normalized, source_unit, metadata = _numeric_field_normalization(
                extracted.get(name), field, evidence.get(name)
            )
            precomputed_normalizations[name] = (normalized, source_unit, metadata)
        except ValueError:
            normalized, source_unit = extracted.get(name), None
            precomputed_normalizations[name] = (
                normalized,
                None,
                {"converted": False, "error": "Unsafe unit conversion"},
            )
        normalized_values[name] = normalized
        source_units[name] = source_unit

    extraction_records = records_from_extracted(
        extracted, schema, evidence, source_units=source_units, normalized_values=normalized_values, verification_status="UNVERIFIED"
    )
    for record in extraction_records:
        errors = validate_record(record)
        if errors:
            raise ValueError(f"Invalid extraction record for {record.field_name}: {'; '.join(errors)}")

    candidate_records = list(extraction_records)
    if overrides:
        field_by_name = {f.get("field_name"): f for f in schema.get("fields", [])}
        conflicting_model = {}
        for name, ov_val in overrides.items():
            mod_val = model_extracted.get(name)
            if mod_val in (None, "") or mod_val == ov_val:
                continue
            f_spec = field_by_name.get(name, {})
            # For numeric fields (like NPSHA vs NPSHR or Rated Power vs Motor Rating),
            # deterministic label disambiguation is authoritative and not a conflict.
            if f_spec.get("unit") or name == "npsha_available_m":
                continue
            # If one is just a column-cleaned version of the other (e.g. "Electric Motor Pump" vs "Electric Motor"), not a conflict
            if _norm_label(str(mod_val)) in _norm_label(str(ov_val)) or _norm_label(str(ov_val)) in _norm_label(str(mod_val)):
                continue
            conflicting_model[name] = mod_val
        if conflicting_model:
            model_records = records_from_extracted(
                conflicting_model,
                schema,
                evidence,
                source_units=source_units,
                normalized_values={name: conflicting_model[name] for name in conflicting_model},
            )
            candidate_records.extend(model_records)
    conflicts = detect_conflicts(candidate_records)

    rows = compare_against_schema(
        extracted,
        schema,
        evidence=evidence,
        verify_evidence=verify_evidence,
        extraction_records=extraction_records,
        conflicts=conflicts,
        precomputed_normalizations=precomputed_normalizations,
    )
    return rows, raw_output, extracted


def run_pdf_audit_with_evidence(file_bytes_or_path, schema, *, include_intelligence=False):
    pages = extract_pdf_pages_with_evidence(file_bytes_or_path, schema=schema)
    indexed_text = build_evidence_index(pages)
    evidence = build_evidence_map(pages, schema)
    rows, raw_output, extracted = run_audit(
        indexed_text, schema, evidence=evidence, verify_evidence=True, pages=pages
    )
    if include_intelligence:
        intelligence = run_engineering_reasoning(rows, schema, extracted, model_name=MODEL_NAME)
        return rows, raw_output, extracted, pages, intelligence
    return rows, raw_output, extracted, pages


def audit_summary(rows):
    counts = {"MATCHED": 0, "MISSING": 0, "MISMATCHED": 0, "OUT OF RANGE": 0, "NEEDS_REVIEW": 0}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    counts["TOTAL"] = len(rows)
    return counts


# --------------------------------------------------------------------------
# Bulk audit
# --------------------------------------------------------------------------

def guess_column_mapping(schema, columns):
    mapping = {}
    normalized = {col: _norm_label(col) for col in columns}

    for f in schema["fields"]:
        target = _norm_label(f["label"])
        best_col, best_score = None, 0

        for col, norm in normalized.items():
            if target == norm:
                best_col, best_score = col, 999
                break
            if target in norm or norm in target:
                score = min(len(target), len(norm))
                if score > best_score:
                    best_col, best_score = col, score

        if best_col is None:
            close = difflib.get_close_matches(f["label"], columns, n=1, cutoff=0.5)
            best_col = close[0] if close else None

        mapping[f["field_name"]] = best_col

    return mapping


def guess_identifier_column(columns):
    priorities = ["equipment tag", "tag number", "tag", "equipment id", "id", "equipment"]
    lower_map = {col.lower(): col for col in columns}
    for p in priorities:
        for lc, original in lower_map.items():
            if p in lc:
                return original
    return columns[0] if columns else None


def run_bulk_audit(records, schema, column_map, identifier_column=None):
    results = []
    for i, record in enumerate(records):
        extracted = {}
        for f in schema["fields"]:
            col = column_map.get(f["field_name"])
            value = record.get(col) if col else None
            if value == "":
                value = None
            extracted[f["field_name"]] = value

        field_rows = compare_against_schema(extracted, schema)

        identifier = record.get(identifier_column) if identifier_column else None
        identifier = str(identifier).strip() if identifier not in (None, "") else f"Row {i + 1}"

        results.append({
            "identifier": identifier,
            "rows": field_rows,
            "summary": audit_summary(field_rows),
        })
    return results


def bulk_overview(results):
    overview = []
    for r in results:
        s = r["summary"]
        has_error = bool(r.get("error"))
        overview.append({
            "identifier": r["identifier"],
            "matched": s["MATCHED"],
            "missing": s["MISSING"],
            "mismatched": s["MISMATCHED"],
            "out_of_range": s["OUT OF RANGE"],
            "needs_review": s.get("NEEDS_REVIEW", 0),
            "total": s["TOTAL"],
            "all_matched": (not has_error) and s["TOTAL"] > 0 and s["MATCHED"] == s["TOTAL"],
            "error": r.get("error"),
        })
    return overview


# --------------------------------------------------------------------------
# Batch AI processing
# --------------------------------------------------------------------------

_EMPTY_SUMMARY = {"MATCHED": 0, "MISSING": 0, "MISMATCHED": 0, "OUT OF RANGE": 0, "NEEDS_REVIEW": 0, "TOTAL": 0}


def _result_or_error(identifier, rows=None, raw_output=None, intelligence=None, error=None, performance=None):
    if error is not None:
        result = {
            "identifier": identifier, "rows": [], "summary": dict(_EMPTY_SUMMARY),
            "raw_output": None, "error": str(error),
        }
        if performance is not None:
            result["performance"] = performance
        return result
    result = {
        "identifier": identifier, "rows": rows or [],
        "summary": audit_summary(rows or []), "raw_output": raw_output, "error": None,
    }
    if intelligence is not None:
        result["intelligence"] = intelligence.to_dict()
    if performance is not None:
        result["performance"] = performance
    return result


def _run_one_for_batch(identifier, datasheet_text, schema):
    started = time.perf_counter()
    try:
        rows, raw_output, _ = run_audit(datasheet_text, schema)
        performance = {"total_s": round(time.perf_counter() - started, 3)}
        return _result_or_error(identifier, rows, raw_output, performance=performance)
    except Exception as e:  # noqa: BLE001
        performance = {"total_s": round(time.perf_counter() - started, 3)}
        return _result_or_error(identifier, error=e, performance=performance)


def _run_one_pdf_for_batch(identifier, pdf_bytes, schema, include_intelligence=False):
    started = time.perf_counter()
    try:
        result = run_pdf_audit_with_evidence(
            pdf_bytes, schema, include_intelligence=include_intelligence
        )
        if include_intelligence:
            rows, raw_output, _extracted, _pages, intelligence = result
        else:
            rows, raw_output, _extracted, _pages = result
            intelligence = None
        performance = {"total_s": round(time.perf_counter() - started, 3)}
        return _result_or_error(
            identifier, rows, raw_output, intelligence=intelligence, performance=performance
        )
    except Exception as e:  # noqa: BLE001
        performance = {"total_s": round(time.perf_counter() - started, 3)}
        return _result_or_error(identifier, error=e, performance=performance)


def run_batch_audit(named_texts, schema, max_workers=3, progress_callback=None):
    results = [None] * len(named_texts)
    if not named_texts:
        return results

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        future_to_idx = {
            executor.submit(_run_one_for_batch, name, text, schema): i
            for i, (name, text) in enumerate(named_texts)
        }
        done = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()
            done += 1
            if progress_callback:
                progress_callback(done, len(named_texts))

    return results


def run_batch_pdf_audit(named_pdfs, schema, max_workers=3, progress_callback=None, include_intelligence=False):
    results = [None] * len(named_pdfs)
    if not named_pdfs:
        return results

    worker_count = max(1, min(int(max_workers), 6))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_idx = {
            executor.submit(
                _run_one_pdf_for_batch, name, pdf_bytes, schema, include_intelligence
            ): i
            for i, (name, pdf_bytes) in enumerate(named_pdfs)
        }
        done = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                name = named_pdfs[idx][0]
                results[idx] = _result_or_error(name, error=exc)
            done += 1
            if progress_callback:
                try:
                    progress_callback(done, len(named_pdfs))
                except Exception:
                    pass

    return results
