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
    paciente_nombre = serializers.ReadOnlyField(source='paciente.nombre')
    concepto = serializers.CharField(source='descripcion', required=False, allow_blank=True)
    metodo_pago = serializers.SerializerMethodField()

    class Meta:
        model = Transaccion
        fields = ['id', 'paciente', 'paciente_nombre', 'monto', 'tipo', 'fecha', 'descripcion', 'concepto', 'metodo_pago']
        extra_kwargs = {'tipo': {'required': False}}

    def get_metodo_pago(self, obj):
        if 'STRIPE' in obj.descripcion or 'TARJETA' in obj.descripcion: return 'TARJETA'
        elif 'QR' in obj.descripcion: return 'QR'
        elif '[' in obj.descripcion and ']' in obj.descripcion:
            return obj.descripcion.split('[')[-1].split(']')[0]
        return 'EFECTIVO'

    def create(self, validated_data):
        if 'tipo' not in validated_data:
            validated_data['tipo'] = 'PAGO'
        metodo_pago = self.initial_data.get('metodo_pago', 'EFECTIVO')
        if 'descripcion' in validated_data:
            validated_data['descripcion'] = f"{validated_data['descripcion']} [{metodo_pago}]"
        return super().create(validated_data)

class ComprobanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comprobante
        fields = '__all__'
