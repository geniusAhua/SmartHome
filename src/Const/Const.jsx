
export const IP = "yujunwei.love"
export const PORT = "2048"
export const SOCKET_URL = `ws://${IP}:${PORT}`
export const HANDSHAKE2ROUTER_HEADER = "SHAKEHAND://"
export const INTEREST_HEADER = "INTEREST://"
export const HANDSHAKE2HUB_HELLO = ".CLIENTHELLO"
export const HANDSHAKE2HUB_RANDOM = ".RANDOM"
export const HANDSHAKE2HUB_LOGIN_PERMIT = ".LOGINPERMIT"
export const SENSORS_FILE = ".sensors"
export const SENSORS_DATA_FILE = ".data"
export const COMMAND_SWITCH = ".switch"
export const COMMAND_TEMPERATURE = ".temperature"
export const isEmpty = (obj) => {
    return Object.keys(obj).length === 0;
}