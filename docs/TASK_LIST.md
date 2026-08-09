# françoise — task list

This task list comes from `docs/PLAN.md`. Each task takes one day or less for a junior
engineer. The text follows ASD-STE100 style: short sentences, active voice, simple tenses,
and one instruction per sentence.

## Glossary

- **OLTP store** — the SQLite database of record. It holds accounts, users, sessions,
  agents, conversations, and messages.
- **The graph** — the Oxigraph RDF store. It holds what an agent knows as quads.
- **Quad** — a fact with four parts: subject, predicate, object, and provenance graph.
- **Provenance graph** — the fourth part of a quad. It marks the source: `real`, `world`,
  `synthetic`, or `inferred`.
- **IRI** — the identifier for a graph entity. We mint URNs like `urn:francoise:agent:42`.
- **Agent** — the persona. It has a name, a location, an age, and a language level.
- **Presence** — the state of a persona in its local time: `asleep`, `school`, `free`,
  or `busy`.
- **Core** — the module `core.py`. It turns an inbound message into a reply.

---

## Phase 1 — Core

### Task 1 — Create the core module

**Goal:** Move the reply logic into one function that works for any medium.

**Requirements:**
1. Create the file `françoise/core.py`.
2. Add the function `handle_inbound(conversation_id, text)`.
3. Make the function return the reply text.
4. Do not import FastAPI in `core.py`.

**Acceptance criteria:**
- The module `core.py` has the function `handle_inbound`.
- The function returns a string.
- The module imports no HTTP code.

**Test plan:**
1. Import `handle_inbound` in a test.
2. Call the function with a test conversation.
3. Check that the function returns the reply text.

### Task 2 — Move the chat logic into the core

**Goal:** Put the current email reply steps inside `handle_inbound`.

**Requirements:**
1. Move the database read, the prompt build, the chat call, and the writes from
   `chat_and_reply` into `handle_inbound`.
2. Keep the same order of steps.
3. Return the reply text instead of sending mail.

**Acceptance criteria:**
- The function reads the conversation from the OLTP store.
- The function writes the user message and the reply to the OLTP store.
- The function does not send mail.

**Test plan:**
1. Seed a test conversation in a temporary database.
2. Call `handle_inbound`.
3. Check that the store has the new user message and the new reply.

### Task 3 — Connect the Mailgun route to the core

**Goal:** Make the email path call the core and then send the reply.

**Requirements:**
1. Change the `/mailgun` route to call `handle_inbound`.
2. Send the returned text with the Mailgun adapter.
3. Remove the moved logic from `chat_and_reply`.

**Acceptance criteria:**
- The route calls `handle_inbound`.
- The route sends the reply text by mail.
- The email behavior does not change.

**Test plan:**
1. Send a test webhook to `/mailgun`.
2. Check that the core runs.
3. Check that the adapter sends the reply.

### Task 4 — Write core tests

**Goal:** Protect the core with unit tests.

**Requirements:**
1. Add a test file for `core.py`.
2. Test one normal reply.
3. Test one error when the conversation does not exist.

**Acceptance criteria:**
- The tests run with the project test command.
- The normal test passes.
- The error test passes.

**Test plan:**
1. Run the test command.
2. Check that all core tests pass.

---

## Phase 2 — Migrations and tenancy

### Task 5 — Add Alembic

**Goal:** Manage schema changes with ordered migrations.

**Requirements:**
1. Add Alembic to the project dependencies.
2. Start Alembic with a migrations folder.
3. Write migrations as raw SQL with `op.execute`.

**Acceptance criteria:**
- The command `alembic upgrade head` runs with no error.
- Alembic owns the `alembic_version` table.

**Test plan:**
1. Run `alembic upgrade head` on an empty database.
2. Check that the version table exists.

### Task 6 — Write the base migration

**Goal:** Recreate the current tables through Alembic.

**Requirements:**
1. Write a migration that creates `users`, `agents`, `conversations`, and `messages`.
2. Remove the old `create_schema` bootstrap from `db.py`.
3. Add a downgrade that drops the tables.

**Acceptance criteria:**
- The upgrade creates the four tables.
- The downgrade drops the four tables.

