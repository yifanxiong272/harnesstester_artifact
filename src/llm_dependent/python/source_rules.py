#!/usr/bin/env python3
"""Provider-name and endpoint rules for Python LLM source detection.

Named SDK calls and constructors use recognized module prefixes and exact API
suffixes. HTTP sources use the provider host and path rules below.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


PY_LIKE_EXTENSIONS = {".py"}


@dataclass(frozen=True)
class ProviderSourceRule:
    modules: frozenset[str]
    module_call_suffixes: frozenset[str]
    client_constructor_suffixes: frozenset[str] = frozenset()
    client_request_suffixes: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ProviderEndpointRule:
    provider_module: str
    hosts: frozenset[str]
    paths: frozenset[str]


OPENAI_CLIENT_REQUEST_SUFFIXES = frozenset(
    {
        "audio.speech.create",
        "audio.transcriptions.create",
        "audio.translations.create",
        "chat.completions.parse",
        "chat.completions.create",
        "chat.completions.stream",
        "completions.create",
        "embeddings.create",
        "images.create_variation",
        "images.edit",
        "images.generate",
        "responses.parse",
        "responses.create",
        "responses.stream",
    }
)

OPENAI_MODULE_REQUEST_SUFFIXES = OPENAI_CLIENT_REQUEST_SUFFIXES | frozenset(
    {
        "Embedding.acreate",
        "Embedding.create",
    }
)

OPENAI_CLIENT_CONSTRUCTOR_SUFFIXES = frozenset(
    {
        "AsyncAzureOpenAI",
        "AsyncClient",
        "AsyncOpenAI",
        "AzureOpenAI",
        "Client",
        "OpenAI",
    }
)

ANTHROPIC_CLIENT_CONSTRUCTOR_SUFFIXES = frozenset(
    {
        "Anthropic",
        "AnthropicBedrock",
        "AsyncAnthropic",
        "AsyncAnthropicBedrock",
        "AsyncClient",
        "Client",
    }
)

ANTHROPIC_CLIENT_REQUEST_SUFFIXES = frozenset(
    {
        "beta.messages.create",
        "completions.create",
        "messages.create",
        "messages.parse",
        "messages.stream",
    }
)

GENERIC_CLIENT_CONSTRUCTOR_SUFFIXES = frozenset(
    {
        "AsyncClient",
        "Client",
        "Mistral",
        "MistralClient",
    }
)

MISTRALAI_CLIENT_REQUEST_SUFFIXES = frozenset(
    {
        "chat.complete",
        "chat.complete_async",
        "chat.parse",
        "chat.parse_async",
        "chat.parse_stream",
        "chat.parse_stream_async",
        "chat.stream",
        "chat.stream_async",
    }
)

COHERE_CLIENT_REQUEST_SUFFIXES = frozenset(
    {
        "chat",
        "chat_stream",
        "embed",
        "generate",
        "generate_stream",
        "rerank",
        "v2.chat",
        "v2.chat_stream",
        "v2.embed",
        "v2.rerank",
    }
)

GOOGLE_GENAI_CLIENT_REQUEST_SUFFIXES = frozenset(
    {
        "aio.models.generate_content",
        "aio.models.generate_content_stream",
        "models.generate_content",
        "models.generate_content_stream",
        "models.generate_images",
    }
)

OLLAMA_CLIENT_REQUEST_SUFFIXES = frozenset(
    {
        "chat",
        "embed",
        "embeddings",
        "generate",
    }
)

OCI_GENERATIVE_AI_CLIENT_REQUEST_SUFFIXES = frozenset({"chat"})

LANGCHAIN_OPENAI_CLIENT_CONSTRUCTOR_SUFFIXES = frozenset(
    {
        "AzureChatOpenAI",
        "AzureOpenAI",
        "AzureOpenAIEmbeddings",
        "ChatOpenAI",
        "OpenAI",
        "OpenAIEmbeddings",
    }
)

LANGCHAIN_RUNNABLE_REQUEST_SUFFIXES = frozenset(
    {
        "abatch",
        "aembed_documents",
        "aembed_query",
        "agenerate",
        "agenerate_prompt",
        "ainvoke",
        "apredict",
        "apredict_messages",
        "astream",
        "batch",
        "embed_documents",
        "embed_query",
        "generate",
        "generate_prompt",
        "invoke",
        "predict",
        "predict_messages",
        "stream",
    }
)

PROVIDER_SOURCE_RULES = (
    ProviderSourceRule(
        modules=frozenset({"litellm"}),
        module_call_suffixes=frozenset(
            {
                "acompletion",
                "completion",
                "aembedding",
                "embedding",
                "aimage_generation",
                "image_generation",
                "aresponses",
                "responses",
                "arerank",
                "rerank",
                "aspeech",
                "speech",
                "atranscription",
                "transcription",
            }
        ),
    ),
    ProviderSourceRule(
        modules=frozenset({"openai"}),
        module_call_suffixes=OPENAI_MODULE_REQUEST_SUFFIXES,
        client_constructor_suffixes=OPENAI_CLIENT_CONSTRUCTOR_SUFFIXES,
        client_request_suffixes=OPENAI_CLIENT_REQUEST_SUFFIXES,
    ),
    ProviderSourceRule(
        modules=frozenset({"anthropic"}),
        module_call_suffixes=ANTHROPIC_CLIENT_REQUEST_SUFFIXES,
        client_constructor_suffixes=ANTHROPIC_CLIENT_CONSTRUCTOR_SUFFIXES,
        client_request_suffixes=ANTHROPIC_CLIENT_REQUEST_SUFFIXES,
    ),
    ProviderSourceRule(
        modules=frozenset({"groq"}),
        module_call_suffixes=frozenset({"chat.completions.create"}),
        client_constructor_suffixes=GENERIC_CLIENT_CONSTRUCTOR_SUFFIXES,
        client_request_suffixes=frozenset({"chat.completions.create"}),
    ),
    ProviderSourceRule(
        modules=frozenset({"portkey_ai"}),
        module_call_suffixes=frozenset(),
        client_constructor_suffixes=frozenset({"AsyncPortkey", "Portkey"}),
        client_request_suffixes=OPENAI_CLIENT_REQUEST_SUFFIXES,
    ),
    ProviderSourceRule(
        modules=frozenset({"mistralai"}),
        module_call_suffixes=MISTRALAI_CLIENT_REQUEST_SUFFIXES,
        client_constructor_suffixes=GENERIC_CLIENT_CONSTRUCTOR_SUFFIXES,
        client_request_suffixes=MISTRALAI_CLIENT_REQUEST_SUFFIXES,
    ),
    ProviderSourceRule(
        modules=frozenset({"cohere"}),
        module_call_suffixes=COHERE_CLIENT_REQUEST_SUFFIXES,
        client_constructor_suffixes=GENERIC_CLIENT_CONSTRUCTOR_SUFFIXES,
        client_request_suffixes=COHERE_CLIENT_REQUEST_SUFFIXES,
    ),
    ProviderSourceRule(
        modules=frozenset({"google.genai"}),
        module_call_suffixes=GOOGLE_GENAI_CLIENT_REQUEST_SUFFIXES,
        client_constructor_suffixes=GENERIC_CLIENT_CONSTRUCTOR_SUFFIXES,
        client_request_suffixes=GOOGLE_GENAI_CLIENT_REQUEST_SUFFIXES,
    ),
    ProviderSourceRule(
        modules=frozenset({"google.generativeai"}),
        module_call_suffixes=frozenset({"generate_content"}),
        client_constructor_suffixes=frozenset({"GenerativeModel"}),
        client_request_suffixes=frozenset({"generate_content", "generate_content_async"}),
    ),
    ProviderSourceRule(
        modules=frozenset({"ollama"}),
        module_call_suffixes=OLLAMA_CLIENT_REQUEST_SUFFIXES,
        client_constructor_suffixes=frozenset({"AsyncClient", "Client"}),
        client_request_suffixes=OLLAMA_CLIENT_REQUEST_SUFFIXES,
    ),
    ProviderSourceRule(
        modules=frozenset({"oci.generative_ai_inference"}),
        module_call_suffixes=frozenset(),
        client_constructor_suffixes=frozenset({"GenerativeAiInferenceClient"}),
        client_request_suffixes=OCI_GENERATIVE_AI_CLIENT_REQUEST_SUFFIXES,
    ),
    ProviderSourceRule(
        modules=frozenset({"aws.bedrock-runtime"}),
        module_call_suffixes=frozenset(),
        client_request_suffixes=frozenset({"converse"}),
    ),
    ProviderSourceRule(
        modules=frozenset({"langchain_openai"}),
        module_call_suffixes=frozenset(),
        client_constructor_suffixes=LANGCHAIN_OPENAI_CLIENT_CONSTRUCTOR_SUFFIXES,
        client_request_suffixes=LANGCHAIN_RUNNABLE_REQUEST_SUFFIXES,
    ),
)

PROVIDER_ENDPOINT_RULES = (
    ProviderEndpointRule(
        provider_module="openai",
        hosts=frozenset({"api.openai.com"}),
        paths=frozenset(
            {
                "/v1/audio/transcriptions",
                "/v1/audio/translations",
                "/v1/chat/completions",
                "/v1/completions",
                "/v1/embeddings",
                "/v1/images/generations",
                "/v1/responses",
            }
        ),
    ),
    ProviderEndpointRule(
        provider_module="openrouter",
        hosts=frozenset({"openrouter.ai"}),
        paths=frozenset({"/api/v1/chat/completions", "/api/v1/responses"}),
    ),
    ProviderEndpointRule(
        provider_module="requesty",
        hosts=frozenset({"router.requesty.ai"}),
        paths=frozenset({"/v1/chat/completions"}),
    ),
    ProviderEndpointRule(
        provider_module="mistral",
        hosts=frozenset({"api.mistral.ai"}),
        paths=frozenset({"/v1/chat/completions"}),
    ),
    ProviderEndpointRule(
        provider_module="browser_use_cloud",
        hosts=frozenset({"llm.api.browser-use.com"}),
        paths=frozenset({"/v1/chat/completions"}),
    ),
    ProviderEndpointRule(
        provider_module="modelslab",
        hosts=frozenset({"modelslab.com"}),
        paths=frozenset({"/api/v6/images/text2img"}),
    ),
)

LLM_PROVIDER_MODULES = frozenset(
    module
    for rule in PROVIDER_SOURCE_RULES
    for module in rule.modules
)


def matches_call_suffix(suffix: str | None, suffixes: frozenset[str]) -> bool:
    """Return whether the complete suffix matches an allowlisted API path."""

    return bool(suffix) and suffix in suffixes


def provider_module_and_suffix(
    full_name: str | None,
    *,
    rule: ProviderSourceRule | None = None,
) -> tuple[ProviderSourceRule, str, str] | None:
    if not full_name:
        return None
    rules = (rule,) if rule is not None else PROVIDER_SOURCE_RULES
    for candidate_rule in rules:
        for module in sorted(candidate_rule.modules, key=lambda item: (-len(item), item)):
            if full_name == module:
                return candidate_rule, module, ""
            prefix = f"{module}."
            if full_name.startswith(prefix):
                return candidate_rule, module, full_name[len(prefix) :]
    return None


def certified_provider_module_call(full_name: str | None) -> tuple[str, str] | None:
    match = provider_module_and_suffix(full_name)
    if match is None:
        return None
    rule, module, suffix = match
    if matches_call_suffix(suffix, rule.module_call_suffixes):
        return module, suffix
    return None


def certified_provider_client_constructor(full_name: str | None) -> tuple[str, str] | None:
    match = provider_module_and_suffix(full_name)
    if match is None:
        return None
    rule, module, suffix = match
    if matches_call_suffix(suffix, rule.client_constructor_suffixes):
        return module, suffix
    return None


def is_provider_client_request_suffix(suffix: str | None) -> bool:
    return any(
        matches_call_suffix(suffix, rule.client_request_suffixes)
        for rule in PROVIDER_SOURCE_RULES
    )


def certified_provider_endpoint(url: str | None) -> tuple[str, str] | None:
    """Return provider provenance for a known LLM REST endpoint URL."""

    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    for rule in PROVIDER_ENDPOINT_RULES:
        if host in rule.hosts and path in rule.paths:
            return rule.provider_module, path
    return None
