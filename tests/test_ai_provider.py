from types import SimpleNamespace

import pytest

import ai_provider


class _FakeCompletions:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = next(self.responses)
        if isinstance(item, Exception):
            raise item
        return item


class _FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=_FakeCompletions(responses))


def _response(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_nebius_provider_preserves_request_shape():
    client = _FakeClient([_response('{"material": "Steel"}')])
    provider = ai_provider.NebiusNemotronProvider(client=client)

    result = provider.generate("extract this", model_name="test-model")

    assert result == '{"material": "Steel"}'
    call = client.chat.completions.calls[0]
    assert call["model"] == "test-model"
    assert call["temperature"] == 0
    assert call["messages"][0]["role"] == "system"
    assert call["messages"][1] == {"role": "user", "content": "extract this"}


def test_nebius_provider_reads_reasoning_content_when_content_empty():
    client = _FakeClient([
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="", reasoning_content='{"ok": true}')
                )
            ]
        )
    ])
    provider = ai_provider.NebiusNemotronProvider(client=client)

    assert provider.generate("prompt") == '{"ok": true}'


def test_nebius_provider_retries_transient_failure(monkeypatch):
    client = _FakeClient([RuntimeError("temporary"), _response('{"ok": true}')])
    provider = ai_provider.NebiusNemotronProvider(client=client)
    monkeypatch.setattr(ai_provider.time, "sleep", lambda _: None)

    assert provider.generate("prompt") == '{"ok": true}'
    assert len(client.chat.completions.calls) == 2


def test_nebius_provider_rejects_empty_output():
    client = _FakeClient([_response("   "), _response("   ")])
    provider = ai_provider.NebiusNemotronProvider(client=client)

    with pytest.raises(RuntimeError, match="Model call failed"):
        provider.generate("prompt")


def test_provider_factory_defaults_to_nebius_nemotron(monkeypatch):
    monkeypatch.delenv("SUTREVA_MODEL_PROVIDER", raising=False)
    provider = ai_provider.build_model_provider()
    assert provider.name == "nebius_nemotron"


def test_provider_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unsupported Sutreva model provider"):
        ai_provider.build_model_provider("does-not-exist")


def test_core_call_model_delegates_to_provider(monkeypatch):
    sentinel = object()
    calls = []

    class FakeProvider:
        def generate(self, prompt, model_name):
            calls.append((prompt, model_name))
            return sentinel

    import core

    monkeypatch.setattr(core, "get_model_provider", lambda: FakeProvider())

    assert core.call_model("prompt", model_name="model-x") is sentinel
    assert calls == [("prompt", "model-x")]


def test_provider_honors_runtime_model_override(monkeypatch):
    from ai_provider import NebiusNemotronProvider

    monkeypatch.setenv("NEBIUS_MODEL_NAME", "nvidia/custom-nemotron")

    class Message:
        content = '{"ok": true}'
        reasoning_content = None

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]

    calls = {}

    class Completions:
        def create(self, **kwargs):
            calls.update(kwargs)
            return Response()

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    result = NebiusNemotronProvider(client=Client()).generate("hello")
    assert result == '{"ok": true}'
    assert calls["model"] == "nvidia/custom-nemotron"
