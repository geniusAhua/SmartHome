import './App.css';
import { useState, useEffect, useContext } from 'react';
import { MyAuthProvider } from './Components/AuthContext';
import MainPage from './Pages/MainPage/MainPage';
import { WsProvider } from './Components/WsContext';

function App() {
    return (
        <MyAuthProvider>
            <WsProvider>
                <MainPage />
            </WsProvider>
        </MyAuthProvider>
    );
};

export default App;
