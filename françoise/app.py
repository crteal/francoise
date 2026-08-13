import asyncio
import html
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import markdown as markdown_lib

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
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from evals.harness import CEFR_LEVELS

from .core import handle_inbound, stream_inbound
from .db import open_db
from .graph import open_graph
from .mail import parse_conversation_id_from_headers, send_mail, verify_signature
from .persona import build_persona_prompt
from .presence import is_free, presence_label, presence_local_time

TEMPLATES = Jinja2Templates(directory='templates')


def reply_fragment(conversation_id: int, message: str) -> str:
    # OOB fragment that appends a reply chunk (incoming letter) to an open
    # conversation's messages. Live chunks stay escaped plain text; only the
    # server-rendered history renders the persona's markdown.
    return ('<div id="messages-%d" hx-swap-oob="beforeend">'
            '<article class="letter letter--in"><div class="letter__body">%s'
            '</div></article></div>'
            % (conversation_id, html.escape(message)))


def unread_badge_fragment(conversation_id: int, count: int) -> str:
    # OOB fragment that raises the unread count on a background conversation.
    return ('<span id="unread-%d" hx-swap-oob="true">%d</span>'
            % (conversation_id, count))


def presence_fragment(conversation_id: int, agent: dict) -> str:
    # OOB fragment that refreshes the presence indicator (state + local time)
    # in the chat header and the conversation list for a conversation.
    label = html.escape(presence_label(agent))
    local_time = html.escape(presence_local_time(agent))
    return (
        '<span id="presence-%d" hx-swap-oob="true">%s %s</span>'
        % (conversation_id, label, local_time))


def render_message(role: str, content: str) -> str:
    # Server-rendered history: the persona's markdown becomes HTML; user text is
    # escaped. Python-Markdown passes raw HTML through, so escape first (markdown
    # syntax is *_#` etc., untouched by html.escape) — literal markup in an LLM
    # reply then shows as text instead of executing.
    if role == 'assistant':
        return markdown_lib.markdown(html.escape(content))
    return html.escape(content)


def get_config(
        config: dict[str, str],
        k: str,
        default: Optional[str] = None) -> str:
    # NOTE checks the configuration first, then the environment, then default
    return config.get(k, os.environ.get(k, default))


