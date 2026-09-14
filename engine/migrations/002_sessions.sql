alter table requests add column session_id text;
alter table requests add column seed integer;
create index if not exists requests_session_idx on requests (session_id, created_at);
update requests set session_id = id where session_id is null;
