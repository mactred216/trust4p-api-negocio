from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, CompletarDiagnostico, ConsultarDiagnostico,
    DiagnosticoEnCursoExistente, DiagnosticoNoEncontrado, GuardarRespuesta,
    IniciarDiagnostico, ListarDiagnosticosDeEmpresa, NoHayVersionVigente,
    ObtenerDiagnosticoEnCurso)
from src.dominio.entidades.diagnostico import Diagnostico
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.modelo_madurez import (CondicionActivacion,
                                                  ModeloMadurez, Pregunta)
from src.dominio.entidades.usuario import Rol, Usuario


def crear_usuario_prueba(empresa_id="emp-1"):
    return Usuario(
        id="user-1",
        correo="ana@innovatech.com",
        clave_hash="hash",
        nombres="Ana",
        apellidos="Pérez",
        rol=Rol(codigo="representante"),
        empresa_id=empresa_id,
    )


def crear_empresa_prueba():
    return Empresa(
        id="emp-1",
        nombre="InnovaTech",
        sector=Sector(id="s1", codigo="J62", nombre="Software"),
    )


def crear_modelo_prueba(publicado=True):
    modelo = ModeloMadurez(
        id="modelo-1", version="v1", nombre="Modelo", publicado=publicado
    )
    modelo.preguntas = [
        Pregunta(
            codigo="p1",
            dimension_codigo="innovacion",
            enunciado="¿Invierte en I+D?",
            tipo="escala",
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=1,
        )
    ]
    return modelo


def crear_diagnostico_prueba(empresa_id="emp-1"):
    return Diagnostico(
        id="diag-1",
        empresa_id=empresa_id,
        empresa_nombre="InnovaTech",
        usuario_id="user-1",
        modelo_version="v1",
        consecutivo=1,
    )


@pytest.mark.asyncio
async def test_iniciar_diagnostico():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_en_curso_por_empresa.return_value = None
    repo_diagnostico.contar_por_empresa.return_value = 0
    repo_diagnostico.guardar.side_effect = lambda d: d
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = crear_empresa_prueba()
    repo_modelo = AsyncMock()
    repo_modelo.obtener_vigente.return_value = crear_modelo_prueba()

    caso_uso = IniciarDiagnostico(
        repo_diagnostico, repo_usuario, repo_empresa, repo_modelo
    )
    diagnostico = await caso_uso.ejecutar("user-1")

    assert diagnostico.consecutivo == 1
    assert diagnostico.modelo_version == "v1"
    assert diagnostico.empresa_nombre == "InnovaTech"


@pytest.mark.asyncio
async def test_iniciar_diagnostico_con_uno_en_curso_falla():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_en_curso_por_empresa.return_value = (
        crear_diagnostico_prueba()
    )
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()
    repo_empresa = AsyncMock()
    repo_modelo = AsyncMock()

    caso_uso = IniciarDiagnostico(
        repo_diagnostico, repo_usuario, repo_empresa, repo_modelo
    )
    with pytest.raises(DiagnosticoEnCursoExistente):
        await caso_uso.ejecutar("user-1")
    repo_diagnostico.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_iniciar_diagnostico_sin_version_vigente_falla():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_en_curso_por_empresa.return_value = None
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()
    repo_empresa = AsyncMock()
    repo_modelo = AsyncMock()
    repo_modelo.obtener_vigente.return_value = None

    caso_uso = IniciarDiagnostico(
        repo_diagnostico, repo_usuario, repo_empresa, repo_modelo
    )
    with pytest.raises(NoHayVersionVigente):
        await caso_uso.ejecutar("user-1")


@pytest.mark.asyncio
async def test_iniciar_diagnostico_usuario_sin_empresa_falla():
    repo_diagnostico = AsyncMock()
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba(empresa_id=None)
    repo_empresa = AsyncMock()
    repo_modelo = AsyncMock()

    caso_uso = IniciarDiagnostico(
        repo_diagnostico, repo_usuario, repo_empresa, repo_modelo
    )
    with pytest.raises(ValueError):
        await caso_uso.ejecutar("user-1")