**Test plan:**
1. Run the upgrade.
2. Check that the four tables exist.
3. Run the downgrade and check that the tables are gone.

### Task 7 — Add the accounts table

**Goal:** Add the tenant table.

**Requirements:**
1. Write a migration that creates `accounts` with `id`, `name`, and `created_at`.
2. Add insert and read functions for accounts in `db.py`.

**Acceptance criteria:**
- The `accounts` table exists after the upgrade.
- The functions insert and read an account.

**Test plan:**
1. Run the upgrade.
2. Insert an account.
3. Read the account back and check the fields.

### Task 8 — Add account scope to the core tables

**Goal:** Link users, agents, and conversations to an account.

**Requirements:**
1. Write a migration that adds `account_id` to `users`, `agents`, and `conversations`.
2. Add foreign keys to `accounts`.

**Acceptance criteria:**
- Each table has an `account_id` column.
- Each `account_id` references `accounts`.

**Test plan:**
1. Run the upgrade.
2. Insert rows with an account.
3. Check that a bad `account_id` fails.

### Task 9 — Add IRI columns

**Goal:** Give users and agents a graph identity.

**Requirements:**
1. Write a migration that adds `iri` to `users` and `agents`.
2. Set the IRI from the type and the id, for example `urn:francoise:agent:42`.
3. Do not build the IRI from a name.

**Acceptance criteria:**
- Each user has an IRI.
- Each agent has an IRI.
- The IRI uses the surrogate id.

**Test plan:**
1. Run the upgrade.
2. Insert a user and an agent.
3. Check that each IRI matches the id pattern.

### Task 10 — Scope the queries by account

**Goal:** Enforce tenant isolation in the data layer.

**Requirements:**
1. Add an `account_id` filter to every read and write in `db.py`.
2. Reject a query that has no `account_id`.

**Acceptance criteria:**
- Each query filters by `account_id`.
- A query without an account raises an error.

**Test plan:**
1. Seed two accounts with data.
2. Read as account one.
3. Check that the result excludes account two.

---

## Phase 3 — Web authentication

### Task 11 — Use argon2id for passwords

**Goal:** Hash passwords with argon2id.

**Requirements:**
1. Add the argon2 library to the dependencies.
2. Change the user scripts to store one `password_hash`.
3. Write a migration that replaces the `salt` and `password` columns.

**Acceptance criteria:**
- The store keeps one `password_hash` per user.
- The hash uses argon2id.

**Test plan:**
1. Onboard a test user.
2. Check that the store holds an argon2id hash.

### Task 12 — Add the sessions table

**Goal:** Store web sessions.

**Requirements:**
1. Write a migration that creates `sessions` with `id`, `user_id`, and `expires_at`.
2. Add functions to create, read, and delete a session.

**Acceptance criteria:**
- The `sessions` table exists.
- The functions create, read, and delete a session.

**Test plan:**
1. Create a session.
2. Read the session back.
3. Delete the session and check that it is gone.

### Task 13 — Add the login routes

**Goal:** Let a user log in with a password.

**Requirements:**
1. Add `GET /login` that shows the login form.
2. Add `POST /login` that checks the password with argon2id.
3. Create a session on a correct password.

**Acceptance criteria:**
- A correct password creates a session.
- A wrong password shows an error.

**Test plan:**
1. Post a correct password and check for a session.
2. Post a wrong password and check for the error.

### Task 14 — Add the session cookie and guard

**Goal:** Protect pages behind a session.

**Requirements:**
1. Set a session cookie after login.
2. Add an auth dependency that reads the cookie.
3. Redirect a request with no session to `/login`.

**Acceptance criteria:**
- A logged-in request reaches the page.
- A request with no session goes to `/login`.

**Test plan:**
1. Request a page with a valid cookie.
2. Request the same page with no cookie.
3. Check the redirect.

---

## Phase 4 — Web chat

### Task 15 — Replace the global queue

**Goal:** Remove the shared queue that leaks messages between users.

**Requirements:**
1. Remove the single global `asyncio.Queue`.
2. Add one message channel for each user.
3. Route each event to the correct user only.

**Acceptance criteria:**
- Each user has a separate channel.
- One user does not receive another user's events.

