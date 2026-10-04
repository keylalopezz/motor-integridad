variable "proyecto" {
  description = "Prefijo de los recursos"
  type        = string
  default     = "motor-integridad"
}

variable "base_datos" {
  description = "Base de datos / keyspace del caso de estudio"
  type        = string
  default     = "tienda"
}

# --- Supabase ---
variable "supabase_access_token" {
  type      = string
  sensitive = true
  default   = ""
}

variable "supabase_org_id" {
  type    = string
  default = ""
}

variable "supabase_db_password" {
  type      = string
  sensitive = true
  default   = ""
}

variable "supabase_region" {
  type    = string
  default = "us-east-1"
}

# --- MongoDB Atlas ---
variable "atlas_public_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "atlas_private_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "atlas_org_id" {
  type    = string
  default = ""
}

variable "atlas_region" {
  type    = string
  default = "US_EAST_1"
}

variable "mongo_usuario" {
  type    = string
  default = "motor_app"
}

variable "mongo_password" {
  type      = string
  sensitive = true
  default   = ""
}

# --- Upstash ---
variable "upstash_email" {
  type    = string
  default = ""
}

variable "upstash_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "upstash_region" {
  type    = string
  default = "us-east-1"
}

# --- DataStax Astra ---
variable "astra_token" {
  type      = string
  sensitive = true
  default   = ""
}

variable "astra_region" {
  type    = string
  default = "us-east1"
}
