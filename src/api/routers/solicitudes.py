from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, field_validator

from src.api.dependencias import (obtener_caso_uso_consultar_solicitud,
                                  obtener_caso_uso_listar_solicitudes,
                                  obtener_caso_uso_radicar_solicitud,
                                  obtener_caso_uso_resolver_solicitud,
                                  obtener_repositorio_auditoria)
from src.api.middleware.auditoria import registrar_accion
from src.api.middleware.autorizacion import requiere_rol
from src.api.middleware.limites import limite_solicitudes
from src.api.validadores_comunes import (nit_valido, telefono_valido,
                                         texto_no_vacio,
                                         texto_opcional_no_vacio)
from src.aplicacion.casos_uso.consultar_solicitudes import (ConsultarSolicitud,
                                                            ListarSolicitudes)
from src.aplicacion.casos_uso.radicar_solicitud import (RadicarSolicitud,
                                                        SectorInvalido,
                                                        SolicitudDuplicada)
from src.aplicacion.casos_uso.resolver_solicitud import (ResolverSolicitud,
                                                         SolicitudNoEncontrada)
from src.dominio.entidades.empresa import Sector
from src.dominio.entidades.solicitud_acceso import SolicitudYaResuelta
from src.dominio.servicios.indicadores_agregados import clasificar_tamano

router = APIRouter(prefix="/solicitudes-acceso", tags=["solicitudes"])


class RadicarSolicitudRequest(BaseModel):
    """RF-01: datos de la empresa y del solicitante, con la autorización de
    tratamiento de datos (RF-43)."""

    nombre_empresa: str
    nit: str
    sector_codigo: str
    numero_empleados: int
    ciudad: Optional[str] = None
    nombre_solicitante: str
    cargo: str
    correo_solicitante: EmailStr
    telefono: str
    acepto_tratamiento: bool

    @field_validator("nombre_empresa", "nombre_solicitante", "cargo")
    @classmethod
    def _texto_no_vacio(cls, v: str) -> str:
        return texto_no_vacio(v, minimo=2, maximo=200)

    @field_validator("nit")
    @classmethod
    def _nit_valido(cls, v: str) -> str:
        return nit_valido(v)

    @field_validator("sector_codigo")
    @classmethod
    def _sector_valido(cls, v: str) -> str:
        return texto_no_vacio(v, maximo=50)

    @field_validator("ciudad")
    @classmethod
    def _ciudad_valida(cls, v: Optional[str]) -> Optional[str]:
        return texto_opcional_no_vacio(v, maximo=100)

    @field_validator("telefono")
    @classmethod
    def _telefono_valido(cls, v: str) -> str:
        return telefono_valido(v)

    @field_validator("numero_empleados")
    @classmethod
    def _empleados_validos(cls, v: int) -> int:
        if v <= 0 or v > 1_000_000:
            raise ValueError(
                "El número de empleados debe ser un entero positivo razonable"
            )
        return v

    @field_validator("acepto_tratamiento")
    @classmethod
    def _debe_aceptar(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "Debe aceptar el tratamiento de datos personales para radicar la solicitud"
            )
        return v


class SolicitudResponse(BaseModel):
    id: str
    nombre_empresa: str
    estado: str


class SolicitudDetalleResponse(BaseModel):
    id: str
    estado: str
    nombre_empresa: str
    nit: Optional[str]
    sector_codigo: Optional[str]
    sector_nombre: Optional[str]
    numero_empleados: Optional[int]
    tamano: Optional[str]
    ciudad: Optional[str]
    nombre_solicitante: str
    cargo: Optional[str]
    correo_solicitante: str
    telefono: Optional[str]
    motivo_rechazo: Optional[str]
    empresa_id: Optional[str]
    creado_en: datetime
    resuelto_en: Optional[datetime]


class AprobarSolicitudRequest(BaseModel):
    """Opcional: por defecto se usa el sector que declaró el solicitante."""

    sector_id: str
    sector_codigo: str
    sector_nombre: str

    @field_validator("sector_id", "sector_codigo", "sector_nombre")
    @classmethod
    def _texto_no_vacio(cls, v: str) -> str:
        return texto_no_vacio(v)


class RechazarSolicitudRequest(BaseModel):
    motivo: str

    @field_validator("motivo")
    @classmethod
    def motivo_valido(cls, v: str) -> str:
        return texto_no_vacio(v, minimo=10, maximo=500)


class EmpresaResponse(BaseModel):
    id: str
    nombre: str


def _a_detalle(s) -> SolicitudDetalleResponse:
    return SolicitudDetalleResponse(
        id=s.id,
        estado=s.estado.value,
        nombre_empresa=s.nombre_empresa,
        nit=s.nit,
        sector_codigo=s.sector_codigo,
        sector_nombre=s.sector_nombre,
        numero_empleados=s.numero_empleados,
        tamano=clasificar_tamano(s.numero_empleados),
        ciudad=s.ciudad,
        nombre_solicitante=s.nombre_solicitante,
        cargo=s.cargo,
        correo_solicitante=s.correo_solicitante,
        telefono=s.telefono,
        motivo_rechazo=s.motivo_rechazo,
        empresa_id=s.empresa_id,
        creado_en=s.creado_en,
        resuelto_en=s.resuelto_en,
    )


