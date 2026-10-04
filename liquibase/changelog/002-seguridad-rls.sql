--liquibase formatted sql

--changeset datastack:002-rls
--comment: Row Level Security sin políticas públicas; la app usa la service_role key
alter table usuarios_sistema enable row level security;
alter table reglas enable row level security;
alter table auditoria_violaciones enable row level security;
alter table conexiones_motores enable row level security;
--rollback alter table usuarios_sistema disable row level security; alter table reglas disable row level security; alter table auditoria_violaciones disable row level security; alter table conexiones_motores disable row level security;

--changeset datastack:002-indices
--comment: Índices para las consultas por usuario
create index if not exists idx_auditoria_usuario_regla on auditoria_violaciones (usuario, regla_id);
create index if not exists idx_reglas_usuario on reglas (usuario);
--rollback drop index if exists idx_auditoria_usuario_regla; drop index if exists idx_reglas_usuario;