@pytest.mark.asyncio
async def test_guardar_respuesta():
    diagnostico = crear_diagnostico_prueba()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = crear_modelo_prueba()

    caso_uso = GuardarRespuesta(repo_diagnostico, repo_usuario, repo_modelo)
    resultado = await caso_uso.ejecutar(
        "user-1", "diag-1", pregunta_codigo="p1", opcion_codigo="alta"
    )

    assert len(resultado.respuestas) == 1
    assert resultado.respuestas[0].dimension_codigo == "innovacion"
    repo_diagnostico.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_guardar_respuesta_diagnostico_inexistente_falla():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = None
    repo_usuario = AsyncMock()
    repo_modelo = AsyncMock()

    caso_uso = GuardarRespuesta(repo_diagnostico, repo_usuario, repo_modelo)
    with pytest.raises(DiagnosticoNoEncontrado):
        await caso_uso.ejecutar("user-1", "no-existe", pregunta_codigo="p1")


@pytest.mark.asyncio
async def test_guardar_respuesta_de_otra_empresa_falla():
    diagnostico = crear_diagnostico_prueba(empresa_id="emp-otra")
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba(empresa_id="emp-1")
    repo_modelo = AsyncMock()

    caso_uso = GuardarRespuesta(repo_diagnostico, repo_usuario, repo_modelo)
    with pytest.raises(AccesoNoAutorizado):
        await caso_uso.ejecutar("user-1", "diag-1", pregunta_codigo="p1")
    repo_diagnostico.actualizar.assert_not_called()


@pytest.mark.asyncio
async def test_guardar_respuesta_pregunta_inexistente_falla():
    diagnostico = crear_diagnostico_prueba()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = crear_modelo_prueba()

    caso_uso = GuardarRespuesta(repo_diagnostico, repo_usuario, repo_modelo)
    with pytest.raises(ValueError):
        await caso_uso.ejecutar("user-1", "diag-1", pregunta_codigo="no-existe")


@pytest.mark.asyncio
async def test_guardar_respuesta_pregunta_inactiva_falla():
    diagnostico = crear_diagnostico_prueba()
    modelo = crear_modelo_prueba()
    modelo.preguntas[0].activo = False
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = modelo

    caso_uso = GuardarRespuesta(repo_diagnostico, repo_usuario, repo_modelo)
    with pytest.raises(ValueError):
        await caso_uso.ejecutar("user-1", "diag-1", pregunta_codigo="p1")


@pytest.mark.asyncio
async def test_obtener_diagnostico_en_curso():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_en_curso_por_empresa.return_value = (
        crear_diagnostico_prueba()
    )
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()

    caso_uso = ObtenerDiagnosticoEnCurso(repo_diagnostico, repo_usuario)
    diagnostico = await caso_uso.ejecutar("user-1")

    assert diagnostico.id == "diag-1"


@pytest.mark.asyncio
async def test_obtener_diagnostico_en_curso_sin_ninguno_falla():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_en_curso_por_empresa.return_value = None
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()

    caso_uso = ObtenerDiagnosticoEnCurso(repo_diagnostico, repo_usuario)
    with pytest.raises(DiagnosticoNoEncontrado):
        await caso_uso.ejecutar("user-1")


@pytest.mark.asyncio
async def test_consultar_diagnostico():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = crear_diagnostico_prueba()
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()

    caso_uso = ConsultarDiagnostico(repo_diagnostico, repo_usuario)
    diagnostico = await caso_uso.ejecutar("user-1", "diag-1")

    assert diagnostico.id == "diag-1"


@pytest.mark.asyncio
async def test_consultar_diagnostico_de_otra_empresa_falla():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = crear_diagnostico_prueba(
        empresa_id="emp-otra"
    )
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba(empresa_id="emp-1")

    caso_uso = ConsultarDiagnostico(repo_diagnostico, repo_usuario)
    with pytest.raises(AccesoNoAutorizado):
        await caso_uso.ejecutar("user-1", "diag-1")