**Test plan:**
1. Connect two test users.
2. Send an event to user one.
3. Check that user two receives nothing.

### Task 16 — Add the message post route

**Goal:** Accept a chat message from the web form.

**Requirements:**
1. Add `POST /c/{id}/message`.
2. Save the user message to the store.
3. Return the user message partial for an immediate echo.

**Acceptance criteria:**
- The route saves the message.
- The route returns the message partial.

**Test plan:**
1. Post a message.
2. Check that the store has the message.
3. Check that the response holds the partial.

### Task 17 — Add the per-user SSE stream

**Goal:** Push replies to the browser over one stream.

**Requirements:**
1. Add `GET /stream` for the logged-in user.
2. Send events from the user's channel.
3. Close the stream when the request disconnects.

**Acceptance criteria:**
- The stream sends events for the user.
- The stream stops on disconnect.

**Test plan:**
1. Open the stream.
2. Push a test event.
3. Check that the browser receives the event.

### Task 18 — Add out-of-band swap fragments

**Goal:** Update the open chat or a badge from one stream.

**Requirements:**
1. Add a fragment that appends a reply to an open conversation.
2. Add a fragment that raises the unread count on a background conversation.
3. Mark each fragment with `hx-swap-oob`.

**Acceptance criteria:**
- An open conversation shows the new reply.
- A background conversation shows a higher unread count.

**Test plan:**
1. Open conversation one.
2. Push a reply for conversation two.
3. Check that the badge for conversation two goes up.

### Task 19 — Connect the web route to the core

**Goal:** Generate the web reply with the core.

**Requirements:**
1. Call `handle_inbound` from the message route as a background task.
2. Push the reply to the user's channel.

**Acceptance criteria:**
- The web path calls the core.
- The reply reaches the browser over the stream.

**Test plan:**
1. Post a web message.
2. Check that the core runs.
3. Check that the reply arrives over the stream.

---

## Phase 5 — Streaming provider

### Task 20 — Add the provider seam

**Goal:** Call many model hosts through one interface.

**Requirements:**
1. Add LiteLLM to the dependencies.
2. Add a thin `Provider` seam in `chat.py`.
3. Route calls through LiteLLM by default.

**Acceptance criteria:**
- The seam sends a chat request through LiteLLM.
- The seam returns the reply text.

**Test plan:**
1. Call the seam against a local Ollama model.
2. Check that it returns text.

### Task 21 — Add the model_configs table

**Goal:** Store the model choice as a referenced row.

**Requirements:**
1. Write a migration that creates `model_configs` with `dialect`, `host`, `endpoint`,
   `model_id`, `params`, and `credential_ref`.
2. Replace the `model` string on `conversations` with `model_config_id`.

**Acceptance criteria:**
- The `model_configs` table exists.
- A conversation references a model config by id.

**Test plan:**
1. Insert a model config.
2. Link a conversation to the config.
3. Read the config through the conversation.

### Task 22 — Read secrets by reference

**Goal:** Keep keys out of the database rows.

**Requirements:**
1. Add a secret store that maps a `credential_ref` to a key.
2. Read the key from the store at call time.
3. Never store an inline key in a row.

**Acceptance criteria:**
- The provider reads the key by reference.
- No row holds a plain key.

**Test plan:**
1. Set a secret for a reference.
2. Call the provider.
3. Check that the call uses the stored key.

### Task 23 — Stream the provider output

**Goal:** Send model chunks to the browser as they arrive.

**Requirements:**
1. Turn on streaming in the provider seam.
2. Yield chunks as a uniform iterator.
3. Push each chunk to the user's SSE stream.

**Acceptance criteria:**
- The provider yields chunks.
- The browser shows the reply as it streams.

**Test plan:**
1. Send a web message.
2. Watch the stream.
3. Check that the reply arrives in parts.

### Task 24 — Add the native Anthropic path

**Goal:** Use the Anthropic SDK when prompt caching helps.

**Requirements:**
1. Add a native Anthropic path in the seam.
2. Turn on prompt caching for the system prompt.
3. Select the path by the model config.

**Acceptance criteria:**
- A Claude config uses the native path.
- The system prompt uses caching.

