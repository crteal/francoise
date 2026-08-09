import asyncio
import html
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import (
    BackgroundTasks,
    Cookie,
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, StreamingResponse

from .core import handle_inbound
from .db import open_db
from .mail import parse_conversation_id_from_headers, send_mail

LOGIN_FORM = """<!DOCTYPE html>
<html lang="en">
<body>
    <form method="post" action="/login">
        <input type="email" name="email" required>
        <input type="password" name="password" required>
        <button type="submit">Log in</button>
    </form>
</body>
</html>
"""


def reply_fragment(conversation_id: int, message: str) -> str:
    # OOB fragment that appends a reply to an open conversation's messages.
    return ('<div id="messages-%d" hx-swap-oob="beforeend"><div>%s</div></div>'
            % (conversation_id, html.escape(message)))


def unread_badge_fragment(conversation_id: int, count: int) -> str:
    # OOB fragment that raises the unread count on a background conversation.
    return ('<span id="unread-%d" hx-swap-oob="true">%d</span>'
            % (conversation_id, count))


def get_config(
        config: dict[str, str],
        k: str,
        default: Optional[str] = None) -> str:
    # NOTE checks the configuration first, then the environment, then default
    return config.get(k, os.environ.get(k, default))


def App(**kwargs):

    app = FastAPI()

    DATABASE_URL = get_config(kwargs, 'DATABASE_URL', 'data.db')
    LLM_API_CHAT_URL = get_config(kwargs, 'LLM_API_CHAT_URL', 'http://localhost:11434/api/chat')
    MAILGUN_API_KEY = get_config(kwargs, 'MAILGUN_API_KEY')
    MAILGUN_API_SENDER = get_config(kwargs, 'MAILGUN_API_SENDER')
    MAILGUN_API_URL = get_config(kwargs, 'MAILGUN_API_URL')
    SERVER_API_KEY = get_config(kwargs, 'SERVER_API_KEY')

    # NOTE one message channel for each user, keyed by user id, so events
    # route to the right user instead of leaking through a shared queue.
    # ponytail: plain dict, no eviction; add cleanup when SSE tasks land (#17)
    channels: dict[int, asyncio.Queue] = {}

    def get_channel(user_id: int) -> asyncio.Queue:
        channel = channels.get(user_id)
        if channel is None:
            channel = channels[user_id] = asyncio.Queue()
        return channel

    app.state.channels = channels
    app.state.get_channel = get_channel

    def chat_and_reply(
            headers: str,
            message: str,
            sender: Optional[str],
            subject: Optional[str]) -> None:
        conversation_id = parse_conversation_id_from_headers(headers)
        if not conversation_id:
            raise Exception('unspecified conversation `id` in %s' % (headers,))

        with open_db(DATABASE_URL) as resolver:
            account_id = resolver.get_account_id_for_conversation(conversation_id)
        if account_id is None:
            raise Exception('conversation with `id` %d does not exist' % conversation_id)

        with open_db(DATABASE_URL, account_id=account_id) as db:
            result = db.get_conversation(conversation_id)

            if not result:
                raise Exception('conversation with `id` %d does not exist' % conversation_id)

            conversation = db.conversation_to_dict(result)

            user_email = conversation.get('user_email')
            if sender not in user_email:
                raise Exception('invalid user email `%s` for conversation %d' % (user_email, conversation_id))

        response = handle_inbound(conversation_id, message)

        data = {
            "from": "%s.%d <%s>" % (conversation.get('agent_name'), conversation_id, MAILGUN_API_SENDER),
            "to": sender,
            "text": response
        }

        # NOTE what follows is integral to threaded replies
        match = re.search('"Message-Id","([^\"]*)"', headers)
        if match:
            data["h:In-Reply-To"] = match.group(1)

        # NOTE only add the subject if it exists
        if subject:
            data['subject'] = subject

        send_mail(MAILGUN_API_URL, api_key=MAILGUN_API_KEY, data=data)

    @app.get('/heartbeat', status_code=200)
    def heartbeat(api_key: str, response: Response) -> None:
        if api_key != SERVER_API_KEY:
            response.status_code = status.HTTP_401_UNAUTHORIZED

    @app.get('/login', response_class=HTMLResponse)
    def login_form() -> str:
        return LOGIN_FORM

    @app.post('/login', response_class=HTMLResponse)
    def login(
            email: Annotated[str, Form()],
            password: Annotated[str, Form()],
            response: Response) -> str:
        with open_db(DATABASE_URL) as db:
            user = db.get_user_by_email(email)

        if user is not None:
            try:
                PasswordHasher().verify(user[3], password)
            except VerifyMismatchError:
                user = None

        if user is None:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return 'Invalid email or password.'

        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        with open_db(DATABASE_URL) as db:
            db.create_session(session_id, user[0], expires_at.isoformat())

        response.set_cookie('session', session_id, httponly=True)

        return 'Logged in.'

    def require_session(session: Annotated[Optional[str], Cookie()] = None):
        if session is not None:
            with open_db(DATABASE_URL) as db:
                row = db.get_session(session)
            if row is not None:
                return row
        raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={'Location': '/login'})

    @app.get('/', response_class=HTMLResponse)
    def home(session=Depends(require_session)) -> str:
        return 'Welcome.'

    @app.get('/stream')
    async def stream(request: Request, session=Depends(require_session)):
        channel = get_channel(session[1])

        async def events():
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(channel.get(), timeout=1)
                except asyncio.TimeoutError:
                    continue
                yield 'data: %s\n\n' % event

        return StreamingResponse(events(), media_type='text/event-stream')

    @app.post('/c/{id}/message', response_class=HTMLResponse)
    def post_message(
            id: int,
            message: Annotated[str, Form()],
            session=Depends(require_session)) -> str:
        with open_db(DATABASE_URL) as resolver:
            account_id = resolver.get_account_id_for_conversation(id)
        if account_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        with open_db(DATABASE_URL, account_id=account_id) as db:
            db.add_user_message(id, message)

        # user message partial for an immediate echo
        return '<div>%s</div>' % html.escape(message)

    @app.post('/mailgun', status_code=200)
    async def mailgun(
            headers: Annotated[str, Form(alias='message-headers')],
            message: Annotated[str, Form(alias='body-plain')],
            sender: Annotated[str, Form()],
            subject: Annotated[str, Form()],
            background_tasks: BackgroundTasks) -> None:
        background_tasks.add_task(
                chat_and_reply,
                headers,
                message,
                sender,
                subject)

    return app
