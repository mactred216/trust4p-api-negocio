# 0017. Infraestructura como código con Terraform y despliegue sin llaves mediante Workload Identity

**Estado:** Aceptado

## Contexto

La plataforma (servicios de Cloud Run, repositorio de imágenes, cuentas de servicio, secretos) debe poder reconstruirse y auditarse. Crear los recursos desde la consola no deja rastro revisable, y guardar la llave de una cuenta de servicio como secreto del CI introduce una credencial de larga duración que puede filtrarse.

## Decisión

Todos los recursos se declaran en Terraform (repositorio `trust4p-infraestructura`). El CI de cada repositorio se autentica en Google Cloud con Workload Identity Federation (`ci.tf`): GitHub Actions intercambia su identidad por credenciales de corta duración, restringidas a los repositorios autorizados. No existe ninguna llave de cuenta de servicio.

## Consecuencias

- **Positivas:** la infraestructura es reproducible y su cambio pasa por revisión; no hay credenciales de larga duración en el CI.
- **Negativas:** el primer `apply` y la configuración de variables en GitHub son pasos manuales que deben documentarse; el estado de Terraform debe custodiarse.
