import os

from dotenv import load_dotenv

from src.config import GROQ_MODEL, LLM_PROVIDER, MAX_TOKENS, TEMPERATURE

load_dotenv()

PROVIDER = LLM_PROVIDER  # remove the os.getenv line


def chat(
    messages: list[dict], temperature: float = TEMPERATURE, max_tokens: int = MAX_TOKENS
) -> str:
    if PROVIDER == "groq":
        return _groq(messages, temperature, max_tokens)
    elif PROVIDER == "azure_openai":
        return _azure_openai(messages, temperature, max_tokens)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {PROVIDER}")


def _groq(messages: list[dict], temperature: float, max_tokens: int) -> str:
    from groq import Groq

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=GROQ_MODEL, temperature=temperature, max_tokens=max_tokens, messages=messages
    )
    return response.choices[0].message.content


def _azure_openai(messages: list[dict], temperature: float, max_tokens: int) -> str:
    from openai import AzureOpenAI

    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
    )
    return response.choices[0].message.content

def chat_vision(image_bytes: bytes, media_type: str, prompt: str) -> str:
    """
    Describe an image using the configured vision LLM provider.
    Supports: groq, azure_openai
    """
    from src.config import VISION_PROVIDER

    if VISION_PROVIDER == "groq":
        return _groq_vision(image_bytes, media_type, prompt)
    elif VISION_PROVIDER == "azure_openai":
        return _azure_openai_vision(image_bytes, media_type, prompt)
    else:
        raise ValueError(f"Unknown VISION_PROVIDER: {VISION_PROVIDER}")


def _groq_vision(image_bytes: bytes, media_type: str, prompt: str) -> str:
    import base64
    from groq import Groq
    from src.config import GROQ_VISION_MODEL

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return response.choices[0].message.content


def _azure_openai_vision(image_bytes: bytes, media_type: str, prompt: str) -> str:
    import base64
    from openai import AzureOpenAI
    from src.config import AZURE_OPENAI_DEPLOYMENT

    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return response.choices[0].message.content
