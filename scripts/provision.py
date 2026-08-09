#!/usr/bin/env python3
"""Provision a ready-to-test environment in one non-interactive command.

Migrates the target database to head then seeds one account, user, agent, and
conversation, printing the seeded ids and credentials as JSON on stdout so
automation (QA, integration tests, smoke tests) can log in immediately.

    uv run python -m scripts.provision --database dev.db --reset
"""

import argparse
import json
import os
import sys

from argon2 import PasswordHasher

from françoise.db import open_db
from françoise.migrate import upgrade_to_head


def provision(
        database='dev.db',
        reset=False,
        account='Acme',
        name='Alice',
        email='alice@example.com',
        password='correct horse',
        agent_name='Boku',
        language='French',
        proficiency='A1',
        prompt='You are {agent_name}.',
        model='ollama/llama3',
        timezone='UTC',
        age=10):
    if reset and os.path.exists(database):
        os.remove(database)

    upgrade_to_head(database)
    password_hash = PasswordHasher().hash(password)

    with open_db(database) as db:
        account_row = db.create_account(account)

    with open_db(database, account_id=account_row[0]) as db:
        user = db.create_user(name, email, password_hash)
        # create_agent has no persona kwargs; insert directly so timezone/age
        # are present and presence is testable.
        agent = db.table_insert(
                'agents',
                name=agent_name,
                language=language,
                proficiency=proficiency,
                prompt=prompt,
                timezone=timezone,
                age=age)
        conversation = db.create_conversation(
                user_id=user[0],
                agent_id=agent[0],
                proficiency=proficiency,
                model=model)

    return {
        'account_id': account_row[0],
        'user_id': user[0],
        'agent_id': agent[0],
        'conversation_id': conversation[0],
        'email': email,
        'password': password,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='dev.db')
    parser.add_argument('--reset', action='store_true')
    parser.add_argument('--email', default='alice@example.com')
    parser.add_argument('--password', default='correct horse')
    parser.add_argument('--account', default='Acme')
    parser.add_argument('--name', default='Alice')
    parser.add_argument('--agent-name', default='Boku')
    parser.add_argument('--language', default='French')
    parser.add_argument('--proficiency', default='A1')
    parser.add_argument('--model', default='ollama/llama3')
    parser.add_argument('--timezone', default='UTC')
    parser.add_argument('--age', type=int, default=10)
    args = parser.parse_args(argv)

    seeded = provision(
        database=args.database,
        reset=args.reset,
        account=args.account,
        name=args.name,
        email=args.email,
        password=args.password,
        agent_name=args.agent_name,
        language=args.language,
        proficiency=args.proficiency,
        model=args.model,
        timezone=args.timezone,
        age=args.age)
    json.dump(seeded, sys.stdout)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
