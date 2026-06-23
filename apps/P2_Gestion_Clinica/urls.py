from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    PacienteListCreateAPIView,
    PacienteRetrieveUpdateAPIView,
    PacienteRegistroPublicoAPIView,
    HistoriaClinicaViewSet,
    EvolucionClinicaViewSet,
    HistorialClinicoAPIView,
    NotaClinicaAPIView,
    ArchivoAdjuntoAPIView,
)

from apps.P2_Gestion_Clinica.debug_view import debug_pacientes

router = SimpleRouter()
router.register(r'historias', HistoriaClinicaViewSet, basename='historia')
router.register(r'evoluciones', EvolucionClinicaViewSet, basename='evolucion')

urlpatterns = [
    path("api/pacientes/", PacienteListCreateAPIView.as_view(), name="api_pacientes"),
    path(
        "api/pacientes/<int:pk>/",
        PacienteRetrieveUpdateAPIView.as_view(),
        name="api_pacientes_detalle",
    ),
    path(
        "api/pacientes/<int:pk>/historial/",
        HistorialClinicoAPIView.as_view(),
        name="api_pacientes_historial",
    ),
    path("api/pacientes/registro-publico/",
        PacienteRegistroPublicoAPIView.as_view(),
        name="api_pacientes_registro_publico",
    ),
    path("api/clinica/notas-clinicas/", NotaClinicaAPIView.as_view(), name="api_notas_clinicas"),
    path("api/clinica/archivos-adjuntos/", ArchivoAdjuntoAPIView.as_view(), name="api_archivos_adjuntos"),
    path("api/debug/pacientes/", debug_pacientes),
    path("api/", include(router.urls)),
]
