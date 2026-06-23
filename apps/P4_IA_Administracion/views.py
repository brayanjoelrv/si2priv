import os
import datetime
import uuid
import base64
import requests
import io
from decimal import Decimal
from django.db.models import Sum, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import viewsets, status, generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from gtts import gTTS
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import openpyxl

from apps.P1_Identidad_Acceso.models import Usuario, DispositivoMovil, TransaccionClinica
from apps.P1_Identidad_Acceso.permissions import (
    HasClinicaAsignada, EsAdministrador, EsPsicologoOAdministrador, 
    RequiresModuloContabilidad, RequiresModuloIA, RequiresModuloAuditoria, EsPaciente
)
from apps.P2_Gestion_Clinica.models import Paciente, EvolucionClinica
from apps.P3_Logistica_Citas.models import Cita
from .models import LogAuditoria, Transaccion, Comprobante
from .serializers import TransaccionSerializer, ComprobanteSerializer, LogAuditoriaSerializer
from .services.ai_service import AIService

class LogAuditoriaAPIView(generics.ListAPIView):
    """
    Endpoint de bitácora exclusivo para el Administrador de la clínica, o Psicólogos para ver trazabilidad de pacientes.
    """
    serializer_class = LogAuditoriaSerializer
    permission_classes = [IsAuthenticated, HasClinicaAsignada, EsPsicologoOAdministrador, RequiresModuloAuditoria]

    def get_queryset(self):
        return LogAuditoria.objects.filter(clinica=self.request.user.clinica).order_by('-fecha')

class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated, HasClinicaAsignada]

    def get(self, request):
        clinica = request.user.clinica
        total_pacientes = Paciente.objects.filter(clinica=clinica).count() if clinica else 0
        citas_pendientes = Cita.objects.filter(
            paciente__clinica=clinica, estado="PENDIENTE"
        ).count() if clinica else 0

        data = {
            "clinica": clinica.nombre if clinica else "Sin Clínica",
            "metricas": {
                "total_pacientes": total_pacientes,
                "citas_pendientes": citas_pendientes,
            },
        }
        return Response(data, status=status.HTTP_200_OK)

