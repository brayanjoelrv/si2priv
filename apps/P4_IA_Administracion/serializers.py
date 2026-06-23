from rest_framework import serializers
from .models import LogAuditoria, Transaccion, Comprobante

class LogAuditoriaSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField()
    usuario_nombre = serializers.ReadOnlyField(source='usuario.username')
    fecha_formateada = serializers.SerializerMethodField()

    class Meta:
        model = LogAuditoria
        fields = ["id", "usuario", "usuario_nombre", "accion", "ip_address", "user_agent", "fecha", "fecha_formateada"]

    def get_fecha_formateada(self, obj):
        return obj.fecha.strftime("%d/%m/%Y %H:%M:%S")

class TransaccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaccion
        fields = '__all__'

class ComprobanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comprobante
        fields = '__all__'
