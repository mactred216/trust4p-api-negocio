from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from src.api.dependencias import (obtener_caso_uso_consultar_empresa,
                                  obtener_caso_uso_desactivar_empresa,
                                  obtener_caso_uso_editar_empresa,
                                  obtener_caso_uso_listar_empresas,
                                  obtener_caso_uso_reactivar_empresa,
                                  obtener_repositorio_auditoria)
from src.api.middleware.auditoria import registrar_accion
from src.api.middleware.autorizacion import requiere_rol
from src.aplicacion.casos_uso.gestionar_empresas import (ConsultarEmpresa,
                                                         DesactivarEmpresa,
                                                         EditarEmpresa,
                                                         EmpresaNoEncontrada,
                                                         ListarEmpresas,
                                                         ReactivarEmpresa)

router = APIRouter(prefix="/empresas", tags=["empresas"])


class EmpresaResponse(BaseModel):
    id: str
    nombre: str
    nit: Optional[str]
    numero_empleados: Optional[int]
    ciudad: Optional[str]
    activo: bool


class EditarEmpresaRequest(BaseModel):
    nombre: Optional[str] = None
    nit: Optional[str] = None
    numero_empleados: Optional[int] = None
    ciudad: Optional[str] = None

    @field_validator("nombre", "nit", "ciudad")
    @classmethod
    def si_viene_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Si se envía este campo, no puede estar vacío")
        return v

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


def _a_response(empresa) -> EmpresaResponse:
    return EmpresaResponse(
        id=empresa.id,
        nombre=empresa.nombre,
        nit=empresa.nit,
        numero_empleados=empresa.numero_empleados,
        ciudad=empresa.ciudad,
        activo=empresa.activo,
    )


@router.get("", response_model=list[EmpresaResponse])
async def listar_empresas(
    solo_activas: bool = Query(default=True),
    caso_uso: ListarEmpresas = Depends(obtener_caso_uso_listar_empresas),
    usuario_id: str = Depends(requiere_rol("administrador")),
):
    empresas = await caso_uso.ejecutar(solo_activas=solo_activas)
    return [_a_response(e) for e in empresas]


@router.get("/{empresa_id}", response_model=EmpresaResponse)
async def consultar_empresa(
    empresa_id: str,
    caso_uso: ConsultarEmpresa = Depends(obtener_caso_uso_consultar_empresa),
    usuario_id: str = Depends(requiere_rol("administrador")),
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
    usuario_id: str = Depends(requiere_rol("administrador")),
):
    try:
        empresa = await caso_uso.ejecutar(
            empresa_id,
            nombre=datos.nombre,
            nit=datos.nit,
            numero_empleados=datos.numero_empleados,
            ciudad=datos.ciudad,
        )
    except EmpresaNoEncontrada:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return _a_response(empresa)


@router.post("/{empresa_id}/desactivar", status_code=204)
async def desactivar_empresa(
    empresa_id: str,
    caso_uso: DesactivarEmpresa = Depends(obtener_caso_uso_desactivar_empresa),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
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
        valores_nuevos={"activo": False},
    )


@router.post("/{empresa_id}/reactivar", status_code=204)
async def reactivar_empresa(
    empresa_id: str,
    caso_uso: ReactivarEmpresa = Depends(obtener_caso_uso_reactivar_empresa),
    usuario_id: str = Depends(requiere_rol("administrador")),
):
    try:
        await caso_uso.ejecutar(empresa_id)
    except EmpresaNoEncontrada:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
