import base64
import enum
import os
import random
import socket
import threading
import websockets
import sys
import time
import asyncio

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession, CompleteStyle
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter

from CS import CS

from FIB import FIB
from PIT import PIT
from SendFormat import SendFormat

    
class Router:
    def __init__(self, nodeName):
        self.server = None
        self.__nodeName = nodeName
        self.__URL_table = {}
        #{
        # 'targetName': 'websocket'
        # }
        self.__connections = {}
        self.__port = 2048
        self.__CS = CS()
        self.__CS_lock = asyncio.Lock()
        self.__PIT = PIT()
        self.__PIT_lock = asyncio.Lock()
        self.__FIB = FIB()
        self.__FIB_lock = asyncio.Lock()
        self.__echo_tag = 0 # 0: not echo, 1: echo received msg


    # echo info
    def __echo(self, msg):
        with patch_stdout():
            if self.__echo_tag == 1:
                print(msg)
        
    # transform the msg to the target
    '''def __transform_msg'''
    async def __transform_msg(self, msg, from_name, from_ws):
        packet = msg.split("://", 1)
        if len(packet) < 2: return
        pktHeader = packet[0]
        packet = packet[1]

        try:
            if pktHeader == SendFormat.HANDSHAKE:
                clientName = packet
                if clientName not in self.__connections:
                    if not from_name:
                        from_name += [clientName]
                    else:
                        self.__connections.pop(from_name[0], None)
                        self.__FIB.delete_nexthop_fib(from_name[0])
                        self.__PIT.delete_pit_with_outface(from_name[0])
                        from_name[0] = clientName
                    
                    self.__connections[clientName] = from_ws
                    #send handshake message
                    handshake_msg = SendFormat.send_(SendFormat.HANDSHAKE, "success")
                    await from_ws.send(handshake_msg)
                    self.__echo(f"[{clientName}] connect to this router successfully")
                    self.__FIB.add_nexthop_fib(clientName)
                    return
                else:
                    err_msg = SendFormat.send_(SendFormat.E_SHAKEHAND, 'clientName already exists')
                    await from_ws.send(err_msg)
                    self.__echo(f"[{clientName}] already connected to this router")
                    return
            # check if the ws has a name
            elif not from_name:
                await from_ws.send(SendFormat.send_(SendFormat.E_SHAKEHAND, 'please send handshake message first'))
                return

            elif pktHeader == SendFormat.INTEREST:
                target = packet.split("/")
                # wrong packet
                if len(target) < 2: return
                if target[-2] == self.__nodeName:
                    if target[-1] == ".debug":
                        await from_ws.send(SendFormat.send_(SendFormat.DATA, f"{packet}//debugPacket"))
                        return
                        
                if self.__CS.isExist(packet):
                    # send data
                    async with self.__CS_lock:
                        data = self.__CS.find_item(packet)
                        await from_ws.send(SendFormat.send_(SendFormat.DATA, packet + "//" + data))
                        return
                
                else:
                    if self.__PIT.isExist(packet):
                        async with self.__PIT_lock:
                            self.__PIT.add_pit_item(packet, from_name[0])
                        return
                    else:
                        async with self.__PIT_lock:
                            self.__PIT.add_pit_item(packet, from_name[0])
                        # forward interest
                        async with self.__FIB_lock:
                            next_hop_name = self.__FIB.select_nexthop(packet)
                        if next_hop_name is not None and next_hop_name in self.__connections:
                            forward_ws = self.__connections[next_hop_name]
                            await forward_ws.send(msg)
                            return
                            
                        else:
                            # broadcast
                            async with self.__FIB_lock:
                                broadcast_list = self.__FIB.broadcast_list()
                            for _next in broadcast_list:
                                if _next != from_name[0]:
                                    forward_ws = self.__connections[_next]
                                    self.__echo(f"[{from_name[0]}] broadcast interest to [{_next}]")
                                    await forward_ws.send(msg)
                            return
            
            elif pktHeader == SendFormat.DATA:
                dataPacket = packet.split("//", 1)
                if self.__PIT.isExist(dataPacket[0]):
                    async with self.__PIT_lock:
                        outfaces = self.__PIT.find_item(dataPacket[0])
                    for outface in outfaces:
                        if outface in self.__connections:
                            forward_ws = self.__connections[outface]
                            await forward_ws.send(msg)
                    
                    async with self.__CS_lock:
                        self.__CS.add_cs_item(dataPacket[0], dataPacket[1])
                    async with self.__PIT_lock:
                        self.__PIT.delete_pit_item(dataPacket[0])
                    async with self.__FIB_lock:
                        self.__FIB.update_fib(from_name[0], dataPacket[0].split("/")[0])
                    return
        except Exception as e:
            self.__echo(f'An error occurred: {e}')
            return
    '''def __transform_msg'''

    # for the other routers which connect to this router
    async def __handle_client(self, ws, path):
        clientName = []
        try:
            async for message in ws:
                if clientName == []:
                    self.__echo(f"get a message: '{message}'")
                else:
                    self.__echo(f"[{clientName[0]}] send '{message}'")
                # transform message
                await self.__transform_msg(message, clientName, ws)

        except websockets.exceptions.ConnectionClosedError:
            pass
        finally:
            if clientName:
                self.__echo(f"[{clientName[0]}] disconnect from this router")
                self.__connections.pop(clientName[0], None)
                self.__FIB.delete_nexthop_fib(clientName[0])
                self.__PIT.delete_pit_with_outface(clientName[0])

    # connect to another node
    async def connect(self, clientName):
        # connect to another node
        async with websockets.connect(self.__URL_table[clientName]) as ws:
            # send hello message
            await ws.send(SendFormat.send_(SendFormat.HANDSHAKE, self.__nodeName))

            response = await ws.recv()

            header, _success = response.split("://", 1)
            if header == SendFormat.HANDSHAKE and _success == "success":
                # connection established
                self.__echo(f"[{self.__nodeName}] connect to the router - [{clientName}] successfully")
                self.__connections[clientName] = ws
                self.__FIB.add_nexthop_fib(clientName)
            else:
                self.__echo(f"[{self.__nodeName}] connect to the router - [{clientName}] failed")
                return

            try:
                async for message in ws:
                    self.__echo(f"[{clientName}] send '{message}'")
                    # transform message
                    await self.__transform_msg(message, clientName, ws)

            finally:
                self.__connections.pop(clientName, None)

    # clear cs and pit
    async def clear_CS_PIT(self):
        async with self.__CS_lock:
            self.__CS.clear()
        async with self.__PIT_lock:
            self.__PIT.clear()

    # disconnect from another node
    async def disconnect(self, targetName):
        # find target websocket
        target_ws = self.__connections.get(targetName)
        # close connection
        await target_ws.close()
        # remove connection from connections
        self.__connections.pop(target_ws, None)

    # close
    async def close(self):
        # close all connections
        for key, ws in list(self.__connections.items()):
            await ws.close()
            self.__connections.pop(key, None)
        # clear 
        self.__CS.clear()
        self.__PIT.clear()
        self.__FIB.clear()
        # close server
        self.server_task.cancel()
        try:
            await self.server_task
        except asyncio.CancelledError:
            pass
    
    # change the echo tag
    def showEcho(self):
        self.__echo_tag = 1
        self.__echo(f"[{self.__nodeName}] echo is on")

    def shutEcho(self):
        self.__echo(f"[{self.__nodeName}] echo is off")
        self.__echo_tag = 0

    async def main(self):
        self.server = websockets.serve(self.__handle_client, "0.0.0.0", self.__port)
        self.server_task = asyncio.ensure_future(self.server)
        await asyncio.Future()  # run forever

    async def run(self):
        print(f"[{self.__nodeName}] is running...")
        try:
            await self.main()
        except KeyboardInterrupt:
            await self.close()

    async def showPIT(self):
        async with self.__PIT_lock:
            return self.__PIT.get_pit()
    
    async def showCS(self):
        async with self.__CS_lock:
            return self.__CS.get_cs()
    
    async def showFIB(self):
        async with self.__FIB_lock:
            return self.__FIB.get_fib()




