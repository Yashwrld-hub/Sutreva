# Sutreva — Session 44: AI Provider Abstraction v1

## Objective

Introduce a provider boundary without changing Sutreva extraction semantics.

## Implemented

- Added `ai_provider.py`.
- Added `ModelProvider` protocol.
- Added `NebiusNemotronProvider` for the existing Nebius Token Factory + Nemotron path.
- Kept `core.call_model()` as a compatibility entry point and delegated provider networking to `ai_provider.get_model_provider()`.
- Preserved the existing request shape, system prompt, temperature, retry behavior, and `content`/`reasoning_content` fallback.
- Added `SUTREVA_MODEL_PROVIDER` selection with `nebius_nemotron` as the default.
- Added offline provider tests covering request shape, retries, empty responses, factory behavior, and `core.call_model()` delegation.
- Updated deployment sanity checks to require/import `ai_provider.py`.

## Validation

- 240 tests passed.
- Deployment sanity check passed.
- Python compilation passed.

## Not yet implemented

NeMo runtime/orchestration is not introduced in this session. The provider boundary is intentionally the seam for the next phase.
