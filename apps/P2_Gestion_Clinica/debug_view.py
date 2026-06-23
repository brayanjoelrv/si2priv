from django.http import HttpResponse, JsonResponse
import traceback
import json

def debug_pacientes(request):
    """Debug view to simulate patient creation to catch the 500 error."""
    try:
        from apps.P2_Gestion_Clinica.models import Paciente, HistoriaClinica
        from apps.P1_Identidad_Acceso.models import Clinica, Usuario
        from apps.P4_IA_Administracion.models import LogAuditoria
        
        # 1. Get the admin user and clinica
        user = Usuario.objects.filter(username='admin').first() or Usuario.objects.first()
        clinica = user.clinica if user else Clinica.objects.first()
        
        if not clinica:
            return JsonResponse({'error': 'No clinica found'})
        
        # 2. Try to create a dummy patient
        import random
        ci_dummy = str(random.randint(1000000, 9999999))
        paciente = Paciente(
            nombre='Test Simulation',
            ci=ci_dummy,
            fecha_nacimiento='2000-01-01',
            telefono='12345678',
            clinica=clinica
        )
        paciente.save()
        
        # 3. Create HistoriaClinica
        HistoriaClinica.objects.get_or_create(paciente=paciente)
        
        # 4. Create LogAuditoria
        LogAuditoria.objects.create(
            usuario=user,
            accion=f"Registró un nuevo paciente (API): {paciente.nombre}",
        )
        
        # 5. Serialize
        from apps.P2_Gestion_Clinica.serializers import PacienteSerializer
        serializer = PacienteSerializer(paciente)
        data = serializer.data
        
        # Cleanup
        paciente.delete()
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return HttpResponse("FATAL ERROR:\n" + traceback.format_exc(), status=500, content_type='text/plain')