**Test plan:**
1. Call the seam with a Claude config.
2. Check that the native path runs.

---

## Phase 6 — Graph, persona, and presence

### Task 25 — Add the graph wrapper

**Goal:** Read and write quads through one module.

**Requirements:**
1. Add pyoxigraph to the dependencies.
2. Add `graph.py` with functions to assert and query quads.
3. Back the store with a file on disk.

**Acceptance criteria:**
- The module asserts a quad.
- The module queries the quad back with SPARQL.

**Test plan:**
1. Assert a test quad.
2. Query the quad.
3. Check that the result matches.

### Task 26 — Define the vocabulary

**Goal:** Fix the classes, predicates, and provenance graphs.

**Requirements:**
1. List the Schema.org classes and predicates to use.
2. Add the local `fr:` predicates: `fr:enjoys`, `fr:practices`, `fr:learning`.
3. Name the provenance graphs: `real`, `world`, `synthetic`, and `inferred`.

**Acceptance criteria:**
- The vocabulary lives in one place.
- The graph module rejects an unknown predicate.

**Test plan:**
1. Assert a quad with a known predicate.
2. Assert a quad with an unknown predicate.
3. Check that the second assert fails.

### Task 27 — Seed the persona into the graph

**Goal:** Turn persona config into quads when an agent is created.

**Requirements:**
1. Write persona facts as quads in the `real` graph on agent create.
2. Create topic nodes for interests.
3. Link the agent to each interest with a trait predicate.

**Acceptance criteria:**
- A new agent has self facts in the graph.
- Each interest has a topic node and a trait edge.

**Test plan:**
1. Create a test agent.
2. Query the agent's facts.
3. Check the interest edges.

### Task 28 — Add structured persona fields

**Goal:** Replace the free prose prompt with fields.

**Requirements:**
1. Add `location`, `timezone`, `interests`, `age`, and `native_language` to `agents`.
2. Render a trusted template in `persona.py` from the fields.
3. Pass the user text as a user message, not into the template.

**Acceptance criteria:**
- The persona prompt comes from fields.
- The user text never enters the system prompt.

**Test plan:**
1. Build a persona prompt from a test agent.
2. Check that the prompt holds the fields.
3. Check that the user text stays separate.

### Task 29 — Read facts into the prompt

**Goal:** Give the reply recent and relevant memory.

**Requirements:**
1. Read the last N messages by time for the short-term window.
2. Read recent facts from the graph by time.
3. Read relevant facts from the graph by the current topics.

**Acceptance criteria:**
- The prompt holds recent messages.
- The prompt holds relevant facts.

**Test plan:**
1. Seed messages and facts.
2. Build the prompt.
3. Check that both parts appear.

### Task 30 — Add the extraction pass

**Goal:** Turn messages into facts in the background.

**Requirements:**
1. Add a background task that extracts entities and events from messages.
2. Resolve each entity against existing IRIs before you assert it.
3. Assert new facts into the `real` graph with the source message id.

**Acceptance criteria:**
- The task asserts facts from a message.
- The task reuses an existing IRI for a known entity.

**Test plan:**
1. Send a message with a clear fact.
2. Run the extraction.
3. Check that the graph holds the fact once.

### Task 31 — Add the presence module

**Goal:** Compute the persona state from local time.

**Requirements:**
1. Add `presence.py`.
2. Read the local time with `zoneinfo` and the agent timezone.
3. Map the time to `asleep`, `school`, `free`, or `busy` by an age schedule.

**Acceptance criteria:**
- The module returns a state for a time.
- The state follows the age schedule.

**Test plan:**
1. Call the module at 02:00 local for a child.
2. Check that the state is `asleep`.
3. Call at 16:00 and check for `free`.

### Task 32 — Add temporal context to the prompt

**Goal:** Tell the persona the real local date and time.

**Requirements:**
1. Add the local date, the weekday, and the season to the prompt.

**Acceptance criteria:**
- The prompt holds the local date and weekday.

**Test plan:**
1. Build a prompt for a test agent.
2. Check that the date and weekday appear.

### Task 33 — Defer replies outside waking hours

**Goal:** Hold a reply until the persona is free.

