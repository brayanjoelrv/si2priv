import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService';
import { dashboardStyles as styles } from '../styles/dashboardStyles';

const Bitacora = () => {
    const navigate = useNavigate();
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchLogs = async () => {
            try {
                const response = await authService.apiClient.get('admin/auditoria/');
                setLogs(response.data);
                setLoading(false);
            } catch (error) {
                console.error("Error cargando logs:", error);
                setLoading(false);
            }
        };
        fetchLogs();
    }, []);

    return (
        <div style={styles.layout}>
            <aside style={styles.sidebar}>
                <div style={styles.brandContainer}>
                    <span style={styles.brandText}>AUDITORÍA</span>
                </div>
                <nav style={styles.navSection}>
                    <div style={styles.navItem} onClick={() => navigate('/admin-reportes')}>⬅️ Volver a Reportes</div>
                </nav>
            </aside>

            <main style={styles.main}>
                <header style={styles.header}>
                    <div style={styles.headerPath}>Administración / Bitácora de Auditoría (RF-30)</div>
                </header>

                <div style={styles.content}>
                    <div style={styles.panelSection}>
                        <div style={styles.panelHeader}>
                            <h3 style={styles.panelTitle}>📜 Historial de Acciones del Sistema</h3>
                        </div>
                        
                        <div style={styles.tableContainer}>
                            <table style={styles.table}>
                                <thead>
                                    <tr style={styles.tableHeader}>
                                        <th style={styles.th}>FECHA Y HORA (LOCAL)</th>
                                        <th style={styles.th}>USUARIO</th>
                                        <th style={styles.th}>ACCIÓN REALIZADA</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {loading ? (
                                        <tr><td colSpan="3" style={{ textAlign: 'center', padding: '20px' }}>Cargando bitácora...</td></tr>
                                    ) : logs.length > 0 ? (
                                        logs.map((log, index) => (
                                            <tr key={index} style={styles.tableRow}>
                                                <td style={styles.td}>{log.fecha}</td>
                                                <td style={styles.tdBold}>{(log.usuario || 'SISTEMA').toUpperCase()}</td>
                                                <td style={styles.td}>{log.accion}</td>
                                            </tr>
                                        ))
                                    ) : (
                                        <tr><td colSpan="3" style={{ textAlign: 'center', padding: '20px' }}>No hay registros de auditoría aún.</td></tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                        <p style={styles.technicalNote}>
                            * Este registro es inmutable y cumple con el Requerimiento Funcional RF-30 de Trazabilidad.
                        </p>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default Bitacora;
