from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from src.api.dependencias import (obtener_caso_uso_consultar_empresa,
                                  obtener_caso_uso_crear_empresa,
                                  obtener_caso_uso_desactivar_empresa,
                                  obtener_caso_uso_editar_empresa,
                                  obtener_caso_uso_listar_empresas,
                                  obtener_caso_uso_reactivar_empresa,
                                  obtener_repositorio_auditoria)
from src.api.middleware.auditoria import registrar_accion, registrar_cambio
from src.api.middleware.autorizacion import requiere_rol
from src.api.validadores_comunes import (nit_valido, texto_no_vacio,
                                         texto_opcional_no_vacio)
from src.aplicacion.casos_uso.gestionar_empresas import (ConsultarEmpresa,
                                                         CrearEmpresa,
                                                         DesactivarEmpresa,
                                                         EditarEmpresa,
                                                         EmpresaNoEncontrada,
                                                         ListarEmpresas,
                                                         NitYaRegistrado,
                                                         ReactivarEmpresa,
                                                         SectorNoValido)
from src.dominio.entidades.empresa import Sector

router = APIRouter(prefix="/empresas", tags=["empresas"])


class EmpresaResponse(BaseModel):
    id: str
    nombre: str
    nit: Optional[str]
    numero_empleados: Optional[int]
    ciudad: Optional[str]
    activo: bool
    sector_codigo: Optional[str] = None
    sector_nombre: Optional[str] = None


class CrearEmpresaRequest(BaseModel):
    nit: str
    nombre: str
    sector_id: str
    sector_codigo: str
    sector_nombre: str
    numero_empleados: int
    ciudad: Optional[str] = None

    @field_validator("nit")
    @classmethod
    def _nit_valido(cls, v: str) -> str:
        return nit_valido(v)

    @field_validator("nombre", "sector_id", "sector_codigo", "sector_nombre")
    @classmethod
    def _no_vacio(cls, v: str) -> str:
        return texto_no_vacio(v, maximo=200)

    @field_validator("ciudad")
    @classmethod
    def _ciudad_valida(cls, v: Optional[str]) -> Optional[str]:
        return texto_opcional_no_vacio(v)

    @field_validator("numero_empleados")
    @classmethod
    def _empleados_validos(cls, v: int) -> int:
        if v <= 0 or v > 1_000_000:
            raise ValueError(
                "El número de empleados debe ser un entero positivo razonable"
            )
        return v


