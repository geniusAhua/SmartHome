
export const IP = "xxx.xxx.xxx.xxx"
export const PORT = ""
export const SOCKET_URL = `ws://${IP}:${PORT}`
export const HANDSHAKE2ROUTER_HEADER = "SHAKEHAND://"
export const INTEREST_HEADER = "INTEREST://"
export const HANDSHAKE2HUB_HELLO = ".CLIENTHELLO"
export const HANDSHAKE2HUB_LOGIN_PERMIT = ".LOGINPERMIT"
export const HANDSHAKE2HUB_LOGOUT = ".LOGOUT"
export const SENSORS_FILE = ".sensors"
export const SENSORS_DATA_FILE = ".data"
export const COMMAND_SWITCH = ".switch"
export const COMMAND_TEMPERATURE = ".temperature"
export const isEmpty = (obj) => {
    return Object.keys(obj).length === 0;
}
// Conmunicate with NDN
export const formatINTEREST = (ndnAdress, fileName, params = null) => {
    let _mustBeFresh = true;
    if (fileName == HANDSHAKE2HUB_HELLO){
        // PACKET: INTEREST://ndnAdress/.CLIENTHELLO//F
        _mustBeFresh = false;
    }
    else if(fileName == HANDSHAKE2HUB_LOGIN_PERMIT){
        // PACKET: INTEREST://ndnAdress/.LOGINPERMIT//T//encrypted
        _mustBeFresh = true;
    }
    else if(fileName == HANDSHAKE2HUB_LOGOUT){
        // PACKET: INTEREST://ndnAdress/.LOGOUT//T//userName
        _mustBeFresh = true;
    }
    else if(fileName == SENSORS_FILE){
        // PACKET: INTEREST://ndnAdress/.sensors//F//userName
        _mustBeFresh = true;
    }
    else if(fileName == SENSORS_DATA_FILE){
        // PACKET: INTEREST://ndnAdress/.data//T//userName
        _mustBeFresh = true;
    }
    else if(fileName == COMMAND_SWITCH){
        // PACKET: INTEREST://ndnAdress/.switch//F//switchValue//userName
        _mustBeFresh = true;
    }
    else if(fileName == COMMAND_TEMPERATURE){
        // PACKET: INTEREST://ndnAdress/.temperature//T//temperatureValue//userName
        _mustBeFresh = true;
    }

    return INTEREST_HEADER + ndnAdress + "/" + fileName + (_mustBeFresh ? "//T" : "//F") + (params == null ? "" : "//" + params);
};