**Requirements:**
1. Check the presence state before you send a reply.
2. Queue the reply when the state is `asleep` or `school`.
3. Send the queued reply in the next free window over the SSE stream.

**Acceptance criteria:**
- A reply waits while the persona sleeps.
- The reply sends in the next free window.

**Test plan:**
1. Send a message at a sleep time.
2. Check that no reply sends yet.
3. Move to a free time and check that the reply sends.

### Task 34 — Show the presence indicator

**Goal:** Show the persona state in the web UI.

**Requirements:**
1. Show the state and the local time in the chat header.
2. Show the state in the conversation list.
3. Update the indicator with an out-of-band fragment.

**Acceptance criteria:**
- The header shows the state and the local time.
- The indicator updates over the stream.

**Test plan:**
1. Open the chat for a sleeping persona.
2. Check that the header shows `Sleeping`.
3. Move to a free time and check that the header updates.

---

## Phase 7 — Grounded personhood and outreach

### Task 35 — Add the weather provider

**Goal:** Fetch weather for the persona location.

**Requirements:**
1. Add `signals.py`.
2. Add a weather provider that reads Open-Meteo from the lat/long.
3. Return a structured signal with topic, place, and time.

**Acceptance criteria:**
- The provider returns a weather signal.
- The signal holds a place and a time.

**Test plan:**
1. Call the provider for a test location.
2. Check the signal fields.

### Task 36 — Add the calendar provider

**Goal:** Fetch seasonal and holiday signals.

**Requirements:**
1. Add a calendar provider in `signals.py`.
2. Return holiday and season signals for the date.

**Acceptance criteria:**
- The provider returns a calendar signal for a holiday.

**Test plan:**
1. Call the provider on a known holiday.
2. Check that the signal marks the holiday.

### Task 37 — Store signals in the world graph

**Goal:** Keep real-world facts in the graph.

**Requirements:**
1. Assert each signal into the `world` graph.
2. Cache the signals for each region.

**Acceptance criteria:**
- The `world` graph holds the signals.
- Two agents in one region share one fetch.

**Test plan:**
1. Fetch signals for two agents in one region.
2. Check that the provider runs once.

### Task 38 — Add the grounding step

**Goal:** Keep only signals that fit the persona.

**Requirements:**
1. Match each signal to an interest edge, the home location, or a known topic.
2. Drop a signal that matches nothing.

**Acceptance criteria:**
- A matched signal stays.
- An unmatched signal drops.

**Test plan:**
1. Give an agent one interest.
2. Pass a matching signal and a non-matching signal.
3. Check that only the match stays.

### Task 39 — Add the synthesis step

**Goal:** Make a first-person event from a grounded signal.

**Requirements:**
1. Ask the model for an event that fits the persona and the past events.
2. Check the event against the graph for a conflict.
3. Assert the event into the `synthetic` graph with a link to the world node.

**Acceptance criteria:**
- The synthesis asserts a synthetic event.
- The event links to its world signal.

**Test plan:**
1. Ground a test signal.
2. Run the synthesis.
3. Check the synthetic event and its link.

### Task 40 — Add the contact step

**Goal:** Start a message from a synthetic event.

**Requirements:**
1. Build an opening message from the synthetic event.
2. Send the message through the active medium.
3. Reuse the conversation-starter path.

**Acceptance criteria:**
- The contact step sends an opening message.
- The message talks about the event as the persona's own life.

**Test plan:**
1. Create a synthetic event.
2. Run the contact step.
3. Check that the message sends.

### Task 41 — Gate outreach by presence

**Goal:** Send outreach only in waking hours.

**Requirements:**
1. Check the presence state before outreach.
2. Send only in a `free` window.

**Acceptance criteria:**
- Outreach sends in a free window.
- Outreach does not send at a sleep time.

**Test plan:**
1. Run outreach at a sleep time and check for no send.
2. Run at a free time and check for a send.

---

## Phase 8 — Eval and safety

### Task 42 — Build the eval harness

**Goal:** Run fixed tests against a model config.

**Requirements:**
1. Add the folder `evals/`.
2. Load test fixtures.
3. Run a config and record a score.

**Acceptance criteria:**
- The harness runs a config.
- The harness prints a score.

