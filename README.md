# Trust 4P — API de negocio

Servicio de negocio del sistema Trust 4P: autenticación y sesiones, empresas y usuarios, modelo de madurez, diagnósticos, motor de cálculo del índice, consultoría, indicadores, informes y auditoría. Delega la generación de recomendaciones al servicio de evaluación asistida (`trust4p-servicio-agente`). Python 3.13, FastAPI, MongoDB (Motor).

## Arquitectura

Diseño hexagonal (puertos y adaptadores). Las dependencias apuntan siempre hacia el dominio: `api` → `aplicacion` → `dominio` ← `infraestructura`.

| Carpeta | Responsabilidad | Componentes del documento de arquitectura |
|---|---|---|
| `src/dominio/entidades` | Entidades y reglas de integridad (diagnóstico, empresa, usuario, modelo de madurez, rol, permiso, solicitud, token, auditoría, notificación) | Núcleo de dominio |
| `src/dominio/servicios` | Lógica pura sin entradas ni salidas: `motor_calculo` (índice determinístico, ADR-005), `logica_adaptativa`, `simulacion_pesos`, `indicadores_agregados`, `diagnostico_demo` | Motor de cálculo |
| `src/dominio/puertos` | Interfaces que el dominio necesita: repositorios, `servicio_correo`, `cliente_servicio_agente` (ADR-011) | Puertos |
| `src/aplicacion/casos_uso` | Un módulo por capacidad: `iniciar_sesion`, `radicar_solicitud`, `gestionar_diagnostico`, `evaluar_diagnostico`, `gestionar_consultoria`, `gestionar_modelo_madurez`, `generar_informe`, etc. | Casos de uso |
| `src/aplicacion/servicios` | Enlaces y notificaciones compartidos por los casos de uso | Servicios de aplicación |
| `src/api/routers` | Endpoints HTTP bajo el prefijo `/v1` (ADR-015); validación de entrada con Pydantic (ADR-013) | Adaptador de entrada |
| `src/api/middleware` | Sesión y autorización por permiso (ADR-010), registro de auditoría, límite de peticiones por IP, cabeceras de seguridad | Seguridad transversal |
| `src/infraestructura/persistencia` | Repositorios MongoDB, conexión, inicialización idempotente de permisos y roles, sembrado del modelo 4P | Adaptador de salida: persistencia |
| `src/infraestructura/clientes` | Cliente HTTP del servicio de evaluación (clave de servicio, tiempo máximo configurable) y cliente SMTP | Adaptadores de salida: integraciones |
| `src/infraestructura/informes` | Generación del informe en PDF | Adaptador de salida: informes |

El punto de entrada es `src/api/main.py`; el ciclo de vida del proceso asegura el catálogo de permisos y los roles de sistema al arrancar.

## Contrato de la API

El contrato OpenAPI vigente está en [`docs/api/openapi.json`](docs/api/openapi.json) (73 rutas, 85 operaciones, incluida `/salud`). La documentación interactiva se sirve en `/docs` cuando el servicio corre. Para regenerarlo:

```bash
PYTHONPATH=. MONGO_URI=mongodb://localhost:1 python -c "import json; from src.api.main import app; json.dump(app.openapi(), open('docs/api/openapi.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2, sort_keys=True)"
```

## Decisiones de arquitectura

Ver [`docs/adr`](docs/adr/README.md). La numeración es la del catálogo unificado del documento de arquitectura.

## Ejecución local

```bash
python -m venv venv
venv\Scripts\activate          # en Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # o cree .env con las variables de la tabla siguiente
uvicorn src.api.main:app --reload
```

### Variables de entorno

| Variable | Uso | Por defecto |
|---|---|---|
| `MONGO_URI` | Cadena de conexión a MongoDB (base `trust4p`) | — (obligatoria) |
| `CORS_ORIGENES` | Orígenes permitidos, separados por coma | `http://localhost:5173,http://localhost:3000` |
| `URL_FRONTEND` | Base de los enlaces de los correos | `http://localhost:5173` |
| `SERVICIO_AGENTE_URL`, `API_KEY_SERVICIOS` | Dirección y clave del servicio de evaluación asistida | — |
| `AGENTE_TIEMPO_ESPERA_SEGUNDOS` | Tiempo máximo de la llamada al servicio de evaluación | `300` |
| `SMTP_HOST`, `SMTP_PUERTO`, `SMTP_USUARIO`, `SMTP_CLAVE`, `SMTP_REMITENTE` | Envío de correo | `smtp.gmail.com`, `587` |
| `SALTOS_PROXY` | Cantidad de proxies de confianza delante del servicio | `0` |
| `LIMITE_LOGIN_*`, `LIMITE_CORREO_*`, `LIMITE_TOKEN_*`, `LIMITE_SOLICITUDES_*`, `LIMITE_MODELO_PUBLICO_*`, `DEMO_*` | Topes de peticiones por IP (`*_MAX`) y su ventana en segundos (`*_VENTANA`) | ver `src/api/middleware/limites.py` |

## Pruebas

```bash
pytest tests/unitarias        # sin base de datos
pytest tests/integracion      # requiere MongoDB accesible
```

## Despliegue

El `Dockerfile` construye la imagen que se ejecuta en Cloud Run (usa la variable `PORT`). La infraestructura y el despliegue continuo se declaran en el repositorio `trust4p-infraestructura` (ADR-016 y ADR-017).
