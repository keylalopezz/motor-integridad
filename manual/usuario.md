# Manual de usuario

Ingresa a <https://motor-integridad.streamlit.app/>. Cada usuario tiene su propio espacio de trabajo: sus
conexiones, reglas y anomalías no son visibles para otros usuarios.

![Casos de uso](diagramas/srs_casos_uso.png)

## 1. Acceso

- **Crear Cuenta:** usuario de 3 a 30 caracteres (letras, números, guion o guion bajo) y contraseña de al menos
  6 caracteres. El usuario no distingue mayúsculas.
- **Iniciar Sesión:** ingresa usuario y contraseña y pulsa **Ingresar al panel**.
- **Cerrar Sesión:** botón en la barra lateral.

## 2. Bases de Datos (conexiones)

1. Elige el motor: MongoDB, Redis o Cassandra.
2. Ingresa las credenciales: URI de MongoDB Atlas, host/puerto/contraseña de Upstash, o el *Secure Connect
   Bundle* de DataStax Astra.
3. **Probar conexión** verifica sin guardar; **Probar y guardar** guarda la conexión cifrada.
4. **Eliminar conexión guardada** la borra.

## 3. Reglas

En **Crear Nueva Regla** elige el tipo:

| Tipo | Qué completar | Ejemplo |
|---|---|---|
| Esquema | Motor, colección y JSON Schema | `usuarios` debe tener `email` |
| Unicidad | Motor, colección y campo | `email` único en `usuarios` |
| Referencial | Origen y destino (motor, colección y campo de cruce) | `pagos.pedido_id` → `pedidos._id` |
| Consistencia | Origen y destino (motor, colección y campo de cruce) | `usuarios` de MongoDB = `usuarios` de Redis |

Las reglas se listan en **Reglas Activas**, donde también se eliminan.

## 4. Ejecución

- **Simulador pre-escritura:** elige motor y colección, pega el registro JSON y pulsa **Ejecutar Validación**.
  Comprueba las reglas de esquema y unicidad antes de escribir el dato.
- **Scan Batch:** **Iniciar Escaneo Profundo** evalúa todas las reglas sobre los datos existentes y registra
  las anomalías.

## 5. Monitor

Elige un motor y pulsa **Ejecutar Diagnóstico Completo** para ver estado, latencia, versión, recursos,
esquemas, una muestra de registros y estadísticas del servidor.

## 6. Dashboard y Reportes

- **Dashboard:** motores usados, cantidad de reglas y de anomalías, y resumen de auditorías.
- **Reportes:** cada anomalía con su explicación y una sugerencia de corrección; **Descargar Reporte PDF**.

## 7. Comunidad

Muestra los usuarios con actividad en los últimos cinco minutos.
