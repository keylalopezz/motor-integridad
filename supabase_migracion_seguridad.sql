-- Migracion para proyectos existentes (NO borra datos). Ejecutar una vez en el SQL Editor de Supabase.

-- Seguridad: activar Row Level Security sin politicas publicas.
-- Asi la anon key (expuesta en clientes) no puede leer hashes de contrasenas ni credenciales.
-- La app se conecta desde el servidor con la service_role key, que ignora RLS.
alter table usuarios_sistema enable row level security;
alter table reglas enable row level security;
alter table auditoria_violaciones enable row level security;
alter table conexiones_motores enable row level security;

create index if not exists idx_auditoria_usuario_regla on auditoria_violaciones (usuario, regla_id);
create index if not exists idx_reglas_usuario on reglas (usuario);
