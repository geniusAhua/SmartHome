import { useState, useCallback, useEffect, useRef, useContext, createContext } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { ReadyState } from 'react-use-websocket';

import EntryPage from '../EntryPage/EntryPage.jsx';
import LoadingMask from '../../Components/LoadingMask';
import MyToast from '../../Components/MyToast';
import HomePage from '../HomePage/HomePage';

import { MyAuthContext } from '../../Components/AuthContext';
import { WsContext } from '../../Components/WsContext';
import { SOCKET_URL, HANDSHAKE2ROUTER_HEADER, INTEREST_HEADER, HANDSHAKE2HUB, HANDSHAKE2HUB_FILE } from '../../Const/Const.jsx';

function MainPage (){

    const [NDNurl, setNDNurl] = useState(null);
    const isConn2Router = useRef(false);
    const isConn2Hub = useRef(false);

    // For NDN authentication
    const auth = useAuth();

    // Get websocket context
    const ws = useWs();
    const { readyState } = ws.webSocket;
    // The state of websocket connection
    const connectionStatus = {
        [ReadyState.CONNECTING]: 'Connecting',
        [ReadyState.OPEN]: 'Open',
        [ReadyState.CLOSING]: 'Closing',
        [ReadyState.CLOSED]: 'Closed',
        [ReadyState.UNINSTANTIATED]: 'Uninstantiated',
      }[readyState];

    //for loading mask
    const [isLoading, setIsLoading] = useState(false);
    //loadingMaskRef
    const loadingMaskRef = useRef(null);
    //toastRef
    const toastRef = useRef(null);

     //Initiate loading mask
    let animationDuration = 2500;

    //for Toast
    const showToast = (message, duration = 3000) => {
        if (toastRef.current != null) {
            toastRef.current.showToast(message, duration);
        }
    };

    //for loading mask
    const startLoading = () => {
        if (loadingMaskRef.current != null) {
            loadingMaskRef.current.playLoading(true);
        }
    };

    const stopLoading = () => {
        if (loadingMaskRef.current != null) {
            loadingMaskRef.current.playLoading(false);
        }
    };
    //If loading is timeout
    const handleTimeout = useCallback(() => {
        showToast("Connection timeout, please try again later.", 5000);
        //TODO: handle timeout
        auth.logout();
    }, []);

    // connect to router and hub
    let routerPromise = useRef(null);
    function getRouterMsg(){
        return new Promise((resolve, reject) => {
            routerPromise.current = resolve;
        });
    }
    async function connect2Router(userName) {
        ws.webSocket.sendMessage(HANDSHAKE2ROUTER_HEADER + userName);
        let msg = await getRouterMsg();
        console.log("msg: " + msg);
        const params = msg.split("://");
        if(params[0] == "SHAKEHAND"){
            return params[1] == "success" ? [true, msg] : [false, msg];
        }
        else return [false, msg];
    };
    let hubPromise = useRef(null);
    function getHubMsg(){
        return new Promise((resolve, reject) => {
            hubPromise.current = resolve;
        });
    }
    async function connect2Hub(userName, ndnAdress, password) {
        // FIRST: connect to router
        if(!isConn2Router.current){
            const [isOk, msg] = await connect2Router(userName);
            if(isOk){
                console.log("success to connect to router");
                isConn2Router.current = true;
            }
            else{
                toastRef.current.showToast("Fail to connect to router");
                console.log("fail to connect to router, the message is: " + msg);
                stopLoading();
                return false;
            }
        }

        if(isConn2Router.current){
            ws.webSocket.sendMessage(INTEREST_HEADER + ndnAdress + "/" + HANDSHAKE2HUB_FILE);
            let serverHello = await getHubMsg();
            let packet = serverHello.split("://")[1];
            let [publicKey, serverRandom] = packet.split("//");
        }
        toastRef.current.showToast("Success to connect");
        stopLoading();
        return true;
    }


    // handle submit
    const handleSubmit = (userName, ndnAdress, password, from, navigate) => {
        // forbidden empty input
        if (userName === "" || ndnAdress === "" || password === "") {
            showToast("Please fill in all the fields");
            return;
        }

        // check the connection status
        if (connectionStatus !== "Open") {
            showToast("You don't have the Internet!");
            return;
        }

        // start loading
        startLoading();

        
        // Start actions after loading mask is shown
        setTimeout( async () => {
            let isOk = await connect2Hub(userName, ndnAdress, password);
            if(isOk){
                auth.login(userName, ndnAdress, password, navigate(from, { replace: true }));
            }
            else{
                auth.logout(navigate("/login", { replace: true }));
            }
            //setIsAuthenticated(true);
        }, animationDuration);


    };

//    // send message to websocket server when rendering
//    useEffect(() => {
//        webSocket.sendMessage("Hello");
//
//    }, []);
//    // listen to websocket server

    useEffect(() => {
        ws.onRefresh.current = connect2Hub;
        ws.onmessage.current = (event) => {
            const msg = event.data;
            
            console.log("got a msg:" + msg);
    
            if ((msg.split("://")[0] == "SHAKEHAND" || msg.split("://")[0] == "E_SHAKEHAND") && routerPromise.current != null){
                routerPromise.current(msg);
            }
            // if we haven't connected to hub, we should process the message with different method
            else if (msg.split("://")[0] == "DATA" && !isConn2Hub.current && hubPromise.current != null){
                hubPromise.current(msg);
            }
        };
    }, []);


    return (
        <>
            <MyToast ref={toastRef} />
            <div className='main-container' style={{width: "100%", height: "100%"}}>
                <Router>
                    <Routes>
                        <Route path="/login" element={<EntryPage onSubmit={handleSubmit} isSubmiting={isLoading}/>}/>
                        <Route path="/" element={
                            <AuthChecker>
                                <HomePage/>
                            </AuthChecker>
                        }/>
                        <Route path="*" element={<h1>Not Found</h1>}/>
                    </Routes>
                </Router>
            </div>
            <LoadingMask ref={loadingMaskRef} animationDuration={animationDuration} onTimeout={handleTimeout} />
        </>
    )
};

// get websocket context
function useWs() {
    const ws = useContext(WsContext);
    return ws;
}
// get authentication context
function useAuth() {
    const auth = useContext(MyAuthContext);
    return auth;
}

// component for checking the authentication
function AuthChecker({ children }) {
    let { user } = useAuth();
    let location = useLocation();
    let [count, setCount] = useState(0);

    if(user){
        return(
            <>
                {children}
            </>
        );
    }
    return (
        <Navigate to="/login" state={{from: location}} replace />
    );
};



export default MainPage;