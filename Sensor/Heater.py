import sys
import traceback
sys.path.insert(0, '/home/ahua/Dissertation')
import json
import websockets
import asyncio

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession, CompleteStyle
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter

from Module.SendFormat import SendFormat

class Sensor:
    def __init__(self, nodeName):
        self.server = None
        self.__nodeName = nodeName
        self.__URL_table = {"Hub": "ws://192.168.1.64:2000"}
        self.__ws = None
        self.__sensorType = "Heater"
        self.__status = "off"
        self.__temperature = 50
        self.__echo_tag = 0 # 0: not echo, 1: echo received msg

    # echo info
    def __echo(self, msg):
        with patch_stdout():
            if self.__echo_tag == 1:
                print(msg)
        
    # process the msg
    '''def __handle_INTEREST'''
    async def __respond_to_interest_with_data(self, dataName, _fileName, params, fromName, from_ws):
        # Packet: INTEREST://NDNName/file//data1//data2//...
        fileName = _fileName
        
        if fileName == ".debug":
            self.__echo(f"[{self.__nodeName}] received <debug> packet from {fromName}")
            await from_ws.send(SendFormat.send_(SendFormat.DATA, f"{dataName}//debugPacket"))
            return True
        elif fileName == ".data":
            self.__echo(f"[{self.__nodeName}] received <.data> packet from {fromName}")
            sensorData = {}
            sensorData["status"] = self.__status
            sensorData["temperature"] = self.__temperature
            _json_obj = json.dumps(sensorData)
            await from_ws.send(SendFormat.send_(SendFormat.DATA, f"{dataName}//{_json_obj}"))
            return True
        elif fileName == ".switch":
            self.__echo(f"[{self.__nodeName}] received <.switch> packet from {fromName}")
            self.__status = params[0]
            jsonData = {}
            jsonData["status"] = "success"
            _json_obj = json.dumps(jsonData)
            await from_ws.send(SendFormat.send_(SendFormat.DATA, f"{dataName}//{_json_obj}"))
        elif fileName == ".temperature":
            data = params[0]
            self.__echo(f"[{self.__nodeName}] received <.temperature> packet from {fromName}")
            self.__temperature = int(data)
            jsonData = {}
            jsonData["status"] = "success"
            _json_obj = json.dumps(jsonData)
            await from_ws.send(SendFormat.send_(SendFormat.DATA, f"{dataName}//{_json_obj}"))
        return False

    async def __handle_INTEREST(self, packet, fromName, from_ws):
        # Packet: INTEREST://NDNName/file//MustBeFresh//data1//data2//...
        otherList = packet.split("//")
        fileURL = otherList[0]
        freshToken = otherList[1]
        # params is a list
        params = None if len(otherList) < 3 else otherList[2:]
        targetList = fileURL.split("/")
        # wrong packet
        if targetList[0] != self.__nodeName:
            return
        if len(targetList) < 2:
            return
        
        if targetList[-2] == self.__nodeName and targetList[0] == targetList[-2]:
            # return a debug packet
            if await self.__respond_to_interest_with_data(fileURL, targetList[-1], params, fromName, from_ws):
                return
        self.__echo(f"[{self.__nodeName}] can't handle this INTEREST ==> {packet}")
        return
    '''def __handle_INTEREST'''

    '''def __handle_DATA'''
    async def __handle_DATA(self, packet, fromName):
        dataName, data = packet.split("//", 1)
        self.__echo(f"[{self.__nodeName}] received data from {fromName} ==> {packet}\n\ndataName: {dataName}\ndata: {data}")
    '''def __handle_DATA'''

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
                
            # DATA://targetName/DeviceNDNName/fileName//data1//data2//...
            elif pktHeader == SendFormat.DATA:
                await self.__handle_DATA(packet, from_name)
                return
                        
        except Exception as e:
            self.__echo(f'An error occurred in __transform_msg: {traceback.print_exc()}')
            return
    '''def __transform_msg'''

    async def send_interest(self, targetName, fileName):
        formatPacket = SendFormat.send_(SendFormat.INTEREST, f"{targetName}/{fileName}")
        ws = self.__ws
        self.__echo(f"[{self.__nodeName}] send interest to {targetName} ::: {formatPacket}")
        await ws.send(formatPacket)


    # connect to another node
    async def connect(self, clientName):

        if self.__ws:
            self.__echo(f"[{self.__nodeName}] already connected to the Hub, we will disconnect it")
            await self.__ws.close()
            self.__ws = None
            self.__echo(f"[{self.__nodeName}] disconnect to the Hub successfully")

        # connect to another node
        async with websockets.connect(self.__URL_table[clientName]) as ws:
                
            # send hello message
            await ws.send(SendFormat.send_(SendFormat.HANDSHAKE, f"{self.__nodeName}//{self.__sensorType}"))

            response = await ws.recv()

            header, _success = response.split("://", 1)
            if header == SendFormat.HANDSHAKE and _success == "success":
                # connection established
                self.__echo(f"[{self.__nodeName}] connect to the Hub - [{clientName}] successfully")
                self.__ws = ws
            else:
                self.__echo(f"[{self.__nodeName}] connect to the Hub - [{clientName}] failed ::: {response}")
                return

            try:
                async for message in ws:
                    self.__echo(f"[{clientName}] send '{message}'")
                    # transform message
                    await self.__transform_msg(message, clientName, ws)
            except Exception as e:
                self.__echo(f"[{self.__nodeName}] received an error ==> {traceback.print_exc()}")
                
            finally:
                await ws.close()
                self.__ws = None
                self.__echo(f"[{self.__nodeName}] disconnect with {clientName}")

    # disconnect from another node
    async def disconnect(self):
        await self.__ws.close()

    # close
    async def close(self):
        # close all connections
        if self.__ws:
            await self.__ws.close()
    
    # change the echo tag
    def showEcho(self):
        self.__echo_tag = 1
        self.__echo(f"[{self.__nodeName}] echo is on")

    def shutEcho(self):
        self.__echo(f"[{self.__nodeName}] echo is off")
        self.__echo_tag = 0
    
    async def sendDebug(self, target):
        ws = self.__ws
        await ws.send(SendFormat.send_(SendFormat.INTEREST, f"{target}/.debug//T"))

        return




