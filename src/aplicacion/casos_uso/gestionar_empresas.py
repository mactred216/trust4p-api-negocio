from typing import Optional

from src.dominio.entidades.empresa import Empresa
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa


class EmpresaNoEncontrada(Exception):
    pass


class ListarEmpresas:
    def __init__(self, repo: RepositorioEmpresa):
        self._empresas = repo

    async def ejecutar(self, solo_activas: bool = True) -> list[Empresa]:
        if solo_activas:
            return await self._empresas.listar_activas()
        return await self._empresas.listar_todas()


class ConsultarEmpresa:
    def __init__(self, repo: RepositorioEmpresa):
        self._empresas = repo

    async def ejecutar(self, empresa_id: str) -> Empresa:
        empresa = await self._empresas.obtener_por_id(empresa_id)
        if empresa is None:
            raise EmpresaNoEncontrada()
        return empresa


class EditarEmpresa:
    def __init__(self, repo: RepositorioEmpresa):
        self._empresas = repo

    async def ejecutar(
        self,
        empresa_id: str,
        nombre: Optional[str] = None,
        nit: Optional[str] = None,
        numero_empleados: Optional[int] = None,
        ciudad: Optional[str] = None,
    ) -> Empresa:
        empresa = await self._empresas.obtener_por_id(empresa_id)
        if empresa is None:
            raise EmpresaNoEncontrada()

        if nombre is not None:
            empresa.nombre = nombre
        if nit is not None:
            empresa.nit = nit
        if numero_empleados is not None:
            empresa.numero_empleados = numero_empleados
        if ciudad is not None:
            empresa.ciudad = ciudad

        await self._empresas.actualizar(empresa)
        return empresa


class DesactivarEmpresa:
    """RF-24: baja lógica. Regla R-06: preserva diagnósticos asociados."""

    def __init__(self, repo: RepositorioEmpresa):
        self._empresas = repo

    async def ejecutar(self, empresa_id: str) -> None:
        empresa = await self._empresas.obtener_por_id(empresa_id)
        if empresa is None:
            raise EmpresaNoEncontrada()

        empresa.desactivar()
        await self._empresas.actualizar(empresa)


class ReactivarEmpresa:
    def __init__(self, repo: RepositorioEmpresa):
        self._empresas = repo

    async def ejecutar(self, empresa_id: str) -> None:
        empresa = await self._empresas.obtener_por_id(empresa_id)
        if empresa is None:
            raise EmpresaNoEncontrada()

        empresa.reactivar()
        await self._empresas.actualizar(empresa)
