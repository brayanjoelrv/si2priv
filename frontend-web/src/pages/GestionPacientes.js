import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/axiosConfig';

const GestionPacientes = () => {
    const navigate = useNavigate();
    
    // Lista de pacientes y estados de carga
    const [pacientes, setPacientes] = useState([]);
    const [loading, setLoading] = useState(true);
    
    // Controles de Búsqueda, Filtros y Ordenación (CU19)
    const [busqueda, setBusqueda] = useState('');
    const [filtroProcedencia, setFiltroProcedencia] = useState('ALL'); // 'ALL' | 'WEB' | 'MOVIL'
    const [ordenarPor, setOrdenarPor] = useState('nombre'); // 'nombre' | 'ci' | 'id'
    const [ordenDireccion, setOrdenDireccion] = useState('asc'); // 'asc' | 'desc'
    
    // Paciente Seleccionado y Expediente Clínico (CU20)
    const [selectedPaciente, setSelectedPaciente] = useState(null);
    const [expediente, setExpediente] = useState(null);
    const [loadingExpediente, setLoadingExpediente] = useState(false);
    const [activeTab, setActiveTab] = useState('notas'); // 'notas' | 'archivos' | 'bitacora'
    
    // Formulario de Nueva Nota Clínica
    const [nuevaNota, setNuevaNota] = useState('');
    const [guardandoNota, setGuardandoNota] = useState(false);
    
    // Formulario de Archivo Adjunto
    const [adjunto, setAdjunto] = useState(null);
    const [descripcionAdjunto, setDescripcionAdjunto] = useState('');
    const [subiendoArchivo, setSubiendoArchivo] = useState(false);
    
    // Bitácora de Auditoría del Paciente (CU21)
    const [patientLogs, setPatientLogs] = useState([]);
    const [loadingLogs, setLoadingLogs] = useState(false);

    // Cargar pacientes
    const fetchPacientes = useCallback(async () => {
        try {
            setLoading(true);
            const response = await apiClient.get('pacientes/');
            setPacientes(response.data);
        } catch (err) {
            console.error("Error al cargar pacientes", err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchPacientes();
    }, [fetchPacientes]);

    // Eliminar paciente (Fixing endpoint to 'pacientes/${id}/')
    const handleEliminar = async (pacienteId, nombre) => {
        if (window.confirm(`¿Está seguro de eliminar a ${nombre}? Esta acción quedará registrada en la bitácora.`)) {
            try {
                await apiClient.delete(`pacientes/${pacienteId}/`);
                alert("Paciente eliminado correctamente.");
                if (selectedPaciente?.id === pacienteId) {
                    setSelectedPaciente(null);
                    setExpediente(null);
                }
                fetchPacientes();
            } catch (err) {
                console.error(err);
                alert("Error al eliminar el paciente. Verifique sus permisos.");
            }
        }
    };

    // Auto-recuperación de expediente al seleccionar paciente (CU20)
    const handleSelectPaciente = async (paciente) => {
        setSelectedPaciente(paciente);
        setExpediente(null);
        setLoadingExpediente(true);
        setNuevaNota('');
        setAdjunto(null);
        setDescripcionAdjunto('');
        
        try {
            // El backend crea el expediente si no existe
            const response = await apiClient.get(`pacientes/${paciente.id}/`);
            setExpediente(response.data.expediente || null);
            
            // Cargar logs de auditoría para este paciente (CU21)
            fetchPatientLogs(paciente.nombre);
        } catch (err) {
            console.error("Error al recuperar expediente clínico", err);
        } finally {
            setLoadingExpediente(false);
        }
    };

    // Recuperar logs para el paciente seleccionado (CU21)
    const fetchPatientLogs = async (nombrePaciente) => {
        setLoadingLogs(true);
        try {
            const response = await apiClient.get('admin/auditoria/');
            // Filtrar logs donde la acción contenga el nombre del paciente
            const filtered = response.data.filter(log => 
                log.accion.toLowerCase().includes(nombrePaciente.toLowerCase())
            );
            setPatientLogs(filtered);
        } catch (err) {
            console.error("Error al cargar logs del paciente", err);
        } finally {
            setLoadingLogs(false);
        }
    };

    // Registrar Nota Clínica
    const handleAddNota = async (e) => {
        e.preventDefault();
        if (!nuevaNota.trim() || !expediente) return;
        
        setGuardandoNota(true);
        try {
            await apiClient.post('clinica/notas-clinicas/', {
                expediente: expediente.id,
                contenido: nuevaNota
            });
            setNuevaNota('');
            
            // Refrescar expediente
            const response = await apiClient.get(`pacientes/${selectedPaciente.id}/`);
            setExpediente(response.data.expediente);
            
            // Refrescar logs
            fetchPatientLogs(selectedPaciente.nombre);
        } catch (err) {
            console.error("Error al guardar nota", err);
            alert("No se pudo guardar la nota.");
        } finally {
            setGuardandoNota(false);
        }
    };

    // Subir Archivo Adjunto
    const handleUploadArchivo = async (e) => {
        e.preventDefault();
        if (!adjunto || !expediente) return;
        
        setSubiendoArchivo(true);
        try {
            const formData = new FormData();
            formData.append('expediente', expediente.id);
            formData.append('archivo', adjunto);
            formData.append('descripcion', descripcionAdjunto);
            
            await apiClient.post('clinica/archivos-adjuntos/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });
            
            setAdjunto(null);
            setDescripcionAdjunto('');
            // Reset input file element
            document.getElementById('file-input').value = '';
            
            // Refrescar expediente
            const response = await apiClient.get(`pacientes/${selectedPaciente.id}/`);
            setExpediente(response.data.expediente);
            
            // Refrescar logs
            fetchPatientLogs(selectedPaciente.nombre);
        } catch (err) {
            console.error("Error al subir archivo", err);
            alert("No se pudo subir el archivo.");
        } finally {
            setSubiendoArchivo(false);
        }
    };

    // Lógica inteligente de filtrado y ordenamiento (CU19)
    const filteredPacientes = pacientes
        .filter(p => {
            // Filtro por búsqueda de texto
            const matchesSearch = 
                p.nombre.toLowerCase().includes(busqueda.toLowerCase()) || 
                p.ci.includes(busqueda) ||
                (p.motivo_consulta && p.motivo_consulta.toLowerCase().includes(busqueda.toLowerCase()));
            
            // Filtro por procedencia
            const matchesProcedencia = 
                filtroProcedencia === 'ALL' ||
                (filtroProcedencia === 'WEB' && p.origen !== 'MOVIL') ||
                (filtroProcedencia === 'MOVIL' && p.origen === 'MOVIL');
                
            return matchesSearch && matchesProcedencia;
        })
        .sort((a, b) => {
            let fieldA = a[ordenarPor] || '';
            let fieldB = b[ordenarPor] || '';
            
            if (typeof fieldA === 'string') {
                fieldA = fieldA.toLowerCase();
                fieldB = fieldB.toLowerCase();
            }
            
            if (fieldA < fieldB) return ordenDireccion === 'asc' ? -1 : 1;
            if (fieldA > fieldB) return ordenDireccion === 'asc' ? 1 : -1;
            return 0;
        });

    // Resaltado de coincidencias
    const highlightText = (text, search) => {
        if (!search || !text) return text;
        const parts = text.split(new RegExp(`(${search})`, 'gi'));
        return parts.map((part, i) => 
            part.toLowerCase() === search.toLowerCase() 
                ? <mark key={i} style={styles.highlight}>{part}</mark>
                : part
        );
    };

    return (
        <div style={styles.container}>
            <div style={styles.mainGrid}>
                {/* LISTADO DE PACIENTES */}
                <div style={{ flex: 1, minWidth: '0' }}>
                    <header style={styles.header}>
                        <div>
                            <h2 style={styles.title}>GESTIÓN DE PACIENTES (CU19)</h2>
                            <p style={styles.subtitle}>Búsqueda Inteligente, Listados y Expedientes Clínicos</p>
                        </div>
                        <button 
                            style={styles.btnPrimary}
                            onClick={() => navigate('/registro-paciente')}
                        >
                            + NUEVO PACIENTE
                        </button>
                    </header>

                    {/* BARRA DE FILTROS INTELIGENTE */}
                    <div style={styles.filterBar}>
                        <div style={styles.searchContainer}>
                            <span style={styles.searchIcon}>🔍</span>
                            <input 
                                type="text" 
                                placeholder="Buscar por nombre, CI, motivo..." 
                                style={styles.searchInput}
                                value={busqueda}
                                onChange={(e) => setBusqueda(e.target.value)}
                            />
                        </div>

                        <div style={styles.filterGroup}>
                            <div style={styles.selectWrapper}>
                                <label style={styles.selectLabel}>Procedencia</label>
                                <select 
                                    value={filtroProcedencia}
                                    onChange={(e) => setFiltroProcedencia(e.target.value)}
                                    style={styles.select}
                                >
                                    <option value="ALL">Todos los orígenes</option>
                                    <option value="WEB">Portal Web</option>
                                    <option value="MOVIL">Aplicación Móvil</option>
                                </select>
                            </div>

                            <div style={styles.selectWrapper}>
                                <label style={styles.selectLabel}>Ordenar por</label>
                                <select 
                                    value={ordenarPor}
                                    onChange={(e) => setOrdenarPor(e.target.value)}
                                    style={styles.select}
                                >
                                    <option value="nombre">Nombre</option>
                                    <option value="ci">Cédula Identidad</option>
                                    <option value="id">Registro ID</option>
                                </select>
                            </div>

                            <button 
                                onClick={() => setOrdenDireccion(prev => prev === 'asc' ? 'desc' : 'asc')}
                                style={styles.btnSortToggle}
                                title="Cambiar dirección de orden"
                            >
                                {ordenDireccion === 'asc' ? '▲ Asc' : '▼ Desc'}
                            </button>
                        </div>
                    </div>

                    {loading ? (
                        <p style={{ textAlign: 'center', color: '#64748b', padding: '40px' }}>Cargando pacientes de la clínica...</p>
                    ) : (
                        <div style={styles.tableCard}>
                            {filteredPacientes.length > 0 ? (
                                <table style={styles.table}>
                                    <thead>
                                        <tr style={styles.trHead}>
                                            <th style={styles.th}>REG. ID</th>
                                            <th style={styles.th}>PACIENTE</th>
                                            <th style={styles.th}>CI / IDENTIFICACIÓN</th>
                                            <th style={styles.th}>TELÉFONO</th>
                                            <th style={styles.th}>ORIGEN</th>
                                            <th style={styles.th}>ACCIONES</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {filteredPacientes.map(p => (
                                            <tr 
                                                key={p.id} 
                                                style={{
                                                    ...styles.trBody,
                                                    backgroundColor: selectedPaciente?.id === p.id ? '#f0fdf4' : 'transparent',
                                                    borderLeft: selectedPaciente?.id === p.id ? '4px solid #16a34a' : '4px solid transparent'
                                                }}
                                            >
                                                <td style={styles.td}>#{p.id}</td>
                                                <td style={styles.tdBold}>
                                                    {highlightText(p.nombre, busqueda)}
                                                </td>
                                                <td style={styles.td}>{highlightText(p.ci, busqueda)}</td>
                                                <td style={styles.td}>{p.telefono}</td>
                                                <td style={styles.td}>
                                                    {p.origen === 'MOVIL' ? (
                                                        <span style={styles.badgeMobile}>📱 MÓVIL</span>
                                                    ) : (
                                                        <span style={styles.badgeWeb}>💻 WEB</span>
                                                    )}
                                                </td>
                                                <td style={styles.td}>
                                                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                                        <button 
                                                            style={{ ...styles.btnExpediente, background: '#7c3aed', fontSize: '11px', padding: '6px 10px' }} 
                                                            onClick={() => navigate(`/historial-clinico/${p.id}`)}
                                                        >
                                                            📋 Historial
                                                        </button>
                                                        <button 
                                                            style={{ ...styles.btnExpediente, background: '#4f46e5', fontSize: '11px', padding: '6px 10px' }} 
                                                            onClick={() => navigate(`/registro-evolucion/${p.id}`)}
                                                        >
                                                            ➕ Evolución
                                                        </button>
                                                        <button 
                                                            style={styles.btnExpediente} 
                                                            onClick={() => handleSelectPaciente(p)}
                                                        >
                                                            📂 Expediente
                                                        </button>
                                                        <button 
                                                            style={styles.btnDiagnose} 
                                                            onClick={() => navigate(`/ia?paciente=${p.id}`)}
                                                        >
                                                            ✨ Diagnóstico IA
                                                        </button>
                                                        <button 
                                                            style={styles.btnDelete} 
                                                            onClick={() => handleEliminar(p.id, p.nombre)}
                                                        >
                                                            🗑️
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            ) : (
                                <div style={styles.noResults}>
                                    <p>🔍 No se encontraron coincidencias para tu búsqueda.</p>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* DRAWER LATERAL: EXPEDIENTE CLÍNICO (CU20) */}
                {selectedPaciente && (
                    <div style={styles.drawer}>
                        <div style={styles.drawerHeader}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h3 style={styles.drawerTitle}>📂 EXPEDIENTE CLÍNICO</h3>
                                <button 
                                    onClick={() => { setSelectedPaciente(null); setExpediente(null); }}
                                    style={styles.btnCloseDrawer}
                                >
                                    ✕ Cerrar
                                </button>
                            </div>
                            <h4 style={styles.patientName}>{selectedPaciente.nombre.toUpperCase()}</h4>
                            <p style={styles.patientMeta}>
                                👤 CI: {selectedPaciente.ci} | 📞 Tel: {selectedPaciente.telefono}
                            </p>
                            {selectedPaciente.motivo_consulta && (
                                <div style={styles.motivoBox}>
                                    <strong>Motivo de consulta:</strong> {selectedPaciente.motivo_consulta}
                                </div>
                            )}
                        </div>

                        {loadingExpediente ? (
                            <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                                Recuperando datos clínicos de forma automática...
                            </div>
                        ) : expediente ? (
                            <>
                                {/* PESTAÑAS DEL DRAWER */}
                                <div style={styles.tabsContainer}>
                                    <button 
                                        onClick={() => setActiveTab('notas')}
                                        style={activeTab === 'notas' ? styles.tabActive : styles.tab}
                                    >
                                        📝 Notas ({expediente.notas?.length || 0})
                                    </button>
                                    <button 
                                        onClick={() => setActiveTab('archivos')}
                                        style={activeTab === 'archivos' ? styles.tabActive : styles.tab}
                                    >
                                        📎 Archivos ({expediente.archivos?.length || 0})
                                    </button>
                                    <button 
                                        onClick={() => setActiveTab('bitacora')}
                                        style={activeTab === 'bitacora' ? styles.tabActive : styles.tab}
                                    >
                                        📜 Bitácora ({patientLogs.length})
                                    </button>
                                </div>

                                <div style={styles.drawerBody}>
                                    {/* SECCIÓN 1: NOTAS CLÍNICAS */}
                                    {activeTab === 'notas' && (
                                        <div>
                                            <form onSubmit={handleAddNota} style={styles.addNoteForm}>
                                                <textarea
                                                    placeholder="Escriba aquí los detalles de la consulta actual..."
                                                    value={nuevaNota}
                                                    onChange={(e) => setNuevaNota(e.target.value)}
                                                    style={styles.noteTextarea}
                                                    required
                                                />
                                                <button 
                                                    type="submit" 
                                                    disabled={guardandoNota || !nuevaNota.trim()}
                                                    style={styles.btnSaveNote}
                                                >
                                                    {guardandoNota ? 'Guardando nota...' : '➕ Registrar Nota'}
                                                </button>
                                            </form>

                                            <div style={styles.notesList}>
                                                {expediente.notas && expediente.notas.length > 0 ? (
                                                    expediente.notas.map(nota => (
                                                        <div key={nota.id} style={styles.noteItem}>
                                                            <div style={styles.noteHeader}>
                                                                <span style={styles.noteAuthor}>⚕️ Dr(a). {nota.psicologo_nombre || 'Especialista'}</span>
                                                                <span style={styles.noteDate}>{new Date(nota.fecha).toLocaleString()}</span>
                                                            </div>
                                                            <p style={styles.noteContent}>{nota.contenido}</p>
                                                        </div>
                                                    ))
                                                ) : (
                                                    <p style={styles.emptyState}>No hay notas clínicas registradas aún.</p>
                                                )}
                                            </div>
                                        </div>
                                    )}

                                    {/* SECCIÓN 2: ARCHIVOS ADJUNTOS */}
                                    {activeTab === 'archivos' && (
                                        <div>
                                            <form onSubmit={handleUploadArchivo} style={styles.uploadForm}>
                                                <div style={{ marginBottom: '10px' }}>
                                                    <label style={styles.uploadLabel}>Seleccionar Archivo (PDF, Img)</label>
                                                    <input 
                                                        type="file" 
                                                        id="file-input"
                                                        onChange={(e) => setAdjunto(e.target.files[0])}
                                                        style={styles.fileInput}
                                                        required
                                                    />
                                                </div>
                                                <div style={{ marginBottom: '15px' }}>
                                                    <input 
                                                        type="text" 
                                                        placeholder="Descripción del documento..."
                                                        value={descripcionAdjunto}
                                                        onChange={(e) => setDescripcionAdjunto(e.target.value)}
                                                        style={styles.descInput}
                                                    />
                                                </div>
                                                <button 
                                                    type="submit" 
                                                    disabled={subiendoArchivo || !adjunto}
                                                    style={styles.btnSaveNote}
                                                >
                                                    {subiendoArchivo ? 'Subiendo...' : '📤 Adjuntar Archivo'}
                                                </button>
                                            </form>

                                            <div style={styles.filesList}>
                                                {expediente.archivos && expediente.archivos.length > 0 ? (
                                                    expediente.archivos.map(file => (
                                                        <div key={file.id} style={styles.fileItem}>
                                                            <div style={styles.fileIcon}>📄</div>
                                                            <div style={styles.fileInfo}>
                                                                <a 
                                                                    href={file.archivo} 
                                                                    target="_blank" 
                                                                    rel="noopener noreferrer"
                                                                    style={styles.fileName}
                                                                >
                                                                    {file.descripcion || 'Documento adjunto'}
                                                                </a>
                                                                <span style={styles.fileMeta}>{new Date(file.fecha_subida).toLocaleDateString()}</span>
                                                            </div>
                                                        </div>
                                                    ))
                                                ) : (
                                                    <p style={styles.emptyState}>No hay archivos adjuntos en este expediente.</p>
                                                )}
                                            </div>
                                        </div>
                                    )}

                                    {/* SECCIÓN 3: BITÁCORA DEL PACIENTE (CU21) */}
                                    {activeTab === 'bitacora' && (
                                        <div>
                                            <p style={{ fontSize: '11px', color: '#64748b', marginBottom: '15px' }}>
                                                Trazabilidad de auditoría e historial de acciones relativas al paciente.
                                            </p>
                                            {loadingLogs ? (
                                                <p style={styles.emptyState}>Cargando bitácora del paciente...</p>
                                            ) : patientLogs.length > 0 ? (
                                                <div style={styles.timeline}>
                                                    {patientLogs.map((log, index) => (
                                                        <div key={index} style={styles.timelineItem}>
                                                            <div style={styles.timelineDot}></div>
                                                            <div style={styles.timelineContent}>
                                                                <div style={styles.timelineHeader}>
                                                                    <span style={styles.timelineUser}>{(log.usuario || 'SISTEMA').toUpperCase()}</span>
                                                                    <span style={styles.timelineDate}>{new Date(log.fecha).toLocaleString()}</span>
                                                                </div>
                                                                <p style={styles.timelineAction}>{log.accion}</p>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <p style={styles.emptyState}>No hay registros de actividad específicos.</p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </>
                        ) : (
                            <div style={{ padding: '40px', textAlign: 'center', color: '#ef4444' }}>
                                Error al recuperar el expediente.
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

const styles = {
    container: { padding: '40px', backgroundColor: '#f8fafc', minHeight: '100vh' },
    mainGrid: { display: 'flex', gap: '30px', alignItems: 'flex-start' },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' },
    title: { margin: 0, color: '#0f172a', fontSize: '24px', fontWeight: 'bold' },
    subtitle: { margin: '4px 0 0 0', color: '#64748b', fontSize: '13px' },
    btnPrimary: { padding: '12px 24px', backgroundColor: '#2563eb', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' },
    
    // Barra de filtros
    filterBar: { display: 'flex', justifyContent: 'space-between', gap: '20px', marginBottom: '20px', flexWrap: 'wrap' },
    searchContainer: { display: 'flex', alignItems: 'center', backgroundColor: 'white', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '0 12px', flex: 1, minWidth: '260px' },
    searchIcon: { marginRight: '8px' },
    searchInput: { border: 'none', outline: 'none', width: '100%', padding: '10px 0', fontSize: '14px' },
    filterGroup: { display: 'flex', gap: '15px', alignItems: 'flex-end' },
    selectWrapper: { display: 'flex', flexDirection: 'column', gap: '4px' },
    selectLabel: { fontSize: '10px', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase' },
    select: { padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: 'white', fontSize: '13px', outline: 'none', minWidth: '150px' },
    btnSortToggle: { padding: '10px 16px', backgroundColor: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px', color: '#475569' },
    
    // Tabla
    tableCard: { backgroundColor: 'white', borderRadius: '12px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)', overflow: 'hidden', border: '1px solid #cbd5e1' },
    table: { width: '100%', borderCollapse: 'collapse' },
    trHead: { backgroundColor: '#f1f5f9', textAlign: 'left' },
    th: { padding: '15px', fontSize: '12px', fontWeight: 'bold', color: '#64748b' },
    trBody: { borderTop: '1px solid #f1f5f9', transition: 'background-color 0.2s' },
    td: { padding: '15px', fontSize: '13px', color: '#334155' },
    tdBold: { padding: '15px', fontSize: '13px', fontWeight: 'bold', color: '#0f172a' },
    highlight: { backgroundColor: '#fef08a', color: '#854d0e', padding: '2px 4px', borderRadius: '4px' },
    
    // Badges
    badgeWeb: { fontSize: '10px', fontWeight: 'bold', color: '#0369a1', backgroundColor: '#e0f2fe', padding: '4px 8px', borderRadius: '12px' },
    badgeMobile: { fontSize: '10px', fontWeight: 'bold', color: '#15803d', backgroundColor: '#dcfce7', padding: '4px 8px', borderRadius: '12px' },
    
    // Acciones de tabla
    btnExpediente: { padding: '6px 12px', backgroundColor: '#16a34a', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold' },
    btnDiagnose: { padding: '6px 12px', backgroundColor: '#8b5cf6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold' },
    btnDelete: { padding: '6px 12px', backgroundColor: '#ef4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' },
    noResults: { textAlign: 'center', padding: '40px', color: '#64748b', fontSize: '14px' },

    // DRAWER LATERAL (EXPEDIENTE CLÍNICO)
    drawer: { width: '450px', backgroundColor: 'white', borderRadius: '16px', border: '1px solid #cbd5e1', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)', padding: '25px', display: 'flex', flexDirection: 'column', alignSelf: 'stretch', maxHeight: '90vh', overflowY: 'auto' },
    drawerHeader: { borderBottom: '1px solid #e2e8f0', paddingBottom: '15px', marginBottom: '15px' },
    drawerTitle: { margin: 0, fontSize: '12px', color: '#2563eb', fontWeight: '800', letterSpacing: '1px' },
    patientName: { margin: '8px 0 4px 0', fontSize: '20px', color: '#0f172a', fontWeight: '900' },
    patientMeta: { margin: 0, fontSize: '11px', color: '#64748b', fontWeight: 'bold' },
    motivoBox: { backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', padding: '10px 14px', borderRadius: '8px', fontSize: '12px', color: '#475569', marginTop: '12px' },
    btnCloseDrawer: { border: 'none', backgroundColor: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold' },
    
    // Tabs
    tabsContainer: { display: 'flex', gap: '5px', borderBottom: '2px solid #e2e8f0', marginBottom: '20px' },
    tab: { flex: 1, padding: '10px 0', border: 'none', background: 'none', color: '#64748b', cursor: 'pointer', fontWeight: 'bold', fontSize: '12px', textAlign: 'center' },
    tabActive: { flex: 1, padding: '10px 0', border: 'none', background: 'none', color: '#2563eb', borderBottom: '2px solid #2563eb', cursor: 'pointer', fontWeight: 'bold', fontSize: '12px', textAlign: 'center' },
    
    drawerBody: { flex: 1, display: 'flex', flexDirection: 'column' },
    
    // Notas
    addNoteForm: { display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '25px' },
    noteTextarea: { minHeight: '80px', padding: '10px', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '13px', outline: 'none', fontFamily: 'inherit' },
    btnSaveNote: { padding: '10px', backgroundColor: '#0f172a', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer', fontSize: '12px' },
    notesList: { display: 'flex', flexDirection: 'column', gap: '15px' },
    noteItem: { padding: '15px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px' },
    noteHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '10px', fontWeight: 'bold' },
    noteAuthor: { color: '#475569' },
    noteDate: { color: '#94a3b8' },
    noteContent: { margin: 0, fontSize: '12.5px', color: '#1e293b', whiteSpace: 'pre-wrap', lineHeight: '1.5' },
    
    // Archivos
    uploadForm: { display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '25px', padding: '15px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #cbd5e1' },
    uploadLabel: { fontSize: '10px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '4px' },
    fileInput: { fontSize: '11px', color: '#64748b' },
    descInput: { padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: '6px', fontSize: '12px', width: '100%', boxSizing: 'border-box' },
    filesList: { display: 'flex', flexDirection: 'column', gap: '10px' },
    fileItem: { display: 'flex', alignItems: 'center', gap: '12px', padding: '12px', border: '1px solid #e2e8f0', borderRadius: '8px', transition: 'background-color 0.2s' },
    fileIcon: { fontSize: '20px' },
    fileInfo: { display: 'flex', flexDirection: 'column' },
    fileName: { fontSize: '12px', fontWeight: 'bold', color: '#2563eb', textDecoration: 'none' },
    fileMeta: { fontSize: '9px', color: '#94a3b8', marginTop: '2px' },
    emptyState: { textAlign: 'center', color: '#94a3b8', fontSize: '12px', padding: '20px 0' },

    // Timeline para Bitácora del Paciente
    timeline: { display: 'flex', flexDirection: 'column', gap: '16px', position: 'relative', paddingLeft: '20px', borderLeft: '2px solid #e2e8f0' },
    timelineItem: { position: 'relative' },
    timelineDot: { width: '10px', height: '10px', backgroundColor: '#2563eb', borderRadius: '50%', position: 'absolute', left: '-26px', top: '5px', border: '2px solid white' },
    timelineContent: { backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', padding: '10px 14px', borderRadius: '8px' },
    timelineHeader: { display: 'flex', justifyContent: 'space-between', fontSize: '9px', fontWeight: 'bold', color: '#94a3b8', marginBottom: '4px' },
    timelineUser: { color: '#64748b' },
    timelineDate: {},
    timelineAction: { margin: 0, fontSize: '11.5px', color: '#1e293b', lineHeight: '1.4' }
};

export default GestionPacientes;
