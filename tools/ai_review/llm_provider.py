"""LLM provider abstraction — Anthropic and OpenAI."""
import os
from typing import Any

from .config import ReviewConfig

_ANTHROPIC_DEFAULT = "claude-opus-4-8"
_OPENAI_DEFAULT = "gpt-4o"
_DEEPSEEK_DEFAULT = "deepseek-reasoner"
_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def _detect_provider(config: ReviewConfig) -> str:
    if config.llm_provider:
        return config.llm_provider.lower()
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("DEEPSEEK_API_KEY"):
        return "deepseek"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    raise EnvironmentError(
        "No LLM provider configured. Set ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, or OPENAI_API_KEY."
    )


def call_llm(system_prompt: str, user_prompt: str, config: ReviewConfig) -> str:
    provider = _detect_provider(config)
    print(f"[ai-review] Provider: {provider}")

    if provider == "anthropic":
        return _call_anthropic(system_prompt, user_prompt, config)
    elif provider == "openai":
        return _call_openai(system_prompt, user_prompt, config)
    elif provider == "deepseek":
        return _call_deepseek(system_prompt, user_prompt, config)
    else:
        raise ValueError(f"Unknown provider: {provider!r}. Use 'anthropic', 'openai', or 'deepseek'.")


def _call_anthropic(system_prompt: str, user_prompt: str, config: ReviewConfig) -> str:
    import anthropic

    model = config.review_model or _ANTHROPIC_DEFAULT
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    with client.messages.stream(
        model=model,
        max_tokens=8096,
        thinking={"type": "adaptive"},
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        response = stream.get_final_message()

    # Extract text blocks only (skip thinking blocks)
    text = "\n".join(
        block.text for block in response.content
        if hasattr(block, "text")
    )
    print(f"[ai-review] Tokens used: {response.usage.input_tokens} in / {response.usage.output_tokens} out")
    return text


def _call_openai(system_prompt: str, user_prompt: str, config: ReviewConfig) -> str:
    import openai

    model = config.review_model or _OPENAI_DEFAULT
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=8096,
        response_format={"type": "json_object"},
    )
    usage = response.usage
    print(f"[ai-review] Tokens used: {usage.prompt_tokens} in / {usage.completion_tokens} out")
    return response.choices[0].message.content


def _call_deepseek(system_prompt: str, user_prompt: str, config: ReviewConfig) -> str:
    # DeepSeek exposes an OpenAI-compatible chat completions endpoint.
    # deepseek-reasoner (R1) produces a reasoning_content field before the answer;
    # we only return the final message content which already contains the JSON.
    import openai

    model = config.review_model or _DEEPSEEK_DEFAULT
    client = openai.OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=_DEEPSEEK_BASE_URL,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=8096,
    )
    usage = response.usage
    print(f"[ai-review] Tokens used: {usage.prompt_tokens} in / {usage.completion_tokens} out")
    return response.choices[0].message.content
