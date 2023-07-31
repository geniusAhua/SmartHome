#writen by @Asish Prasad Rath
class PIT():
    def __init__(self):
        self.__pit = {}

    def add_pit_item(self, dataname, incominginterface):
        if dataname not in self.__pit:
            self.__pit[dataname] = []
            self.__pit[dataname] += [incominginterface]
        else:
            if incominginterface not in self.__pit[dataname]:
                self.__pit[dataname] += [incominginterface]

    def find_item(self, dataname):
        if dataname in self.__pit:
            return self.__pit[dataname]
        else: return 0

    def isExist(self, dataname):
        if dataname in self.__pit:
            return True
        else: return False

    def delete_pit_item(self, dataname):
        if dataname in self.__pit:
            del self.__pit[dataname]

    def delete_pit_with_outface(self, outface):
        for k, v in self.__pit.items():
            if outface in v:
                v.remove(outface)
        for k in list(self.__pit.keys()):
            if len(self.__pit[k]) == 0:
                del self.__pit[k]

    def get_pit(self):
        return self.__pit

    
    
    def clear(self):
        self.__pit.clear()