class _Prompt():
    __cli_header = f'router-cli@'
    @staticmethod
    def begining(name = ''):
        _Prompt.__cli_header += str(name)
        return _Prompt.__cli_header + ' >'
    
    @staticmethod
    def running_bind():
        return _Prompt.__cli_header + f'-running >'


class Command():
    SET_NAME = 'set-name' #set-name -name
    SHOW_MSG = 'show-msg' #show-msg this is for showing information about connection
    SHUT_SHOW_MSG = 'shut-show-msg' #shut-show-msg
    CONNECT = 'connect' #connect -next_device
    SHOWCS = 'show-cs' #debug: show-cs Show Content Store
    SHOWPIT = 'show-pit' #debug: show-pit Show Pending Interest Table
    SHOWFIB = 'show-fib' #debug: show-fib Show Forward Information Base
    CLEARCS = 'clear-cs' #debug: clear-cs Clear Content Store
    CLEARPIT = 'clear-pit' #debug: clear-pit Clear Pending Interest Table

    @staticmethod
    def not_found(input):
        print(f'Command "{input}" not found.')
    
    @staticmethod
    def connect_failed(target_name):
        print(f'There has something wrong to connect to {target_name}.')



class Demo:
    def __init__(self):
        self.__nodeName = None
        self.__ndn = None


    async def __cli_input(self):
        try:
            #add a key binding to quit the cli
            isLoop = True
            kb = KeyBindings()
            @kb.add('escape')
            @kb.add('c-c')
            async def _(event):
                nonlocal isLoop
                isLoop = False
                event.app.exit()

            @kb.add('c-d')#debug 
            async def _(event):
                if self.__ndn != None:
                    self.__ndn.showEcho()
                else:
                    print("Please open network first.")

            #welcom text
            welcom_text = "Welcom to use ndn Router.\nYou can press 'escape' or 'Control + c' to quit.\nPlease set Router name first. Use set-name [name].\n"
            print(welcom_text)
            #set history
            history = InMemoryHistory()
            history.append_string(Command.SET_NAME)
            history.append_string(Command.CONNECT)
            history.append_string(Command.SHOW_MSG)
            history.append_string(Command.SHUT_SHOW_MSG)
            history.append_string(Command.SHOWPIT)
            history.append_string(Command.SHOWFIB)
            history.append_string(Command.SHOWCS)
            history.append_string(Command.CLEARCS)
            history.append_string(Command.CLEARPIT)

            command_c = WordCompleter([
                Command.SET_NAME,
                Command.CONNECT,
                Command.SHOW_MSG,
                Command.SHUT_SHOW_MSG,
                Command.SHOWPIT,
                Command.SHOWFIB,
                Command.SHOWCS,
                Command.CLEARCS,
                Command.CLEARPIT,
            ],
            ignore_case=True,
            )
            #Create Prompt
            session = PromptSession(history=history, enable_history_search=True)
            prompt = _Prompt.begining
            
            #Run echo loop.
            while isLoop:
                try:
                    commandline = await session.prompt_async(prompt, key_bindings = kb, auto_suggest=AutoSuggestFromHistory(), completer=command_c, complete_while_typing=True)
                    if commandline != None and commandline != '':
                        command = commandline.split(" ")

                        if not self.__nodeName:
                            if command[0] == Command.SET_NAME:
                                if len(command) != 2:
                                    print(f"The expression is wrong. Please check it. {command[0]} [name]")
                                else:
                                    self.__nodeName = command[1]
                                    prompt = _Prompt.begining(self.__nodeName)
                                    self.__ndn = Router(self.__nodeName)
                                    asyncio.create_task(self.__ndn.run())
                                    prompt = _Prompt.running_bind
                            else:
                                print("Please set your name first!")
                        
                        else:
                            if command[0] == Command.SHOW_MSG:
                                with patch_stdout():
                                    self.__ndn.showEcho()
                            
                            elif command[0] == Command.SHUT_SHOW_MSG:
                                with patch_stdout():
                                    self.__ndn.shutEcho()

                            elif command[0] == Command.CONNECT:
                                if len(command) != 2:
                                    print(f'The expression is wrong. please check it. {command[0]} [name]')
                                else:
                                    target_name = command[1]
                                    with patch_stdout():
                                        asyncio.create_task(self.__ndn.connect(target_name))

                            elif command[0] == Command.SHOWCS:
                                with patch_stdout():
                                    cs_ = await self.__ndn.showCS()
                                    if len(cs_) == 0:
                                        print("There is no item in Content Store.")
                                    else: print(cs_)

                            elif command[0] == Command.SHOWPIT:
                                with patch_stdout():
                                    pit_ = await self.__ndn.showPIT()
                                    if len(pit_) == 0:
                                        print("There is no item in Pending Interest Table.")
                                    else: print(pit_)
                            
                            elif command[0] == Command.SHOWFIB:
                                with patch_stdout():
                                    fib_ = await self.__ndn.showFIB()
                                    if len(fib_) == 0:
                                        print("There is no item in Forward Informant Base.")
                                    else: print(fib_)
                            
                            elif command[0] == Command.CLEARCS:
                                with patch_stdout():
                                    await self.__ndn.clear_CS_PIT()
                                    print("Content Store is cleared.")
                            
                            elif command[0] == Command.CLEARPIT:
                                with patch_stdout():
                                    await self.__ndn.clear_CS_PIT()
                                    print("Pending Interest Table is cleared.")

                            elif command != None:
                                with patch_stdout():
                                    Command.not_found(command)
                except KeyboardInterrupt:
                    pass
                except (EOFError):
                    return
        except Exception as e:
            print(f'An error occurred: {e}')

    async def __main(self):
        with patch_stdout():
            try:
                await self.__cli_input()
            except Exception as e:
                print(f'An error occurred: {e}')
            finally:
                # close all connections
                if self.__ndn != None:
                    await self.__ndn.close()
            print("\nQuitting CLI. Bye.\n")

    def run(self):
        try:
            from asyncio import run
        except ImportError:
            asyncio.run_until_complete(self.__main())
        else:
            asyncio.run(self.__main())
    '''<<< CLI and thread things'''


if __name__ == '__main__':
    demo = Demo()
    demo.run()