**Test plan:**
1. Run the harness on one config.
2. Check that it prints a score.

### Task 43 — Add the identity eval

**Goal:** Check that the persona keeps its facts.

**Requirements:**
1. Add fixtures that ask for persona facts.
2. Score the reply against the known facts.

**Acceptance criteria:**
- The eval passes for a correct persona.
- The eval fails for a wrong fact.

**Test plan:**
1. Run the identity eval.
2. Check the pass and the fail cases.

### Task 44 — Add the CEFR eval

**Goal:** Check that the reply matches the level.

**Requirements:**
1. Add fixtures for each level from A1 to C2.
2. Score the reply for level fit.

**Acceptance criteria:**
- The eval scores each level.

**Test plan:**
1. Run the CEFR eval.
2. Check the scores.

### Task 45 — Add the memory-recall eval

**Goal:** Check that the persona recalls stored facts.

**Requirements:**
1. Store a fact in an early turn.
2. Ask for the fact in a later turn.
3. Score the recall and check for no mis-attribution.

**Acceptance criteria:**
- The eval passes when the persona recalls the fact.
- The eval fails when the persona treats a synthetic fact as the user's.

**Test plan:**
1. Run the memory eval.
2. Check the recall score.

### Task 46 — Add moderation in the core

**Goal:** Check inbound and outbound text for safety.

**Requirements:**
1. Check the inbound text before you assert it or call the model.
2. Check the outbound reply before you send it.
3. Keep the general policy permissive.

**Acceptance criteria:**
- The core blocks unsafe inbound text.
- The core blocks unsafe outbound text.

**Test plan:**
1. Send safe text and check that it passes.
2. Send unsafe text and check that it blocks.

### Task 47 — Add the minor-safety block

**Goal:** Block sexual content that involves a child persona.

**Requirements:**
1. Route the minor-safety check to a specialized provider.
2. Block the content, write an audit log, and flag the account.
3. Never let the permissive policy apply here.

**Acceptance criteria:**
- The check blocks the content.
- The system writes an audit log and flags the account.

**Test plan:**
1. Send a blocked test case.
2. Check the block, the log, and the flag.

### Task 48 — Add the age gate

**Goal:** Keep the product adults-only at launch.

**Requirements:**
1. Add a self-attested 18-plus check at signup.
2. Stop signup when the user is under 18.

**Acceptance criteria:**
- A user over 18 completes signup.
- A user under 18 cannot sign up.

**Test plan:**
1. Sign up as over 18 and check for success.
2. Sign up as under 18 and check for the stop.

### Task 49 — Check the Mailgun signature

**Goal:** Reject a forged webhook.

**Requirements:**
1. Read the Mailgun signature from the webhook.
2. Check the signature before you process the message.
3. Reject a bad signature with a 401 status.

**Acceptance criteria:**
- A valid signature passes.
- A bad signature returns 401.

**Test plan:**
1. Post a valid webhook and check for success.
2. Post a forged webhook and check for 401.

### Task 50 — Fix the sender match

**Goal:** Match the sender to the user by an exact check.

**Requirements:**
1. Replace the substring check with an exact match.
2. Reject a sender that does not match the user email.

**Acceptance criteria:**
- An exact sender passes.
- A near-match sender fails.

**Test plan:**
1. Send from the exact email and check for success.
2. Send from a near-match email and check for the reject.

### Task 51 — Add rate limiting

**Goal:** Limit requests for each account.

**Requirements:**
1. Add an in-process rate limit for each account.
2. Reject a request over the limit.

**Acceptance criteria:**
- A request under the limit passes.
- A request over the limit returns an error.

**Test plan:**
1. Send requests under the limit and check for success.
2. Cross the limit and check for the error.

---

## Notes

- Tasks 1 to 4 ship a safe refactor with no behavior change.
- Tasks 5 to 19 ship a multi-tenant web product with real chat.
- Tasks 20 to 24 add streaming and many model hosts.
- Tasks 25 to 34 add the graph, the persona, and presence.
- Tasks 35 to 41 add grounded outreach, the headline feature.
- Tasks 42 to 51 add eval and safety.
- The safety block (Task 47) and the age gate (Task 48) must ship before launch, not
  after Phase 8.
