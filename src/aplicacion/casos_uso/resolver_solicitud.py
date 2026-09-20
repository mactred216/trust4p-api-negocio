from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_solicitud import RepositorioSolicitud
from src.dominio.puertos.repositorio_token import RepositorioToken


class SolicitudNoEncontrada(Exception):
    pass


class ResolverSolicitud:
    def __init__(
        self,
        repo_solicitud: RepositorioSolicitud,
        repo_empresa: RepositorioEmpresa,
        repo_token: RepositorioToken,
    ):
        self._solicitudes = repo_solicitud
        self._empresas = repo_empresa
        self._tokens = repo_token

    async def aprobar(self, solicitud_id: str, sector: Sector) -> tuple[Empresa, str]:
        solicitud = await self._solicitudes.obtener_por_id(solicitud_id)
        if solicitud is None:
            raise SolicitudNoEncontrada()

        empresa = Empresa(id=None, nombre=solicitud.nombre_empresa, sector=sector)
        empresa = await self._empresas.guardar(empresa)

        solicitud.aprobar(empresa_id=empresa.id)
        await self._solicitudes.actualizar(solicitud)

        codigo = TokenVerificacion.generar_codigo()
        token = TokenVerificacion(
            id=None,
            tipo=TipoToken.INVITACION,
            correo_destino=solicitud.correo_solicitante,
            solicitud_id=solicitud.id,
        )
        await self._tokens.guardar(token, codigo)

        return (
            empresa,
            codigo,
        )  # el código en claro se devuelve UNA SOLA VEZ, para el correo

    async def rechazar(self, solicitud_id: str, motivo: str) -> None:
        solicitud = await self._solicitudes.obtener_por_id(solicitud_id)
        if solicitud is None:
            raise SolicitudNoEncontrada()
        solicitud.rechazar(motivo=motivo)
        await self._solicitudes.actualizar(solicitud)
