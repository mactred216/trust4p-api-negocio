from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_solicitud import RepositorioSolicitud


class SolicitudNoEncontrada(Exception):
    pass


class ResolverSolicitud:
    def __init__(
        self, repo_solicitud: RepositorioSolicitud, repo_empresa: RepositorioEmpresa
    ):
        self._solicitudes = repo_solicitud
        self._empresas = repo_empresa

    async def aprobar(self, solicitud_id: str, sector: Sector) -> Empresa:
        solicitud = await self._solicitudes.obtener_por_id(solicitud_id)
        if solicitud is None:
            raise SolicitudNoEncontrada()

        empresa = Empresa(
            id=None,
            nombre=solicitud.nombre_empresa,
            sector=sector,
        )
        empresa = await self._empresas.guardar(empresa)

        solicitud.aprobar(empresa_id=empresa.id)
        await self._solicitudes.actualizar(solicitud)

        return empresa

    async def rechazar(self, solicitud_id: str, motivo: str) -> None:
        solicitud = await self._solicitudes.obtener_por_id(solicitud_id)
        if solicitud is None:
            raise SolicitudNoEncontrada()

        solicitud.rechazar(motivo=motivo)
        await self._solicitudes.actualizar(solicitud)
