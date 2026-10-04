# Infraestructura del Motor de Integridad Multibase NoSQL (capas gratuitas).
#   - Supabase (PostgreSQL): base de control (usuarios, reglas, auditoría, conexiones).
#   - MongoDB Atlas M0, Upstash Redis y DataStax Astra (Cassandra): motores a validar.
# La aplicación Streamlit se publica en Streamlit Community Cloud (sin proveedor Terraform).

terraform {
  required_version = ">= 1.7"
  required_providers {
    mongodbatlas = {
      source  = "mongodb/mongodbatlas"
      version = "~> 1.26"
    }
    upstash = {
      source  = "upstash/upstash"
      version = "~> 1.5"
    }
    astra = {
      source  = "datastax/astra"
      version = "~> 2.3"
    }
    supabase = {
      source  = "supabase/supabase"
      version = "~> 1.5"
    }
  }
}

provider "mongodbatlas" {
  public_key  = var.atlas_public_key
  private_key = var.atlas_private_key
}

provider "upstash" {
  email   = var.upstash_email
  api_key = var.upstash_api_key
}

provider "astra" {
  token = var.astra_token
}

provider "supabase" {
  access_token = var.supabase_access_token
}

# --- Base de control: Supabase ---
resource "supabase_project" "control" {
  organization_id   = var.supabase_org_id
  name              = "${var.proyecto}-control"
  database_password = var.supabase_db_password
  region            = var.supabase_region

  lifecycle {
    ignore_changes = [database_password]
  }
}

# --- MongoDB Atlas (M0 gratuito) ---
resource "mongodbatlas_project" "motor" {
  name   = var.proyecto
  org_id = var.atlas_org_id
}

resource "mongodbatlas_cluster" "principal" {
  project_id                  = mongodbatlas_project.motor.id
  name                        = "${var.proyecto}-mongo"
  provider_name               = "TENANT"
  backing_provider_name       = "AWS"
  provider_region_name        = var.atlas_region
  provider_instance_size_name = "M0"
}

resource "mongodbatlas_database_user" "app" {
  project_id         = mongodbatlas_project.motor.id
  username           = var.mongo_usuario
  password           = var.mongo_password
  auth_database_name = "admin"

  roles {
    role_name     = "readWrite"
    database_name = var.base_datos
  }
}

# Streamlit Community Cloud no tiene IP fija: se permite el acceso desde cualquier origen.
resource "mongodbatlas_project_ip_access_list" "streamlit" {
  project_id = mongodbatlas_project.motor.id
  cidr_block = "0.0.0.0/0"
  comment    = "Streamlit Community Cloud y GitHub Actions"
}

# --- Upstash Redis (plan gratuito) ---
resource "upstash_redis_database" "cache" {
  database_name  = "${var.proyecto}-redis"
  region         = "global"
  primary_region = var.upstash_region
  tls            = true
}

# --- DataStax Astra DB (Cassandra serverless gratuito) ---
resource "astra_database" "cassandra" {
  name           = "${var.proyecto}-cassandra"
  keyspace       = var.base_datos
  cloud_provider = "gcp"
  regions        = [var.astra_region]
}
