from core import extract_text_from_pdf, load_schema


def test_actual_oem_material_values_have_traceable_evidence(monkeypatch):
    schema = load_schema("templates/centrifugal_pump_audit.json")
    monkeypatch.setattr(
        "core.call_model",
        lambda prompt: '{"rated_power_kw": 687.4, "npsha_available_m": 5.96, '
                        '"casing_material": null, "shaft_material": null, '
                        '"driver_type": null}',
    )
    with open("tests/fixtures/provided_driver_type_case.pdf", "rb") as fh:
        extract_text_from_pdf(fh.read(), schema=schema)
    from core import run_pdf_audit_with_evidence
    rows, _, extracted, _ = run_pdf_audit_with_evidence(
        open("tests/fixtures/provided_driver_type_case.pdf", "rb").read(), schema
    )

    assert extracted["casing_material"] == "A216WCB"
    assert extracted["shaft_material"] == "A276-410"
    casing = next(r for r in rows if r["field_name"] == "casing_material")
    shaft = next(r for r in rows if r["field_name"] == "shaft_material")
    assert casing["status"] == "MATCHED"
    assert shaft["status"] == "MATCHED"
    assert casing["evidence"]["source"] == "label_match"
    assert "A216WCB" in casing["evidence"]["text"]
    assert shaft["evidence"]["source"] == "label_match"
    assert "A276-410" in shaft["evidence"]["text"]


def test_centrifugal_pump_domain_mapping_for_motor_power_and_materials(monkeypatch):
    schema = load_schema("templates/centrifugal_pump_audit.json")
    monkeypatch.setattr(
        "core.call_model",
        lambda prompt: '{"rated_power_kw": null, "npsha_available_m": null, '
                        '"casing_material": null, "shaft_material": null, "driver_type": null}',
    )
    from core import run_audit
    text = """N.P.S.H available : -
Brake power : 4.9 kW
Motor power : 7.5 kW
Casing : Cast Iron
Shaft : Stainless Steel AISI329
"""
    rows, _, extracted = run_audit(text, schema)

    assert extracted["rated_power_kw"] == "7.5 kW"
    assert extracted["npsha_available_m"] is None
    assert extracted["casing_material"] == "Cast Iron"
    assert extracted["shaft_material"] == "Stainless Steel AISI329"
    assert next(r for r in rows if r["field_name"] == "rated_power_kw")["status"] == "MATCHED"
    assert next(r for r in rows if r["field_name"] == "npsha_available_m")["status"] == "MISSING"
