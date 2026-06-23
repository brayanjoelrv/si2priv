// [SPRINT 1 - T010] Interfaz de Autenticación: Enrutador raíz de la SPA React.
// [RF-28] Control de Acceso RBAC: Guardia de rutas 'PrivateRoute' con validación de roles.
// [RNF-03] Seguridad: Redirección automática a login si no hay sesión válida.
// [SPRINT 0 - T002] Stack Tecnológico: React 19 + React Router v7 confirmado.
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext'; // [SPRINT 1 - T021] Contexto global de sesión

// [SPRINT 1 - T010] Página de Login
import Login from './pages/Login';
// [SPRINT 1 - T016] Dashboard administrativo con métricas
import Dashboard from './pages/Dashboard';
// [SPRINT 1 - T013] Módulo de Registro de Pacientes
import RegistroPaciente from './pages/RegistroPaciente';
// [SPRINT 1 - T024] Módulo de Alta de Clínica (Tenant)
import RegistroClinica from './pages/RegistroClinica';
// [SPRINT 1 - RF-29] Mantenimiento de Clínica Institucional
import ConfiguracionClinica from './pages/ConfiguracionClinica';
// [SPRINT 1 - T021] Navbar con botón de Logout (CU-04)
import Navbar from './components/Navbar';
// [SPRINT 1 - T019] [CU-03] Flujo de recuperación de credenciales (pública)
import RecuperarContrasena from './pages/RecuperarContrasena';
// [SPRINT 1 - CU-05] Gestión de Psicólogos
import GestionPersonal from './pages/GestionPersonal';
// [SPRINT 1 - T025] Interfaz de monitoreo de límites SaaS
import SuscripcionInfo from './pages/SuscripcionInfo';
import Landing from './pages/Landing'; // [CIERRE SPRINT 1] Landing Comercial B2B
import GestionPacientes from './pages/GestionPacientes'; // [SPRINT 2] CU13
import AgendaCitas from './pages/AgendaCitas'; // [SPRINT 2] CU14/15
import ModuloFinanciero from './pages/ModuloFinanciero'; // [SPRINT 2] CU11/12
import AsistenteVoz from './pages/AsistenteVoz';
import RegistroCita from './pages/RegistroCita';
import DiagnosticoIA from './pages/DiagnosticoIA'; // [SPRINT 2] IA Predictiva
import AdminReportes from './pages/AdminReportes';
import Bitacora from './pages/Bitacora';
import PreferenciasNotificaciones from './pages/PreferenciasNotificaciones';
// [SPRINT 4] Historial Clínico, Evoluciones y Analítica (CU29/CU22)
import HistorialClinico from './pages/HistorialClinico';
import RegistroEvolucion from './pages/RegistroEvolucion';
import AnaliticaClinica from './pages/AnaliticaClinica';
import PagoExitoso from './pages/PagoExitoso';
import PagoCancelado from './pages/PagoCancelado';

// ==============================================================================
// RUTAS PROTEGIDAS (RNF-03: Seguridad de Acceso)
// ==============================================================================
const PrivateRoute = ({ children, allowedRoles }) => {
    const { user } = useAuth(); // 👈 El guardia ahora escucha la radio oficial

    // Si no hay usuario en la RAM, patada al Login
    if (!user) {
        return <Navigate to="/" />;
    }

    // [ALINEACIÓN SPRINT 1 - RF-29] "Bypass Global": Si el administrador no tiene Clínica asignada, solo puede ver el Registro B2B
    // Excepción: Los pacientes móviles no tienen clinica_id (o podrían no tenerlo) hasta escanear, pero esta Web es solo Admin/B2B
    if (user && (!user.clinica_id || user.clinica_id === "null" || user.clinica_id === "undefined") && user.role !== 'PACIENTE') {
        return <Navigate to="/registro-clinica" />;
    }

    // Si la ruta exige rol (ej. ADMIN) y el usuario no lo tiene, patada al Dashboard
    if (allowedRoles && !allowedRoles.includes(user.role)) {
        return <Navigate to="/dashboard" />;
    }
    // 👇 AQUÍ ESTÁ LA MAGIA: Renderizamos el Navbar globalmente para rutas seguras
    return (
        <>
            <Navbar /> 
            {children}
        </>
    );
};    


