output "recursos" {
  description = "Resumen de la infraestructura aprovisionada"
  value       = {
    supabase_proyecto = supabase_project.control.name
    mongodb_cluster   = mongodbatlas_cluster.principal.name
    mongodb_plan      = mongodbatlas_cluster.principal.provider_instance_size_name
    redis_base        = upstash_redis_database.cache.database_name
    cassandra_base    = astra_database.cassandra.name
    keyspace          = astra_database.cassandra.keyspace
  }
}

output "mongodb_uri" {
  description = "Cadena de conexión SRV de MongoDB Atlas"
  value       = mongodbatlas_cluster.principal.connection_strings
  sensitive   = true
}

output "redis_endpoint" {
  description = "Host de Upstash Redis"
  value       = upstash_redis_database.cache.endpoint
}
