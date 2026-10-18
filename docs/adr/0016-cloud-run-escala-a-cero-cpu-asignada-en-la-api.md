# 0016. Cloud Run con escala a cero y CPU siempre asignada en la API de negocio

**Estado:** Aceptado

## Contexto

La API de negocio evalúa un diagnóstico en segundo plano: responde al cliente y sigue trabajando mientras espera al servicio de evaluación asistida (hasta 300 s). En Cloud Run, con la CPU asignada solo durante la petición, el proceso se congela al terminar la respuesta y la evaluación en segundo plano no avanza. Mantener instancias mínimas permanentes evita el problema, pero tiene un costo fijo alto para un sistema de uso intermitente.

## Decisión

Las tres piezas del sistema escalan a cero (`min_instance_count = 0`). Solo la API de negocio declara `cpu_idle = false` (CPU siempre asignada mientras la instancia existe); el servicio de evaluación y el frontend mantienen la CPU asignada solo durante la petición. La configuración vive en Terraform (repositorio `trust4p-infraestructura`, `cloud_run.tf`).

## Consecuencias

- **Positivas:** la evaluación en segundo plano termina aunque el cliente ya haya recibido la respuesta; sin costo fijo cuando no hay tráfico.
- **Negativas:** la primera petición tras un periodo inactivo paga el arranque en frío; la API cuesta más por segundo de instancia viva que si la CPU se asignara solo durante la petición.
