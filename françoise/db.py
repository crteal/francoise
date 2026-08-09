from contextlib import contextmanager
from datetime import datetime, timezone
import sqlite3

tables = [
    (
        'accounts',
        [
            ('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('name', 'TEXT NOT NULL'),
            ('created_at', 'TEXT NOT NULL')
        ]
    ),

    (
        'users',
         [
             ('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
             ('name', 'TEXT NOT NULL'),
             ('email', 'TEXT UNIQUE'),
             ('password_hash', 'TEXT NOT NULL')
         ]
    ),

    (
         'agents',
         [
             ('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
             ('name', 'TEXT NOT NULL'),
             ('language', 'TEXT NOT NULL'),
             ('proficiency', 'TEXT NOT NULL'),
             ('prompt', 'TEXT NOT NULL')
         ]
    ),

    (
        'model_configs',
        [
            ('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('dialect', 'TEXT'),
            ('host', 'TEXT'),
            ('endpoint', 'TEXT'),
            ('model_id', 'TEXT NOT NULL'),
            ('params', 'TEXT'),
            ('credential_ref', 'TEXT')
        ],
        [
            'UNIQUE(model_id)'
        ]
    ),

    (
        'conversations',
        [
            ('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('user_id', 'INTEGER NOT NULL'),
            ('agent_id', 'INTEGER NOT NULL'),
            ('model_config_id', 'INTEGER NOT NULL'),
            ('proficiency', 'TEXT NOT NULL')
        ],
        [
            'UNIQUE(model_config_id, user_id, agent_id)',
            'FOREIGN KEY(user_id) REFERENCES users(id)',
            'FOREIGN KEY(agent_id) REFERENCES agents(id)',
            'FOREIGN KEY(model_config_id) REFERENCES model_configs(id)'
        ]
    ),

    (
        'messages',
        [
            ('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('conversation_id', 'INTEGER NOT NULL'),
            ('role', 'TEXT NOT NULL'),
            ('content', 'TEXT NOT NULL'),
            ('created_at', 'TEXT NOT NULL')
        ],
        [
            'FOREIGN KEY(conversation_id) REFERENCES conversations(id)'
        ]
    ),

    (
        'sessions',
        [
            ('id', 'TEXT PRIMARY KEY'),
            ('user_id', 'INTEGER NOT NULL'),
            ('expires_at', 'TEXT NOT NULL')
        ],
        [
            'FOREIGN KEY(user_id) REFERENCES users(id)'
        ]
    )
]

tables_by_name = {}
for table in tables:
    tables_by_name[table[0]] = table


# Tables scoped by a tenant account. `accounts` is the tenant itself and
# `messages` is scoped transitively through its conversation.
account_scoped_tables = ('users', 'agents', 'conversations')


class Database:
    def __init__(self, connection, account_id=None):
        self.connection = connection
        self.account_id = account_id

    def require_account(self) -> int:
        if self.account_id is None:
            raise Exception('query requires an `account_id`')
        return self.account_id

    def delete_schema(self):
        for table_name in tables_by_name.keys():
            self.table_delete(table_name)

    def table_insert(self, table_name: str, **kwargs) -> tuple:
        table = tables_by_name.get(table_name)
        if not table:
            raise Exception('table with name `%s` is unspecified' % table_name)

        if table_name in account_scoped_tables:
            kwargs['account_id'] = self.require_account()

        columns = []
        params = []
        # TODO verify that the column exists on the table using the definition
        for key, value in kwargs.items():
            columns.append(key)
            params.append(value)

        sql = 'INSERT INTO {table_name} ({columns}) VALUES ({values}) RETURNING *;'.format(
                table_name=table_name,
                columns=','.join(columns),
                values=','.join(list(map(lambda col: '?', columns))))

        with self.connection:
            cursor = self.connection.execute(sql, params)
            row = cursor.fetchone()

        return row

    def create_account(self, name: str) -> tuple:
        now = datetime.now(timezone.utc)
        return self.table_insert(
                'accounts',
                name=name,
                created_at=now.isoformat())

    def get_account(self, id: int):
        res = self.connection.execute(
            "SELECT id, name, created_at FROM accounts WHERE id = ?", (id,))
        return res.fetchone()

    def get_account_id_for_conversation(self, conversation_id: int):
        # Unscoped resolver: identifies which tenant owns a conversation so a
        # caller can open a scoped Database. This is the one entry point that
        # runs before an account is known.
        res = self.connection.execute(
            "SELECT account_id FROM conversations WHERE id = ?",
            (conversation_id,))
        row = res.fetchone()
        return row[0] if row else None

    def get_account_id_for_user(self, user_id: int):
        # Unscoped resolver: a session carries only the user id, so map it to
        # its owning account before opening a scoped Database.
        res = self.connection.execute(
            "SELECT account_id FROM users WHERE id = ?", (user_id,))
        row = res.fetchone()
        return row[0] if row else None

    def create_agent(
            self,
            name: str,
            language: str,
            proficiency: str,
            prompt: str,
            location: str = None,
            timezone: str = None,
            interests: str = None,
            age: int = None,
            native_language: str = None) -> tuple:
        # Optional structured persona fields default to None so the existing
        # 4-arg callers (provisioner, tests) keep working; only set columns
        # that were given.
        extra = {
            'location': location,
            'timezone': timezone,
            'interests': interests,
            'age': age,
            'native_language': native_language,
        }
        return self.table_insert(
                'agents',
                name=name,
                language=language,
                proficiency=proficiency,
                prompt=prompt,
                **{k: v for k, v in extra.items() if v is not None})

    def list_agents(self) -> list:
        # Account-scoped list for the persona index (name, language, level,
        # location).
        res = self.connection.execute(
            "SELECT id, name, language, proficiency, location FROM agents "
            "WHERE account_id = ? ORDER BY id",
            (self.require_account(),))
        return res.fetchall()

    def get_agent(self, id: int):
        res = self.connection.execute(
            "SELECT id, name, language, proficiency FROM agents "
            "WHERE id = ? AND account_id = ?",
            (id, self.require_account()))
        return res.fetchone()

    def create_user(
            self,
            name: str,
            email: str,
            password_hash: str) -> tuple:
        return self.table_insert(
                'users',
                name=name,
                email=email,
                password_hash=password_hash)

    def get_user_by_email(self, email: str):
        # Unscoped lookup: login happens before an account is known and
        # `users.email` is globally UNIQUE.
        res = self.connection.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email,))
        return res.fetchone()

    def create_session(
            self,
            id: str,
            user_id: int,
            expires_at: str) -> tuple:
        return self.table_insert(
                'sessions',
                id=id,
                user_id=user_id,
                expires_at=expires_at)

    def get_session(self, id: str):
        res = self.connection.execute(
            "SELECT id, user_id, expires_at FROM sessions WHERE id = ?", (id,))
        return res.fetchone()

    def delete_session(self, id: str):
        with self.connection:
            self.connection.execute(
                "DELETE FROM sessions WHERE id = ?", (id,))

    def upsert_model_config(self, model_id: str) -> int:
        # Reuse a config for the same model string rather than duplicating it.
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO model_configs (model_id) VALUES (?)",
                (model_id,))
        res = self.connection.execute(
            "SELECT id FROM model_configs WHERE model_id = ?", (model_id,))
        return res.fetchone()[0]

    def create_conversation(
            self,
            user_id: int,
            agent_id: int,
            proficiency: str,
            model: str) -> tuple:
        return self.table_insert(
                'conversations',
                user_id=user_id,
                agent_id=agent_id,
                proficiency=proficiency,
                model_config_id=self.upsert_model_config(model))

    def create_message(self, conversation_id: int, role: str, content: str):
        # messages are scoped through their conversation's account
        if not self.get_conversation(conversation_id):
            raise Exception(
                'conversation with `id` %d does not exist for account'
                % conversation_id)
        now = datetime.now(timezone.utc)
        return self.table_insert(
                'messages',
                conversation_id=conversation_id,
                role=role,
                content=content,
                created_at=now.isoformat())

    def add_user_message(self, conversation_id: int, content: str):
        self.create_message(conversation_id, 'user', content)

    def add_assistant_message(self, conversation_id: int, content: str):
        self.create_message(conversation_id, 'assistant', content)

    def get_conversation(self, id: int):
        res = self.connection.execute("""
            SELECT
                conversation.id,
                model_config.model_id AS model,
                conversation.user_id,
                user.email AS user_email,
                user.name AS user_name,
                conversation.proficiency AS user_proficiency,
                conversation.agent_id,
                agent.name AS agent_name,
                agent.language AS agent_language,
                agent.proficiency AS agent_proficiency,
                agent.prompt AS agent_prompt,
                agent.timezone AS timezone,
                agent.age AS age
            FROM conversations conversation
            JOIN users user
            ON conversation.user_id = user.id
            JOIN agents agent
            ON conversation.agent_id = agent.id
            JOIN model_configs model_config
            ON conversation.model_config_id = model_config.id
            WHERE conversation.id = ?
            AND conversation.account_id = ?
        """, (id, self.require_account()))
        return res.fetchone()

    def conversation_to_dict(self, conversation: tuple) -> dict[str, str]:
        return dict(zip(('id',
                         'model',
                         'user_id',
                         'user_email',
                         'user_name',
                         'user_proficiency',
                         'agent_id',
                         'agent_name',
                         'agent_language',
                         'agent_proficiency',
                         'agent_prompt',
                         'timezone',
                         'age'),
                    conversation))

    def get_messages_by_conversation(self, conversation_id: int):
        res = self.connection.execute("""
            SELECT role, content FROM messages
            WHERE conversation_id = ?
            AND conversation_id IN (
                SELECT id FROM conversations WHERE account_id = ?
            )
        """, (conversation_id, self.require_account()))
        return res.fetchall()

    def table_delete(self, table_name: str):
        table = tables_by_name.get(table_name)
        if not table:
            raise Exception('table with name `%s` is unspecified' % table_name)

        with self.connection:
            self.connection.execute("DELETE FROM %s" % (table_name,))
            self.connection.execute("DELETE FROM SQLITE_SEQUENCE WHERE name = ?", [table_name])

    def delete_messages(self):
        self.table_delete('messages')


@contextmanager
def open_db(url: str, account_id=None):
    connection = sqlite3.connect(url)
    try:
        yield Database(connection, account_id)
    finally:
        connection.close()
