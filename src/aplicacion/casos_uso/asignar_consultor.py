from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario


class ConsultorNoEncontrado(Exception):
    pass


class EmpresaNoEncontrada(Exception):
    pass


class ConsultorInactivo(Exception):
    pass


class EmpresaInactiva(Exception):
    pass


class AsignarConsultor:
    def __init__(
        self, repo_usuario: RepositorioUsuario, repo_empresa: RepositorioEmpresa
    ):
        self._usuarios = repo_usuario
        self._empresas = repo_empresa

    async def asignar(self, consultor_id: str, empresa_id: str) -> None:
        consultor = await self._usuarios.obtener_por_id(consultor_id)
        if consultor is None:
            raise ConsultorNoEncontrado()
        if not consultor.activo:
            raise ConsultorInactivo()

        empresa = await self._empresas.obtener_por_id(empresa_id)
        if empresa is None:
            raise EmpresaNoEncontrada()
        if not empresa.activo:
            raise EmpresaInactiva()

        consultor.asignar_empresa(empresa_id)
        await self._usuarios.actualizar(consultor)

    async def finalizar(self, consultor_id: str, empresa_id: str) -> None:
        consultor = await self._usuarios.obtener_por_id(consultor_id)
        if consultor is None:
            raise ConsultorNoEncontrado()

        consultor.finalizar_asignacion(empresa_id)
        await self._usuarios.actualizar(consultor)
