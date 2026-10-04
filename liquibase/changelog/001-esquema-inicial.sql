--liquibase formatted sql

--changeset datastack:001-usuarios-sistema
--comment: Usuarios de la plataforma (multi-tenant)
create table if not exists usuarios_sistema (
  id uuid primary key default gen_random_uuid(),
  usuario text unique not null,
  password_hash text not null,
  creado_en timestamptz default now(),
  ultimo_acceso timestamptz default now()
);
--rollback drop table if exists usuarios_sistema cascade;

--changeset datastack:001-reglas
--comment: Reglas de integridad definidas por cada usuario
create table if not exists reglas (
  id uuid primary key default gen_random_uuid(),
  usuario text references usuarios_sistema(usuario) on delete cascade,
  tipo text not null check (tipo in ('esquema','unicidad','referencial','consistencia')),
  motor_origen text not null,
  coleccion_origen text not null,
  campo text not null,
  motor_destino text,
  coleccion_destino text,
  campo_destino text,
  schema jsonb,
  creado_en timestamptz default now()
);
--rollback drop table if exists reglas cascade;

--changeset datastack:001-auditoria-violaciones
--comment: Anomalías detectadas por el escaneo batch
create table if not exists auditoria_violaciones (
  id uuid primary key default gen_random_uuid(),
  usuario text references usuarios_sistema(usuario) on delete cascade,
  regla_id uuid references reglas(id) on delete cascade,
  tipo text not null,
  motores_involucrados text not null,
  dato_afectado jsonb,
  detectado_en timestamptz default now()
);
--rollback drop table if exists auditoria_violaciones cascade;

--changeset datastack:001-conexiones-motores
--comment: Credenciales cifradas (Fernet) de MongoDB, Redis y Cassandra por usuario
create table if not exists conexiones_motores (
  usuario text references usuarios_sistema(usuario) on delete cascade,
  motor text not null,
  config jsonb not null,
  actualizado_en timestamptz default now(),
  primary key (usuario, motor)
);
--rollback drop table if exists conexiones_motores cascade;