// ==============================================================================
// ENRUTADOR PRINCIPAL
// ==============================================================================
function App() {
    return (
        <AuthProvider> 
            <Router>
                <Routes>
                    {/* [CIERRE SPRINT 1] Landing Page Comercial B2B SaaS */}
                    <Route path="/" element={<Landing />} />
                    
                    {/* [SPRINT 1 - T010] Login reubicado */}
                    <Route path="/login" element={<Login />} />
                    
                    {/* [SPRINT 1 - T019] [CU-03] Ruta pública: no requiere autenticación */}
                    <Route path="/recuperar" element={<RecuperarContrasena />} />

                    {/* [SPRINT 1 - T024] [CU-25] Registro B2B de Clínicas SaaS */}
                    <Route path="/registro-clinica" element={<RegistroClinica />} />
                    
                    <Route path="/dashboard" element={
                        <PrivateRoute>
                            <Dashboard />
                        </PrivateRoute>
                    } />

                    <Route path="/registro-paciente" element={
                        <PrivateRoute allowedRoles={['PSICOLOGO', 'ADMIN']}>
                            <RegistroPaciente />
                        </PrivateRoute>
                    } />

                    {/* [SPRINT 2] Gestión Completa de Pacientes (CU13) */}
                    <Route path="/pacientes" element={
                        <PrivateRoute allowedRoles={['PSICOLOGO', 'ADMIN']}>
                            <GestionPacientes />
                        </PrivateRoute>
                    } />

                    {/* [SPRINT 2] Agenda de Citas (CU14/15/26) */}
                    <Route path="/citas" element={
                        <PrivateRoute allowedRoles={['PSICOLOGO', 'ADMIN']}>
                            <AgendaCitas />
                        </PrivateRoute>
                    } />

                    {/* [SPRINT 2] Módulo Financiero (CU11/12) */}
                    <Route path="/pagos" element={<PrivateRoute><ModuloFinanciero /></PrivateRoute>} />

                    {/* [SPRINT 2] IA Predictiva con Gemini */}
                    <Route path="/ia" element={
                        <PrivateRoute allowedRoles={['PSICOLOGO', 'ADMIN']}>
                            <DiagnosticoIA />
                        </PrivateRoute>
                    } />

                    {/* [SPRINT 1 - CU-05] Gestión de Personal Clínico (Solo Admin) */}
                    <Route path="/gestion-personal" element={
                        <PrivateRoute allowedRoles={['ADMIN']}>
                            <GestionPersonal />
                        </PrivateRoute>
                    } />

                    {/* [SPRINT 1 - RF-29] Mantenimiento de Clínica (Solo Admin) */}
                    <Route path="/configuracion-clinica" element={
                        <PrivateRoute allowedRoles={['ADMIN']}>
                            <ConfiguracionClinica />
                        </PrivateRoute>
                    } />

                    {/* [SPRINT 1 - T025] Límites SaaS (Solo Admin) */}
                    <Route path="/suscripcion" element={
                        <PrivateRoute allowedRoles={['ADMIN']}>
                            <SuscripcionInfo />
                        </PrivateRoute>
                    } />

                    <Route path="/reporte-voz" element={<PrivateRoute><AsistenteVoz /></PrivateRoute>} />
                    <Route path="/admin-reportes" element={
                        <PrivateRoute allowedRoles={['ADMIN']}>
                            <AdminReportes />
                        </PrivateRoute>
                    } />
                    <Route path="/admin/auditoria" element={
                        <PrivateRoute allowedRoles={['ADMIN']}>
                            <Bitacora />
                        </PrivateRoute>
                    } />
                    <Route path="/preferencias-notificaciones" element={
                        <PrivateRoute>
                            <PreferenciasNotificaciones />
                        </PrivateRoute>
                    } />
                    <Route path="/registro-cita" element={<PrivateRoute><RegistroCita /></PrivateRoute>} />

                    {/* [SPRINT 4] Historial Clínico del Paciente (CU29 - T062) */}
                    <Route path="/historial-clinico/:pacienteId" element={
                        <PrivateRoute allowedRoles={['PSICOLOGO', 'ADMIN']}>
                            <HistorialClinico />
                        </PrivateRoute>
                    } />

                    {/* [SPRINT 4] Registro de Evoluciones y Diagnósticos (CU29 - T063/T064) */}
                    <Route path="/registro-evolucion/:pacienteId" element={
                        <PrivateRoute allowedRoles={['PSICOLOGO', 'ADMIN']}>
                            <RegistroEvolucion />
                        </PrivateRoute>
                    } />

                    {/* [SPRINT 4] Dashboard de Analítica Clínica (CU22 - T071) */}
                    <Route path="/analitica-clinica" element={
                        <PrivateRoute allowedRoles={['PSICOLOGO', 'ADMIN']}>
                            <AnaliticaClinica />
                        </PrivateRoute>
                    } />

                    <Route path="/pago-exitoso" element={<PagoExitoso />} />
                    <Route path="/pago-cancelado" element={<PagoCancelado />} />

                    <Route path="*" element={<Navigate to="/" />} />
                </Routes>
            </Router>
        </AuthProvider>
    );
}

export default App;