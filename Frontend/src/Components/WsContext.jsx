import React, { useRef } from 'react';
import { useState, createContext, useEffect, useContext } from "react";
import useWebSocket from 'react-use-websocket';
import { SOCKET_URL, isEmpty } from '../Const/Const.jsx';
import { MyAuthContext } from './AuthContext';

const WsContext = createContext();

function WsProvider({ children }) {
    let {user} = useContext(MyAuthContext);
    let onmessage = useRef(null);
    let onRefresh = useRef(null);
    const [sensorsTemp, setSensorsTemp] = useState(null); // [sensor1, sensor2, ...]
    const [sensorsDataTemp, setSensorsDataTemp] = useState(null); // [sensor1_data, sensor2_data, ...

    //for websocket - connect to router
    const webSocket = useWebSocket(SOCKET_URL, {
        // Will attempt to reconnect on all close events, such as server shutting down
        retryOnError: true,
        // Should the WebSocket be closed automatically on component unmount
        shouldClose: true,
        reconnectAttempts: 10,
        reconnectInterval: 3000,
        onMessage: (event) => {
            onmessage.current(event);
        },
    });


    let values = { webSocket, onmessage, onRefresh, sensorsTemp, sensorsDataTemp, setSensorsTemp, setSensorsDataTemp };

    useEffect(() => {
        if(user && onRefresh.current != null){
            onRefresh.current(user.userName, user.ndnAdress, user.password);
        }
    }, [user]);


    return (
        <WsContext.Provider value={values}>
            {children}
        </WsContext.Provider>
    );
};

export { WsContext, WsProvider };