import sys
import traceback
sys.path.insert(0, '../../Dissertation')
import websockets
import sys
import asyncio

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession, CompleteStyle
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter

from Module.CS import CS

from Module.FIB import FIB
from Module.PIT import PIT
from Module.SendFormat import SendFormat

    
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
    
    # process the msg for the target
    '''def __handle_HANDSHAKE'''
    async def __handle_HANDSHAKE(self, packet, from_name, from_ws):
        clientName = packet
        if clientName not in self.__connections:
            if not from_name:
                from_name += [clientName]
            else:
                # Means this connection wants to change its name
                self.__connections.pop(from_name[0], None)
                self.__PIT.delete_pit_with_outface(from_name[0])
                from_name[0] = clientName
            
            # save the connection
            self.__connections[clientName] = from_ws
            #send handshake message
            handshake_msg = SendFormat.send_(SendFormat.HANDSHAKE, "success")
            await from_ws.send(handshake_msg)
            self.__echo(f"[{clientName}] connect to this router successfully")
            return True
        else:
            err_msg = SendFormat.send_(SendFormat.E_SHAKEHAND, 'clientName already exists')
            await from_ws.send(err_msg)
            self.__echo(f"[{clientName}] already connected to this router")
            return False
    '''def __handle_HANDSHAKE'''

    '''def __handle_INTEREST'''
    async def __send_data_if_exist(self, dataName, freshToke, fromName, from_ws, originalDataName = None):
        if freshToke == "T":
            self.__echo(f"[{self.__nodeName}] received a MustBeFresh INTEREST from {fromName}, so doesn't check the CS")
            return False
       
        
        if self.__CS.isExist(dataName):
            async with self.__CS_lock:
                data = self.__CS.find_item(dataName)
            # if trans back to WAN, we need to transform the name of DATA
            formatDataPacket = SendFormat.send_(SendFormat.DATA, f"{dataName if not originalDataName else originalDataName}//{data}")
            self.__echo(f"[{self.__nodeName}] has the data and trans back to {fromName} ::: {formatDataPacket}")
            await from_ws.send(formatDataPacket)
            return True
        return False
    
    async def __add_to_pit_if_exists(self, dataName, fromName):
        if self.__PIT.isExist(dataName):
            self.__echo(f"[{self.__nodeName}] find the {dataName} in PIT and add it")
            async with self.__PIT_lock:
                self.__PIT.add_pit_item(dataName, fromName)
            return True
        return False

    async def __forward_interest_then_add_pit(self, dataName, freshToken, params, fromName, to_ws):
        transform_msg = SendFormat.send_(SendFormat.INTEREST, f"{dataName}//{freshToken}{'//'+'//'.join(params) if params else ''}")
        self.__echo(f"[{self.__nodeName}] forward interest to {fromName} ::: {transform_msg}")
        await to_ws.send(transform_msg)
        async with self.__PIT_lock:
            self.__PIT.add_pit_item(dataName, fromName)
        return
    
    async def __respond_to_interest_with_default_data(self, packet, fileName, params, fromName, from_ws):
        if fileName == ".debug":
            self.__echo(f"[{self.__nodeName}] received debug packet from {fromName}")
            await from_ws.send(SendFormat.send_(SendFormat.DATA, f"{packet}//debugPacket"))
            return True
        return False

    async def __handle_INTEREST(self, packet, fromName, from_ws):
        try:
            # Packet: INTEREST://targetName/DeviceNDNName/fileName//MustBeFresh//params
            otherList = packet.split("//")
            fileURL = otherList[0]
            freshToken = otherList[1]
            # params is a list
            params = [] if len(otherList) < 3 else otherList[2:]
            targetList = fileURL.split("/")
            dataName = None
            forward_ws = None
            originalDataName = None
            # wrong packet
            if len(targetList) < 2:
                return
            
            if targetList[0] == self.__nodeName and targetList[0] == targetList[-2]:
                # return a debug packet
                if await self.__respond_to_interest_with_default_data(fileURL, targetList[-1], params, fromName, from_ws):
                    return
            
            dataName = fileURL
            # Packet: INTEREST://targetName/DeviceNDNName/fileName//MustBeFresh//params
            if await self.__send_data_if_exist(dataName, freshToken, fromName, from_ws):
                return
            if await self.__add_to_pit_if_exists(dataName, fromName):
                return
            # forward interest
            await self.__forward_interest_then_add_pit(dataName, freshToken, params, fromName, forward_ws)
            return
        
        except Exception as e:
            self.__echo(f"An error occurred in __handle_INTEREST: {traceback.print_exc()}")
    '''def __handle_INTEREST'''

    '''def __handle_DATA'''
    async def __handle_DATA(self, packet, fromName):
        try:
            # Packet: DATA://targetName/DeviceNDNName/fileName//data//signature
            otherList = packet.split("//", 1)
            dataName = otherList[0]
            targetName = dataName.split("/")[0]
            contentBlock = otherList[1]
            if self.__PIT.isExist(dataName):
                async with self.__PIT_lock:
                    outfaces = self.__PIT.find_item(dataName)
                for outface in outfaces:
                    if outface == self.__nodeName:
                        self.__echo(f"[{self.__nodeName}] received DATA from {fromName} ===> {packet}")
                    if outface in self.__connections:
                        forward_ws = self.__connections[outface]
                        formatDataPacket = SendFormat.send_(SendFormat.DATA, f"{packet}")
                        await forward_ws.send(formatDataPacket)
                
                async with self.__CS_lock:
                    self.__CS.add_cs_item(dataName, dataName)
                async with self.__PIT_lock:
                    self.__PIT.delete_pit_item(dataName)
                async with self.__FIB_lock:
                    self.__FIB.update_fib(fromName, targetName)
                return
        
        except Exception as e:
            self.__echo(f"An error occurred in __handle_DATA: {traceback.print_exc()}")

    '''def __handle_DATA'''

    # transform the msg to the target
    '''def __transform_msg'''
    async def __transform_msg(self, msg, from_name, from_ws):
        packet = msg.split("://", 1)
        if len(packet) < 2: return
        pktHeader = packet[0]
        packet = packet[1]

        try:
            if pktHeader == SendFormat.INTEREST:
                await self.__handle_INTEREST(packet, from_name, from_ws)
                return
            
            elif pktHeader == SendFormat.DATA:
                await self.__handle_DATA(packet, from_name)
                return
        except Exception as e:
            self.__echo(f"An error occurred in __transform_msg: {traceback.print_exc()}")

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
                
                header, packet = message.split("://", 1)
                if header == SendFormat.HANDSHAKE:
                    # HANDSHAKE://clientName
                    await self.__handle_HANDSHAKE(packet, clientName, ws)
                elif not clientName:
                    self.__echo(f"Can't know the name of this connection. Please send handshake message first")
                    await ws.send(SendFormat.send_(SendFormat.E_SHAKEHAND, 'please send handshake message first'))
                else:
                    # process and transform message
                    await self.__transform_msg(message, clientName[0], ws)

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
                    
            except Exception as e:
                self.__echo(f"[{self.__nodeName}] received an error ==> {traceback.print_exc()}")

            finally:
                self.__connections.pop(clientName, None)
                await ws.close()
                self.__FIB.delete_nexthop_fib(clientName)
                self.__PIT.delete_pit_with_outface(clientName)
                self.__echo(f"[{self.__nodeName}] disconnect with {clientName}")

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
