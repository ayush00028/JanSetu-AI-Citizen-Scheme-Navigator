"""Gemini-backed, catalogue-grounded replies for the JanSetu chat."""
import json
import os
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from dotenv import load_dotenv


load_dotenv()


GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _catalogue_context(schemes, services):
    scheme_lines = [
        f"- {scheme.name}: {scheme.description} Benefits: {scheme.benefits}. "
        f"Eligibility recorded in JanSetu: age {scheme.min_age or 'any'}–{scheme.max_age or 'any'}, "
        f"income ceiling {scheme.max_income or 'none'}, categories {scheme.caste_categories}, "
        f"occupations {scheme.occupations}, states {scheme.states}."
        for scheme in schemes
    ]
    service_lines = [
        f"- {service.name}: {service.description} Fee: {service.fee}; typical duration: {service.duration_estimate}."
        for service in services
    ]
    return "\n".join(["SCHEMES:\n" + "\n".join(scheme_lines), "SERVICES:\n" + "\n".join(service_lines)])


def generate_citizen_reply(message, language, profile_ctx, schemes, services, recent_messages):
    """Return a concise grounded answer, or None when Gemini is unavailable."""
    api_key = os.getenv("GEMINI_API_KEY")
    # Automated tests must stay deterministic and must never consume a live API.
    if not api_key or os.getenv("PYTEST_CURRENT_TEST"):
        return None

    language_name = "Hindi (Devanagari)" if language == "hi" else "English"
    recent = "\n".join(f"{item.sender}: {item.message}" for item in recent_messages[-6:]) or "No earlier messages."
    prompt = f"""You are JanSetu, a careful Indian citizen scheme and public-service navigator.
Reply in {language_name}. Be warm, plain-spoken, and concise (maximum 140 words).
Use ONLY the catalogue below for scheme/service facts. Never invent eligibility, a deadline,
fee, document, benefit, official link, or government policy. Do not make a final eligibility
decision; say the user may be eligible and ask for missing details. Remind users to verify final
requirements on the official portal when useful. Never request Aadhaar, PAN, bank-account,
password, OTP, or other document numbers in chat.

Saved profile (may be incomplete): {json.dumps(profile_ctx, ensure_ascii=False)}
Recent conversation:
{recent}
User: {message}

{_catalogue_context(schemes, services)}
"""
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300},
    }).encode("utf-8")
    request = Request(
        GEMINI_URL.format(model=GEMINI_MODEL), body,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key}, method="POST",
    )
    try:
        with urlopen(request, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text[:1800] if text else None
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, ValueError):
        return None
