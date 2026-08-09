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
             ('salt', 'TEXT NOT NULL'),
             ('password', 'TEXT NOT NULL')
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
        'conversations',
        [
            ('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('user_id', 'INTEGER NOT NULL'),
            ('agent_id', 'INTEGER NOT NULL'),
            ('model', 'TEXT NOT NULL'),
            ('proficiency', 'TEXT NOT NULL')
        ],
        [
            'UNIQUE(model, user_id, agent_id)',
            'FOREIGN KEY(user_id) REFERENCES users(id)',
            'FOREIGN KEY(agent_id) REFERENCES agents(id)'
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
    )
]

tables_by_name = {}
for table in tables:
    tables_by_name[table[0]] = table


class Database:
    def __init__(self, connection):
        self.connection = connection

    def delete_schema(self):
        for table_name in tables_by_name.keys():
            self.table_delete(table_name)

    def table_insert(self, table_name: str, **kwargs) -> tuple:
        table = tables_by_name.get(table_name)
        if not table:
            raise Exception('table with name `%s` is unspecified' % table_name)

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

    def create_agent(
            self,
            name: str,
            language: str,
            proficiency: str,
            prompt: str) -> tuple:
        return self.table_insert(
                'agents',
                name=name,
                language=language,
                proficiency=proficiency,
                prompt=prompt)

    def create_user(
            self,
            name: str,
            email: str,
            salt: str,
            password: str) -> tuple:
        return self.table_insert(
                'users',
                name=name,
                email=email,
                salt=salt,
                password=password)

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
                model=model)

    def create_message(self, conversation_id: int, role: str, content: str):
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
                conversation.model,
                conversation.user_id,
                user.email AS user_email,
                user.name AS user_name,
                conversation.proficiency AS user_proficiency,
                conversation.agent_id,
                agent.name AS agent_name,
                agent.language AS agent_language,
                agent.proficiency AS agent_proficiency,
                agent.prompt AS agent_prompt
            FROM conversations conversation
            JOIN users user
            ON conversation.user_id = user.id
            JOIN agents agent
            ON conversation.agent_id = agent.id
            WHERE conversation.id = ?
        """, (id,))
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
                         'agent_prompt'),
                    conversation))

    def get_messages_by_conversation(self, conversation_id: int):
        res = self.connection.execute("SELECT role, content FROM messages WHERE conversation_id = ?", (conversation_id,))
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
def open_db(url: str):
    connection = sqlite3.connect(url)
    try:
        yield Database(connection)
    finally:
        connection.close()
