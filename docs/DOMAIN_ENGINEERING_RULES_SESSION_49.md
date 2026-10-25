# Sutreva — Session 49 Domain-Aware Engineering Rules v1

## Objective
Add equipment-family context to Sutreva engineering exceptions without creating hidden approval logic or hard-coding project standards into the application.

## Domain profiles
- `centrifugal_pump` — hydraulic, material, and driver review context.
- `mechanical_seal` — seal-face material, thermal envelope, geometry, support plan, and pressure context.
- `lubrication_register` — equipment identity, lubrication point, quantity, lubricant, and grade context.

Each profile is defined in `domain_rules.py` and can be selected explicitly with the template-level `equipment_profile` metadata. Sutreva also falls back to the template name for backward compatibility.

## Authority boundary
Domain profiles provide context, role, focus, and review priority only. They do not replace `compare_against_schema()`, do not add hidden limits, and do not change the authoritative status. Project/OEM acceptance criteria remain in the audit templates.

## UI
Engineering exceptions now show domain role and domain priority, with the active equipment profile displayed above the exception table.

## Validation
Session 49 adds field-specific profile-resolution and exception-context tests while preserving the existing audit/status behavior.
