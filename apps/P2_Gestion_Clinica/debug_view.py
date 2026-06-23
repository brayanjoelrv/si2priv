from django.http import HttpResponse, JsonResponse
import traceback
import json

def debug_pacientes(request):
    """Debug view to diagnose the 500 error on /api/pacientes/."""
    try:
        from apps.P2_Gestion_Clinica.models import Paciente, HistoriaClinica, NotaClinica, ArchivoAdjunto
        from apps.P2_Gestion_Clinica.serializers import PacienteSerializer
        from django.db import connection
        
        results = {}
        
        # 1. Check tables exist
        cursor = connection.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'P2_Gestion_Clinica%%'
            ORDER BY table_name;
        """)
        results['tables'] = [row[0] for row in cursor.fetchall()]
        
        # 2. Count pacientes
        results['paciente_count'] = Paciente.objects.count()
        
        # 3. Try to serialize just one paciente with the FULL serializer
        paciente = Paciente.objects.first()
        if paciente:
            results['paciente_nombre'] = paciente.nombre
            results['has_expediente'] = hasattr(paciente, 'expediente')
            try:
                exp = paciente.expediente
                results['expediente_id'] = exp.id if exp else None
            except Exception as e:
                results['expediente_error'] = str(e)
            
            try:
                serializer = PacienteSerializer(paciente)
                data = serializer.data
                results['serializer_ok'] = True
                results['serialized_data'] = data
            except Exception as e:
                results['serializer_error'] = str(e)
                results['serializer_traceback'] = traceback.format_exc()
        
        # 4. Check NotaClinica table
        try:
            nota_count = NotaClinica.objects.count()
            results['nota_count'] = nota_count
        except Exception as e:
            results['nota_table_error'] = str(e)
        
        # 5. Check ArchivoAdjunto table
        try:
            archivo_count = ArchivoAdjunto.objects.count()
            results['archivo_count'] = archivo_count
        except Exception as e:
            results['archivo_table_error'] = str(e)
        
        return JsonResponse(results, json_dumps_params={'indent': 2, 'ensure_ascii': False})
    except Exception as e:
        return HttpResponse("FATAL ERROR: " + traceback.format_exc(), status=500, content_type='text/plain')