@router.post(
    "",
    response_model=SolicitudResponse,
    status_code=201,
    dependencies=[Depends(limite_solicitudes)],
)
async def radicar_solicitud(
    datos: RadicarSolicitudRequest,
    caso_uso: RadicarSolicitud = Depends(obtener_caso_uso_radicar_solicitud),
):
    try:
        solicitud = await caso_uso.ejecutar(
            nombre_empresa=datos.nombre_empresa,
            correo_solicitante=datos.correo_solicitante,
            nombre_solicitante=datos.nombre_solicitante,
            nit=datos.nit,
            sector_codigo=datos.sector_codigo,
            numero_empleados=datos.numero_empleados,
            ciudad=datos.ciudad,
            cargo=datos.cargo,
            telefono=datos.telefono,
            acepto_tratamiento=datos.acepto_tratamiento,
        )
    except SolicitudDuplicada:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una solicitud pendiente, una cuenta o una empresa registrada con esos datos",
        )
    except SectorInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))

    return SolicitudResponse(
        id=solicitud.id,
        nombre_empresa=solicitud.nombre_empresa,
        estado=solicitud.estado.value,
    )


@router.get(
    "",
    response_model=list[SolicitudDetalleResponse],
    summary="Bandeja de solicitudes de acceso",
    description="RF-02: exclusivo del administrador. Filtro opcional por estado "
    "(pendiente, aprobada, rechazada); las más recientes primero.",
)
async def listar_solicitudes(
    estado: Optional[str] = Query(default=None),
    caso_uso: ListarSolicitudes = Depends(obtener_caso_uso_listar_solicitudes),
    usuario_id: str = Depends(requiere_rol("administrador", "solicitudes.gestionar")),
):
    try:
        solicitudes = await caso_uso.ejecutar(estado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [_a_detalle(s) for s in solicitudes]


@router.get(
    "/{solicitud_id}",
    response_model=SolicitudDetalleResponse,
    summary="Detalle de una solicitud de acceso",
)
async def consultar_solicitud(
    solicitud_id: str,
    caso_uso: ConsultarSolicitud = Depends(obtener_caso_uso_consultar_solicitud),
    usuario_id: str = Depends(requiere_rol("administrador", "solicitudes.gestionar")),
):
    try:
        return _a_detalle(await caso_uso.ejecutar(solicitud_id))
    except SolicitudNoEncontrada:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")


@router.post(
    "/{solicitud_id}/aprobar",
    response_model=EmpresaResponse,
    summary="Aprobar una solicitud de acceso",
    description="Exclusivo del administrador. Crea la empresa con los datos de la "
    "solicitud (sector declarado por el solicitante, salvo que se indique otro) "
    "y emite la invitación.",
)
async def aprobar_solicitud(
    solicitud_id: str,
    datos: Optional[AprobarSolicitudRequest] = None,
    caso_uso: ResolverSolicitud = Depends(obtener_caso_uso_resolver_solicitud),
    usuario_id: str = Depends(requiere_rol("administrador", "solicitudes.gestionar")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    sector = (
        Sector(
            id=datos.sector_id, codigo=datos.sector_codigo, nombre=datos.sector_nombre
        )
        if datos
        else None
    )
    try:
        empresa, _codigo = await caso_uso.aprobar(solicitud_id, sector)
    except SolicitudNoEncontrada:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    except SolicitudYaResuelta as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_id,
        "solicitudes_acceso",
        solicitud_id,
        "actualizar",
        valores_anteriores={"estado": "pendiente"},
        valores_nuevos={"estado": "aprobada", "empresa_id": empresa.id},
    )

    # RF-45 paso 3: el envío de la invitación (fecha, estado de entrega) ya
    # queda registrado en la colección 'notificaciones' dentro del propio
    # caso de uso -- no se duplica aquí en la bitácora genérica.
    return EmpresaResponse(id=empresa.id, nombre=empresa.nombre)


@router.post(
    "/{solicitud_id}/rechazar",
    status_code=204,
    summary="Rechazar una solicitud de acceso",
    description="Exclusivo del administrador. Exige un motivo explícito.",
)
async def rechazar_solicitud(
    solicitud_id: str,
    datos: RechazarSolicitudRequest,
    caso_uso: ResolverSolicitud = Depends(obtener_caso_uso_resolver_solicitud),
    usuario_id: str = Depends(requiere_rol("administrador", "solicitudes.gestionar")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        await caso_uso.rechazar(solicitud_id, datos.motivo)
    except SolicitudNoEncontrada:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    except SolicitudYaResuelta as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_id,
        "solicitudes_acceso",
        solicitud_id,
        "actualizar",
        valores_anteriores={"estado": "pendiente"},
        valores_nuevos={"estado": "rechazada", "motivo": datos.motivo},
    )
