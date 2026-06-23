from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from rest_framework import generics, viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .forms import PacienteForm
from .serializers import (
    PacienteSerializer, 
    HistoriaClinicaSerializer, 
    EvolucionClinicaSerializer,
    PacienteRegistroPublicoSerializer,
    NotaClinicaSerializer,
    ArchivoAdjuntoSerializer,
)
from .models import Paciente, HistoriaClinica, EvolucionClinica, NotaClinica, ArchivoAdjunto
from apps.P4_IA_Administracion.models import LogAuditoria
from apps.P1_Identidad_Acceso.permissions import (
    HasClinicaAsignada,
    EsPsicologoOAdministrador,
)


@login_required
def registrar_paciente_view(request):
    if not getattr(request.user, "clinica", None):
        messages.error(
            request,
            "ATENCIÓN: Tu cuenta actual no está asignada a ninguna clínica. No puedes registrar pacientes hasta tener una clínica.",
        )
        return redirect("dashboard")

    if request.method == "POST":
        form = PacienteForm(request.POST)
        if form.is_valid():
            paciente = form.save(commit=False)
            paciente.clinica = request.user.clinica
            paciente.save()
            LogAuditoria.objects.create(
                usuario=request.user,
                accion=f"Registró un nuevo paciente: {paciente.nombre}",
            )
            return redirect("dashboard")
    else:
        form = PacienteForm()
    return render(request, "P2_Gestion_Clinica/registrar_paciente.html", {"form": form})


@login_required
def editar_paciente_view(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk, clinica=request.user.clinica)
    if request.method == "POST":
        form = PacienteForm(request.POST, instance=paciente)
        if form.is_valid():
            paciente = form.save()
            LogAuditoria.objects.create(
                usuario=request.user,
                accion=f"Actualizó paciente: {paciente.nombre}",
            )
            return redirect("listar_pacientes")
    else:
        form = PacienteForm(instance=paciente)
    return render(
        request,
        "P2_Gestion_Clinica/editar_paciente.html",
        {"form": form, "paciente": paciente},
    )


@login_required
def listar_pacientes_view(request):
    pacientes = Paciente.objects.filter(clinica=request.user.clinica)
    return render(request, "P2_Gestion_Clinica/paciente_list.html", {"pacientes": pacientes})


class PacienteListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = PacienteSerializer
    permission_classes = [
        IsAuthenticated,
        EsPsicologoOAdministrador,
        HasClinicaAsignada,
    ]

    def get_queryset(self):
        queryset = Paciente.objects.filter(clinica=self.request.user.clinica).order_by("nombre")
        
        # T027: Búsqueda y Filtrado
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) | Q(ci__icontains=search)
            )
        return queryset

    def perform_create(self, serializer):
        clinica = self.request.user.clinica
        
        # SaaS Feature-Gating: No hay límites de pacientes en ningún plan.

        paciente = serializer.save(clinica=clinica)
        # Crear automáticamente la Historia Clínica (Expediente)
        HistoriaClinica.objects.get_or_create(paciente=paciente)
        
        LogAuditoria.objects.create(
            usuario=self.request.user,
            accion=f"Registró un nuevo paciente (API): {paciente.nombre}",
        )


class PacienteRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = PacienteSerializer
    permission_classes = [
        IsAuthenticated,
        EsPsicologoOAdministrador,
        HasClinicaAsignada,
    ]

    def get_queryset(self):
        return Paciente.objects.filter(clinica=self.request.user.clinica)

    def perform_update(self, serializer):
        paciente = serializer.save()
        LogAuditoria.objects.create(
            usuario=self.request.user,
            accion=f"Actualizó paciente (API): {paciente.nombre}",
        )

# --- Vistas para Historia Clínica y Evolución ---
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import re

