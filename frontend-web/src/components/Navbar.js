import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/axiosConfig';

const Navbar = () => {
    const { user, logout, tenant } = useAuth(); 
    const navigate = useNavigate();
    const [notificaciones, setNotificaciones] = useState([]);
    const [showDropdown, setShowDropdown] = useState(false);

    useEffect(() => {
        if (!user) return;
        
        const fetchNotificaciones = async () => {
            try {
                const res = await apiClient.get('mobile/notificaciones/');
                
                setNotificaciones(prev => {
                    const newNotifs = res.data;
                    
                    // Solo notificar si hay un incremento real en los no leídos
                    const prevUnreadIds = prev.filter(n => !n.leido).map(n => n.id);
                    const currentUnread = newNotifs.filter(n => !n.leido);
                    
                    const reallyNew = currentUnread.filter(n => !prevUnreadIds.includes(n.id));
                    
                    if (reallyNew.length > 0) {
                        const newest = reallyNew[0];
                        // Lanzar notificación nativa (Push tipo WhatsApp Web)
                        if ("Notification" in window) {
                            if (Notification.permission === "granted") {
                                new Notification(newest.titulo, { body: newest.mensaje, icon: "/favicon.ico" });
                            } else if (Notification.permission !== "denied") {
                                Notification.requestPermission().then(permission => {
                                    if (permission === "granted") {
                                        new Notification(newest.titulo, { body: newest.mensaje, icon: "/favicon.ico" });
                                    }
                                });
                            }
                        }
                    }
                    return newNotifs;
                });
            } catch (error) {
                console.error("Error al obtener notificaciones:", error);
            }
        };

        fetchNotificaciones();
        const interval = setInterval(fetchNotificaciones, 30000); // Poll every 30s
        return () => clearInterval(interval);
    }, [user]);

    const unreadCount = notificaciones.filter(n => !n.leido).length;

    const handleNotifClick = () => {
        if (unreadCount > 0) {
            apiClient.patch('mobile/notificaciones/').then(() => {
                setNotificaciones(notificaciones.map(n => ({...n, leido: true})));
            });
        }
        setShowDropdown(!showDropdown);
    };

    return (
        <nav style={{ padding: '10px 20px', background: '#1a2233', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'relative' }}>
            <div 
                onClick={() => navigate('/dashboard')}
                style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}
            >
                <div style={{ width: '32px', height: '32px', background: '#2563eb', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '900', fontSize: '14px' }}>
                    PS
                </div>
                <h2 style={{ margin: 0, fontSize: '18px', letterSpacing: '1px', fontWeight: '800' }}>PSICOSYSTEM</h2>
            </div>
            {user && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', justifyContent: 'center' }}>
                        <span style={{ color: '#e2e8f0', fontSize: '14px', fontWeight: 'bold' }}>
                            🏥 {tenant?.nombre || "Cargando Clínica..."}
                        </span>
                        <span style={{ color: '#94a3b8', fontSize: '12px' }}>
                            👤 {user.name} ({user.role})
                        </span>
                    </div>

                    <div style={{ position: 'relative' }}>
                        <button onClick={handleNotifClick} style={{ position: 'relative', padding: '8px 16px', background: '#334155', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold', transition: 'background 0.2s' }} onMouseOver={e => e.target.style.background = '#475569'} onMouseOut={e => e.target.style.background = '#334155'}>
                            🔔 Notificaciones
                            {unreadCount > 0 && (
                                <span style={{ position: 'absolute', top: '-5px', right: '-5px', background: '#ef4444', color: 'white', borderRadius: '50%', padding: '2px 6px', fontSize: '11px', fontWeight: 'bold' }}>
                                    {unreadCount}
                                </span>
                            )}
                        </button>
                        
                        {showDropdown && (
                            <div style={{ position: 'absolute', top: '40px', right: '0', width: '300px', background: 'white', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', zIndex: 1000, overflow: 'hidden' }}>
                                <div style={{ padding: '10px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#0f172a', fontWeight: 'bold', display: 'flex', justifyContent: 'space-between' }}>
                                    Notificaciones
                                    <button onClick={() => navigate('/preferencias-notificaciones')} style={{ background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', fontSize: '12px' }}>Ver todas</button>
                                </div>
                                <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                                    {notificaciones.length === 0 ? (
                                        <div style={{ padding: '15px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>No hay notificaciones</div>
                                    ) : (
                                        notificaciones.slice(0, 5).map(n => (
                                            <div key={n.id} style={{ padding: '12px', borderBottom: '1px solid #f1f5f9', background: n.leido ? 'white' : '#f0fdf4' }}>
                                                <div style={{ fontWeight: 'bold', color: '#0f172a', fontSize: '13px' }}>{n.titulo}</div>
                                                <div style={{ color: '#475569', fontSize: '12px', marginTop: '4px' }}>{n.mensaje}</div>
                                                <div style={{ color: '#94a3b8', fontSize: '10px', marginTop: '6px' }}>{new Date(n.fecha).toLocaleString()}</div>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    <button onClick={logout} style={{ padding: '8px 16px', background: '#dc2626', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold', transition: 'background 0.2s' }} onMouseOver={e => e.target.style.background = '#b91c1c'} onMouseOut={e => e.target.style.background = '#dc2626'}>
                        Cerrar Sesión
                    </button>
                </div>
            )}
        </nav>
    );
};

export default Navbar;