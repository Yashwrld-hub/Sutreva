"""Configurable multi-discipline equipment-domain profiles for Sutreva engineering intelligence.

Covers rotating equipment (pumps, compressors, mechanical seals, agitators/mixers),
heat-transfer equipment (shell & tube heat exchangers, air-cooled fin fans),
static/mass-transfer equipment (columns/towers, reactors, pressure vessels),
and plant lubrication registers.

Profiles provide engineering context only. They do not define approval criteria,
change authoritative audit statuses, or replace project/OEM standards configured
in the audit templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DomainFieldProfile:
    field_name: str
    role: str
    focus: str
    priority: str = "MEDIUM"


@dataclass(frozen=True)
class EquipmentDomainProfile:
    profile_id: str
    label: str
    description: str
    fields: dict[str, DomainFieldProfile]


PROFILES: dict[str, EquipmentDomainProfile] = {
    "centrifugal_pump": EquipmentDomainProfile(
        profile_id="centrifugal_pump",
        label="Centrifugal Pump",
        description="Rotating-equipment review context for hydraulic, material, and driver fields.",
        fields={
            "rated_power_kw": DomainFieldProfile("rated_power_kw", "Driver / load interface", "Confirm the selected driver/load field is reviewed with the pump duty context.", "HIGH"),
            "npsha_available_m": DomainFieldProfile("npsha_available_m", "Suction-side margin", "Review suction-side margin and its source evidence before closing the audit.", "CRITICAL"),
            "casing_material": DomainFieldProfile("casing_material", "Pressure-boundary material", "Review casing/barrel material against the governing project/OEM material requirement.", "CRITICAL"),
            "shaft_material": DomainFieldProfile("shaft_material", "Rotating-component material", "Review shaft material against the governing project/OEM material requirement.", "HIGH"),
            "driver_type": DomainFieldProfile("driver_type", "Driver selection", "Confirm driver selection and source evidence are unambiguous.", "HIGH"),
        },
    ),
    "mechanical_seal": EquipmentDomainProfile(
        profile_id="mechanical_seal",
        label="Mechanical Seal",
        description="Seal-system review context for faces, temperature, geometry, plan, and pressure fields.",
        fields={
            "seal_face_material": DomainFieldProfile("seal_face_material", "Seal face material", "Review seal-face material against the governing compatibility requirement.", "HIGH"),
            "max_operating_temp_c": DomainFieldProfile("max_operating_temp_c", "Thermal envelope", "Review the stated operating-temperature envelope against the configured limit.", "HIGH"),
            "shaft_diameter_mm": DomainFieldProfile("shaft_diameter_mm", "Shaft / seal geometry", "Verify the shaft dimension against the configured project requirement and source evidence.", "HIGH"),
            "api_plan": DomainFieldProfile("api_plan", "Seal support plan", "Verify the specified seal support plan against the configured requirement and source evidence.", "CRITICAL"),
            "seal_chamber_pressure_bar": DomainFieldProfile("seal_chamber_pressure_bar", "Seal pressure envelope", "Review seal-chamber pressure against the configured project limit.", "HIGH"),
        },
    ),
    "lubrication_register": EquipmentDomainProfile(
        profile_id="lubrication_register",
        label="Lubrication Register",
        description="Lubrication-document review context for equipment identity, volume, lubricant, and grade.",
        fields={
            "equipment_description": DomainFieldProfile("equipment_description", "Equipment identity", "Confirm the lubricant record is associated with the intended equipment.", "HIGH"),
            "area_to_be_lubricated": DomainFieldProfile("area_to_be_lubricated", "Lubrication point", "Confirm the lubrication area/point is unambiguous.", "MEDIUM"),
            "volume_ltrs": DomainFieldProfile("volume_ltrs", "Lubricant quantity", "Verify the stated lubricant quantity and its source unit.", "HIGH"),
            "uom": DomainFieldProfile("uom", "Quantity unit", "Verify the unit is consistent with the configured lubrication register.", "MEDIUM"),
            "recomm_lubricant": DomainFieldProfile("recomm_lubricant", "Lubricant selection", "Review the recommended lubricant against the configured allowable values.", "CRITICAL"),
            "recomm_grade": DomainFieldProfile("recomm_grade", "Viscosity / grade", "Review the recommended grade against the configured allowable values.", "CRITICAL"),
        },
    ),
    "heat_exchanger": EquipmentDomainProfile(
        profile_id="heat_exchanger",
        label="Shell & Tube Heat Exchanger (TEMA / ASME)",
        description="Thermal and mechanical design review context for shell/tube envelopes, TEMA class, and metallurgy.",
        fields={
            "heat_duty_kw": DomainFieldProfile("heat_duty_kw", "Thermal duty", "Verify exchanged thermal duty and process heat balance.", "HIGH"),
            "heat_transfer_area_m2": DomainFieldProfile("heat_transfer_area_m2", "Effective surface area", "Confirm effective tube surface area and fouling margin.", "HIGH"),
            "shell_design_pressure_bar": DomainFieldProfile("shell_design_pressure_bar", "Shell pressure boundary", "Verify shell design pressure / MAWP exceeds maximum operating pressure.", "CRITICAL"),
            "tube_design_pressure_bar": DomainFieldProfile("tube_design_pressure_bar", "Tube pressure boundary", "Verify tube-side design pressure exceeds maximum operating pressure.", "CRITICAL"),
            "shell_material": DomainFieldProfile("shell_material", "Shell metallurgy", "Review shell material against process corrosion and temperature envelope.", "CRITICAL"),
            "tube_material": DomainFieldProfile("tube_material", "Tube metallurgy", "Review tube material against process fluid compatibility and velocity limits.", "CRITICAL"),
            "tema_class": DomainFieldProfile("tema_class", "TEMA mechanical standard", "Confirm TEMA Class (R, C, or B) matches refinery/plant service severity.", "HIGH"),
        },
    ),
    "fin_fan_cooler": EquipmentDomainProfile(
        profile_id="fin_fan_cooler",
        label="Air-Cooled Fin Fan Exchanger (API 661)",
        description="Air-cooled heat exchanger review context for bundle metallurgy, fan driver power, and header design.",
        fields={
            "heat_duty_kw": DomainFieldProfile("heat_duty_kw", "Thermal duty", "Verify air-cooler thermal duty at design ambient air temperature.", "HIGH"),
            "design_pressure_bar": DomainFieldProfile("design_pressure_bar", "Header / bundle MAWP", "Verify tube bundle design pressure and hydrotest envelope.", "CRITICAL"),
            "tube_material": DomainFieldProfile("tube_material", "Base tube metallurgy", "Verify base tube material against process fluid corrosion envelope.", "CRITICAL"),
            "fin_material": DomainFieldProfile("fin_material", "Fin metallurgy & bonding", "Confirm fin material (e.g. Aluminum) and maximum allowable fin-tip temperature.", "HIGH"),
            "rated_power_kw": DomainFieldProfile("rated_power_kw", "Fan driver rating", "Confirm fan motor rating satisfies API 661 shaft power margin.", "HIGH"),
        },
    ),
    "column_tower": EquipmentDomainProfile(
        profile_id="column_tower",
        label="Distillation Column / Process Tower (ASME Sec VIII)",
        description="Mass-transfer and pressure-vessel review context for shell metallurgy, internals, MAWP/MDMT, and wind/seismic loads.",
        fields={
            "design_pressure_bar": DomainFieldProfile("design_pressure_bar", "Column top/bottom MAWP", "Verify internal and external (vacuum) design pressure envelopes.", "CRITICAL"),
            "design_temperature_c": DomainFieldProfile("design_temperature_c", "Thermal design envelope", "Verify maximum design temperature and MDMT impact-test exemptions.", "CRITICAL"),
            "shell_material": DomainFieldProfile("shell_material", "Shell & head metallurgy", "Verify plate/cladding material against process corrosion and H2S/wet-sour service.", "CRITICAL"),
            "tray_or_packing_material": DomainFieldProfile("tray_or_packing_material", "Mass-transfer internals", "Review tray/structured-packing metallurgy and fouling/corrosion allowance.", "HIGH"),
            "corrosion_allowance_mm": DomainFieldProfile("corrosion_allowance_mm", "Corrosion allowance", "Verify specified corrosion allowance for wetted pressure boundary.", "HIGH"),
        },
    ),
    "reactor_vessel": EquipmentDomainProfile(
        profile_id="reactor_vessel",
        label="Chemical Reactor / Autoclave",
        description="Reaction-vessel review context for pressure/thermal limits, jacket/coil envelope, cladding, and nozzle loads.",
        fields={
            "design_pressure_bar": DomainFieldProfile("design_pressure_bar", "Reactor MAWP", "Verify reactor internal/vacuum design pressure against runaway/relief setpoint.", "CRITICAL"),
            "design_temperature_c": DomainFieldProfile("design_temperature_c", "Reaction thermal limit", "Verify design temperature exceeds peak exothermic operating temperature.", "CRITICAL"),
            "shell_material": DomainFieldProfile("shell_material", "Wetted shell / lining material", "Confirm reactor metallurgy, weld overlay, or glass/PTFE lining specification.", "CRITICAL"),
            "jacket_design_pressure_bar": DomainFieldProfile("jacket_design_pressure_bar", "Jacket / coil MAWP", "Verify heating/cooling jacket pressure and differential buckling limit.", "HIGH"),
            "corrosion_allowance_mm": DomainFieldProfile("corrosion_allowance_mm", "Corrosion allowance", "Verify corrosion allowance for shell and dished heads.", "HIGH"),
        },
    ),
    "agitator_mixer": EquipmentDomainProfile(
        profile_id="agitator_mixer",
        label="Industrial Agitator / Mixer",
        description="Mixing-equipment review context for shaft/impeller metallurgy, mechanical seal, critical speed, and gearbox/motor duty.",
        fields={
            "rated_power_kw": DomainFieldProfile("rated_power_kw", "Mixer motor / absorbed power", "Verify motor power at maximum fluid viscosity and density.", "HIGH"),
            "shaft_material": DomainFieldProfile("shaft_material", "Wetted shaft metallurgy", "Review agitator shaft material and coating/lining against process fluid.", "CRITICAL"),
            "impeller_material": DomainFieldProfile("impeller_material", "Impeller / blade metallurgy", "Review impeller material against erosion and chemical attack.", "CRITICAL"),
            "operating_speed_rpm": DomainFieldProfile("operating_speed_rpm", "Agitation speed", "Confirm operating speed maintains safe margin from first lateral critical speed.", "HIGH"),
            "driver_type": DomainFieldProfile("driver_type", "Drive / gearbox arrangement", "Confirm motor and gear-drive configuration and service factor.", "MEDIUM"),
        },
    ),
    "compressor_package": EquipmentDomainProfile(
        profile_id="compressor_package",
        label="Centrifugal / Reciprocating Compressor (API 617 / 618)",
        description="Gas-compression review context for discharge temperature/pressure, casing/rotor metallurgy, and driver margin.",
        fields={
            "rated_power_kw": DomainFieldProfile("rated_power_kw", "Compressor shaft / driver power", "Verify driver sizing margin across all specified gas molecular weights.", "HIGH"),
            "discharge_pressure_bar": DomainFieldProfile("discharge_pressure_bar", "Discharge pressure envelope", "Verify rated and relief discharge pressure against cylinder/casing MAWP.", "CRITICAL"),
            "max_operating_temp_c": DomainFieldProfile("max_operating_temp_c", "Gas discharge temperature", "Verify maximum discharge temperature against API limit (e.g. 150°C for reciprocating).", "CRITICAL"),
            "casing_material": DomainFieldProfile("casing_material", "Casing / cylinder material", "Verify pressure-retaining casing material against gas composition and MDMT.", "CRITICAL"),
            "shaft_material": DomainFieldProfile("shaft_material", "Rotor / crankshaft material", "Verify shaft material against torque and sour-gas (NACE MR0175) requirements.", "HIGH"),
        },
    ),
}


def infer_profile_id(schema: dict[str, Any]) -> str | None:
    """Resolve an equipment profile from explicit metadata, template name, or field signatures."""
    explicit = str(schema.get("equipment_profile") or "").strip().lower()
    if explicit in PROFILES:
        return explicit

    name = str(schema.get("template_name") or "").lower()
    if "pump" in name:
        return "centrifugal_pump"
    if "mechanical seal" in name or "seal" in name:
        return "mechanical_seal"
    if "lube oil" in name or "lubrication" in name:
        return "lubrication_register"
    if "fin fan" in name or "air cooler" in name or "air-cooled" in name or "api 661" in name:
        return "fin_fan_cooler"
    if "exchanger" in name or "tema" in name or "condenser" in name or "reboiler" in name:
        return "heat_exchanger"
    if "column" in name or "tower" in name or "fractionator" in name or "absorber" in name or "stripper" in name:
        return "column_tower"
    if "reactor" in name or "autoclave" in name or "fermenter" in name:
        return "reactor_vessel"
    if "agitator" in name or "mixer" in name or "blender" in name:
        return "agitator_mixer"
    if "compressor" in name or "blower" in name or "fan" in name:
        return "compressor_package"
    if "vessel" in name or "drum" in name or "separator" in name:
        return "column_tower"

    # Infer from field names if template has a custom user name
    field_names = " ".join(str(f.get("field_name") or "") for f in schema.get("fields", [])).lower()
    if "tube" in field_names and "shell" in field_names:
        return "heat_exchanger"
    if "tray" in field_names or "packing" in field_names:
        return "column_tower"
    if "jacket" in field_names:
        return "reactor_vessel"
    if "npsha" in field_names or "npshr" in field_names:
        return "centrifugal_pump"
    return None


def get_domain_profile(schema: dict[str, Any]) -> EquipmentDomainProfile | None:
    profile_id = infer_profile_id(schema)
    return PROFILES.get(profile_id) if profile_id else None


def domain_context_for_field(schema: dict[str, Any], field_name: str) -> dict[str, str]:
    profile = get_domain_profile(schema)
    if not profile:
        return {}
    field = profile.fields.get(field_name)
    if not field:
        return {
            "profile_id": profile.profile_id,
            "profile_label": profile.label,
            "domain_role": "Engineering specification",
            "domain_focus": f"Verify {field_name.replace('_', ' ')} against the governing {profile.label} specification.",
            "domain_priority": "HIGH",
        }
    return {
        "profile_id": profile.profile_id,
        "profile_label": profile.label,
        "domain_role": field.role,
        "domain_focus": field.focus,
        "domain_priority": field.priority,
    }
