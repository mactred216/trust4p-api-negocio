from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencias import obtener_repositorio_sector
from src.dominio.puertos.repositorio_sector import RepositorioSector

router = APIRouter(prefix="/sectores", tags=["sectores"])


class SectorResponse(BaseModel):
    id: str
    codigo: str
    nombre: str


@router.get(
    "",
    response_model=list[SectorResponse],
    summary="Catálogo de sectores",
    description="Público: alimenta el formulario de solicitud de acceso (RF-01).",
)
async def listar_sectores(
    repo: RepositorioSector = Depends(obtener_repositorio_sector),
):
    return [
        SectorResponse(id=s.id, codigo=s.codigo, nombre=s.nombre)
        for s in await repo.listar_activos()
    ]
