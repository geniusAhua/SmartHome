class SendFormat():
    #The values of these variables must be as same as the end of private function
    HANDSHAKE = 'SHAKEHAND'
    INTEREST = 'INTEREST'
    DATA = 'DATA'
    E_SHAKEHAND = 'E_SHAKEHAND'

    @classmethod
    def __sendSHAKEHAND(cls, param):
        return f"SHAKEHAND://{param}"
    
    @classmethod
    def __sendE_SHAKEHAND(cls, param):
        return f"E_SHAKEHAND://{param}"

    @classmethod
    def __sendINTEREST(cls, param):
        return f"INTEREST://{param}",

    @classmethod
    def __sendDATA(cls, param):
        return f"DATA://{param}",#param = {dataname}:{data}

    @classmethod
    def __Default(cls, param):
        return f"Can't send this type of packag: {param}",

    @classmethod
    def send_(cls, type_, param):
        sendtype = "_SendFormat__send" + type_
        fun = getattr(cls, sendtype, cls.__Default)
        return fun(param)