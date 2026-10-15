-- Log of the hosted dashboard: chat questions with their answers, and page events.
-- "Who" is a random id per browser plus place, network and browser from Cloudflare. No names, no IP addresses.

CREATE TABLE chats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,                 -- UTC, ISO 8601
  visitor TEXT,                     -- random id kept in the browser
  session TEXT,                     -- random id per page load
  country TEXT, city TEXT, network TEXT, browser TEXT,
  turn INTEGER,                     -- the number of this question in its conversation
  question TEXT,
  answer TEXT,
  status INTEGER NOT NULL,          -- HTTP status the page received
  ms INTEGER,                       -- time to the end of the answer
  input_tokens INTEGER, cache_read INTEGER, cache_write INTEGER, output_tokens INTEGER,
  stop TEXT                         -- stop reason, or the error
);
CREATE INDEX chats_ts ON chats (ts);
CREATE INDEX chats_visitor ON chats (visitor);

CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  visitor TEXT, session TEXT,
  country TEXT, city TEXT, network TEXT, browser TEXT,
  name TEXT NOT NULL,               -- view, tab, details, chip, chat_open, click, print, leave
  target TEXT,                      -- what was clicked or opened
  value REAL                        -- a number for the event, such as seconds on the page
);
CREATE INDEX events_ts ON events (ts);
CREATE INDEX events_visitor ON events (visitor, name);
