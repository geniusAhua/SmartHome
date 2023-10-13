#writen by @Liangyu Chen
import threading

class CS():
    def __init__(self):
        self.__cs = {}

    def find_item(self, dataname):
        if dataname in self.__cs:
            return self.__cs[dataname]
        else: return 0

    def isExist(self, dataname):
        if dataname in self.__cs:
            return True
        else: return False

    def get_cs(self):
        return self.__cs

    def add_cs_item(self, dataname, data):
        self.__cs[dataname] = data

    def delete_cs_item(self, dataname):
        self.__cs.pop(dataname, None)

    def clear(self):
        self.__cs.clear()


    