class EditarEmpresaRequest(BaseModel):
    nombre: Optional[str] = None
    nit: Optional[str] = None
    sector_codigo: Optional[str] = None
    numero_empleados: Optional[int] = None
    ciudad: Optional[str] = None

    @field_validator("nombre", "ciudad")
    @classmethod
    def si_viene_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        return texto_opcional_no_vacio(v)

    @field_validator("sector_codigo")
    @classmethod
    def sector_si_viene_valido(cls, v: Optional[str]) -> Optional[str]:
        return texto_opcional_no_vacio(v, maximo=50)

    @field_validator("nit")
    @classmethod
    def nit_si_viene_valido(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else nit_valido(v)

    @field_validator("numero_empleados")
    @classmethod
    def numero_empleados_valido(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v < 0:
            raise ValueError("El número de empleados no puede ser negativo")
        if v > 1_000_000:
            raise ValueError("Valor de empleados no razonable")
        return v


def _resumen_auditoria(empresa) -> dict:
    return {
        "nombre": empresa.nombre,
        "nit": empresa.nit,
        "sector": empresa.sector.codigo,
        "sector_nombre": empresa.sector.nombre,
        "numero_empleados": empresa.numero_empleados,
        "ciudad": empresa.ciudad,
        "activo": empresa.activo,
    }


def _a_response(empresa) -> EmpresaResponse:
    return EmpresaResponse(
        id=empresa.id,
        nombre=empresa.nombre,
        nit=empresa.nit,
        numero_empleados=empresa.numero_empleados,
        ciudad=empresa.ciudad,
        activo=empresa.activo,
        sector_codigo=empresa.sector.codigo,
        sector_nombre=empresa.sector.nombre,
    )


@router.post(
    "",
    response_model=EmpresaResponse,
    status_code=201,
    summary="Crear una empresa",
    description="RF-24: el administrador registra una empresa con NIT, nombre, "
    "sector y tamaño (número de empleados); el NIT no puede estar registrado.",
)
async def crear_empresa(
    datos: CrearEmpresaRequest,
    caso_uso: CrearEmpresa = Depends(obtener_caso_uso_crear_empresa),
    usuario_actual_id: str = Depends(
        requiere_rol("administrador", "empresas.gestionar")
    ),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        empresa = await caso_uso.ejecutar(
            nit=datos.nit,
            nombre=datos.nombre,
            sector=Sector(
                id=datos.sector_id,
                codigo=datos.sector_codigo,
                nombre=datos.sector_nombre,
            ),
            numero_empleados=datos.numero_empleados,
            ciudad=datos.ciudad,
        )
    except NitYaRegistrado:
        raise HTTPException(status_code=409, detail="Ya existe una empresa con ese NIT")

    await registrar_accion(
        repo_auditoria,
        usuario_actual_id,
        "empresas",
        empresa.id,
        "crear",
        valores_nuevos={
            "nit": empresa.nit,
            "nombre": empresa.nombre,
            "sector": empresa.sector.codigo,
            "numero_empleados": empresa.numero_empleados,
        },
    )
    return _a_response(empresa)


@router.get("", response_model=list[EmpresaResponse])
async def listar_empresas(
    solo_activas: bool = Query(default=True),
    nombre: Optional[str] = Query(default=None, max_length=100),
    sector: Optional[str] = Query(
        default=None, max_length=50, description="Código del sector"
    ),
    estado: Optional[str] = Query(default=None, description="activa | inactiva"),
    caso_uso: ListarEmpresas = Depends(obtener_caso_uso_listar_empresas),
    usuario_id: str = Depends(requiere_rol("administrador", "empresas.gestionar")),
):
    try:
        empresas = await caso_uso.ejecutar(
            solo_activas=solo_activas,
            nombre=nombre,
            sector_codigo=sector,
            estado=estado,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [_a_response(e) for e in empresas]


@router.get("/{empresa_id}", response_model=EmpresaResponse)
async def consultar_empresa(
    empresa_id: str,
    caso_uso: ConsultarEmpresa = Depends(obtener_caso_uso_consultar_empresa),
    usuario_id: str = Depends(requiere_rol("administrador", "empresas.gestionar")),
):
    try:
        empresa = await caso_uso.ejecutar(empresa_id)
    except EmpresaNoEncontrada:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return _a_response(empresa)


@router.patch("/{empresa_id}", response_model=EmpresaResponse)
async def editar_empresa(
    empresa_id: str,
    datos: EditarEmpresaRequest,
    caso_uso: EditarEmpresa = Depends(obtener_caso_uso_editar_empresa),
    consulta: ConsultarEmpresa = Depends(obtener_caso_uso_consultar_empresa),
    usuario_id: str = Depends(requiere_rol("administrador", "empresas.gestionar")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        antes = _resumen_auditoria(await consulta.ejecutar(empresa_id))
        empresa = await caso_uso.ejecutar(
            empresa_id,
            nombre=datos.nombre,
            nit=datos.nit,
            numero_empleados=datos.numero_empleados,
            ciudad=datos.ciudad,
            sector_codigo=datos.sector_codigo,
        )
    except EmpresaNoEncontrada:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    except NitYaRegistrado:
        raise HTTPException(status_code=409, detail="Ya existe una empresa con ese NIT")
    except SectorNoValido:
        raise HTTPException(
            status_code=400, detail="El sector indicado no existe o está inactivo"
        )

    await registrar_cambio(
        repo_auditoria,
        usuario_id,
        "empresas",
        empresa_id,
        antes,
        _resumen_auditoria(empresa),
    )
    return _a_response(empresa)


@router.post("/{empresa_id}/desactivar", status_code=204)
async def desactivar_empresa(
    empresa_id: str,
    caso_uso: DesactivarEmpresa = Depends(obtener_caso_uso_desactivar_empresa),
    usuario_actual_id: str = Depends(
        requiere_rol("administrador", "empresas.gestionar")
    ),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        await caso_uso.ejecutar(empresa_id)
    except EmpresaNoEncontrada:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    await registrar_accion(
        repo_auditoria,
        usuario_actual_id,
        "empresas",
        empresa_id,
        "actualizar",
        valores_anteriores={"activo": True},
        valores_nuevos={"activo": False},
    )


@router.post("/{empresa_id}/reactivar", status_code=204)
async def reactivar_empresa(
    empresa_id: str,
    caso_uso: ReactivarEmpresa = Depends(obtener_caso_uso_reactivar_empresa),
    usuario_id: str = Depends(requiere_rol("administrador", "empresas.gestionar")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        await caso_uso.ejecutar(empresa_id)
    except EmpresaNoEncontrada:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    await registrar_accion(
        repo_auditoria,
        usuario_id,
        "empresas",
        empresa_id,
        "actualizar",
        valores_anteriores={"activo": False},
        valores_nuevos={"activo": True},
    )
