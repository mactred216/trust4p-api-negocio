from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, DiagnosticoNoEncontrado)
from src.dominio.entidades.diagnostico import Diagnostico
from src.dominio.puertos.repositorio_diagnostico import RepositorioDiagnostico
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario


class ReprocesarDiagnostico:
    """RF-40, ASR-02: reintenta la evaluación asistida de un diagnóstico que
    quedó 'fallido'. El administrador puede reprocesar el de cualquier
    empresa; el consultor, el de las empresas que tiene asignadas. Lo único
    que hace es devolver el diagnóstico a 'completado'; quien llama programa
    después la evaluación en segundo plano, como al completarlo."""

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
        if usuario is None:
            raise AccesoNoAutorizado()
        if (
            usuario.rol.codigo != "administrador"
            and diagnostico.empresa_id not in usuario.empresas_asignadas_vigentes()
        ):
            raise AccesoNoAutorizado()

        diagnostico.reabrir_para_reproceso()
        await self._diagnosticos.actualizar(diagnostico)
        return diagnostico


class ReprocesarPendientes:
    """RF-40, ASR-02: reanudación diferida. Devuelve a 'completado' todos los
    diagnósticos 'fallido' (del más antiguo al más reciente) y entrega sus
    identificadores para que se evalúen en segundo plano, sin intervención de
    quien los respondió. Exclusivo del administrador (lo garantiza la ruta)."""

    def __init__(self, repo_diagnostico: RepositorioDiagnostico):
        self._diagnosticos = repo_diagnostico

    async def ejecutar(self) -> list[str]:
        ids: list[str] = []
        for diagnostico in await self._diagnosticos.listar_por_estado("fallido"):
            diagnostico.reabrir_para_reproceso()
            await self._diagnosticos.actualizar(diagnostico)
            ids.append(diagnostico.id)
        return ids