def App(**kwargs):

    app = FastAPI()

    app.mount('/static', StaticFiles(directory='static'), name='static')

    DATABASE_URL = get_config(kwargs, 'DATABASE_URL', 'data.db')
    LLM_API_CHAT_URL = get_config(kwargs, 'LLM_API_CHAT_URL', 'http://localhost:11434/api/chat')
    MAILGUN_API_KEY = get_config(kwargs, 'MAILGUN_API_KEY')
    MAILGUN_API_SENDER = get_config(kwargs, 'MAILGUN_API_SENDER')
    MAILGUN_API_URL = get_config(kwargs, 'MAILGUN_API_URL')
    SERVER_API_KEY = get_config(kwargs, 'SERVER_API_KEY')
    GRAPH_PATH = get_config(kwargs, 'GRAPH_PATH', 'graph.db')
    DEFAULT_MODEL = get_config(kwargs, 'DEFAULT_MODEL', 'ollama/llama3')

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

    # NOTE in-process fixed-window rate limit for each account, keyed by
    # account id -> (window_start, count). Enough for a single process; a
    # shared store is the upgrade path when we run more than one.
    # ponytail: fixed window, in-process; swap for a shared store at multi-process
    RATE_LIMIT = int(get_config(kwargs, 'RATE_LIMIT', '30'))
    RATE_LIMIT_WINDOW = float(get_config(kwargs, 'RATE_LIMIT_WINDOW', '60'))
    rate_counts: dict[int, tuple[float, int]] = {}

    def check_rate_limit(account_id: int) -> bool:
        # True if the account is under the limit (and this request counts),
        # False if it has crossed the limit inside the current window.
        now = time.monotonic()
        window_start, count = rate_counts.get(account_id, (now, 0))
        if now - window_start >= RATE_LIMIT_WINDOW:
            window_start, count = now, 0
        if count >= RATE_LIMIT:
            rate_counts[account_id] = (window_start, count)
            return False
        rate_counts[account_id] = (window_start, count + 1)
        return True

    app.state.check_rate_limit = check_rate_limit

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
            if sender != user_email:
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
    def login_form(request: Request):
        return TEMPLATES.TemplateResponse(request, 'login.html')

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

    @app.get('/signup', response_class=HTMLResponse)
    def signup_form(request: Request):
        return TEMPLATES.TemplateResponse(request, 'signup.html')

    @app.post('/signup', response_class=HTMLResponse)
    def signup(
            name: Annotated[str, Form()],
            email: Annotated[str, Form()],
            password: Annotated[str, Form()],
            response: Response,
            over_18: Annotated[Optional[str], Form()] = None) -> str:
        # Self-attested age gate: keep the product adults-only at launch.
        if over_18 != 'yes':
            response.status_code = status.HTTP_403_FORBIDDEN
            return 'You must be 18 or older to sign up.'

        password_hash = PasswordHasher().hash(password)
        with open_db(DATABASE_URL) as db:
            account = db.create_account(name)
        with open_db(DATABASE_URL, account_id=account[0]) as db:
            db.create_user(name, email, password_hash)

        return 'Signed up.'

    def require_session(session: Annotated[Optional[str], Cookie()] = None):
        if session is not None:
            with open_db(DATABASE_URL) as db:
                row = db.get_session(session)
                if row is not None:
                    # Resolve the owning account once and ride it on the row
                    # (session[3]) so account-scoped routes need no re-lookup.
                    account_id = db.get_account_id_for_user(row[1])
                    return tuple(row) + (account_id,)
        raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={'Location': '/login'})

    @app.get('/', response_class=HTMLResponse)
    def landing(request: Request,
                session: Annotated[Optional[str], Cookie()] = None):
        # Public magazine-cover landing. No auth: anonymous visitors see the
        # cover series; a logged-in visitor gets a link into the app instead
        # of the sign-up CTA.
        logged_in = False
        if session is not None:
            with open_db(DATABASE_URL) as db:
                logged_in = db.get_session(session) is not None
        return TEMPLATES.TemplateResponse(
            request, 'landing.html', {'logged_in': logged_in})

    @app.get('/app', response_class=HTMLResponse)
    def home(request: Request, session=Depends(require_session)):
        with open_db(DATABASE_URL, account_id=session[3]) as db:
            rows = db.list_conversations(session[1])
        conversations = []
        for id, agent_name, tz, age in rows:
            agent = {'timezone': tz, 'age': age}
            conversations.append({
                'id': id,
                'agent_name': agent_name,
                'presence': '%s %s' % (
                    presence_label(agent), presence_local_time(agent)),
            })
        return TEMPLATES.TemplateResponse(
            request, 'chat_list.html', {'conversations': conversations})

    @app.get('/c/{id}', response_class=HTMLResponse)
    def chat(request: Request, id: int, session=Depends(require_session)):
        with open_db(DATABASE_URL, account_id=session[3]) as db:
            row = db.get_conversation(id)
            if row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            conversation = db.conversation_to_dict(row)
            messages = [
                {'role': r,
                 'html': render_message(r, c),
                 'created_at': ts}
                for r, c, ts in db.get_messages_by_conversation(id)]
        return TEMPLATES.TemplateResponse(
            request, 'chat.html',
            {'conversation': conversation,
             'messages': messages,
             'presence': presence_label(conversation),
             'local_time': presence_local_time(conversation)})

    @app.get('/c/{id}/settings', response_class=HTMLResponse)
    def conversation_settings(
            request: Request, id: int, session=Depends(require_session)):
        with open_db(DATABASE_URL, account_id=session[3]) as db:
            row = db.get_conversation(id)
            if row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            conversation = db.conversation_to_dict(row)
        return TEMPLATES.TemplateResponse(
            request, 'conversation_settings.html',
            {'conversation': conversation, 'cefr_levels': CEFR_LEVELS})

    @app.post('/c/{id}/settings')
    def update_conversation_settings(
            request: Request,
            id: int,
            proficiency: Annotated[str, Form()],
            model: Annotated[str, Form()],
            session=Depends(require_session)):
        with open_db(DATABASE_URL, account_id=session[3]) as db:
            row = db.get_conversation(id)
            if row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            if proficiency not in CEFR_LEVELS:
                conversation = db.conversation_to_dict(row)
                return TEMPLATES.TemplateResponse(
                    request, 'conversation_settings.html',
                    {'conversation': conversation,
                     'cefr_levels': CEFR_LEVELS,
                     'error': 'Proficiency must be one of %s.'
                              % ', '.join(CEFR_LEVELS)},
                    status_code=status.HTTP_400_BAD_REQUEST)
            db.update_conversation_settings(id, proficiency, model)
        return RedirectResponse(
            '/c/%d' % id, status_code=status.HTTP_303_SEE_OTHER)

    @app.get('/settings', response_class=HTMLResponse)
    def account_settings(request: Request, session=Depends(require_session)):
        with open_db(DATABASE_URL, account_id=session[3]) as db:
            account = db.get_account(session[3])
        return TEMPLATES.TemplateResponse(
            request, 'account_settings.html',
            {'always_available': bool(account[3])})

    @app.post('/settings')
    def update_account_settings(
            session=Depends(require_session),
            always_available: Annotated[Optional[str], Form()] = None):
        with open_db(DATABASE_URL, account_id=session[3]) as db:
            db.set_account_always_available(
                session[3], always_available == 'yes')
        return RedirectResponse(
            '/settings', status_code=status.HTTP_303_SEE_OTHER)

    @app.get('/agents', response_class=HTMLResponse)
    def list_agents(request: Request, session=Depends(require_session)):
        with open_db(DATABASE_URL, account_id=session[3]) as db:
            rows = db.list_agents()
        agents = [
            dict(zip(('id', 'name', 'language', 'proficiency', 'location'), r))
            for r in rows]
        return TEMPLATES.TemplateResponse(
            request, 'agents_list.html', {'agents': agents})

    @app.get('/agents/new', response_class=HTMLResponse)
    def new_agent(request: Request, session=Depends(require_session)):
        return TEMPLATES.TemplateResponse(
            request, 'agents_new.html', {'cefr_levels': CEFR_LEVELS})

    @app.post('/agents')
    def create_agent(
            request: Request,
            name: Annotated[str, Form()],
            native_language: Annotated[str, Form()],
            language: Annotated[str, Form()],
            proficiency: Annotated[str, Form()],
            session=Depends(require_session),
            location: Annotated[Optional[str], Form()] = None,
            timezone: Annotated[Optional[str], Form()] = None,
            interests: Annotated[Optional[str], Form()] = None,
            age: Annotated[Optional[str], Form()] = None):
        # Validate at the trust boundary before anything is persisted.
        error = None
        parsed_age = None
        if proficiency not in CEFR_LEVELS:
            error = 'Proficiency must be one of %s.' % ', '.join(CEFR_LEVELS)
        elif timezone:
            try:
                ZoneInfo(timezone)
            except (ZoneInfoNotFoundError, ValueError):
                error = 'Timezone must be a valid IANA name.'
        if error is None and age:
            try:
                parsed_age = int(age)
            except ValueError:
                error = 'Age must be a number.'

        if error is not None:
            return TEMPLATES.TemplateResponse(
                request, 'agents_new.html',
                {'cefr_levels': CEFR_LEVELS, 'error': error},
                status_code=status.HTTP_400_BAD_REQUEST)

        interest_list = [
            i.strip() for i in (interests or '').split(',') if i.strip()]
        interests_text = ', '.join(interest_list) or None

        prompt = build_persona_prompt({
            'name': name,
            'native_language': native_language,
            'location': location,
            'timezone': timezone,
            'interests': interests_text,
            'age': parsed_age,
        })

        with open_db(DATABASE_URL, account_id=session[3]) as db:
            agent = db.create_agent(
                name, language, proficiency, prompt,
                location=location,
                timezone=timezone,
                interests=interests_text,
                age=parsed_age,
                native_language=native_language)

        # Seed the persona into the shared `real` graph via the existing helper.
        with open_graph(GRAPH_PATH) as graph:
            graph.seed_persona(agent[0], name, interests=interest_list)

        return RedirectResponse(
            '/agents', status_code=status.HTTP_303_SEE_OTHER)

    @app.post('/agents/{id}/start')
    def start_conversation(id: int, session=Depends(require_session)):
        with open_db(DATABASE_URL, account_id=session[3]) as db:
            agent = db.get_agent(id)
            if agent is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            conversation = db.create_conversation(
                user_id=session[1],
                agent_id=id,
                proficiency=agent[3],
                model=DEFAULT_MODEL)
        return RedirectResponse(
            '/c/%d' % conversation[0],
            status_code=status.HTTP_302_FOUND)

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

    def get_agent(conversation_id: int) -> tuple[dict, bool]:
        # The persona fields presence reads (timezone/age) ride on the
        # conversation dict; absent ones fall back to UTC/adult in presence.
        # Also returns the owning account's always_available toggle.
        with open_db(DATABASE_URL) as resolver:
            account_id = resolver.get_account_id_for_conversation(conversation_id)
        with open_db(DATABASE_URL, account_id=account_id) as db:
            agent = db.conversation_to_dict(db.get_conversation(conversation_id))
            account = db.get_account(account_id)
        always_available = bool(account[3]) if account else False
        return agent, always_available

    def is_adult(agent: dict) -> bool:
        # Presence treats a missing/non-numeric age as an adult (see
        # presence._schedule), so mirror that here.
        try:
            return int(agent.get('age')) >= 18
        except (TypeError, ValueError):
            return True

    async def wait_until_free(
            agent: dict,
            always_available: bool = False,
            poll: float = 60.0) -> None:
        # Hold here while the persona is asleep/at school; wake in the next
        # free window. Re-checks presence each poll against the moving clock.
        # An adult persona on an always-available account skips the wait; a
        # child persona (age < 18) STILL defers regardless of the toggle.
        if always_available and is_adult(agent):
            return
        while not is_free(agent):
            await asyncio.sleep(poll)

    async def reply_and_push(user_id: int, conversation_id: int, message: str) -> None:
        # Stream the reply through the core and push each chunk to the user's
        # channel so the browser shows the reply as it arrives. Hold the reply
        # until the persona is free (not asleep or at school).
        agent, always_available = get_agent(conversation_id)
        await wait_until_free(agent, always_available)
        channel = get_channel(user_id)
        # Refresh the presence indicator now that the persona is free.
        await channel.put(presence_fragment(conversation_id, agent))
        chunks = stream_inbound(conversation_id, message)
        sentinel = object()
        while True:
            chunk = await asyncio.to_thread(next, chunks, sentinel)
            if chunk is sentinel:
                break
            await channel.put(reply_fragment(conversation_id, chunk))

    @app.post('/c/{id}/message', response_class=HTMLResponse)
    def post_message(
            id: int,
            message: Annotated[str, Form()],
            background_tasks: BackgroundTasks,
            session=Depends(require_session)) -> str:
        with open_db(DATABASE_URL) as resolver:
            account_id = resolver.get_account_id_for_conversation(id)
        if account_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        if not check_rate_limit(account_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS)

        # NOTE handle_inbound persists the user message, so the route no longer
        # saves it; run it off-thread and stream the reply back over /stream.
        background_tasks.add_task(reply_and_push, session[1], id, message)

        # user message partial for an immediate echo (outgoing letter)
        return ('<article class="letter letter--out"><div class="letter__body">'
                '%s</div></article>' % html.escape(message))

    @app.post('/mailgun', status_code=200)
    async def mailgun(
            headers: Annotated[str, Form(alias='message-headers')],
            message: Annotated[str, Form(alias='body-plain')],
            sender: Annotated[str, Form()],
            subject: Annotated[str, Form()],
            timestamp: Annotated[str, Form()],
            token: Annotated[str, Form()],
            signature: Annotated[str, Form()],
            background_tasks: BackgroundTasks) -> None:
        if not verify_signature(
                MAILGUN_API_KEY, timestamp, token, signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        background_tasks.add_task(
                chat_and_reply,
                headers,
                message,
                sender,
                subject)

    return app
