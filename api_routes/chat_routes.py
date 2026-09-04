import json
import uuid
from urllib.parse import quote_plus
import base64
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from models import User, Profile, ChatMessage, Service, Scheme
from schemas import ChatRequest
from auth import get_current_user
from nlp_engine import process_message
from scoring import compute_profile_completeness
from ai_assistant import generate_citizen_reply

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message")
def send_message(payload: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # JanSetu keeps one continuous conversation per account.  Older browser
    # session IDs are retained with the messages, but cannot make a returning
    # user lose their conversation.
    session_id = payload.session_id or "default"
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    profile_ctx = {
        "age": profile.age, "income": profile.income, "state": profile.state,
        "category": profile.category, "occupation": profile.occupation,
        "gender": profile.gender, "education": profile.education,
        "marital_status": profile.marital_status,
    } if profile else {}

    language = payload.language if payload.language in {"en", "hi"} else user.language_pref
    result = process_message(payload.message, language=language, profile_ctx=profile_ctx)
    recent_messages = (db.query(ChatMessage).filter(ChatMessage.user_id == user.id)
                       .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(6).all())
    ai_response = generate_citizen_reply(
        payload.message, language, profile_ctx,
        db.query(Scheme).all(), db.query(Service).all(), list(reversed(recent_messages)),
    )
    if ai_response:
        result["response"] = ai_response

    user_msg = ChatMessage(
        user_id=user.id, session_id=session_id, sender="user",
        message=payload.message, intent=result["intent"], entities=json.dumps(result["entities"]),
    )
    db.add(user_msg)

    # Auto-update profile from extracted entities
    entities = result["entities"]
    updated_fields = []
    if profile:
        field_map = {"age": "age", "income": "income", "state": "state", "category": "category",
                     "occupation": "occupation", "gender": "gender", "education": "education",
                     "marital_status": "marital_status", "disability": "disability"}
        for ent_key, prof_field in field_map.items():
            if ent_key in entities:
                setattr(profile, prof_field, entities[ent_key])
                updated_fields.append(prof_field)
        if updated_fields:
            profile.completeness = compute_profile_completeness(profile)

    bot_msg = ChatMessage(
        user_id=user.id, session_id=session_id, sender="bot",
        message=result["response"], intent=result["intent"], entities=json.dumps(entities),
    )
    db.add(bot_msg)
    db.commit()

    redirect_url = None
    redirect_label = None
    service_name = entities.get("service_mentioned")
    if service_name:
        service = db.query(Service).filter(Service.name == service_name).first()
        if service:
            redirect_url = f"/service/{service.id}"
            redirect_label = result["navigation"]["label"]
    if not redirect_url and result.get("navigation"):
        nav_type = result["navigation"]["type"]
        redirect_label = result["navigation"]["label"]
        if nav_type == "scheme":
            scheme_name = entities.get("scheme_mentioned")
            if scheme_name and db.query(Scheme).filter(Scheme.name == scheme_name).first():
                redirect_url = f"/schemes?search={quote_plus(scheme_name)}"
            elif entities.get("scheme_category"):
                redirect_url = f"/schemes?category={quote_plus(entities['scheme_category'])}"
            else:
                redirect_url = "/schemes"
        elif nav_type == "applications":
            redirect_url = "/applications"
        elif nav_type == "profile":
            redirect_url = "/profile"
        elif nav_type == "services":
            redirect_url = "/services"
        elif nav_type == "notifications":
            redirect_url = "/notifications"
        elif nav_type == "settings":
            redirect_url = "/settings"

    return {
        "response": result["response"], "intent": result["intent"],
        "confidence": result["confidence"], "entities": entities,
        "updated_profile_fields": updated_fields,
        "missing_profile_fields": result.get("missing_profile_fields", []),
        "redirect_url": redirect_url,
        "redirect_label": redirect_label,
    }


@router.get("/history")
def get_history(session_id: str = "default", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Do not filter by a client-side session ID: local storage can be cleared
    # during navigation, while the account's conversation must remain intact.
    messages = (db.query(ChatMessage)
                .filter(ChatMessage.user_id == user.id)
                .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc()).all())
    return [{"sender": m.sender, "message": m.message, "intent": m.intent,
             "created_at": m.created_at.isoformat()} for m in messages]


@router.delete("/history")
def clear_history(session_id: str = "default", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete()
    db.commit()
    return {"message": "History cleared"}


@router.get("/new-session")
def new_session():
    return {"session_id": str(uuid.uuid4())}


@router.post("/transcribe")
async def transcribe_hindi(audio: UploadFile = File(...), user: User = Depends(get_current_user)):
    """Transcribe a short microphone clip with Google Cloud Speech-to-Text."""
    api_key = os.getenv("GOOGLE_SPEECH_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(503, "Voice transcription is not configured.")
    if audio.content_type not in {"audio/webm", "audio/webm;codecs=opus"}:
        raise HTTPException(415, "Please record audio in WebM format.")
    content = await audio.read()
    if not content:
        raise HTTPException(400, "The audio recording is empty.")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Voice recordings must be under 10 MB.")
    payload = json.dumps({
        "config": {
            "encoding": "WEBM_OPUS", "sampleRateHertz": 48000,
            "languageCode": "hi-IN", "enableAutomaticPunctuation": True,
        },
        "audio": {"content": base64.b64encode(content).decode("ascii")},
    }).encode("utf-8")
    request = Request(
        f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}", payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise HTTPException(503, "Google Speech-to-Text is not enabled for this API key.")
        raise HTTPException(502, "Google Speech-to-Text could not process the recording.")
    except (URLError, TimeoutError, ValueError):
        raise HTTPException(502, "Google Speech-to-Text is temporarily unavailable.")
    transcript = " ".join(
        item.get("alternatives", [{}])[0].get("transcript", "") for item in result.get("results", [])
    ).strip()
    if not transcript:
        raise HTTPException(422, "No Hindi speech was detected. Please try again.")
    return {"transcript": transcript}
