import React, { useEffect } from 'react';

const PagoExitoso = () => {
    useEffect(() => {
        // Redirigir automáticamente a la aplicación móvil usando Deep Link
        window.location.href = 'psicosystem://pagos/exito';
    }, []);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#f0fdf4', fontFamily: 'sans-serif' }}>
            <div style={{ background: 'white', padding: '40px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', textAlign: 'center', maxWidth: '400px' }}>
                <div style={{ fontSize: '60px', color: '#16a34a', marginBottom: '20px' }}>✅</div>
                <h1 style={{ color: '#16a34a', margin: '0 0 10px 0' }}>¡Pago Exitoso!</h1>
                <p style={{ color: '#4b5563', marginBottom: '30px' }}>Tu pago ha sido procesado correctamente. Serás redirigido a la aplicación en breve.</p>
                <button 
                    onClick={() => window.location.href = 'psicosystem://pagos/exito'}
                    style={{ background: '#16a34a', color: 'white', border: 'none', padding: '12px 24px', borderRadius: '8px', fontSize: '16px', fontWeight: 'bold', cursor: 'pointer', width: '100%' }}
                >
                    Volver a la App
                </button>
            </div>
        </div>
    );
};

export default PagoExitoso;
