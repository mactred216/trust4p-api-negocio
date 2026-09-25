from decimal import Decimal
from typing import Optional

from src.dominio.entidades.diagnostico import Diagnostico, Respuesta
from src.dominio.entidades.modelo_madurez import ModeloMadurez
from src.dominio.puertos.repositorio_diagnostico import RepositorioDiagnostico
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_modelo_madurez import \
    RepositorioModeloMadurez
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario
from src.dominio.servicios.logica_adaptativa import preguntas_aplicables


class DiagnosticoNoEncontrado(Exception):
    pass


class DiagnosticoEnCursoExistente(Exception):
    """R-05: solo puede existir un diagnóstico sin cerrar por empresa (HU-12 CA-02)."""

    pass


class NoHayVersionVigente(Exception):
    """No se puede iniciar un diagnóstico sin una versión publicada del modelo."""

    pass


class AccesoNoAutorizado(Exception):
    """El diagnóstico no pertenece a la empresa del usuario autenticado."""

    pass


class IniciarDiagnostico:
    """RF-11 (HU-12): crea un diagnóstico nuevo conservando los anteriores
    como histórico, con el consecutivo siguiente y la versión vigente del
    modelo de madurez fijada (RF-33)."""

    def __init__(
        self,
        repo_diagnostico: RepositorioDiagnostico,
        repo_usuario: RepositorioUsuario,
        repo_empresa: RepositorioEmpresa,
        repo_modelo_madurez: RepositorioModeloMadurez,
    ):
        self._diagnosticos = repo_diagnostico
        self._usuarios = repo_usuario
        self._empresas = repo_empresa
        self._modelos = repo_modelo_madurez

    async def ejecutar(self, usuario_id: str) -> Diagnostico:
        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None or usuario.empresa_id is None:
            raise ValueError("El usuario no tiene una empresa asociada")

        en_curso = await self._diagnosticos.obtener_en_curso_por_empresa(
            usuario.empresa_id
        )
        if en_curso is not None:
            raise DiagnosticoEnCursoExistente()

        modelo = await self._modelos.obtener_vigente()
        if modelo is None:
            raise NoHayVersionVigente()

        empresa = await self._empresas.obtener_por_id(usuario.empresa_id)
        if empresa is None:
            raise ValueError("La empresa asociada al usuario no existe")

        consecutivo = (
            await self._diagnosticos.contar_por_empresa(usuario.empresa_id) + 1
        )

        diagnostico = Diagnostico(
            id=None,
            empresa_id=usuario.empresa_id,
            empresa_nombre=empresa.nombre,
            usuario_id=usuario.id,
            modelo_version=modelo.version,
            consecutivo=consecutivo,
        )
        return await self._diagnosticos.guardar(diagnostico)


class GuardarRespuesta:
    """RF-09 (HU-10): guarda cada respuesta de inmediato, sin acción
    explícita de 'guardar'."""

    def __init__(
        self,
        repo_diagnostico: RepositorioDiagnostico,
        repo_usuario: RepositorioUsuario,
        repo_modelo_madurez: RepositorioModeloMadurez,
    ):
        self._diagnosticos = repo_diagnostico
        self._usuarios = repo_usuario
        self._modelos = repo_modelo_madurez

    async def ejecutar(
        self,
        usuario_id: str,
        diagnostico_id: str,
        pregunta_codigo: str,
        opcion_codigo: Optional[str] = None,
        valor: Optional[Decimal] = None,
        texto: Optional[str] = None,
    ) -> Diagnostico:
        diagnostico = await self._diagnosticos.obtener_por_id(diagnostico_id)
        if diagnostico is None:
            raise DiagnosticoNoEncontrado()

        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None or usuario.empresa_id != diagnostico.empresa_id:
            raise AccesoNoAutorizado()

        modelo = await self._modelos.obtener_por_version(diagnostico.modelo_version)
        if modelo is None:
            raise ValueError(
                "La versión del modelo aplicada a este diagnóstico ya no existe"
            )

        pregunta = next(
            (p for p in modelo.preguntas if p.codigo == pregunta_codigo and p.activo),
            None,
        )
        if pregunta is None:
            raise ValueError(
                f"La pregunta '{pregunta_codigo}' no existe o no está activa en la "
                f"versión '{diagnostico.modelo_version}'"
            )

        respuesta = Respuesta(
            pregunta_codigo=pregunta_codigo,
            dimension_codigo=pregunta.dimension_codigo,
            opcion_codigo=opcion_codigo,
            valor=valor,
            texto=texto,
        )

        respuestas_tentativas = [
            r for r in diagnostico.respuestas if r.pregunta_codigo != pregunta_codigo
        ] + [respuesta]
        aplicables = preguntas_aplicables(modelo.preguntas, respuestas_tentativas)
        codigos_obligatorias_aplicables = {
            p.codigo for p in aplicables if p.obligatoria
        }

        diagnostico.registrar_respuesta(respuesta, codigos_obligatorias_aplicables)
        await self._diagnosticos.actualizar(diagnostico)
        return diagnostico


