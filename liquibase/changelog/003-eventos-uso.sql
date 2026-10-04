--liquibase formatted sql

--changeset datastack:003-eventos-uso
--comment: Eventos de utilización del producto para el dashboard de uso
create table if not exists eventos_uso (
  id bigint generated always as identity primary key,
  usuario text references usuarios_sistema(usuario) on delete cascade,
  accion text not null,
  detalle jsonb default '{}'::jsonb,
  creado_en timestamptz default now()
);
alter table eventos_uso enable row level security;
create index if not exists idx_eventos_uso_fecha on eventos_uso (creado_en);
--rollback drop table if exists eventos_uso cascade;
