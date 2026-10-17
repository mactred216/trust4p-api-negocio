# 0020. Desarrollo iterativo con tablero Kanban, sin Scrum

**Estado:** Aceptado

## Contexto

El proyecto lo desarrolla un equipo muy reducido con un plazo corto para el prototipo funcional. Los eventos y roles de Scrum (planeación, revisión, retrospectiva, dueño de producto) tienen un costo fijo que no se justifica con ese tamaño.

## Decisión

Se trabaja en iteraciones cortas con un tablero Kanban: una historia de usuario por rama y por solicitud de integración, y verificación (pruebas automáticas y prueba en vivo) antes de integrar.

## Consecuencias

- **Positivas:** poco costo de gestión; el progreso es visible por historia y el historial de integraciones queda trazado.
- **Negativas:** no hay estimación formal ni velocidad medida; la priorización depende de la disciplina de quien gestiona el tablero.
