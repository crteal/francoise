import os

from .chat import chat, get_prompt_message_from_conversation, message_tuple_to_dict
from .db import open_db


def handle_inbound(conversation_id: int, text: str) -> str:
    """Generate a reply for an inbound message on a conversation.

    Reads the conversation, builds the prompt, persists the user message,
    calls the LLM, persists the reply, and returns the reply text. This is
    medium-agnostic: it knows nothing about email or HTTP.
    """
    database_url = os.environ.get('DATABASE_URL', 'data.db')
    llm_api_chat_url = os.environ.get('LLM_API_CHAT_URL', 'http://localhost:11434/api/chat')

    with open_db(database_url) as db:
        result = db.get_conversation(conversation_id)
        if not result:
            raise Exception('conversation with `id` %d does not exist' % conversation_id)

        conversation = db.conversation_to_dict(result)

        prompt = get_prompt_message_from_conversation(conversation)
        db.add_user_message(conversation_id, text)
        messages = db.get_messages_by_conversation(conversation_id)
        message_objects = list(map(message_tuple_to_dict, [prompt] + messages))
        reply = chat(message_objects, model=conversation.get('model'), url=llm_api_chat_url)
        db.add_assistant_message(conversation_id, reply)

    return reply
