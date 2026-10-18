from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, CerrarDiagnostico, CompletarDiagnostico,
    ConsultarDiagnostico, DiagnosticoEnCursoExistente, DiagnosticoNoEncontrado,
    GuardarRespuesta, IniciarDiagnostico, ListarDiagnosticosDeEmpresa,
    NoHayVersionVigente, ObtenerCuestionario, ObtenerDiagnosticoEnCurso)
from src.dominio.entidades.diagnostico import Diagnostico
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.modelo_madurez import (CondicionActivacion,
                                                  ModeloMadurez,
                                                  OpcionPregunta, Pregunta)
from src.dominio.entidades.usuario import Asignacion, Rol, Usuario


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
        "user-1", "diag-1", pregunta_codigo="p1", valor=Decimal("7")
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
        "user-1", "diag-1", pregunta_codigo="p1", valor=Decimal("3")
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


@pytest.mark.asyncio
async def test_obtener_cuestionario():
    diagnostico = crear_diagnostico_prueba()
    modelo = crear_modelo_prueba()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = modelo

    caso_uso = ObtenerCuestionario(repo_diagnostico, repo_usuario, repo_modelo)
    resultado = await caso_uso.ejecutar("user-1", "diag-1")

    assert resultado.version == "v1"
    repo_modelo.obtener_por_version.assert_called_once_with("v1")


@pytest.mark.asyncio
async def test_obtener_cuestionario_diagnostico_inexistente_falla():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = None
    repo_usuario = AsyncMock()
    repo_modelo = AsyncMock()

    caso_uso = ObtenerCuestionario(repo_diagnostico, repo_usuario, repo_modelo)
    with pytest.raises(DiagnosticoNoEncontrado):
        await caso_uso.ejecutar("user-1", "no-existe")


@pytest.mark.asyncio
async def test_obtener_cuestionario_de_otra_empresa_falla():
    diagnostico = crear_diagnostico_prueba(empresa_id="emp-otra")
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba(empresa_id="emp-1")
    repo_modelo = AsyncMock()

    caso_uso = ObtenerCuestionario(repo_diagnostico, repo_usuario, repo_modelo)
    with pytest.raises(AccesoNoAutorizado):
        await caso_uso.ejecutar("user-1", "diag-1")
    repo_modelo.obtener_por_version.assert_not_called()


@pytest.mark.asyncio
async def test_obtener_cuestionario_version_de_modelo_inexistente_falla():
    diagnostico = crear_diagnostico_prueba()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = None

    caso_uso = ObtenerCuestionario(repo_diagnostico, repo_usuario, repo_modelo)
    with pytest.raises(ValueError):
        await caso_uso.ejecutar("user-1", "diag-1")


def crear_modelo_con_pregunta_seleccion(tipo="seleccion_multiple"):
    modelo = crear_modelo_prueba()
    modelo.preguntas = [
        Pregunta(
            codigo="p1",
            dimension_codigo="innovacion",
            enunciado="¿Qué canales usa para innovar?",
            tipo=tipo,
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=1,
            opciones=[
                OpcionPregunta(codigo="alta", etiqueta="Alta", valor=Decimal("10")),
                OpcionPregunta(codigo="media", etiqueta="Media", valor=Decimal("5")),
            ],
        )
    ]
    return modelo


@pytest.mark.asyncio
async def test_guardar_respuesta_seleccion_multiple_acepta_varias_opciones():
    diagnostico = crear_diagnostico_prueba()
    modelo = crear_modelo_con_pregunta_seleccion("seleccion_multiple")
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = modelo

    caso_uso = GuardarRespuesta(repo_diagnostico, repo_usuario, repo_modelo)
    resultado = await caso_uso.ejecutar(
        "user-1", "diag-1", pregunta_codigo="p1", opciones_codigo=["alta", "media"]
    )

    assert resultado.respuestas[0].opciones_codigo == ["alta", "media"]


@pytest.mark.asyncio
async def test_guardar_respuesta_seleccion_unica_rechaza_varias_opciones():
    diagnostico = crear_diagnostico_prueba()
    modelo = crear_modelo_con_pregunta_seleccion("seleccion_unica")
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = modelo

    caso_uso = GuardarRespuesta(repo_diagnostico, repo_usuario, repo_modelo)
    with pytest.raises(ValueError):
        await caso_uso.ejecutar(
            "user-1", "diag-1", pregunta_codigo="p1", opciones_codigo=["alta", "media"]
        )