class _Prompt():
    __cli_header = f'sensor-cli@'
    @staticmethod
    def begining(name = ''):
        _Prompt.__cli_header += str(name)
        return _Prompt.__cli_header + ' >'
    
    @staticmethod
    def running_bind():
        return _Prompt.__cli_header + f'-running >'


class Command():
    SHOW_MSG = 'show-msg' #show-msg this is for showing information about connection
    SHUT_SHOW_MSG = 'shut-show-msg' #shut-show-msg
    CONNECT = 'connect' #connect [next_device_name]
    SENDDEBUG = 'send-debug' #debug: send-debug [target]

    @staticmethod
    def not_found(input):
        print(f'Command "{input}" not found.')
    
    @staticmethod
    def connect_failed(target_name):
        print(f'There has something wrong to connect to {target_name}.')



class Demo:
    def __init__(self):
        self.__nodeName = "Heater"
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
            welcom_text = f"Welcom to use ndn {self.__nodeName}.\nYou can press 'escape' or 'Control + c' to quit.\n\n"
            print(welcom_text)
            #set history
            history = InMemoryHistory()
            history.append_string(Command.CONNECT)
            history.append_string(Command.SHOW_MSG)
            history.append_string(Command.SHUT_SHOW_MSG)
            history.append_string(Command.SENDDEBUG)

            command_c = WordCompleter([
                Command.CONNECT,
                Command.SHOW_MSG,
                Command.SHUT_SHOW_MSG,
                Command.SENDDEBUG,
            ],
            ignore_case=True,
            )
            #start Heater
            self.__ndn = Sensor(self.__nodeName)
            #Create Prompt
            session = PromptSession(history=history, enable_history_search=True)
            prompt = _Prompt.begining(self.__nodeName)        
            prompt = _Prompt.running_bind
            
            #Run echo loop.
            while isLoop:
                try:
                    commandline = await session.prompt_async(prompt, key_bindings = kb, auto_suggest=AutoSuggestFromHistory(), completer=command_c, complete_while_typing=True)
                    if commandline != None and commandline != '':
                        command = commandline.split(" ")

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
                        
                        elif command[0] == Command.SENDDEBUG:
                            if len(command) != 2:
                                print(f'The expression is wrong. please check it. {command[0]} [target]')
                            else:
                                target_name = command[1]
                                with patch_stdout():
                                    await self.__ndn.sendDebug(target_name)

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
