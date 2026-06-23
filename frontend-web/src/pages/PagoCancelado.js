import React, { useEffect } from 'react';

const PagoCancelado = () => {
    useEffect(() => {
        // Redirigir automáticamente a la aplicación móvil usando Deep Link
        window.location.href = 'psicosystem://pagos/cancelado';
    }, []);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#fef2f2', fontFamily: 'sans-serif' }}>
            <div style={{ background: 'white', padding: '40px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', textAlign: 'center', maxWidth: '400px' }}>
                <div style={{ fontSize: '60px', color: '#dc2626', marginBottom: '20px' }}>❌</div>
                <h1 style={{ color: '#dc2626', margin: '0 0 10px 0' }}>Pago Cancelado</h1>
                <p style={{ color: '#4b5563', marginBottom: '30px' }}>El proceso de pago fue cancelado. Serás redirigido a la aplicación en breve.</p>
                <button 
                    onClick={() => window.location.href = 'psicosystem://pagos/cancelado'}
                    style={{ background: '#dc2626', color: 'white', border: 'none', padding: '12px 24px', borderRadius: '8px', fontSize: '16px', fontWeight: 'bold', cursor: 'pointer', width: '100%' }}
                >
                    Volver a la App
                </button>
            </div>
        </div>
    );
};

export default PagoCancelado;
