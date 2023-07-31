
export const IP = "192.168.1.169"
export const PORT = "2048"
export const SOCKET_URL = `ws://${IP}:${PORT}`
export const HANDSHAKE2ROUTER_HEADER = "SHAKEHAND://"
export const HANDSHAKE2HUB_FILE = ".CLIENTHELLO"
export const INTEREST_HEADER = "INTEREST://"
export const isEmpty = (obj) => {
    return Object.keys(obj).length === 0;
}