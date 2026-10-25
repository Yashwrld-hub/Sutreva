from core import _deterministic_text_overrides, load_schema, run_audit


def test_actual_oem_material_fields_are_recovered_from_labelled_lines():
    schema = load_schema("templates/centrifugal_pump_audit.json")
    with open("tests/fixtures/provided_driver_type_case.pdf", "rb") as fh:
        from core import extract_text_from_pdf
        text = extract_text_from_pdf(fh.read(), schema=schema)
    overrides = _deterministic_text_overrides(text, schema)
    assert overrides["casing_material"] == "A216WCB"
    assert overrides["shaft_material"] == "A276-410"


def test_deterministic_text_overrides_are_conservative_on_multi_value_lines():
    schema = load_schema("templates/centrifugal_pump_audit.json")
    text = "BARREL / CASE A216WCB IMPELLER A487CA6NM\nSHAFT A276-410\n"
    overrides = _deterministic_text_overrides(text, schema)
    assert overrides["casing_material"] == "A216WCB"
    assert overrides["shaft_material"] == "A276-410"


def test_full_audit_prefers_source_material_values_over_model_null(monkeypatch):
    schema = load_schema("templates/centrifugal_pump_audit.json")
    monkeypatch.setattr(
        "core.call_model",
        lambda prompt: '{"rated_power_kw": null, "npsha_available_m": null, '
                        '"casing_material": null, "shaft_material": null, '
                        '"driver_type": null}',
    )
    from core import extract_text_from_pdf
    with open("tests/fixtures/provided_driver_type_case.pdf", "rb") as fh:
        text = extract_text_from_pdf(fh.read(), schema=schema)
    rows, _, extracted = run_audit(text, schema)
    assert extracted["casing_material"] == "A216WCB"
    assert extracted["shaft_material"] == "A276-410"
    assert next(r for r in rows if r["field_name"] == "casing_material")["status"] == "MATCHED"
    assert next(r for r in rows if r["field_name"] == "shaft_material")["status"] == "MATCHED"


def test_narrative_mentions_cannot_override_field_value():
    schema = load_schema("templates/centrifugal_pump_audit.json")
    text = (
        "SHAFT A479-316\n"
        "NOTE: Shaft Material differs from configured expected value A276-410.\n"
    )
    overrides = _deterministic_text_overrides(text, schema)
    assert "shaft_material" not in overrides


def test_generic_label_override_recovers_materials_outside_template_vocab():
    schema = load_schema("templates/centrifugal_pump_audit.json")
    text = (
        "Casing: (63E31-B) Ductile Iron 65-45-12.\n"
        "Impeller Shaft: Carbon Steel 1045.\n"
    )
    from core import _deterministic_label_overrides
    overrides = _deterministic_label_overrides(text, schema)
    assert "Ductile Iron 65-45-12" in overrides["casing_material"]
    assert overrides["shaft_material"] == "Carbon Steel 1045"


def test_full_deterministic_override_recovers_explicit_material_values():
    schema = load_schema("templates/centrifugal_pump_audit.json")
    text = (
        "Casing: (63E31-B) Ductile Iron 65-45-12.\n"
        "Impeller Shaft: Carbon Steel 1045.\n"
    )
    from core import _deterministic_overrides
    overrides = _deterministic_overrides(text, schema)
    assert "Ductile Iron 65-45-12" in overrides["casing_material"]
    assert overrides["shaft_material"] == "Carbon Steel 1045"