class HistorialClinicoAPIView(APIView):
    permission_classes = [IsAuthenticated, EsPsicologoOAdministrador, HasClinicaAsignada]

    def get(self, request, pk):
        try:
            paciente = Paciente.objects.get(pk=pk, clinica=request.user.clinica)
        except Paciente.DoesNotExist:
            return Response({"detail": "No se encontró información del paciente."}, status=status.HTTP_404_NOT_FOUND)

        try:
            historia = HistoriaClinica.objects.get(paciente=paciente)
        except HistoriaClinica.DoesNotExist:
            historia = HistoriaClinica.objects.create(paciente=paciente)

        # Diagnóstico Global: Mapeo de Historia Clínica y Última Evolución
        evoluciones_qs = historia.evoluciones.all().order_by('-fecha_sesion')
        
        import json
        diagnostico_global = None
        if historia.diagnostico_preliminar or evoluciones_qs.exists():
            dx_text = historia.diagnostico_preliminar or "Sin diagnóstico preliminar"
            try:
                dx_data = json.loads(dx_text)
                diagnostico_global = {
                    "diagnostico_inicial": dx_data.get("diagnostico_inicial", ""),
                    "fecha_inicio": dx_data.get("fecha_inicio", historia.fecha_creacion.strftime('%Y-%m-%d')),
                    "estado": dx_data.get("estado", "EN_TRATAMIENTO"),
                    "estado_display": "En Tratamiento" if dx_data.get("estado") == "EN_TRATAMIENTO" else ("Alta" if dx_data.get("estado") == "ALTA" else "Suspendido"),
                    "diagnostico_final": dx_data.get("diagnostico_final", ""),
                    "fecha_fin": dx_data.get("fecha_fin", "")
                }
            except (json.JSONDecodeError, TypeError):
                diagnostico_global = {
                    "diagnostico_inicial": dx_text,
                    "fecha_inicio": historia.fecha_creacion.strftime('%Y-%m-%d'),
                    "estado": "EN_TRATAMIENTO",
                    "estado_display": "En Tratamiento",
                    "diagnostico_final": "",
                    "fecha_fin": ""
                }

        evoluciones_data = []
        for evo in evoluciones_qs:
            # Extraer campos parseando notas_sesion
            # Formato: [Estado: BUENO] Diagnóstico de Sesión: XYZ \n\nObservaciones: ABC
            estado_animo = "REGULAR"
            diagnostico = "Sin diagnóstico"
            observaciones = evo.notas_sesion

            m = re.match(r'^\[Estado: ([^\]]+)\] Diagnóstico de Sesión: (.*?)(?:\n\nObservaciones: (.*))?$', evo.notas_sesion, flags=re.DOTALL)
            if m:
                estado_animo = m.group(1).strip()
                diagnostico = m.group(2).strip()
                observaciones = m.group(3).strip() if m.group(3) else ""

            # Extraer recomendacion
            recomendacion = evo.recomendaciones.first()

            evoluciones_data.append({
                "id": evo.id,
                "fecha_sesion": evo.fecha_sesion.strftime('%Y-%m-%d %H:%M'),
                "estado_animo": estado_animo,
                "estado_animo_display": estado_animo.capitalize(),
                "psicologo_nombre": f"{evo.psicologo.first_name} {evo.psicologo.last_name}".strip() if evo.psicologo else "N/A",
                "diagnostico": diagnostico,
                "observaciones": observaciones,
                "recomendacion": recomendacion.texto if recomendacion else ""
            })

        data = {
            "paciente": {
                "nombre": paciente.nombre,
                "ci": paciente.ci,
                "fecha_nacimiento": paciente.fecha_nacimiento.strftime('%Y-%m-%d') if paciente.fecha_nacimiento else "",
                "telefono": paciente.telefono,
                "motivo_consulta": paciente.motivo_consulta
            },
            "diagnostico_global": diagnostico_global,
            "evoluciones": evoluciones_data
        }

        return Response(data, status=status.HTTP_200_OK)

class HistoriaClinicaViewSet(viewsets.ModelViewSet):
    serializer_class = HistoriaClinicaSerializer
    permission_classes = [IsAuthenticated, EsPsicologoOAdministrador, HasClinicaAsignada]

    def get_queryset(self):
        return HistoriaClinica.objects.filter(paciente__clinica=self.request.user.clinica)