class AnaliticaClinicaAPIView(APIView):
    """
    Endpoint para el Dashboard de Analítica Clínica (CU22 - T071).
    Provee métricas sobre tratamientos, IA y estados de ánimo.
    """
    permission_classes = [IsAuthenticated, HasClinicaAsignada, EsPsicologoOAdministrador]

    def get(self, request):
        clinica = request.user.clinica
        
        # 1. Total Pacientes
        total_pacientes = Paciente.objects.filter(clinica=clinica).count() if clinica else 0
        
        # 2. Distribución de Estados Real
        from apps.P2_Gestion_Clinica.models import HistoriaClinica
        import json

        en_tratamiento = 0
        alta = 0
        abandono = 0
        sin_diagnostico = 0

        historias = HistoriaClinica.objects.filter(paciente__clinica=clinica)
        pacientes_con_historia = set()

        for hist in historias:
            pacientes_con_historia.add(hist.paciente_id)
            estado = None
            if hist.diagnostico_preliminar:
                try:
                    dx_data = json.loads(hist.diagnostico_preliminar)
                    if isinstance(dx_data, dict):
                        estado = dx_data.get('estado')
                except (json.JSONDecodeError, TypeError):
                    estado = 'EN_TRATAMIENTO'
            
            if not estado and hist.evoluciones.exists():
                estado = 'EN_TRATAMIENTO'

            estado_upper = str(estado).upper() if estado else ''
            
            if estado_upper == 'ALTA':
                alta += 1
            elif estado_upper == 'ABANDONO':
                abandono += 1
            elif estado_upper == 'EN_TRATAMIENTO' or estado_upper == 'EN TRATAMIENTO':
                en_tratamiento += 1
            else:
                sin_diagnostico += 1

        # Contabilizar pacientes que ni siquiera tienen historia
        sin_diagnostico += total_pacientes - len(pacientes_con_historia)

        # 3. Evoluciones Reales
        evoluciones = EvolucionClinica.objects.filter(
            historia__paciente__clinica=clinica
        ).order_by('-fecha_sesion')[:5]

        ultimas_evoluciones = []
        for evo in evoluciones:
            ultimas_evoluciones.append({
                "id": evo.id,
                "fecha_sesion": evo.fecha_sesion.strftime("%Y-%m-%d"),
                "estado_animo": "BUENO", # Simulado
                "estado_animo_display": "Bueno",
                "diagnostico": "Evaluación Psicológica", 
                "recomendacion": "Continuar tratamiento",
                "psicologo_nombre": evo.psicologo.get_full_name() if evo.psicologo else "N/A"
            })

        # 4. Análisis IA
        ia_records = EvolucionClinica.objects.filter(
            historia__paciente__clinica=clinica
        ).exclude(analisis_ia='').order_by('-fecha_sesion')[:5]

        ultimos_ia = []
        for ia in ia_records:
            ultimos_ia.append({
                "id": ia.id,
                "fecha_analisis": ia.fecha_sesion.strftime("%Y-%m-%d"),
                "paciente__nombre": ia.historia.paciente.nombre,
                "resultado_ia": ia.analisis_ia[:100] + "..." if len(ia.analisis_ia) > 100 else ia.analisis_ia,
                "probabilidad_acierto": 0.95
            })

        data = {
            "total_pacientes": total_pacientes,
            "en_tratamiento": en_tratamiento,
            "alta": alta,
            "abandono": abandono,
            "sin_diagnostico": sin_diagnostico,
            "estados_animo": [
                {"estado_animo": "BUENO", "total": int(en_tratamiento * 0.5)},
                {"estado_animo": "REGULAR", "total": int(en_tratamiento * 0.3)},
                {"estado_animo": "MALO", "total": int(en_tratamiento * 0.2)}
            ],
            "ultimas_evoluciones": ultimas_evoluciones,
            "ultimos_ia": ultimos_ia
        }

        return Response(data, status=status.HTTP_200_OK)

# --- Módulo Financiero ---

class TransaccionViewSet(viewsets.ModelViewSet):
    serializer_class = TransaccionSerializer
    permission_classes = [IsAuthenticated, HasClinicaAsignada, EsPsicologoOAdministrador, RequiresModuloContabilidad]

    def get_queryset(self):
        return Transaccion.objects.filter(paciente__clinica=self.request.user.clinica)

    def perform_create(self, serializer):
        transaccion = serializer.save()
        LogAuditoria.objects.create(
            usuario=self.request.user,
            accion=f"Registró transacción ({transaccion.tipo}) de {transaccion.monto} para {transaccion.paciente.nombre}"
        )

class SaldoPacienteView(APIView):
    """
    Calcula el saldo actual (deuda) de un paciente.
    """
    permission_classes = [IsAuthenticated, HasClinicaAsignada, EsPsicologoOAdministrador, RequiresModuloContabilidad]

    def get(self, request, paciente_id):
        paciente = get_object_or_404(Paciente, id=paciente_id, clinica=request.user.clinica)
        
        pagos = Transaccion.objects.filter(paciente=paciente, tipo='PAGO').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        deudas = Transaccion.objects.filter(paciente=paciente, tipo='DEUDA').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        ajustes = Transaccion.objects.filter(paciente=paciente, tipo='AJUSTE').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        saldo = deudas - pagos + ajustes
        
        return Response({
            "paciente": paciente.nombre,
            "total_pagado": pagos,
            "total_deuda_acumulada": deudas,
            "saldo_pendiente": saldo
        }, status=status.HTTP_200_OK)

