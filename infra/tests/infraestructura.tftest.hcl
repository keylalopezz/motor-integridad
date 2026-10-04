# Pruebas de la infraestructura con proveedores simulados (no crean recursos reales).
mock_provider "mongodbatlas" {}
mock_provider "upstash" {}
mock_provider "astra" {}
mock_provider "supabase" {}

variables {
  atlas_org_id         = "org-prueba"
  mongo_password       = "clave-de-prueba"
  supabase_org_id      = "org-prueba"
  supabase_db_password = "clave-de-prueba"
}

run "mongodb_usa_capa_gratuita_m0" {
  command = plan
  assert {
    condition     = mongodbatlas_cluster.principal.provider_instance_size_name == "M0" && mongodbatlas_cluster.principal.provider_name == "TENANT"
    error_message = "El clúster de MongoDB debe ser M0 (gratuito)."
  }
}

run "usuario_mongo_con_permiso_minimo" {
  command = plan
  assert {
    condition     = one(mongodbatlas_database_user.app.roles).role_name == "readWrite"
    error_message = "El usuario de la app solo debe tener readWrite."
  }
}

run "acceso_desde_streamlit_cloud" {
  command = plan
  assert {
    condition     = mongodbatlas_project_ip_access_list.streamlit.cidr_block == "0.0.0.0/0"
    error_message = "Streamlit Cloud no tiene IP fija: se requiere 0.0.0.0/0."
  }
}

run "redis_con_tls" {
  command = plan
  assert {
    condition     = upstash_redis_database.cache.tls == true
    error_message = "Upstash Redis debe usar TLS."
  }
}

run "cassandra_con_keyspace_del_caso" {
  command = plan
  assert {
    condition     = astra_database.cassandra.keyspace == "tienda"
    error_message = "El keyspace de Astra debe ser 'tienda'."
  }
}

run "nombres_con_prefijo_del_proyecto" {
  command = plan
  assert {
    condition = alltrue([
      startswith(supabase_project.control.name, "motor-integridad"),
      startswith(mongodbatlas_cluster.principal.name, "motor-integridad"),
      startswith(upstash_redis_database.cache.database_name, "motor-integridad"),
      startswith(astra_database.cassandra.name, "motor-integridad"),
    ])
    error_message = "Todos los recursos deben usar el prefijo del proyecto."
  }
}

run "aprovisionamiento_completo" {
  command = apply
  assert {
    condition     = output.recursos.mongodb_plan == "M0" && output.recursos.keyspace == "tienda"
    error_message = "El resumen de recursos no coincide con la configuración."
  }
}