class EvolucionClinicaViewSet(viewsets.ModelViewSet):
    serializer_class = EvolucionClinicaSerializer
    permission_classes = [IsAuthenticated, EsPsicologoOAdministrador, HasClinicaAsignada]

    def get_queryset(self):
        return EvolucionClinica.objects.filter(historia__paciente__clinica=self.request.user.clinica)

    def perform_create(self, serializer):
        evolucion = serializer.save(psicologo=self.request.user)
        
        recomendacion_texto = self.request.data.get('recomendacion', '').strip()
        if recomendacion_texto:
            from .models import Recomendacion
            from apps.P1_Identidad_Acceso.models import NotificacionPush, Usuario
            
            Recomendacion.objects.create(
                evolucion=evolucion,
                paciente=evolucion.historia.paciente,
                psicologo=self.request.user,
                texto=recomendacion_texto,
                estado='PENDIENTE'
            )
            
            # Notificar al paciente móvil (que coincida el CI)
            usuario_paciente = Usuario.objects.filter(ci=evolucion.historia.paciente.ci, rol='PACIENTE').first()
            if usuario_paciente:
                fecha_str = getattr(evolucion, 'fecha_sesion', None)
                if fecha_str:
                    fecha_str = fecha_str.strftime('%d/%m/%Y %H:%M')
                else:
                    from django.utils import timezone
                    fecha_str = timezone.now().strftime('%d/%m/%Y %H:%M')
                    
                clinica_nombre = self.request.user.clinica.nombre if getattr(self.request.user, 'clinica', None) else 'la Clínica'
                
                NotificacionPush.objects.create(
                    usuario=usuario_paciente,
                    titulo="Nueva Recomendación",
                    mensaje=f"El psicólogo {self.request.user.first_name} {self.request.user.last_name} de {clinica_nombre} te ha enviado una recomendación para la sesión del {fecha_str}."
                )

        LogAuditoria.objects.create(
            usuario=self.request.user,
            accion=f"Añadió nota de evolución para: {evolucion.historia.paciente.nombre}",
        )


class NotaClinicaAPIView(generics.ListCreateAPIView):
    """GET: listar notas del expediente. POST: crear nueva nota clínica (CU20)."""
    serializer_class = NotaClinicaSerializer
    permission_classes = [IsAuthenticated, EsPsicologoOAdministrador, HasClinicaAsignada]

    def get_queryset(self):
        expediente_id = self.request.query_params.get('expediente')
        qs = NotaClinica.objects.filter(
            expediente__paciente__clinica=self.request.user.clinica
        )
        if expediente_id:
            qs = qs.filter(expediente_id=expediente_id)
        return qs

    def perform_create(self, serializer):
        nota = serializer.save(psicologo=self.request.user)
        LogAuditoria.objects.create(
            usuario=self.request.user,
            accion=f"Registró nota clínica para: {nota.expediente.paciente.nombre}",
        )


class ArchivoAdjuntoAPIView(generics.ListCreateAPIView):
    """GET: listar archivos del expediente. POST: subir nuevo archivo adjunto (CU20)."""
    serializer_class = ArchivoAdjuntoSerializer
    permission_classes = [IsAuthenticated, EsPsicologoOAdministrador, HasClinicaAsignada]

    def get_queryset(self):
        expediente_id = self.request.query_params.get('expediente')
        qs = ArchivoAdjunto.objects.filter(
            expediente__paciente__clinica=self.request.user.clinica
        )
        if expediente_id:
            qs = qs.filter(expediente_id=expediente_id)
        return qs

    def perform_create(self, serializer):
        archivo = serializer.save(subido_por=self.request.user)
        LogAuditoria.objects.create(
            usuario=self.request.user,
            accion=f"Adjuntó archivo al expediente de: {archivo.expediente.paciente.nombre}",
        )

class PacienteRegistroPublicoAPIView(generics.CreateAPIView):
    """Endpoint público para que los pacientes se auto-registren desde la App Móvil."""
    serializer_class = PacienteRegistroPublicoSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            paciente = serializer.save()
            
            # Crear notificación de bienvenida
            from apps.P1_Identidad_Acceso.models import NotificacionPush, Usuario
            email = serializer.validated_data.get('email')
            if email:
                try:
                    usuario_obj = Usuario.objects.get(email=email)
                    NotificacionPush.objects.create(
                        usuario=usuario_obj,
                        titulo="Bienvenido a PsicoSystem",
                        mensaje="Gracias por registrarte. Ya puedes buscar clínicas y agendar tus citas."
                    )
                except Usuario.DoesNotExist:
                    pass
            
            return Response(
                {"message": "Registro exitoso. Ya puedes iniciar sesión."},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
