from django.http import HttpResponse
import traceback
from apps.P2_Gestion_Clinica.serializers import PacienteSerializer
from apps.P2_Gestion_Clinica.models import Paciente

def debug_pacientes(request):
    try:
        pacientes = Paciente.objects.all()[:1]
        serializer = PacienteSerializer(pacientes, many=True)
        data = serializer.data
        return HttpResponse("OK: " + str(data))
    except Exception as e:
        return HttpResponse("ERROR: " + traceback.format_exc(), status=500)
