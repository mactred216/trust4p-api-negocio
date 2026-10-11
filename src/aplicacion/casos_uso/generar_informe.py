from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, DiagnosticoNoEncontrado)
from src.dominio.entidades.diagnostico import Diagnostico
from src.dominio.puertos.repositorio_diagnostico import RepositorioDiagnostico
from src.dominio.puertos.repositorio_modelo_madurez import \
    RepositorioModeloMadurez
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario


class DiagnosticoSinResultado(Exception):
    """RF-17: no hay un resultado evaluado sobre el cual generar el informe."""


class GenerarInformeDiagnostico:
    """RF-17 (HU-018): valida que el diagnóstico pertenezca a la empresa del
    usuario y que ya tenga un resultado evaluado completo. La generación del
    archivo PDF en sí vive en infraestructura/informes — este caso de uso
    solo decide si procede."""

    def __init__(
        self, repo_diagnostico: RepositorioDiagnostico, repo_usuario: RepositorioUsuario
    ):
        self._diagnosticos = repo_diagnostico
        self._usuarios = repo_usuario

    async def ejecutar(self, usuario_id: str, diagnostico_id: str) -> Diagnostico:
        diagnostico = await self._diagnosticos.obtener_por_id(diagnostico_id)
        if diagnostico is None:
            raise DiagnosticoNoEncontrado()

        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None or usuario.empresa_id != diagnostico.empresa_id:
            raise AccesoNoAutorizado()

        # Cerrado = el consultor concluyó el acompañamiento; el resultado sigue
        # siendo suyo y debe poder descargarlo.
        if (
            diagnostico.estado not in ("evaluado", "cerrado")
            or diagnostico.resultado is None
        ):
            raise DiagnosticoSinResultado()

        return diagnostico


async def nombres_de_dimensiones(
    repo_modelo: RepositorioModeloMadurez, diagnostico: Diagnostico
) -> dict[str, str]:
    """Nombre de cada dimensión según la versión del modelo con que se evaluó el
    diagnóstico, para que el informe no muestre códigos internos. Si esa versión
    ya no existe, el informe usa el código."""
    modelo = await repo_modelo.obtener_por_version(diagnostico.modelo_version)
    if modelo is None:
        return {}
    return {d.codigo: d.nombre for d in modelo.dimensiones}
