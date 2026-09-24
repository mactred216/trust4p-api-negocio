from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_solicitud import RepositorioSolicitud
from src.dominio.puertos.repositorio_token import RepositorioToken
from src.dominio.puertos.servicio_correo import ServicioCorreo


class SolicitudNoEncontrada(Exception):
    pass


class ResolverSolicitud:
    def __init__(
        self,
        repo_solicitud: RepositorioSolicitud,
        repo_empresa: RepositorioEmpresa,
        repo_token: RepositorioToken,
        servicio_correo: ServicioCorreo,
    ):
        self._solicitudes = repo_solicitud
        self._empresas = repo_empresa
        self._tokens = repo_token
        self._correo = servicio_correo

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

        await self._correo.enviar(
            destinatario=solicitud.correo_solicitante,
            asunto="Trust 4P - Invitación para completar tu registro",
            cuerpo=(
                f"Hola {solicitud.nombre_solicitante},\n\n"
                f"Tu solicitud de acceso para {empresa.nombre} fue aprobada. "
                f"Usa el siguiente código para completar tu registro: {codigo}"
            ),
        )

        return (
            empresa,
            codigo,
        )  # el código en claro se devuelve UNA SOLA VEZ, para trazabilidad del llamador

    async def rechazar(self, solicitud_id: str, motivo: str) -> None:
        solicitud = await self._solicitudes.obtener_por_id(solicitud_id)
        if solicitud is None:
            raise SolicitudNoEncontrada()
        solicitud.rechazar(motivo=motivo)
        await self._solicitudes.actualizar(solicitud)
