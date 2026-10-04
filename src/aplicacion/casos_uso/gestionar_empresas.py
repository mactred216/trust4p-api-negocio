from typing import Optional

from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa


class EmpresaNoEncontrada(Exception):
    pass


class NitYaRegistrado(Exception):
    pass


class CrearEmpresa:
    """RF-24 paso 1: crea la empresa validando que el NIT no exista."""

    def __init__(self, repo: RepositorioEmpresa):
        self._empresas = repo

    async def ejecutar(
        self,
        nit: str,
        nombre: str,
        sector: Sector,
        numero_empleados: int,
        ciudad: Optional[str] = None,
    ) -> Empresa:
        if await self._empresas.obtener_por_nit(nit) is not None:
            raise NitYaRegistrado()
        return await self._empresas.guardar(
            Empresa(
                id=None,
                nombre=nombre,
                sector=sector,
                nit=nit,
                numero_empleados=numero_empleados,
                ciudad=ciudad,
            )
        )


class ListarEmpresas:
    """RF-24 paso 2: listado con filtros por nombre, sector y estado."""

    def __init__(self, repo: RepositorioEmpresa):
        self._empresas = repo

    async def ejecutar(
        self,
        solo_activas: bool = True,
        nombre: Optional[str] = None,
        sector_codigo: Optional[str] = None,
        estado: Optional[str] = None,
    ) -> list[Empresa]:
        if estado is not None:
            if estado not in ("activa", "inactiva"):
                raise ValueError("Estado inválido; use 'activa' o 'inactiva'")
            empresas = await self._empresas.listar_todas()
            empresas = [e for e in empresas if e.activo == (estado == "activa")]
        elif solo_activas:
            empresas = await self._empresas.listar_activas()
        else:
            empresas = await self._empresas.listar_todas()
        if nombre:
            empresas = [e for e in empresas if nombre.lower() in e.nombre.lower()]
        if sector_codigo:
            empresas = [e for e in empresas if e.sector.codigo == sector_codigo]
        return empresas


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
        if nit is not None and nit != empresa.nit:
            existente = await self._empresas.obtener_por_nit(nit)
            if existente is not None and existente.id != empresa.id:
                raise NitYaRegistrado()
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
