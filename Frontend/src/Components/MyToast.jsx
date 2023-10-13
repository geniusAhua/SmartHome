import Toast from 'react-bootstrap/Toast';
import React, { useState, useEffect, forwardRef, useImperativeHandle, useRef } from 'react';
import './MyToast.css';

const MyToast = forwardRef(({}, ref) => {
    const [config, setConfig] = useState({
        show: false,
        message: 'this is a toast',
    });

    let __duration = useRef(3000);

    const timeoutId = useRef(null);

    const toggleShowA = () => {
        setConfig({
            ...config,
            show: !config.show,
        });
    };

    const startTimeout = () => {
        console.log('toast show: ' + config.show);
        timeoutId.current = setTimeout(() => {
            if(config.show) toggleShowA();
        }, __duration.current);
    };

    const clearTimeOut = () => {
        if(timeoutId.current){
            clearTimeout(timeoutId.current);
            timeoutId.current = null;
        }
    };

    useImperativeHandle(ref, () => ({
        showToast: (message, duration = 3000) => {
            __duration.current = duration;
            setConfig({
                show: true,
                message: message,
            });
        },
    }));

    useEffect(() => {
        if(config.show) startTimeout();

        return () => {
            clearTimeOut();
        };
    }, [config.show]);

    return (
        <>
            <div className='toast-container' style={{display: config.show ? 'block' : 'none'}}>
                <Toast className='my-toast' show={config.show}>
                    <Toast.Body>{config.message}</Toast.Body>
                </Toast>
            </div>
        </>
    );
});

export default MyToast;