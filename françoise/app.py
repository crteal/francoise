import os
import re
from typing import Annotated, Optional

from fastapi import BackgroundTasks, FastAPI, Form, Response, status

from .core import handle_inbound
from .db import open_db
from .mail import parse_conversation_id_from_headers, send_mail


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

    def chat_and_reply(
            headers: str,
            message: str,
            sender: Optional[str],
            subject: Optional[str]) -> None:
        conversation_id = parse_conversation_id_from_headers(headers)
        if not conversation_id:
            raise Exception('unspecified conversation `id` in %s' % (headers,))

        with open_db(DATABASE_URL) as db:
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
