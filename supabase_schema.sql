-- Eliminar tablas antiguas (IMPORTANTE: Esto borrará los datos existentes para aplicar el nuevo esquema SaaS)
drop table if exists auditoria_violaciones cascade;
drop table if exists reglas cascade;
drop table if exists conexiones_motores cascade;
drop table if exists usuarios_sistema cascade;

-- Tabla de usuarios del sistema
create table if not exists usuarios_sistema (
  id uuid primary key default gen_random_uuid(),
  usuario text unique not null,
  password_hash text not null,
  creado_en timestamptz default now(),
  ultimo_acceso timestamptz default now()
);

-- Tabla de reglas (Multi-Tenant)
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

-- Tabla de auditoria (Multi-Tenant)
create table if not exists auditoria_violaciones (
  id uuid primary key default gen_random_uuid(),
  usuario text references usuarios_sistema(usuario) on delete cascade,
  regla_id uuid references reglas(id) on delete cascade,
  tipo text not null,
  motores_involucrados text not null,
  dato_afectado jsonb,
  detectado_en timestamptz default now()
);

-- Tabla de conexiones (Multi-Tenant)
create table if not exists conexiones_motores (
  usuario text references usuarios_sistema(usuario) on delete cascade,
  motor text not null,
  config jsonb not null,
  actualizado_en timestamptz default now(),
  primary key (usuario, motor)
);

-- Seguridad: activar Row Level Security sin politicas publicas.
-- Asi la anon key (expuesta en clientes) no puede leer hashes de contrasenas ni credenciales.
-- La app se conecta desde el servidor con la service_role key, que ignora RLS.
alter table usuarios_sistema enable row level security;
alter table reglas enable row level security;
alter table auditoria_violaciones enable row level security;
alter table conexiones_motores enable row level security;

create index if not exists idx_auditoria_usuario_regla on auditoria_violaciones (usuario, regla_id);
create index if not exists idx_reglas_usuario on reglas (usuario);