@pytest.mark.asyncio
async def test_listar_diagnosticos_de_empresa():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_empresa.return_value = [crear_diagnostico_prueba()]
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()

    caso_uso = ListarDiagnosticosDeEmpresa(repo_diagnostico, repo_usuario)
    resultado = await caso_uso.ejecutar("user-1")

    assert len(resultado) == 1
    repo_diagnostico.listar_por_empresa.assert_called_once_with("emp-1")


def crear_modelo_con_obligatoria_y_opcional():
    """RF-10: el avance solo debe contar preguntas obligatorias aplicables;
    responder la opcional no debe mover el porcentaje."""
    modelo = crear_modelo_prueba()
    modelo.preguntas.append(
        Pregunta(
            codigo="p2",
            dimension_codigo="innovacion",
            enunciado="¿Comentario opcional?",
            tipo="texto_libre",
            obligatoria=False,
            peso=Decimal("1"),
            en_demo=False,
            orden=2,
        )
    )
    return modelo


@pytest.mark.asyncio
async def test_guardar_respuesta_de_pregunta_opcional_no_mueve_el_avance():
    diagnostico = crear_diagnostico_prueba()
    modelo = crear_modelo_con_obligatoria_y_opcional()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = modelo

    caso_uso = GuardarRespuesta(repo_diagnostico, repo_usuario, repo_modelo)
    resultado = await caso_uso.ejecutar(
        "user-1", "diag-1", pregunta_codigo="p2", texto="algo"
    )

    assert resultado.porcentaje_avance == 0


@pytest.mark.asyncio
async def test_guardar_respuesta_ignora_preguntas_bloqueadas_por_condicion():
    """RF-08: una pregunta obligatoria bloqueada por una condición no cumplida
    no debe contar en el denominador del avance."""
    diagnostico = crear_diagnostico_prueba()
    modelo = crear_modelo_prueba()
    modelo.preguntas.append(
        Pregunta(
            codigo="p2",
            dimension_codigo="innovacion",
            enunciado="¿Solo si p1 es alta?",
            tipo="texto_libre",
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=2,
            condicion=CondicionActivacion(
                pregunta_codigo="p1", operador="igual", valor="alta"
            ),
        )
    )
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = modelo

    caso_uso = GuardarRespuesta(repo_diagnostico, repo_usuario, repo_modelo)
    resultado = await caso_uso.ejecutar(
        "user-1", "diag-1", pregunta_codigo="p1", opcion_codigo="baja"
    )

    assert resultado.porcentaje_avance == 100


@pytest.mark.asyncio
async def test_completar_diagnostico():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.porcentaje_avance = 100
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()

    caso_uso = CompletarDiagnostico(repo_diagnostico, repo_usuario)
    resultado = await caso_uso.ejecutar("user-1", "diag-1")

    assert resultado.estado == "completado"
    repo_diagnostico.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_completar_diagnostico_incompleto_falla():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.porcentaje_avance = 50
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()

    caso_uso = CompletarDiagnostico(repo_diagnostico, repo_usuario)
    with pytest.raises(ValueError):
        await caso_uso.ejecutar("user-1", "diag-1")
    repo_diagnostico.actualizar.assert_not_called()


@pytest.mark.asyncio
async def test_completar_diagnostico_inexistente_falla():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = None
    repo_usuario = AsyncMock()

    caso_uso = CompletarDiagnostico(repo_diagnostico, repo_usuario)
    with pytest.raises(DiagnosticoNoEncontrado):
        await caso_uso.ejecutar("user-1", "no-existe")


@pytest.mark.asyncio
async def test_completar_diagnostico_de_otra_empresa_falla():
    diagnostico = crear_diagnostico_prueba(empresa_id="emp-otra")
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba(empresa_id="emp-1")

    caso_uso = CompletarDiagnostico(repo_diagnostico, repo_usuario)
    with pytest.raises(AccesoNoAutorizado):
        await caso_uso.ejecutar("user-1", "diag-1")
    repo_diagnostico.actualizar.assert_not_called()
