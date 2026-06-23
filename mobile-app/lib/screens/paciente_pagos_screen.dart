import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:open_filex/open_filex.dart';
import 'package:url_launcher/url_launcher.dart';
import '../services/cita_pago_service.dart';

class PacientePagosScreen extends StatefulWidget {
  final String token;
  const PacientePagosScreen({Key? key, required this.token}) : super(key: key);

  @override
  _PacientePagosScreenState createState() => _PacientePagosScreenState();
}

class _PacientePagosScreenState extends State<PacientePagosScreen> with WidgetsBindingObserver {
  final Color primaryBlue = const Color(0xFF2563EB);
  final Color darkBlue = const Color(0xFF0F172A);
  
  bool _isLoading = true;
  List<dynamic> _citas = [];
  String _filtroActual = 'TODOS';
  String _searchQuery = '';
  double _totalPendiente = 0.0;
  String? _error;

  final _audioRecorder = AudioRecorder();
  bool _isRecording = false;
  bool _isProcessingVoice = false;

  String _tarjetaNumero = '';
  String _tarjetaFecha = '';
  String _tarjetaCvc = '';

  List<dynamic> get _citasFiltradas {
    return _citas.where((c) {
      if (c['estado'] == 'CANCELADA') return false;

      final matchEstado = _filtroActual == 'TODOS' || (c['estado_pago'] ?? 'PENDIENTE').toString().toUpperCase() == _filtroActual;
      if (!matchEstado) return false;
      
      if (_searchQuery.isEmpty) return true;
      final query = _searchQuery.toLowerCase();
      final motivo = (c['motivo'] ?? '').toString().toLowerCase();
      final clinica = (c['clinica_nombre'] ?? '').toString().toLowerCase();
      
      return motivo.contains(query) || clinica.contains(query);
    }).toList();
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _loadData();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _audioRecorder.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      // Cuando volvemos de Stripe (Navegador), recargamos para ver si ya pagó
      _loadData();
    }
  }

  Future<void> _toggleRecording() async {
    try {
      if (await _audioRecorder.isRecording()) {
        final path = await _audioRecorder.stop();
        setState(() {
          _isRecording = false;
          _isProcessingVoice = true;
        });
        
        if (path != null) {
          _processAudioFile(path);
        } else {
          setState(() => _isProcessingVoice = false);
        }
      } else {
        if (await Permission.microphone.request().isGranted) {
          final tempDir = await getTemporaryDirectory();
          final path = '${tempDir.path}/report_audio.m4a';
          await _audioRecorder.start(
            const RecordConfig(encoder: AudioEncoder.aacLc),
            path: path,
          );
          setState(() {
            _isRecording = true;
          });
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Permiso de micrófono denegado.')),
          );
        }
      }
    } catch (e) {
      print('Error recording: $e');
      setState(() {
        _isRecording = false;
        _isProcessingVoice = false;
      });
    }
  }

  Future<void> _processAudioFile(String path) async {
    try {
      final text = await CitaPagoService.transcribeAudio(token: widget.token, filePath: path);
      setState(() => _isProcessingVoice = false);
      _mostrarEditorTexto(text);
    } catch (e) {
      setState(() => _isProcessingVoice = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al transcribir: $e'), backgroundColor: Colors.red),
      );
    }
  }

  void _mostrarEditorTexto(String textoInicial) {
    final controller = TextEditingController(text: textoInicial);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Revisar Transcripción', style: GoogleFonts.outfit(fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Corrige cualquier error antes de solicitar el reporte:', style: GoogleFonts.outfit(fontSize: 14)),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              maxLines: 4,
              decoration: InputDecoration(
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            child: Text('Cancelar', style: GoogleFonts.outfit(color: Colors.grey)),
            onPressed: () => Navigator.pop(ctx),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: primaryBlue),
            child: Text('Generar Reporte', style: GoogleFonts.outfit(color: Colors.white)),
            onPressed: () {
              Navigator.pop(ctx);
              _solicitarReporte(controller.text);
            },
          ),
        ],
      ),
    );
  }

  Future<void> _solicitarReporte(String texto) async {
    setState(() => _isProcessingVoice = true);
    try {
      final res = await CitaPagoService.generarReporte(token: widget.token, transcript: texto);
      setState(() => _isProcessingVoice = false);
      _mostrarBotonesDescarga(res['pdf_base64'], res['excel_base64']);
    } catch (e) {
      setState(() => _isProcessingVoice = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al generar: $e'), backgroundColor: Colors.red),
      );
    }
  }

  void _mostrarBotonesDescarga(String? pdfBase64, String? excelBase64) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Reporte Generado', style: GoogleFonts.outfit(fontWeight: FontWeight.bold)),
        content: Text('Tus reportes por filtros de voz están listos.', style: GoogleFonts.outfit()),
        actionsAlignment: MainAxisAlignment.center,
        actions: [
          if (pdfBase64 != null)
            ElevatedButton.icon(
              icon: const Icon(Icons.picture_as_pdf, color: Colors.white),
              style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
              label: Text('Abrir PDF', style: GoogleFonts.outfit(color: Colors.white)),
              onPressed: () => _guardarYAbrirArchivo(pdfBase64, 'reporte.pdf'),
            ),
          if (excelBase64 != null)
            ElevatedButton.icon(
              icon: const Icon(Icons.table_chart, color: Colors.white),
              style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
              label: Text('Abrir Excel', style: GoogleFonts.outfit(color: Colors.white)),
              onPressed: () => _guardarYAbrirArchivo(excelBase64, 'reporte.xlsx'),
            ),
        ],
      ),
    );
  }

  Future<void> _guardarYAbrirArchivo(String base64Str, String filename) async {
    try {
      final bytes = base64.decode(base64Str);
      final dir = await getApplicationDocumentsDirectory();
      final file = File('\${dir.path}/\$filename');
      await file.writeAsBytes(bytes);
      await OpenFilex.open(file.path);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al abrir el archivo: $e')),
      );
    }
  }

  Future<void> _loadData() async {
    try {
      final data = await CitaPagoService.getHistorial(widget.token);
      final citas = data['citas'] ?? data['results'] ?? data;
      final lista = citas is List ? citas : [];
      double pendiente = 0.0;
      for (final c in lista) {
        if ((c['estado_pago'] ?? '') == 'PENDIENTE') {
          pendiente += double.tryParse(c['monto']?.toString() ?? '0') ?? 0;
        }
      }
      setState(() {
        _citas = lista;
        _totalPendiente = pendiente;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString().replaceAll('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  String _generarReporteHTML() {
    final now = DateFormat("dd/MM/yyyy HH:mm").format(DateTime.now());
    final filas = _citas.isEmpty
        ? '<tr><td colspan="5" style="text-align:center;color:#999;padding:24px;">Sin registros de pagos aún</td></tr>'
        : _citas.map((c) {
            final fecha = c['fecha_hora'] != null
                ? DateFormat("dd/MM/yyyy HH:mm").format(DateTime.parse(c['fecha_hora']).toLocal())
                : '-';
            final psi = c['psicologo_nombre'] ?? c['psicologo'] ?? '-';
            final motivo = c['motivo'] ?? '-';
            final monto = '\$${c['monto'] ?? '0.00'}';
            final estado = c['estado_pago'] ?? 'PENDIENTE';
            final color = estado == 'PAGADO' ? '#10b981' : '#f59e0b';
            return '<tr><td>$fecha</td><td>$psi</td><td>$motivo</td><td>$monto</td><td style="color:$color;font-weight:bold;">$estado</td></tr>';
          }).join('\n');

    return '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Reporte de Pagos — PsicoSystem</title>
  <style>
    body{font-family:Inter,sans-serif;background:#f8fafc;margin:0;padding:24px;color:#0f172a;}
    h1{color:#2563eb;font-size:22px;margin-bottom:4px;}
    .subtitle{color:#64748b;font-size:13px;margin-bottom:24px;}
    .badge{display:inline-block;background:#fee2e2;color:#dc2626;border-radius:8px;padding:10px 20px;font-size:20px;font-weight:bold;margin-bottom:24px;}
    table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06);}
    th{background:#2563eb;color:#fff;padding:12px 16px;text-align:left;font-size:13px;}
    td{padding:12px 16px;border-bottom:1px solid #f1f5f9;font-size:13px;}
    tr:last-child td{border-bottom:none;}
    .footer{margin-top:24px;color:#94a3b8;font-size:11px;text-align:center;}
  </style>
</head>
<body>
  <h1>📋 Reporte de Pagos y Citas</h1>
  <div class="subtitle">Generado el $now — PsicoSystem</div>
  <div class="badge">💰 Saldo Pendiente: \$$_totalPendiente</div>
  <table>
    <thead>
      <tr><th>Fecha y Hora</th><th>Psicólogo</th><th>Motivo</th><th>Monto</th><th>Estado Pago</th></tr>
    </thead>
    <tbody>$filas</tbody>
  </table>
  <div class="footer">PsicoSystem &copy; 2026 — Documento generado automáticamente</div>
</body>
</html>''';
  }

  void _mostrarReporte() {
    final html = _generarReporteHTML();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(children: [
          Icon(Icons.description, color: primaryBlue),
          const SizedBox(width: 10),
          Text('Reporte HTML', style: GoogleFonts.outfit(fontWeight: FontWeight.bold)),
        ]),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('El reporte está listo. Copia el contenido HTML para abrirlo en tu navegador.', style: GoogleFonts.outfit(fontSize: 13, color: Colors.grey.shade600)),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(color: const Color(0xFFF8FAFC), borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.grey.shade200)),
                child: SelectableText(html, style: const TextStyle(fontFamily: 'monospace', fontSize: 11)),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(child: Text('Cerrar', style: GoogleFonts.outfit(color: Colors.grey)), onPressed: () => Navigator.of(ctx).pop()),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.black87),
        title: Text('Historial y Pagos', style: GoogleFonts.outfit(color: Colors.black87, fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: Icon(Icons.picture_as_pdf, color: primaryBlue),
            tooltip: 'Exportar Reporte',
            onPressed: _mostrarReporte,
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        backgroundColor: _isRecording ? Colors.red : primaryBlue,
        onPressed: _isProcessingVoice ? null : _toggleRecording,
        child: _isProcessingVoice 
            ? const CircularProgressIndicator(color: Colors.white)
            : Icon(_isRecording ? Icons.stop : Icons.mic, color: Colors.white),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              decoration: InputDecoration(
                hintText: 'Buscar por motivo o clínica...',
                prefixIcon: const Icon(Icons.search),
                filled: true,
                fillColor: Colors.grey.shade100,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
              onChanged: (val) {
                setState(() => _searchQuery = val);
              },
            ),
            const SizedBox(height: 16),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: ['TODOS', 'PENDIENTE', 'PAGADO', 'CANCELADO'].map((filtro) {
                  return Padding(
                    padding: const EdgeInsets.only(right: 8.0),
                    child: ChoiceChip(
                      label: Text(filtro, style: GoogleFonts.outfit(fontSize: 12, fontWeight: FontWeight.bold)),
                      selected: _filtroActual == filtro,
                      selectedColor: primaryBlue.withOpacity(0.2),
                      onSelected: (selected) {
                        if (selected) setState(() => _filtroActual = filtro);
                      },
                    ),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 16),
            Text('Historial Reciente', style: GoogleFonts.outfit(fontSize: 18, fontWeight: FontWeight.bold, color: const Color(0xFF0F172A))),
            const SizedBox(height: 16),
            if (_isLoading)
              const Center(child: CircularProgressIndicator())
            else if (_citasFiltradas.isEmpty)
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Text('Aún no hay datos de pagos que coincidan.', style: GoogleFonts.outfit(color: Colors.grey)),
              )
            else
              ..._citasFiltradas.map((c) {
                final pagado = (c['estado_pago'] ?? '') == 'PAGADO';
                final fecha = c['fecha_hora'] != null
                    ? DateFormat("dd MMM yyyy HH:mm").format(DateTime.parse(c['fecha_hora']).toLocal())
                    : '-';
                return _buildPagoItem(c, c['motivo'] ?? 'Consulta', fecha, '\$${c['monto'] ?? "0.00"}', pagado);
              }).toList(),
          ],
        ),
      ),
    );
  }

  Widget _buildPagoItem(dynamic citaData, String concepto, String fecha, String monto, bool pagado) {
    final clinica = citaData['clinica_nombre'] ?? 'Sin Clínica';
    final psicologo = citaData['psicologo_nombre'] ?? 'Sin Psicólogo';
    final numeroFicha = citaData['numero_ficha'] ?? 'N/A';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: pagado ? Colors.green.shade50 : Colors.orange.shade50, borderRadius: BorderRadius.circular(10)),
            child: Icon(pagado ? Icons.check_circle : Icons.access_time, color: pagado ? Colors.green : Colors.orange),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(concepto, style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 4),
                Text('Clínica: $clinica', style: GoogleFonts.outfit(fontSize: 13, color: Colors.grey.shade700)),
                Text('Psicólogo: $psicologo', style: GoogleFonts.outfit(fontSize: 13, color: Colors.grey.shade700)),
                Text('Ficha N°: $numeroFicha', style: GoogleFonts.outfit(fontSize: 13, color: primaryBlue, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Text(fecha, style: GoogleFonts.outfit(color: Colors.grey.shade500, fontSize: 12)),
                if (!pagado) ...[
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      ElevatedButton(
                        onPressed: () => _simularPago(context, citaData),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: primaryBlue,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        child: Text('Pagar Ahora', style: GoogleFonts.outfit(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton(
                        onPressed: () => _cancelarCita(context, citaData),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.red,
                          side: const BorderSide(color: Colors.red),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        child: Text('Cancelar', style: GoogleFonts.outfit(fontSize: 12, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                ]
              ],
            ),
          ),
          Text(monto, style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 16, color: pagado ? Colors.green : Colors.orange)),
        ],
      ),
    );
  }

  void _simularPago(BuildContext context, dynamic citaData) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) {
        String metodoSeleccionado = '';
        return StatefulBuilder(
          builder: (BuildContext context, StateSetter setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 24,
                left: 24, right: 24, top: 24
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Container(
                    width: 40, height: 4,
                    margin: const EdgeInsets.only(bottom: 20),
                    decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(2)),
                  ),
                  Text('Completar Pago', style: GoogleFonts.outfit(color: darkBlue, fontWeight: FontWeight.bold, fontSize: 22)),
                  const SizedBox(height: 8),
                  Text('Monto a cancelar: \$${citaData['monto'] ?? "120.00"}', style: GoogleFonts.outfit(fontSize: 16, color: Colors.grey.shade700)),
                  const SizedBox(height: 24),
                  
                  if (metodoSeleccionado == '') ...[
                    Text('Selecciona un método de pago:', style: GoogleFonts.outfit(fontSize: 16, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 16),
                    ListTile(
                      leading: Icon(Icons.qr_code_scanner, color: primaryBlue),
                      title: Text('Pago Rápido QR', style: GoogleFonts.outfit(fontWeight: FontWeight.bold)),
                      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: Colors.grey.shade200)),
                      onTap: () => setModalState(() => metodoSeleccionado = 'QR'),
                    ),
                    const SizedBox(height: 12),
                    ListTile(
                      leading: Icon(Icons.credit_card, color: primaryBlue),
                      title: Text('Pago con Tarjeta', style: GoogleFonts.outfit(fontWeight: FontWeight.bold)),
                      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: Colors.grey.shade200)),
                      onTap: () => setModalState(() => metodoSeleccionado = 'TARJETA'),
                    ),
                  ] else if (metodoSeleccionado == 'QR') ...[
                    Row(
                      children: [
                        IconButton(
                          icon: const Icon(Icons.arrow_back),
                          onPressed: () => setModalState(() => metodoSeleccionado = ''),
                        ),
                        Text('Pago con QR', style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 18)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Escanea este código QR para confirmar el pago y luego presiona el botón.',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.outfit(fontSize: 13, color: Colors.grey.shade600),
                    ),
                    const SizedBox(height: 16),
                    QrImageView(
                      data: "PSICOSYSTEM|CITA:${citaData['id']}|MONTO:${citaData['monto'] ?? '120'}|PACIENTE:${citaData['clinica_nombre'] ?? ''}",
                      version: QrVersions.auto,
                      size: 200.0,
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        icon: const Icon(Icons.qr_code_scanner, color: Colors.white),
                        style: ElevatedButton.styleFrom(backgroundColor: primaryBlue, padding: const EdgeInsets.symmetric(vertical: 16)),
                        onPressed: () => _procesarPagoQR(ctx, citaData),
                        label: Text('Ya escanée — Confirmar Pago', style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ] else if (metodoSeleccionado == 'TARJETA') ...[
                    Row(
                      children: [
                        IconButton(
                          icon: const Icon(Icons.arrow_back),
                          onPressed: () => setModalState(() => metodoSeleccionado = ''),
                        ),
                        Text('Pagar con Stripe', style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 18)),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [const Color(0xFF635BFF), const Color(0xFF0A2540)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Column(
                        children: [
                          const Icon(Icons.lock, color: Colors.white, size: 32),
                          const SizedBox(height: 8),
                          Text(
                            'Pago Seguro con Stripe',
                            style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Serás redirigido a la página segura de Stripe para ingresar los datos de tu tarjeta.',
                            textAlign: TextAlign.center,
                            style: GoogleFonts.outfit(color: Colors.white70, fontSize: 13),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'Total a pagar: \$${citaData['monto'] ?? "120.00"}',
                            style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 20),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        icon: const Icon(Icons.open_in_browser, color: Colors.white),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF635BFF),
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        onPressed: () => _pagarConStripe(ctx, citaData),
                        label: Text('Ir a Stripe Checkout →', style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.security, size: 14, color: Colors.grey),
                        const SizedBox(width: 4),
                        Text('Pago protegido con cifrado SSL', style: GoogleFonts.outfit(fontSize: 11, color: Colors.grey)),
                      ],
                    ),
                  ],
                ],
              ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _procesarPagoQR(BuildContext ctx, dynamic citaData) async {
    Navigator.of(ctx).pop();
    setState(() => _isLoading = true);
    try {
      await CitaPagoService.pagarCita(
        token: widget.token,
        citaId: citaData['id'],
        metodoPago: 'QR',
      );
      _mostrarPagoExitoso(citaData, 'QR');
      _loadData();
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al procesar el pago: $e', style: GoogleFonts.outfit()), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _pagarConStripe(BuildContext ctx, dynamic citaData) async {
    Navigator.of(ctx).pop();
    setState(() => _isLoading = true);
    try {
      final checkoutUrl = await CitaPagoService.stripeCheckout(
        token: widget.token,
        citaId: citaData['id'],
      );
      setState(() => _isLoading = false);
      
      // Abrir Stripe Checkout en el navegador del celular
      final uri = Uri.parse(checkoutUrl);
      try {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
        // Mostrar snackbar indicando que regrese luego del pago
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              duration: const Duration(seconds: 8),
              backgroundColor: const Color(0xFF635BFF),
              content: Row(
                children: [
                  const Icon(Icons.info_outline, color: Colors.white),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Completa tu pago en el navegador y vuelve aquí.',
                      style: GoogleFonts.outfit(color: Colors.white),
                    ),
                  ),
                ],
              ),
              action: SnackBarAction(
                label: 'Actualizar',
                textColor: Colors.white,
                onPressed: () => _loadData(),
              ),
            ),
          );
        }
      } catch (e) {
        throw Exception('No se pudo abrir el navegador. Revisa la URL o instala un navegador.');
      }
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error Stripe: $e', style: GoogleFonts.outfit()), backgroundColor: Colors.red),
      );
    }
  }

  void _mostrarPagoExitoso(dynamic citaData, String metodo) {
    setState(() => _isLoading = false);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle, color: Colors.green, size: 72),
            const SizedBox(height: 16),
            Text('¡Pago Exitoso!', style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 22, color: Colors.green)),
            const SizedBox(height: 8),
            Text(
              'Tu pago de \$${citaData['monto']} fue procesado correctamente.',
              textAlign: TextAlign.center,
              style: GoogleFonts.outfit(fontSize: 14, color: Colors.grey.shade700),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: Colors.green.shade50, borderRadius: BorderRadius.circular(12)),
              child: Column(
                children: [
                  _detalleRow('📋 Motivo', citaData['motivo'] ?? 'Consulta'),
                  _detalleRow('👨‍⚕️ Psicólogo', citaData['psicologo_nombre'] ?? ''),
                  _detalleRow('🏥 Clínica', citaData['clinica_nombre'] ?? ''),
                  _detalleRow('💳 Método', metodo),
                ],
              ),
            ),
            const SizedBox(height: 4),
            Text('Se enviaron notificaciones al psicólogo y a la clínica. 🔔', textAlign: TextAlign.center, style: GoogleFonts.outfit(fontSize: 11, color: Colors.grey)),
          ],
        ),
        actions: [
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: Colors.green, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
              child: Text('Perfecto ✓', style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold)),
              onPressed: () => Navigator.of(ctx).pop(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _detalleRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Text('$label: ', style: GoogleFonts.outfit(fontSize: 12, fontWeight: FontWeight.bold)),
          Expanded(child: Text(value, style: GoogleFonts.outfit(fontSize: 12), overflow: TextOverflow.ellipsis)),
        ],
      ),
    );
  }

  Future<void> _procesarPago(BuildContext ctx, int citaId, String metodo) async {
    Navigator.of(ctx).pop();
    setState(() => _isLoading = true);
    try {
      await CitaPagoService.pagarCita(
        token: widget.token,
        citaId: citaId,
        metodoPago: metodo,
      );
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Pago procesado con éxito.', style: GoogleFonts.outfit()), backgroundColor: Colors.green),
      );
      _loadData();
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al procesar el pago: $e', style: GoogleFonts.outfit()), backgroundColor: Colors.red),
      );
    }
  }

  void _cancelarCita(BuildContext context, dynamic citaData) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Cancelar Cita', style: GoogleFonts.outfit(color: Colors.red, fontWeight: FontWeight.bold)),
        content: Text('¿Estás seguro de cancelar esta cita? Recuerda que no se puede cancelar faltando menos de 1 hora.', style: GoogleFonts.outfit()),
        actions: [
          TextButton(
            child: Text('No, Mantener', style: GoogleFonts.outfit(color: Colors.grey)),
            onPressed: () => Navigator.of(ctx).pop(),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: Text('Sí, Cancelar', style: GoogleFonts.outfit(color: Colors.white)),
            onPressed: () async {
              Navigator.of(ctx).pop();
              setState(() => _isLoading = true);
              try {
                await CitaPagoService.cancelarCita(token: widget.token, citaId: citaData['id']);
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Cita cancelada con éxito.', style: GoogleFonts.outfit()), backgroundColor: Colors.green),
                );
                _loadData();
              } catch (e) {
                setState(() => _isLoading = false);
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Error al cancelar: $e', style: GoogleFonts.outfit()), backgroundColor: Colors.red),
                );
              }
            },
          ),
        ],
      ),
    );
  }
}
