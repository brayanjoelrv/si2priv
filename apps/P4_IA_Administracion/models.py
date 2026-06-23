from django.db import models
from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from apps.P2_Gestion_Clinica.models import Paciente

class LogAuditoria(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    clinica = models.ForeignKey('P1_Identidad_Acceso.Clinica', on_delete=models.CASCADE, null=True, blank=True)
    accion = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"[{self.fecha.strftime('%Y-%m-%d %H:%M')}] {self.usuario} - {self.accion}"

# ==============================================================================
# MÓDULO FINANCIERO (T058, T059)
# ==============================================================================
class Transaccion(models.Model):
    TIPOS = [
        ('PAGO', 'Pago de Sesión'),
        ('DEUDA', 'Cargo de Sesión'),
        ('AJUSTE', 'Ajuste de Saldo'),
    ]
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='transacciones')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    fecha = models.DateTimeField(auto_now_add=True)
    descripcion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.tipo} - {self.monto} - {self.paciente.nombre}"

class Comprobante(models.Model):
    transaccion = models.OneToOneField(Transaccion, on_delete=models.CASCADE, related_name='comprobante')
    nro_comprobante = models.CharField(max_length=50, unique=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    pdf_path = models.FileField(upload_to='finanzas/comprobantes/', null=True, blank=True)

    def __str__(self):
        return f"Recibo {self.nro_comprobante} ({self.transaccion.paciente.nombre})"

# Señales automáticas para Login y Logout
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    LogAuditoria.objects.create(
        usuario=user, 
        clinica=user.clinica if hasattr(user, 'clinica') else None,
        accion="Inició sesión en el sistema.",
        ip_address=ip,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        LogAuditoria.objects.create(
            usuario=user, 
            clinica=user.clinica if hasattr(user, 'clinica') else None,
            accion="Cerró sesión a través del portal web."
        )