class GenerarComprobantePDFView(APIView):
    """
    Genera un PDF de comprobante para una transacción de pago.
    """
    permission_classes = [IsAuthenticated, HasClinicaAsignada, EsPsicologoOAdministrador, RequiresModuloContabilidad]

    def get(self, request, transaccion_id):
        transaccion = get_object_or_404(
            Transaccion, 
            id=transaccion_id, 
            paciente__clinica=request.user.clinica,
            tipo='PAGO'
        )
        
        # Lógica simplificada de PDF usando reportlab
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)
        
        p.drawString(100, 800, f"PsicoSystem - Comprobante de Pago")
        p.drawString(100, 780, f"Clínica: {request.user.clinica.nombre}")
        p.drawString(100, 750, f"Paciente: {transaccion.paciente.nombre}")
        p.drawString(100, 730, f"Fecha: {transaccion.fecha.strftime('%Y-%m-%d %H:%M')}")
        p.drawString(100, 710, f"Monto: {transaccion.monto} BOB")
        p.drawString(100, 690, f"Descripción: {transaccion.descripcion}")
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf')

# --- IA Diagnostics ---

class AnalisisIAView(APIView):
    """
    Endpoint para disparar el análisis de IA llamando al Microservicio FastAPI.
    """
    permission_classes = [IsAuthenticated, HasClinicaAsignada, EsPsicologoOAdministrador, RequiresModuloIA]

    def post(self, request, evolucion_id):
        evolucion = get_object_or_404(
            EvolucionClinica, 
            id=evolucion_id, 
            historia__paciente__clinica=request.user.clinica
        )
        
        if not evolucion.notas_sesion:
            return Response(
                {"error": "La nota de sesión está vacía."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Llamada al Microservicio Externo
        try:
            response = requests.post(
                "http://127.0.0.1:8001/api/v1/analyze",
                json={"notas": evolucion.notas_sesion},
                timeout=5
            )
            response.raise_for_status()
            resultado = response.json()
            evolucion.analisis_ia = str(resultado)
            evolucion.save()
        except Exception as e:
            return Response(
                {"error": f"Error del Microservicio de IA: {str(e)}"}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        LogAuditoria.objects.create(
            usuario=request.user,
            accion=f"Ejecutó análisis de IA (Vía Microservicio) para la sesión de: {evolucion.historia.paciente.nombre}"
        )

        return Response({"analisis_ia": resultado}, status=status.HTTP_200_OK)

class DiagnosticoIAAPIView(APIView):
    """
    Endpoint para análisis de IA ad-hoc en el dashboard de IA (Soporta historial).
    """
    permission_classes = [IsAuthenticated, HasClinicaAsignada, EsPsicologoOAdministrador]

    def get(self, request):
        # Retorna el historial de los últimos análisis IA realizados por este usuario/clínica
        ia_records = EvolucionClinica.objects.filter(
            historia__paciente__clinica=request.user.clinica
        ).exclude(analisis_ia='').order_by('-fecha_sesion')[:10]

        historial = []
        for ia in ia_records:
            historial.append({
                "id": ia.id,
                "paciente": ia.historia.paciente.nombre,
                "fecha_analisis": ia.fecha_sesion.strftime("%Y-%m-%d %H:%M"),
                "resultado_ia": ia.analisis_ia
            })
        return Response(historial, status=status.HTTP_200_OK)

    def post(self, request):
        notas = request.data.get('notas', '').strip()
        paciente_id = request.data.get('paciente_id')

        if not notas:
            return Response({"detail": "Las notas clínicas no pueden estar vacías."}, status=status.HTTP_400_BAD_REQUEST)

        # Lógica temporal o simulación de Gemini/Groq
        # En una integración real aquí se llama a Groq/Gemini API
        diagnostico_simulado = f"""### Análisis Clínico Asistido por IA

**Impresión Diagnóstica Preliminar:**
Basado en los síntomas descritos: "{notas[:50]}...", se sugiere evaluar un cuadro compatible con malestar general u otra afección primaria. 

**Recomendaciones:**
- Se requiere evaluación presencial.
- Considerar derivación a especialista si persisten los síntomas.

*Nota: Este diagnóstico es generado por IA y debe ser verificado por un profesional de la salud.*"""

        # Si mandaron ID de paciente, tratamos de guardar el análisis en su última evolución
        if paciente_id:
            try:
                paciente = Paciente.objects.get(id=paciente_id, clinica=request.user.clinica)
                ultima_evo = EvolucionClinica.objects.filter(historia__paciente=paciente).order_by('-fecha_sesion').first()
                if ultima_evo:
                    ultima_evo.analisis_ia = diagnostico_simulado
                    ultima_evo.save()
            except Paciente.DoesNotExist:
                pass

        LogAuditoria.objects.create(
            usuario=request.user,
            accion="Ejecutó un diagnóstico ad-hoc asistido por IA."
        )

        return Response({"diagnostico_ia": diagnostico_simulado}, status=status.HTTP_200_OK)

class ReportePersonalizadoAPIView(APIView):
    """
    Genera un reporte personalizado por rango de fechas y opcionalmente un archivo de audio (MP3).
    """
    permission_classes = [IsAuthenticated, HasClinicaAsignada, EsAdministrador]

    def post(self, request):
        fecha_inicio = request.data.get('fecha_inicio')
        fecha_fin = request.data.get('fecha_fin')
        generar_audio = request.data.get('generar_audio', True)

        if not fecha_inicio or not fecha_fin:
            return Response({"error": "Debe proveer fecha_inicio y fecha_fin (YYYY-MM-DD)"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            inicio = datetime.datetime.strptime(fecha_inicio, '%Y-%m-%d')
            fin = datetime.datetime.strptime(fecha_fin, '%Y-%m-%d')
            # Ajustar el fin de día para incluir todo el día
            fin = fin.replace(hour=23, minute=59, second=59)
        except ValueError:
            return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        clinica = request.user.clinica

        # Consultas
        pacientes_nuevos = Paciente.objects.filter(clinica=clinica, fecha_registro__range=(inicio, fin)).count()
        
        pagos = Transaccion.objects.filter(
            paciente__clinica=clinica, 
            fecha__range=(inicio, fin), 
            tipo='PAGO'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        
        deudas = Transaccion.objects.filter(
            paciente__clinica=clinica, 
            fecha__range=(inicio, fin), 
            tipo='DEUDA'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        # Generar Texto del Reporte
        texto_reporte = (
            f"Reporte ejecutivo de la clínica {clinica.nombre}. "
            f"Desde el {inicio.strftime('%d de %B de %Y')} hasta el {fin.strftime('%d de %B de %Y')}. "
            f"Durante este período se registraron {pacientes_nuevos} pacientes nuevos. "
            f"El total de ingresos por pagos de sesiones fue de {pagos} bolivianos. "
            f"Y el total de deuda acumulada o cargos pendientes fue de {deudas} bolivianos. "
            f"Fin del reporte."
        )

        audio_url = None
        if generar_audio:
            try:
                # Usar gTTS para generar el audio en español
                tts = gTTS(text=texto_reporte, lang='es', tld='com.mx')
                
                # Crear directorio si no existe
                reportes_dir = os.path.join(settings.MEDIA_ROOT, 'reportes_audio')
                if not os.path.exists(reportes_dir):
                    os.makedirs(reportes_dir)
                    
                timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"reporte_{clinica.id}_{timestamp}.mp3"
                filepath = os.path.join(reportes_dir, filename)
                
                tts.save(filepath)
                audio_url = settings.MEDIA_URL + f"reportes_audio/{filename}"
            except Exception as e:
                # Si falla el audio, retornamos el texto igual
                print(f"Error generando audio TTS: {e}")

        # Auditoria
        LogAuditoria.objects.create(
            usuario=request.user,
            accion=f"Generó un reporte personalizado del {fecha_inicio} al {fecha_fin} (Audio: {generar_audio})"
        )

        return Response({
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "texto": texto_reporte,
            "audio_url": audio_url
        }, status=status.HTTP_200_OK)

class MobileSaldoPacienteView(APIView):
    """
    Endpoint para que la app móvil (Flutter) consulte la deuda del paciente.
    """
    permission_classes = [IsAuthenticated, EsPaciente]

    def get(self, request, paciente_id):
        paciente = get_object_or_404(Paciente, id=paciente_id)
        
        pagos = Transaccion.objects.filter(paciente=paciente, tipo='PAGO').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        deudas = Transaccion.objects.filter(paciente=paciente, tipo='DEUDA').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        ajustes = Transaccion.objects.filter(paciente=paciente, tipo='AJUSTE').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        saldo = deudas - pagos + ajustes
        
        return Response({
            "paciente_id": paciente.id,
            "paciente_nombre": paciente.nombre,
            "total_pagado": pagos,
            "total_deuda_acumulada": deudas,
            "saldo_pendiente": saldo
        }, status=status.HTTP_200_OK)

class PasarelaPagoMobileAPIView(APIView):
    """
    Endpoint que simula la pasarela de pagos para la aplicación Flutter.
    """
    permission_classes = [IsAuthenticated, EsPaciente]

    def post(self, request):
        paciente_id = request.data.get('paciente_id')
        monto = request.data.get('monto')
        metodo_pago = request.data.get('metodo_pago', 'TARJETA')
        numero_tarjeta = request.data.get('numero_tarjeta', '')

        if not paciente_id or not monto:
            return Response({"error": "Debe proveer paciente_id y monto."}, status=status.HTTP_400_BAD_REQUEST)

        # Validación MUY básica para facilitar las pruebas del Frontend
        # En la vida real, aquí se llamaría a la API de Stripe o PayPal.
        if len(str(numero_tarjeta)) < 4:
            return Response({"error": "La tarjeta debe tener al menos 4 números para ser procesada."}, status=status.HTTP_400_BAD_REQUEST)

        paciente = get_object_or_404(Paciente, id=paciente_id)

        try:
            monto_decimal = Decimal(str(monto))
        except:
            return Response({"error": "Monto inválido."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Registrar la transacción de Pago
        transaccion = Transaccion.objects.create(
            paciente=paciente,
            monto=monto_decimal,
            tipo='PAGO',
            descripcion=f"Pago Móvil via {metodo_pago} (****{numero_tarjeta[-4:]})"
        )

        # 2. Generar el Comprobante automáticamente
        nro_comp = f"MOB-{uuid.uuid4().hex[:8].upper()}"
        comprobante = Comprobante.objects.create(
            transaccion=transaccion,
            nro_comprobante=nro_comp
        )

        # 3. Incrementar el saldo de la clínica (Ingreso SaaS)
        clinica = paciente.clinica
        if clinica:
            clinica.saldo += monto_decimal
            clinica.save()
            
            # Registrar el movimiento en el historial de facturación de la clínica
            TransaccionClinica.objects.create(
                clinica=clinica,
                tipo='INGRESO_PACIENTE',
                monto=monto_decimal,
                descripcion=f"Ingreso por Pago Móvil: Paciente {paciente.nombre} (ID {paciente.id})",
                metodo_pago=metodo_pago
            )

        # 4. Auditoria
        LogAuditoria.objects.create(
            usuario=request.user,
            accion=f"Pago móvil registrado ({monto_decimal} BOB) para el paciente {paciente.nombre}. El saldo de la clínica ha sido incrementado."
        )

        # 5. Enviar Notificación Push (Simulada para la Defensa)
        dispositivos = DispositivoMovil.objects.filter(usuario=request.user)
        for dispositivo in dispositivos:
            # Aquí iría la lógica real de firebase-admin. Ej: messaging.send(...)
            print(f"\n[FIREBASE PUSH SIMULATOR] Enviando notificación de Pago Exitoso al token: {dispositivo.fcm_token}")
            print(f"[FIREBASE PUSH SIMULATOR] Titulo: Pago Aprobado")
            print(f"[FIREBASE PUSH SIMULATOR] Cuerpo: Su pago de {monto_decimal} BOB ha sido procesado con éxito.\n")

        return Response({
            "mensaje": "Pago procesado exitosamente por la pasarela virtual.",
            "transaccion_id": transaccion.id,
            "comprobante": nro_comp,
            "monto_pagado": monto_decimal
        }, status=status.HTTP_201_CREATED)


class RegistroTokenFCMAPIView(APIView):
    """
    Registra el token de dispositivo (Firebase Cloud Messaging) para enviar notificaciones Push.
    """
    permission_classes = [IsAuthenticated, EsPaciente]

    def post(self, request):
        fcm_token = request.data.get('fcm_token')

        if not fcm_token:
            return Response({"error": "Debe proveer fcm_token"}, status=status.HTTP_400_BAD_REQUEST)

        # Actualizar o crear el dispositivo para este usuario
        dispositivo, created = DispositivoMovil.objects.update_or_create(
            usuario=request.user,
            defaults={'fcm_token': fcm_token}
        )

        return Response({
            "mensaje": "Token registrado exitosamente para notificaciones Push.",
            "fcm_token": dispositivo.fcm_token
        }, status=status.HTTP_200_OK)



class VoiceToReportAPIView(APIView):
    """
    Endpoint híbrido que recibe texto de voz, extrae filtros con IA (Gemini) 
    y genera un reporte en PDF.
    """
    permission_classes = [IsAuthenticated, HasClinicaAsignada, EsAdministrador]

    def post(self, request):
        transcript = request.data.get('transcript', '')
        if not transcript:
            return Response({"error": "No se recibió texto de voz."}, status=status.HTTP_400_BAD_REQUEST)

        clinica = request.user.clinica

        # 1. IA extrae filtros
        filtros = AIService.interpretar_comando_voz(transcript)
        if "error" in filtros:
            return Response(filtros, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2. Aplicar filtros ORM
        citas_query = Cita.objects.filter(paciente__clinica=clinica)
        transacciones_query = Transaccion.objects.filter(paciente__clinica=clinica)

        if filtros.get('fecha_inicio'):
            citas_query = citas_query.filter(fecha_hora__date__gte=filtros['fecha_inicio'])
            transacciones_query = transacciones_query.filter(fecha__date__gte=filtros['fecha_inicio'])
        
        if filtros.get('fecha_fin'):
            citas_query = citas_query.filter(fecha_hora__date__lte=filtros['fecha_fin'])
            transacciones_query = transacciones_query.filter(fecha__date__lte=filtros['fecha_fin'])

        if filtros.get('estado_cita'):
            citas_query = citas_query.filter(estado=filtros['estado_cita'].upper())

        if filtros.get('monto_min'):
            transacciones_query = transacciones_query.filter(monto__gte=filtros['monto_min'])
        
        if filtros.get('monto_max'):
            transacciones_query = transacciones_query.filter(monto__lte=filtros['monto_max'])

        psicologo_top = None
        if filtros.get('top_psicologo'):
            top = citas_query.values('psicologo').annotate(total=Count('id')).order_by('-total').first()
            if top:
                user = Usuario.objects.filter(id=top['psicologo']).first()
                if user:
                    psicologo_top = f"{user.get_full_name() or user.username} ({top['total']} citas)"

        # 3. Generar PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph(f"Reporte Generado por IA - PsicoSystem", styles['Title']))
        elements.append(Paragraph(f"Clínica: {clinica.nombre}", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        filtro_str = f"Filtros aplicados: {filtros}"
        elements.append(Paragraph(filtro_str, styles['Normal']))
        elements.append(Spacer(1, 12))

        if psicologo_top:
            elements.append(Paragraph(f"Psicólogo Destacado: {psicologo_top}", styles['Heading2']))
            elements.append(Spacer(1, 12))

        # Tabla de Citas
        data = [["Paciente", "Psicólogo", "Fecha", "Estado"]]
        for c in citas_query[:50]: # Limitar a 50 para el pdf demo
            data.append([
                c.paciente.nombre[:20], 
                c.psicologo.username, 
                c.fecha_hora.strftime("%Y-%m-%d %H:%M"), 
                c.estado
            ])
        
        if len(data) > 1:
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph("No se encontraron citas con estos filtros.", styles['Normal']))

        doc.build(elements)
        
        pdf_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()

        # Auditoria
        LogAuditoria.objects.create(
            usuario=request.user,
            accion=f"Generó un reporte por IA. Filtros: {filtros}"
        )

        return Response({
            "filtros": filtros,
            "pdf_base64": pdf_base64
        }, status=status.HTTP_200_OK)

class TranscribeAudioMobileAPIView(APIView):
    """
    Recibe un archivo de audio del paciente y devuelve el texto transcrito.
    """
    permission_classes = [IsAuthenticated, EsPaciente]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({"error": "No se recibió archivo de audio."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Pasar los bytes al servicio de transcripción de Groq
        resultado = AIService.transcribir_audio_groq(audio_file.read(), audio_file.name)
        if "error" in resultado:
            return Response(resultado, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        return Response({"transcription": resultado["text"]}, status=status.HTTP_200_OK)

class GenerarReporteMobileAPIView(APIView):
    """
    Recibe el texto revisado por el paciente, extrae filtros con IA y genera PDF/Excel en Base64.
    """
    permission_classes = [IsAuthenticated, EsPaciente]

    def post(self, request):
        transcript = request.data.get('transcript', '')
        if not transcript:
            return Response({"error": "No se proporcionó texto transcrito."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. IA extrae filtros
        filtros = AIService.interpretar_comando_voz(transcript)
        if "error" in filtros:
            return Response(filtros, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        paciente = request.user.paciente

        # 2. Aplicar filtros ORM
        citas_query = Cita.objects.filter(paciente=paciente)
        transacciones_query = Transaccion.objects.filter(paciente=paciente)

        if filtros.get('fecha_inicio'):
            citas_query = citas_query.filter(fecha_hora__date__gte=filtros['fecha_inicio'])
            transacciones_query = transacciones_query.filter(fecha__date__gte=filtros['fecha_inicio'])
        
        if filtros.get('fecha_fin'):
            citas_query = citas_query.filter(fecha_hora__date__lte=filtros['fecha_fin'])
            transacciones_query = transacciones_query.filter(fecha__date__lte=filtros['fecha_fin'])

        if filtros.get('estado_cita'):
            citas_query = citas_query.filter(estado=filtros['estado_cita'].upper())

        # Generar PDF en memoria
        buffer_pdf = io.BytesIO()
        doc = SimpleDocTemplate(buffer_pdf, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph(f"Historial de Pagos y Citas - {paciente.nombre}", styles['Title']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Filtros aplicados según tu petición: {filtros}", styles['Normal']))
        elements.append(Spacer(1, 12))

        # Tabla de Pagos
        elements.append(Paragraph("Pagos Registrados", styles['Heading2']))
        data_pagos = [["Fecha", "Concepto", "Monto", "Estado"]]
        
        for t in transacciones_query[:50]:
            data_pagos.append([
                t.fecha.strftime("%Y-%m-%d"), 
                t.descripcion[:30], 
                str(t.monto), 
                t.tipo
            ])
            
        if len(data_pagos) > 1:
            table_pagos = Table(data_pagos, colWidths=[80, 200, 80, 80])
            table_pagos.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table_pagos)
        else:
            elements.append(Paragraph("No se encontraron pagos en esta fecha.", styles['Normal']))

        elements.append(Spacer(1, 12))

        # Tabla de Citas
        elements.append(Paragraph("Citas Relacionadas", styles['Heading2']))
        data_citas = [["Clínica", "Psicólogo", "Fecha", "Estado"]]
        
        for c in citas_query[:50]:
            data_citas.append([
                c.paciente.clinica.nombre[:20] if c.paciente.clinica else "N/A", 
                c.psicologo.get_full_name(), 
                c.fecha_hora.strftime("%Y-%m-%d %H:%M"), 
                c.estado
            ])
            
        if len(data_citas) > 1:
            table_citas = Table(data_citas)
            table_citas.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table_citas)
        else:
            elements.append(Paragraph("No se encontraron citas en esta fecha.", styles['Normal']))

        doc.build(elements)
        pdf_base64 = base64.b64encode(buffer_pdf.getvalue()).decode('utf-8')
        buffer_pdf.close()

        # Generar Excel en memoria
        wb = openpyxl.Workbook()
        ws_pagos = wb.active
        ws_pagos.title = "Pagos"
        
        ws_pagos.append(["Fecha", "Concepto", "Monto", "Estado"])
        for t in transacciones_query:
            ws_pagos.append([t.fecha.strftime("%Y-%m-%d"), t.descripcion, float(t.monto), t.tipo])

        ws_citas = wb.create_sheet(title="Citas")
        ws_citas.append(["Clínica", "Psicólogo", "Fecha", "Estado", "Motivo"])
        for c in citas_query:
            ws_citas.append([
                c.paciente.clinica.nombre if c.paciente.clinica else "N/A", 
                c.psicologo.get_full_name(), 
                c.fecha_hora.strftime("%Y-%m-%d %H:%M"), 
                c.estado,
                c.motivo
            ])

        buffer_excel = io.BytesIO()
        wb.save(buffer_excel)
        excel_base64 = base64.b64encode(buffer_excel.getvalue()).decode('utf-8')
        buffer_excel.close()

        LogAuditoria.objects.create(
            usuario=request.user,
            accion=f"Generó Reportes PDF y Excel desde App Móvil por voz. Filtros interpretados: {filtros}"
        )

        return Response({
            "filtros_detectados": filtros,
            "pdf_base64": pdf_base64,
            "excel_base64": excel_base64
        }, status=status.HTTP_200_OK)

# ==============================================================================
# CHATBOTS PARA MÓVIL
# ==============================================================================

class ChatbotGlobalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        mensaje = request.data.get("mensaje", "")
        
        context_prompt = (
            "Eres 'Chatsito', el asistente inteligente de la plataforma PsicoSystem. "
            "Tu objetivo es ayudar al usuario de manera amigable, profesional y empática. "
            "Responde de forma concisa. No superes los 2 párrafos."
        )
        
        respuesta = AIService.responder_chatbot(context_prompt, mensaje)
        return Response({"respuesta": respuesta}, status=status.HTTP_200_OK)

class ChatbotClinicaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, clinica_id):
        from apps.P1_Identidad_Acceso.models import Clinica
        mensaje = request.data.get("mensaje", "")
        clinica = get_object_or_404(Clinica, id=clinica_id)
        
        context_prompt = (
            f"Eres el asistente virtual de la clínica '{clinica.nombre}'. "
            f"La clínica atiende en los horarios: {clinica.horarios_atencion}. "
            f"Ofrece las siguientes especialidades: {clinica.especialidades}. "
            f"El número de contacto es {clinica.telefono}. "
            "Responde a las preguntas del paciente de manera amigable, usando esta información. Sé breve."
        )
        
        respuesta = AIService.responder_chatbot(context_prompt, mensaje)
        return Response({"respuesta": respuesta}, status=status.HTTP_200_OK)

class ChatbotCitaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, cita_id):
        from apps.P3_Logistica_Citas.models import Cita
        mensaje = request.data.get("mensaje", "")
        cita = get_object_or_404(Cita, id=cita_id)
        
        context_prompt = (
            f"Eres un asistente para una cita psicológica específica. "
            f"El paciente tiene cita con el/la profesional {cita.psicologo.first_name} {cita.psicologo.last_name}. "
            f"La fecha y hora programada es {cita.fecha_hora.strftime('%d/%m/%Y %H:%M')}. "
            f"El motivo de la consulta indicado es: '{cita.motivo}'. "
            f"El estado de la cita es {cita.estado}. "
            "Responde dudas sobre esta cita concreta de forma tranquilizadora y profesional. "
            "Puedes sugerir llegar 10 minutos antes. Sé breve."
        )
        
        respuesta = AIService.responder_chatbot(context_prompt, mensaje)
        return Response({"respuesta": respuesta}, status=status.HTTP_200_OK)
