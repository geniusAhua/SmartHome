#writen by @Liangyu Chen
import ast

class FIB:
    def __init__(self):
        self.__fib = {}  # {'target_name': [next_hop, ...]}

    def get_fib(self):
        return self.__fib

    def select_nexthop(self, targetname):
        if targetname in self.__fib:
            item = self.__fib[targetname]
            return item[0]
        else: return None

    def update_fib(self, pre_name, targetname):
        if targetname in self.__fib:
            if pre_name not in self.__fib[targetname]:
                self.__fib[targetname] += [pre_name]
        else:
            self.__fib[targetname] = [pre_name]

    def add_nexthop_fib(self, next_hop_name):
        self.__fib[next_hop_name] = []
        self.__fib[next_hop_name].append(next_hop_name)

    def delete_nexthop_fib(self, next_hop_name):
        for k, v in self.__fib.items():
            for next in v:
                if(next_hop_name == next):
                    v.remove(next)
        for k in list(self.__fib.keys()):
            if len(self.__fib[k]) == 0:
                del self.__fib[k]

    def broadcast_list(self):
        broadcast_list = []
        for k, v in self.__fib.items():
            if k == v[0]:
                broadcast_list.append(v[0])
        return broadcast_list
    
    def clear(self):
        self.__fib.clear()