class ObtenerDiagnosticoEnCurso:
    """RF-09 paso 3: recupera el último avance guardado de la empresa del usuario."""

    def __init__(
        self, repo_diagnostico: RepositorioDiagnostico, repo_usuario: RepositorioUsuario
    ):
        self._diagnosticos = repo_diagnostico
        self._usuarios = repo_usuario

    async def ejecutar(self, usuario_id: str) -> Diagnostico:
        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None or usuario.empresa_id is None:
            raise ValueError("El usuario no tiene una empresa asociada")

        diagnostico = await self._diagnosticos.obtener_en_curso_por_empresa(
            usuario.empresa_id
        )
        if diagnostico is None:
            raise DiagnosticoNoEncontrado()
        return diagnostico


class ConsultarDiagnostico:
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
        if usuario is None or usuario.empresa_id != diagnostico.empresa_id:
            raise AccesoNoAutorizado()

        return diagnostico


class ObtenerCuestionario:
    """RF-07 (HU-008): entrega la estructura del cuestionario (dimensiones y
    preguntas activas) de la versión del modelo fijada al diagnóstico, para
    que el representante pueda responderlo."""

    def __init__(
        self,
        repo_diagnostico: RepositorioDiagnostico,
        repo_usuario: RepositorioUsuario,
        repo_modelo_madurez: RepositorioModeloMadurez,
    ):
        self._diagnosticos = repo_diagnostico
        self._usuarios = repo_usuario
        self._modelos = repo_modelo_madurez

    async def ejecutar(self, usuario_id: str, diagnostico_id: str) -> ModeloMadurez:
        diagnostico = await self._diagnosticos.obtener_por_id(diagnostico_id)
        if diagnostico is None:
            raise DiagnosticoNoEncontrado()

        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None or usuario.empresa_id != diagnostico.empresa_id:
            raise AccesoNoAutorizado()

        modelo = await self._modelos.obtener_por_version(diagnostico.modelo_version)
        if modelo is None:
            raise ValueError(
                "La versión del modelo aplicada a este diagnóstico ya no existe"
            )
        return modelo


class CompletarDiagnostico:
    """RF-07 paso 5: cierra la etapa de respuestas (borrador -> completado)
    una vez respondidas todas las obligatorias aplicables."""

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
        if usuario is None or usuario.empresa_id != diagnostico.empresa_id:
            raise AccesoNoAutorizado()

        diagnostico.marcar_completado()
        await self._diagnosticos.actualizar(diagnostico)
        return diagnostico


class ListarDiagnosticosDeEmpresa:
    """RF-11 paso 4: histórico de diagnósticos de la empresa."""

    def __init__(
        self, repo_diagnostico: RepositorioDiagnostico, repo_usuario: RepositorioUsuario
    ):
        self._diagnosticos = repo_diagnostico
        self._usuarios = repo_usuario

    async def ejecutar(self, usuario_id: str) -> list[Diagnostico]:
        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None or usuario.empresa_id is None:
            raise ValueError("El usuario no tiene una empresa asociada")
        return await self._diagnosticos.listar_por_empresa(usuario.empresa_id)
