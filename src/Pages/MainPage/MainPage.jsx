import { useState, useCallback, useEffect, useRef, useContext, } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate, useLocation, json } from 'react-router-dom';
import { ReadyState } from 'react-use-websocket';
import forge from 'node-forge';

import EntryPage from '../EntryPage/EntryPage.jsx';
import LoadingMask from '../../Components/LoadingMask';
import MyToast from '../../Components/MyToast';
import HomePage from '../HomePage/HomePage';

import { MyAuthContext } from '../../Components/AuthContext';
import { WsContext } from '../../Components/WsContext';
import { HANDSHAKE2ROUTER_HEADER, INTEREST_HEADER, HANDSHAKE2HUB_HELLO, HANDSHAKE2HUB_LOGIN_PERMIT, SENSORS_FILE, SENSORS_DATA_FILE, COMMAND_SWITCH, COMMAND_TEMPERATURE, HANDSHAKE2HUB_LOGOUT, formatINTEREST } from '../../Const/Const.jsx';
import { set } from 'animejs';

function MainPage (){

    const isConn2Router = useRef(false);
    const isConn2Hub = useRef(false);
    const [isLogin, setIsLogin] = useState(false);
    const {publicKeyTemp, setPublicKeyTemp} = useContext(MyAuthContext);


    // For NDN first connect authentication
    const {user, logout, login} = useAuth();

    // Get websocket context
    const ws = useWs();
    const { readyState } = ws.webSocket;
    const { setSensorsTemp, setSensorsDataTemp, sensorsTemp, sensorsDataTemp} = useContext(WsContext);
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
        logout();
    }, []);

    // connect to router and hub
    const [hasPublickey, setHasPublickey] = useState(false);
    let publicKey = useRef(null);
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
            let format_msg = formatINTEREST(ndnAdress, HANDSHAKE2HUB_HELLO);
            ws.webSocket.sendMessage(format_msg);
            // PACKET: DATA://ndnAdress/.CLIENTHELLO//{publicKey}
            const jsonHub = await getHubMsg();
            
            if(jsonHub.status == false){
                toastRef.current.showToast("Fail to connect to hub");
                return false;
            }
            else{
                console.log(jsonHub.data.publicKey);
                let pubKey_pem = jsonHub.data.publicKey;
                publicKey.current = forge.pki.publicKeyFromPem(pubKey_pem);
                setPublicKeyTemp(forge.pki.publicKeyFromPem(pubKey_pem));
                setHasPublickey(true);
                
                let encryptedUserName = encrypt_format_to_hub(userName);
                let encryptedPassword = encrypt_format_to_hub(password);

                let param = encryptedPassword + "//" + encryptedUserName;
                let format_msg = formatINTEREST(ndnAdress, HANDSHAKE2HUB_LOGIN_PERMIT, param);
                ws.webSocket.sendMessage(format_msg);

                // PACKET: DATA://ndnAdress/.LOGINPERMIT//{permit}//signature
                const jsonHub_permit = await getHubMsg();
                if(jsonHub_permit.data.permit == false){
                    toastRef.current.showToast("Fail to connect to hub. Please check your password.");
                    isConn2Hub.current = false;
                }
                else{
                    isConn2Hub.current = true;
                }
            }
        };
        if(isConn2Hub.current){
            toastRef.current.showToast("Success to connect");
            setIsLogin(true);
            setTimeout(() => {
                stopLoading();
            }, 1000);
        }
        else{
            toastRef.current.showToast("Fail to connect to hub. Please check your password.");
            setIsLogin(false);
            stopLoading();
            return false;
        }
        return true;
    };

    const encrypt_format_to_hub = (plaintext) => {
        let encrypt = publicKey.current.encrypt(plaintext, "RSA-OAEP", {md: forge.md.sha256.create()});
        let encrypt_b64 = forge.util.encode64(encrypt);
        // replace all the '/' with '|'
        let modifiedEncrypt_b64 = encrypt_b64.replace(/\//g, '|');
        return modifiedEncrypt_b64;
    };

    // Process DATA packet
    const processDATA = (msg, publicKey = null) => {
        // PACKET: DATA://HubName/fileName/.sensors//data//signature
        let packet = msg.split("://", 2)[1];
        let packetList = packet.split("//");
        let dataNameList = packetList[0].split("/");
        let targetName = dataNameList[0];
        let fileName = dataNameList[dataNameList.length - 1];
        let contentBlockList = packetList[1];
        let data = contentBlockList.replace(/\|/g, '/');

       
        let signature = (packetList.length == 3) ? packetList[2].replace(/\|/g, '/') : null;

        let jsonData = JSON.parse(data);
        let jsonMsg = {};

        
        if (signature != null){
            let signature_bytes = forge.util.decode64(signature);
            let md = forge.md.sha256.create();
            md.update(JSON.stringify(jsonData), 'utf8');
            
            console.log(publicKey.current);
            //let verified = publicKey.current.verify(md.digest().bytes(), signature_bytes);
            let verified = true;
            if (!verified){
                console.log("Received a DATA packet ==> " + msg + ", but the signature is not correct");
                jsonMsg.status = false;
            }
        }
        

        if (user != null){
            if(targetName != user.ndnAdress){
                console.log("Received a DATA packet ==> " + msg + ", but the target is not me");
                jsonMsg.status = false;
            }
        }
        
        jsonMsg.status = true;
        jsonMsg.fileName = fileName;
        jsonMsg.data = jsonData;
        jsonMsg.signature = signature;
        
        return jsonMsg;
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
                login(userName, ndnAdress, password, navigate(from, { replace: true }));
            }
            else{
                logout(navigate("/login", { replace: true }));
                setIsLogin(false);
            }
            //setIsAuthenticated(true);
        }, animationDuration);


    };

    // handle logout
    const handleLogout = () => {
        let userName = user.userName;
        let encryptedUserName = encrypt_format_to_hub(userName);
        let format_msg = formatINTEREST(user.ndnAdress, HANDSHAKE2HUB_LOGOUT, encryptedUserName);
        ws.webSocket.sendMessage(format_msg);
        logout();
    }


    useEffect(() => {
        const handleData = (jsonMsg) => {
            let fileName = jsonMsg.fileName;
            let data = jsonMsg.data;
    
            if(fileName == HANDSHAKE2HUB_LOGIN_PERMIT){
                //pass
            }
            else if(fileName == HANDSHAKE2HUB_LOGOUT){
                if(jsonMsg.data.status){
                    toastRef.current.showToast("Success to logout");
                }
            }
            else if(fileName == SENSORS_FILE){
                setSensorsTemp(data);
                //TODO
            }
            else if(fileName == SENSORS_DATA_FILE){
                setSensorsDataTemp(data);
                //TODO
            }
            else if(fileName == COMMAND_SWITCH){
                if(jsonMsg.data.status){
                    toastRef.current.showToast("Success to switch");
                }
                //TODO
            }
            else if(fileName == COMMAND_TEMPERATURE){
                //TODO
            }
        };

        ws.onRefresh.current = connect2Hub;
        ws.onmessage.current = (event) => {
            const msg = event.data;
            
            console.log("for debug: got a msg:" + msg);
    
            if ((msg.split("://")[0] == "SHAKEHAND" || msg.split("://")[0] == "E_SHAKEHAND") && routerPromise.current != null){
                routerPromise.current(msg);
            }
            // if we haven't connected to hub, we should process the message with different method
            else if (msg.split("://")[0] == "DATA"){
                let jsonMsg = processDATA(msg, publicKey.current);
                console.log(jsonMsg);
                if (jsonMsg.fileName == HANDSHAKE2HUB_HELLO){
                    hubPromise.current(jsonMsg);
                }
                else if (jsonMsg.fileName == HANDSHAKE2HUB_LOGIN_PERMIT){
                    console.log("for debug: in permit:" + jsonMsg);
                    hubPromise.current(jsonMsg);
                }
                else{
                    handleData(jsonMsg);
                }
            }
        };
        
        
    }, [user]);

    useEffect(() => {
        console.log(isLogin);
        console.log(publicKey.current);
        let timedTask = null;
        if (user != null && publicKey.current != null){

            timedTask = setInterval(() => {
                console.log(publicKey.current);
                let _userName = user.userName;
                let _encryptedUserName = encrypt_format_to_hub(_userName);
                let _format_msg = formatINTEREST(user.ndnAdress, SENSORS_FILE, _encryptedUserName);
                ws.webSocket.sendMessage(_format_msg);

                let userName = user.userName;
                let encryptedUserName = encrypt_format_to_hub(userName);
                let format_msg = formatINTEREST(user.ndnAdress, SENSORS_DATA_FILE, encryptedUserName);
                ws.webSocket.sendMessage(format_msg);
            }, 5000);
        }

        return () => {
            if (timedTask != null){
                clearInterval(timedTask);
            }
        }
    }, [user, isLogin]);


    return (
        <>
            <MyToast ref={toastRef} />
            <div className='main-container' style={{width: "100%", height: "100%"}}>
                <Router>
                    <Routes>
                        <Route path="/login" element={<EntryPage onSubmit={handleSubmit} isSubmiting={isLoading}/>}/>
                        <Route path="/" element={
                            <AuthChecker>
                                <HomePage onLogout={handleLogout} _encrypt_format_to_hub={encrypt_format_to_hub}/>
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