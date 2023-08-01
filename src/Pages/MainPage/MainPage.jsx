import { useState, useCallback, useEffect, useRef, useContext, } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate, useLocation, json } from 'react-router-dom';
import { ReadyState } from 'react-use-websocket';

import EntryPage from '../EntryPage/EntryPage.jsx';
import LoadingMask from '../../Components/LoadingMask';
import MyToast from '../../Components/MyToast';
import HomePage from '../HomePage/HomePage';

import { MyAuthContext } from '../../Components/AuthContext';
import { WsContext } from '../../Components/WsContext';
import { SOCKET_URL, HANDSHAKE2ROUTER_HEADER, INTEREST_HEADER, HANDSHAKE2HUB_HELLO, SENSORS_FILE, SENSORS_DATA_FILE } from '../../Const/Const.jsx';

function MainPage (){

    const [NDNurl, setNDNurl] = useState(null);
    const isConn2Router = useRef(false);
    const isConn2Hub = useRef(false);

    // encrypt. with HUB
    const publicKey = useRef(null);

    // For NDN first connect authentication
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
            };
        };

        if(isConn2Router.current){
            // SECOND: connect to hub
            format_msg = formatINTEREST(ndnAdress, HANDSHAKE2HUB_HELLO);
            ws.webSocket.sendMessage(format_msg);
            // PACKET: DATA://ndnAdress/.CLIENTHELLO//publicKey
            let jsonHub = await getHubMsg();
            
            if(jsonHub.status == false){
                toastRef.current.showToast("Fail to connect to hub");
                return false;
            }
            else{
                publicKey.current = jsonHub.data;
                console.log("for debug: " + publicKey.current);
            }
        };
        toastRef.current.showToast("Success to connect");
        stopLoading();
        return true;
    };

    // Process DATA packet
    const processDATA = async (msg) => {
        // PACKET: DATA://HubName/fileName/.sensors//T//data//signature
        let packet = msg.split("://")[1];
        let packetList = packet.split("//", 2);
        let dataNameList = packetList.split("/");
        let targetName = dataNameList[0];
        let fileName = dataNameList[dataNameList.length - 1];
        let contentBlockList = packetList[1].split("//");
        let data = contentBlockList[0];

        let signature = (contentBlockList.length == 2) ? contentBlockList[1] : null;

        let jsonData = JSON.parse(data);
        let jsonMsg = {};

        if (targetName != auth.user.ndnAdress){
            console.log("Received a DATA packet ==> " + msg + ", but the target is not me");
            jsonMsg.status = false;
        }
        else{
            jsonMsg.status = true;
            jsonMsg.fileName = fileName;
            jsonMsg.data = jsonData;
            jsonMsg.signature = signature;
        }
    };

    const handleData = (jsonMsg) => {
        if(fileName == HANDSHAKE2HUB_HELLO){
            // Save the public key
            publicKey.current = data;
            return true;
        }
        else if(fileName == HANDSHAKE2HUB_RANDOM){
            //TODO
        }
        else if(fileName == HANDSHAKE2HUB_LOGIN_PERMIT){
            //TODO
        }
        else if(fileName == SENSORS_FILE){
            //TODO
        }
        else if(fileName == SENSORS_DATA_FILE){
            //TODO
        }
        else if(fileName == COMMAND_SWITCH){
            //TODO
        }
        else if(fileName == COMMAND_TEMPERATURE){
            //TODO
        }
    }

    // Conmunicate with NDN
    const formatINTEREST = (ndnAdress, fileName, params = null) => {
        _mustBeFresh = true;
        if (fileName == HANDSHAKE2HUB_HELLO){
            // PACKET: INTEREST://ndnAdress/.CLIENTHELLO//F
            _mustBeFresh = false;
        }
        else if(fileName == HANDSHAKE2HUB_RANDOM){
            // PACKET: INTEREST://ndnAdress/.RANDOM//T//random
            _mustBeFresh = true;
        }
        else if(fileName == HANDSHAKE2HUB_LOGIN_PERMIT){
            // PACKET: INTEREST://ndnAdress/.LOGINPERMIT//T//encrypted
            _mustBeFresh = true;
        }
        else if(fileName == SENSORS_FILE){
            // PACKET: INTEREST://ndnAdress/.sensors//F
            _mustBeFresh = false;
        }
        else if(fileName == SENSORS_DATA_FILE){
            // PACKET: INTEREST://ndnAdress/.data//T
            _mustBeFresh = true;
        }
        else if(fileName == COMMAND_SWITCH){
            // PACKET: INTEREST://ndnAdress/.switch//T//switchValue
            _mustBeFresh = true;
        }
        else if(fileName == COMMAND_TEMPERATURE){
            // PACKET: INTEREST://ndnAdress/.temperature//T//temperatureValue
            _mustBeFresh = true;
        }

        return INTEREST_HEADER + ndnAdress + "/" + fileName + (_mustBeFresh ? "//T" : "//F") + (params == null ? "" : "//" + params);
    };


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
            else if (msg.split("://")[0] == "DATA"){
                let jsonMsg = processDATA(msg);
                if (jsonMsg.fileName == HANDSHAKE2HUB_HELLO){
                    hubPromise.current(jsonMsg);
                }
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