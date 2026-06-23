from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    DashboardAPIView, 
    LogAuditoriaAPIView, 
    AnalisisIAView,
    DiagnosticoIAAPIView,
    TransaccionViewSet,
    SaldoPacienteView,
    GenerarComprobantePDFView,
    ReportePersonalizadoAPIView,
    MobileSaldoPacienteView,
    PasarelaPagoMobileAPIView,
    RegistroTokenFCMAPIView,
    VoiceToReportAPIView,
    ChatbotGlobalAPIView,
    ChatbotClinicaAPIView,
    ChatbotCitaAPIView,
    TranscribeAudioMobileAPIView,
    GenerarReporteMobileAPIView,
    AnaliticaClinicaAPIView,
    ReportePDFAPIView,
    ReporteCSVAPIView
)

router = SimpleRouter()
router.register(r'transacciones', TransaccionViewSet, basename='transaccion')

urlpatterns = [
    path("api/dashboard/", DashboardAPIView.as_view(), name="api_dashboard"),
    path("api/analitica-clinica/", AnaliticaClinicaAPIView.as_view(), name="api_analitica_clinica"),
    path("api/admin/auditoria/", LogAuditoriaAPIView.as_view(), name="api_admin_auditoria"),
    path("api/ia/analizar/<int:evolucion_id>/", AnalisisIAView.as_view(), name="api_ia_analizar"),
    path("api/ia/diagnostico/", DiagnosticoIAAPIView.as_view(), name="api_ia_diagnostico"),
    
    # Finanzas
    path("api/finanzas/", include(router.urls)),
    path("api/finanzas/saldo/<int:paciente_id>/", SaldoPacienteView.as_view(), name="api_saldo_paciente"),
    path("api/finanzas/comprobante/<int:transaccion_id>/pdf/", GenerarComprobantePDFView.as_view(), name="api_comprobante_pdf"),
    path("api/ia/reporte-pdf/", ReportePDFAPIView.as_view(), name="api_ia_reporte_pdf"),
    path("api/ia/reporte-csv/", ReporteCSVAPIView.as_view(), name="api_ia_reporte_csv"),
    path("api/reportes/personalizado/", ReportePersonalizadoAPIView.as_view(), name="api_reporte_personalizado"),
    path("api/reportes/voz/", VoiceToReportAPIView.as_view(), name="api_reportes_voz"),

    # Mobile Flutter Endpoints
    path("api/mobile/paciente/<int:paciente_id>/saldo/", MobileSaldoPacienteView.as_view(), name="api_mobile_saldo"),
    path("api/mobile/paciente/pagar/", PasarelaPagoMobileAPIView.as_view(), name="api_mobile_pagar"),
    path("api/mobile/notificaciones/registrar-token/", RegistroTokenFCMAPIView.as_view(), name="api_mobile_fcm_token"),

    # Mobile Flutter Chatbot
    path("api/mobile/chat/global/", ChatbotGlobalAPIView.as_view(), name="api_mobile_chat_global"),
    path("api/mobile/chat/clinica/<int:clinica_id>/", ChatbotClinicaAPIView.as_view(), name="api_mobile_chat_clinica"),
    path("api/mobile/chat/cita/<int:cita_id>/", ChatbotCitaAPIView.as_view(), name="api_mobile_chat_cita"),

    # IA por Voz para Móvil
    path("api/mobile/transcribe/", TranscribeAudioMobileAPIView.as_view(), name="api_mobile_transcribe"),
    path("api/mobile/generar-reporte/", GenerarReporteMobileAPIView.as_view(), name="api_mobile_generar_reporte"),
]
