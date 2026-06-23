from django.http import HttpResponse, JsonResponse
import traceback

def debug_pacientes(request):
    try:
        from apps.P2_Gestion_Clinica.models import Paciente, HistoriaClinica, NotaClinica, ArchivoAdjunto
        from apps.P2_Gestion_Clinica.serializers import PacienteSerializer
        from django.db import connection
        
        results = {}
        
        # Try to serialize the exact queryset that the list view uses
        # The list view does: Paciente.objects.filter(clinica=user.clinica).order_by("nombre")
        # We will try to serialize EVERY patient to find which one crashes.
        pacientes = Paciente.objects.all()
        results['total_pacientes'] = pacientes.count()
        results['errors'] = []
        
        for p in pacientes:
            try:
                serializer = PacienteSerializer(p)
                data = serializer.data
            except Exception as e:
                results['errors'].append({
                    'paciente_id': p.id,
                    'paciente_nombre': p.nombre,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
        
        # Check P4_IA_Administracion models since there's a migration warning
        from apps.P4_IA_Administracion.models import LogAuditoria
        try:
            results['log_count'] = LogAuditoria.objects.count()
        except Exception as e:
            results['log_error'] = str(e)
            
        return JsonResponse(results, json_dumps_params={'indent': 2})
    except Exception as e:
        return HttpResponse("FATAL ERROR:\n" + traceback.format_exc(), status=500, content_type='text/plain')