@pytest.mark.asyncio
async def test_guardar_respuesta_opcion_inexistente_falla():
    diagnostico = crear_diagnostico_prueba()
    modelo = crear_modelo_con_pregunta_seleccion("seleccion_unica")
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = modelo

    caso_uso = GuardarRespuesta(repo_diagnostico, repo_usuario, repo_modelo)
    with pytest.raises(ValueError):
        await caso_uso.ejecutar(
            "user-1", "diag-1", pregunta_codigo="p1", opciones_codigo=["no-existe"]
        )


def crear_consultor_prueba(empresa_id="emp-1", con_asignacion=True):
    consultor = Usuario(
        id="consultor-1",
        correo="carlos@trust4p.com",
        clave_hash="hash",
        nombres="Carlos",
        apellidos="Gomez",
        rol=Rol(codigo="consultor"),
    )
    if con_asignacion:
        consultor.asignaciones = [Asignacion(empresa_id=empresa_id)]
    return consultor


@pytest.mark.asyncio
async def test_cerrar_diagnostico_evaluado_con_asignacion_vigente():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.estado = "evaluado"
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor_prueba()

    caso_uso = CerrarDiagnostico(repo_diagnostico, repo_usuario)
    resultado = await caso_uso.ejecutar("consultor-1", "diag-1")

    assert resultado.estado == "cerrado"
    assert resultado.cerrado_en is not None
    repo_diagnostico.actualizar.assert_called_once_with(diagnostico)


@pytest.mark.asyncio
async def test_cerrar_diagnostico_fallido_tambien_procede():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.estado = "fallido"
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor_prueba()

    caso_uso = CerrarDiagnostico(repo_diagnostico, repo_usuario)
    resultado = await caso_uso.ejecutar("consultor-1", "diag-1")

    assert resultado.estado == "cerrado"


@pytest.mark.asyncio
async def test_cerrar_diagnostico_sin_asignacion_vigente_falla():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.estado = "evaluado"
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor_prueba(
        con_asignacion=False
    )

    caso_uso = CerrarDiagnostico(repo_diagnostico, repo_usuario)
    with pytest.raises(AccesoNoAutorizado):
        await caso_uso.ejecutar("consultor-1", "diag-1")


@pytest.mark.asyncio
async def test_cerrar_diagnostico_aun_completado_falla():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.estado = "completado"
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor_prueba()

    caso_uso = CerrarDiagnostico(repo_diagnostico, repo_usuario)
    with pytest.raises(ValueError):
        await caso_uso.ejecutar("consultor-1", "diag-1")


@pytest.mark.asyncio
async def test_cerrar_diagnostico_inexistente_falla():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = None
    repo_usuario = AsyncMock()

    caso_uso = CerrarDiagnostico(repo_diagnostico, repo_usuario)
    with pytest.raises(DiagnosticoNoEncontrado):
        await caso_uso.ejecutar("consultor-1", "diag-inexistente")


def crear_administrador_prueba():
    return Usuario(
        id="admin-1",
        correo="admin@trust4p.com",
        clave_hash="hash",
        nombres="Ada",
        apellidos="Admin",
        rol=Rol(codigo="administrador"),
    )


@pytest.mark.asyncio
async def test_administrador_cierra_diagnostico_de_empresa_sin_consultor():
    """Hallazgo de la verificación: la empresa sin consultor asignado no debe
    quedar con un diagnóstico abierto para siempre."""
    diagnostico = crear_diagnostico_prueba()
    diagnostico.estado = "evaluado"
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_administrador_prueba()

    caso_uso = CerrarDiagnostico(repo_diagnostico, repo_usuario)
    resultado = await caso_uso.ejecutar("admin-1", "diag-1")

    assert resultado.estado == "cerrado"
    repo_diagnostico.actualizar.assert_called_once_with(diagnostico)


@pytest.mark.asyncio
async def test_administrador_tambien_cierra_diagnostico_fallido():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.estado = "fallido"
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_administrador_prueba()

    caso_uso = CerrarDiagnostico(repo_diagnostico, repo_usuario)
    resultado = await caso_uso.ejecutar("admin-1", "diag-1")

    assert resultado.estado == "cerrado"


@pytest.mark.asyncio
async def test_administrador_no_cierra_diagnostico_en_proceso():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.estado = "completado"
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_administrador_prueba()

    caso_uso = CerrarDiagnostico(repo_diagnostico, repo_usuario)
    with pytest.raises(ValueError):
        await caso_uso.ejecutar("admin-1", "diag-1")
    repo_diagnostico.actualizar.assert_not_called()


@pytest.mark.asyncio
async def test_cerrar_diagnostico_usuario_inexistente_falla():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.estado = "evaluado"
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = None

    caso_uso = CerrarDiagnostico(repo_diagnostico, repo_usuario)
    with pytest.raises(AccesoNoAutorizado):
        await caso_uso.ejecutar("fantasma", "diag-1")
