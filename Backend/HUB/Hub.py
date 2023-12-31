import base64
import json
import sys
sys.path.insert(0, '../../Dissertation')
import enum
import random
import traceback
import websockets
import asyncio

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession, CompleteStyle
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from Module.CS import CS

from Module.PIT import PIT
from Module.SendFormat import SendFormat

class PortType(enum.Enum):
    WAN = "1"
    LAN = "2"

class Router:
    def __init__(self, nodeName):
        with open("./pri.pem", "r") as f:
            self.__pri_key_pem = f.read()
        with open("./pub.pem", "r") as f:
            self.__pub_key_pem = f.read()

        self.__pri_key = serialization.load_pem_private_key(
            self.__pri_key_pem.encode(),
            password=None,
            backend=default_backend()
        )
        self.__pub_key = serialization.load_pem_public_key(
            self.__pub_key_pem.encode(),
            backend=default_backend()
        )

        self.dataTask = None
        self.server = None
        self.__password = "12345678"
        self.__permitUser = set()
        self.__nodeName = nodeName
        self.__URL_table = {"router1": "ws://xxx.xxx.xxx.xxx:xxx"}
        '''{
                'WAN':{'targetName': 'webSocket'},
                'LAN':{'targetName': 'webSocket'}
            }'''
        self.__connections = {}
        self.__WAN_target = None
        self.__NDN_map = {} # it's for hub
        self.__port = 2000
        '''
        {
            'NDN_addr': {
                'name',
                'type'
            }
        }
        '''
        self.__sensors = {}
        self.__sensors_data = {}
        self.__CS = CS()
        self.__CS_lock = asyncio.Lock()
        self.__PIT = PIT()
        self.__PIT_lock = asyncio.Lock()
        self.__echo_tag = 1 # 0: not echo, 1: echo received msg
        self.__count_LAN_iterface = 10
        self.__addrs_pointer = 10
        self.__available_NDN_addrs = self.__generate_unique_random_name(self.__count_LAN_iterface)

    def __generate_unique_random_name(self, count):
        unique_numbers = random.sample(range(1, 255), count)
        return [self.__nodeName + '-device-' + str(i) for i in unique_numbers]

    async def __get_NDN_addr(self):
        if self.__addrs_pointer == -1:
            return False, None
        
        self.__addrs_pointer -= 1
        addr = self.__available_NDN_addrs[self.__addrs_pointer]

        return True, addr
    
    async def __serve_LAN_port(self, websocket, clientName, sensorType):
        _success, addr = await self.__get_NDN_addr()
        if _success:
            self.__echo(f"success to get a public NDN adress: {addr} for [{clientName}]")
            # add connection
            if clientName not in self.__connections[PortType.LAN]:
                self.__connections[PortType.LAN][clientName] = websocket
                # add subNDN mappping
                self.__NDN_map[addr] = clientName
                self.__sensors[addr] = {}
                self.__sensors[addr]["name"] = clientName
                self.__sensors[addr]["type"] = sensorType
            else:
                self.__echo(f"[{clientName}] already connected to this router")

    # echo info
    def __echo(self, msg):
        with patch_stdout():
            if self.__echo_tag == 1:
                print(msg)
        
    # process the msg for the target
    '''def __handle_HANDSHAKE'''
    async def __handle_HANDSHAKE(self, packet, from_name, from_ws, portType = PortType.LAN):
        # Check if the packet is from LAN
        if portType == PortType.LAN:
            clientName, sensorType = packet.split("//")
            if clientName not in self.__connections[portType.LAN]:
                if not from_name:
                    from_name += [clientName]
                else:
                    self.__connections[PortType.LAN].pop(from_name[0], None)
                    self.__PIT.delete_pit_with_outface(from_name[0])
                    from_name[0] = clientName
                
                # add NDN adress to NDN_map and websocket to connections
                await self.__serve_LAN_port(from_ws, clientName, sensorType)
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
        # Check if the packet is from WAN
        elif portType == PortType.WAN:
            self.__echo(f"Can't handle a handshake packet from WAN")
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
        if len(params) > 1: params.pop()
        transform_msg = SendFormat.send_(SendFormat.INTEREST, f"{dataName}//{freshToken}{'//'+'//'.join(params) if params else ''}")
        self.__echo(f"[{self.__nodeName}] forward interest to {fromName} ::: {transform_msg}")
        await to_ws.send(transform_msg)
        async with self.__PIT_lock:
            self.__PIT.add_pit_item(dataName, fromName)
        return
    
    async def __respond_to_interest_with_default_data(self, dataName, fileName, params, fromName, from_ws):
        if fileName == ".debug":
            self.__echo(f"[{self.__nodeName}] received a requesting debug packet from {fromName}")
            await from_ws.send(SendFormat.send_(SendFormat.DATA, f"{dataName}//debugPacket"))
            return True
        
        elif fileName == ".CLIENTHELLO":
            self.__echo(f"[{self.__nodeName}] received a requesting CLIENTHELLO packet from {fromName}")
            jsonData = {}

            jsonData["publicKey"] = self.__pub_key_pem.replace('\n', '').replace("/", "|")
            _json_obj = json.dumps(jsonData)
            forward_msg = SendFormat.send_(SendFormat.DATA, f"{dataName}//{_json_obj}")
            await from_ws.send(forward_msg)
            return True
        
        elif fileName == ".LOGINPERMIT":
            self.__echo(f"[{self.__nodeName}] received a requesting LOGINPERMIT packet from {fromName}")
            # use the private key to decrypt the message
            plainPassword = await self.__formatEncrypt_and_decrypt_to_UTF8(params[0])
            plainUserName = await self.__formatEncrypt_and_decrypt_to_UTF8(params[-1])
            #self.__echo(f"for debug: | {plainPassword} || {plainUserName} |")
            # check the password and username
            jsonData = {}
            if plainPassword != self.__password:
                self.__echo(f"[{self.__nodeName}] received a wrong password or username from {fromName}")
                jsonData["permit"] = False
            else:
                self.__echo(f"[{self.__nodeName}] received a correct password and username from {fromName}")
                jsonData["permit"] = True
                # add the user to permitUser
                self.__permitUser.add(plainUserName)

            _json_obj = json.dumps(jsonData)
            signature = await self.__sign_and_formatSignature(_json_obj)
            forward_msg = SendFormat.send_(SendFormat.DATA, f"{dataName}//{_json_obj}//{signature}")
            await from_ws.send(forward_msg)
            return True
        
        elif fileName == ".LOGOUT":
            self.__echo(f"[{self.__nodeName}] received a requesting LOGOUT packet from {fromName}")
            # use the private key to decrypt the message
            plainUserName = await self.__formatEncrypt_and_decrypt_to_UTF8(params[-1])
            if plainUserName in self.__permitUser:
                self.__echo(f"[{self.__nodeName}] remove the permition of {fromName}")
                self.__permitUser.remove(plainUserName)
            jsonData = {}
            jsonData["status"] = True
            _json_obj = json.dumps(jsonData)
            forward_msg = SendFormat.send_(SendFormat.DATA, f"{dataName}//{_json_obj}")
            await from_ws.send(forward_msg)
            return True
        
        elif fileName == ".data":
            plainUserName = await self.__formatEncrypt_and_decrypt_to_UTF8(params[-1])
            if plainUserName not in self.__permitUser:
                self.__echo(f"[{self.__nodeName}] can't handle a packet from a user who doesn't have permission ==> {plainUserName}")
                return False
            _json_obj = json.dumps(self.__sensors_data)
            signature = await self.__sign_and_formatSignature(_json_obj)
            forward_msg = SendFormat.send_(SendFormat.DATA, f"{dataName}//{_json_obj}//{signature}")
            self.__echo(f"[{self.__nodeName}] received a requesting data packet from {fromName} and transform back: {forward_msg}")
            await from_ws.send(forward_msg)
            return True
        
        elif fileName == ".sensors":
            plainUserName = await self.__formatEncrypt_and_decrypt_to_UTF8(params[-1])
            if plainUserName not in self.__permitUser:
                self.__echo(f"[{self.__nodeName}] can't handle a packet from a user who doesn't have permission ==> {plainUserName}")
                return False
            _json_obj = json.dumps(self.__sensors)
            signature = await self.__sign_and_formatSignature(_json_obj)
            forward_msg = SendFormat.send_(SendFormat.DATA, f"{dataName}//{_json_obj}//{signature}")
            self.__echo(f"[{self.__nodeName}] received a requesting sensors packet from {fromName} and transform back: {forward_msg}")
            await from_ws.send(forward_msg)
            return True
        return False
    
    async def __formatEncrypt_and_decrypt_to_UTF8(self, encryptStd):
        orignalEncrypt = encryptStd.replace('|', '/')
        orignalEncryptBytes = base64.b64decode(orignalEncrypt)
        plainText = self.__pri_key.decrypt(
            orignalEncryptBytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            )
        ).decode('utf-8')
        return plainText

    async def __formatEncrypt_from_plaintext(self, plainText):
        plainTextBytes = plainText.encode('utf-8')
        
        encryptedBytes = self.__pri_key.encrypt(
            plainTextBytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        encryptedBase64 = base64.b64encode(encryptedBytes)

        formattedEncrypt = encryptedBase64.decode('utf-8').replace('/', '|')
        
        return formattedEncrypt
    
    async def __sign_and_formatSignature(self, plainText):
        signature = self.__pri_key.sign(
            plainText.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        signature_base64 = base64.b64encode(signature).decode()
        formatSignature = signature_base64.replace('/', '|')
        return formatSignature


    async def __handle_INTEREST(self, packet, fromName, from_ws, portType = PortType.LAN):
        try:
            # Packet: INTEREST://targetName/DeviceNDNName/fileName//MustBeFresh//params
            otherList = packet.split("//")
            fileURL = otherList[0]
            freshToken = otherList[1]
            # params is a list
            params = [] if len(otherList) < 3 else otherList[2:]
            user = otherList[-1]
            targetList = fileURL.split("/")
            dataName = None
            forward_ws = None
            originalDataName = None
            # wrong packet
            if portType == PortType.WAN and targetList[0] != self.__nodeName:
                return
            if len(targetList) < 2:
                return
            
            if targetList[-2] == self.__nodeName and targetList[0] == targetList[-2]:
                # return a debug packet
                if await self.__respond_to_interest_with_default_data(fileURL, targetList[-1], params, fromName, from_ws):
                    return
                
            
            #Check if the packet is from WAN
            # Packet: INTEREST://targetName/DeviceNDNName/fileName//MustBeFresh//params
            if portType == PortType.WAN:
                # use the private key to decrypt the message
                plainUserName = await self.__formatEncrypt_and_decrypt_to_UTF8(user)
                # check the user whether has permission
                if plainUserName not in self.__permitUser:
                    self.__echo(f"[{self.__nodeName}] can't handle a packet from a user who doesn't have permission ==> {plainUserName}")
                    return
                
                NDNName = targetList[1]
                subNDNName = NDNName
                originalDataName = fileURL
                if NDNName in self.__NDN_map:
                    subNDNName = self.__NDN_map[NDNName]
                else:
                    self.__echo(f"[{self.__nodeName}] can't find the target [{subNDNName}]")
                    return
                if subNDNName in self.__connections[PortType.LAN]:
                    forward_ws = self.__connections[PortType.LAN][subNDNName]
                else:
                    self.__echo(f"Something wrong with [{self.__nodeName}]. Please check the code.")
                    return

                dataName = f"{subNDNName}{'/' + '/'.join(targetList[2:])}"

            # Check if the packet is from LAN
            # Packet: INTEREST://DeviceNDNName/fileName//MustBeFresh//params
            elif portType == PortType.LAN:
                dataName = fileURL
                targetName = targetList[0]
                if targetName in self.__connections[PortType.LAN]:
                    forward_ws = self.__connections[PortType.LAN][targetName]
                else:
                    forward_ws = self.__connections[PortType.WAN][self.__WAN_target]
            
            if await self.__send_data_if_exist(dataName, freshToken, fromName, from_ws, originalDataName):
                return
            if await self.__add_to_pit_if_exists(dataName, fromName):
                return
            # forward interest
            await self.__forward_interest_then_add_pit(dataName, freshToken, params, fromName, forward_ws)
            return
        except Exception as e:
            self.__echo(f"An error occurred in _handle_INTEREST: {traceback.print_exc()}")
    '''def __handle_INTEREST'''

    '''def __handle_DATA'''
    async def __handle_DATA(self, packet, fromName, portType):
        try:
            # Packet: DATA://targetName/DeviceNDNName/fileName//data//signature
            otherList = packet.split("//", 1)
            dataName = otherList[0]
            contentBlock = otherList[1]
            fileName = dataName.split("/")[-1]

            if self.__PIT.isExist(dataName):
                async with self.__PIT_lock:
                    outfaces = self.__PIT.find_item(dataName)
                for outface in outfaces:
                    if outface == self.__nodeName:
                        self.__echo(f"[{self.__nodeName}] received DATA from {fromName} ===> {packet}")
                        data = contentBlock.split("//", 1)[0]
                        python_obj = json.loads(data)
                        self.__sensors_data[fromName] = python_obj
                        
                    elif outface in self.__connections[PortType.LAN]:
                        forward_ws = self.__connections[PortType.LAN][outface]
                        formatDataPacket = SendFormat.send_(SendFormat.DATA, packet)
                        await forward_ws.send(formatDataPacket)
                    
                    elif outface in self.__connections[PortType.WAN]:
                        if portType == PortType.LAN:
                            forward_ws = self.__connections[PortType.WAN][outface]
                            # cause the packet is from LAN, so we need to transform the name of DATA
                            fileName = dataName.split("/")[-1]
                            formatDataName = None
                            for k, v in self.__NDN_map.items():
                                if v == fromName:
                                    formatDataName = self.__nodeName + "/" + k + "/" + fileName
                                    break
                            formatDataPacket = SendFormat.send_(SendFormat.DATA, formatDataName + "//" + contentBlock)
                            self.__echo(f"[{self.__nodeName}] received DATA from {fromName} and transform to [{outface}]: {formatDataPacket}")
                            await forward_ws.send(formatDataPacket)
                            
                        else:
                            self.__echo(f"This situation should not happen. Please check the code. From {fromName} to {outface} ===> {packet}")
                            return
                
                async with self.__CS_lock:
                    self.__CS.add_cs_item(dataName, contentBlock)
                async with self.__PIT_lock:
                    self.__PIT.delete_pit_item(dataName)
                return
        except Exception as e:
            self.__echo(f"An error occurred in _handle_DATA: {traceback.print_exc()}")

    '''def __handle_DATA'''

    '''def __transform_msg'''
    async def __transform_msg(self, msg, from_name, from_ws, portType = PortType.WAN):
        packet = msg.split("://", 1)
        if len(packet) < 2: return
        pktHeader = packet[0]
        packet = packet[1]

        try:
            if pktHeader == SendFormat.INTEREST:
                await self.__handle_INTEREST(packet, from_name, from_ws, portType)
                return
                
            # DATA://targetName/DeviceNDNName/fileName//data1//data2//...
            elif pktHeader == SendFormat.DATA:
                await self.__handle_DATA(packet, from_name, portType)
                return
                        
        except Exception as e:
            self.__echo(f"An error occurred in _transform_msg: {traceback.print_exc()}")
            
    '''def __transform_msg'''

    '''def __send_interest'''
    async def __send_interest(self, targetName, ws, fileName):
        if targetName == self.__WAN_target:
            self.__echo(f"Sorry, we can't send interest to the router")
            return
        else:
            formatPacket = f"{targetName}/{fileName}//T"
            # Use handle_INTEREST send Interest packet, because it can save the packet to PIT and transform it
            await self.__handle_INTEREST(formatPacket, self.__nodeName, ws, PortType.LAN)
    '''def __send_interest'''
            

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
                    # HANDSHAKE://clientName//sensorType
                    await self.__handle_HANDSHAKE(packet, clientName, ws, PortType.LAN)
                elif not clientName:
                    self.__echo(f"Can't know the name of this connection. Please send handshake message first")
                    await ws.send(SendFormat.send_(SendFormat.E_SHAKEHAND, 'please send handshake message first'))
                else:
                    # process and transform message
                    await self.__transform_msg(message, clientName[0], ws, PortType.LAN)

        except Exception as e:
            self.__echo(f"[{self.__nodeName}] received an error ==> {traceback.print_exc()}")
            
        finally:
            if clientName:
                self.__echo(f"[{clientName[0]}] disconnect from this router")
                self.__connections[PortType.LAN].pop(clientName[0], None)
                self.__PIT.delete_pit_with_outface(clientName[0])
                # remove this node's info
                for k, v in self.__NDN_map.items():
                    if v == clientName[0]:
                        self.__sensors.pop(k, None)
                        self.__sensors_data.pop(v, None)
                        self.__NDN_map.pop(k, None)
                        break
                
                return


    # connect to another node
    async def connect(self, clientName):

        if self.__WAN_target:
            self.__echo(f"[{self.__nodeName}] already connected to the router, we will disconnect it")
            WAN_ws = self.__connections[PortType.WAN][self.__WAN_target]
            await WAN_ws.close()
            # Each connection will clear their resources by close.
            if self.__WAN_target in self.__connections[PortType.WAN]:
                self.__connections[PortType.WAN].pop(self.__WAN_target, None)
                self.__WAN_target = None
            self.__echo(f"[{self.__nodeName}] disconnect to the router successfully")

        # connect to another node
        async with websockets.connect(self.__URL_table[clientName]) as ws:
            # send hello message
            await ws.send(SendFormat.send_(SendFormat.HANDSHAKE, self.__nodeName))

            response = await ws.recv()

            header, _success = response.split("://", 1)
            if header == SendFormat.HANDSHAKE and _success == "success":
                # connection established
                self.__echo(f"[{self.__nodeName}] connect to the router - [{clientName}] successfully")
                self.__connections[PortType.WAN][clientName] = ws
                self.__WAN_target = clientName
            else:
                self.__echo(f"[{self.__nodeName}] connect to the router - [{clientName}] failed ::: {response}")
                return

            try:
                async for message in ws:
                    self.__echo(f"[{clientName}] send '{message}'")
                    # transform message
                    await self.__transform_msg(message, clientName, ws, PortType.WAN)
            except Exception as e:
                self.__echo(f"[{self.__nodeName}] received an error ==> {traceback.print_exc()}")

            finally:
                await ws.close()
                self.__connections[PortType.WAN].pop(clientName, None)
                self.__WAN_target = None
                self.__echo(f"[{self.__nodeName}] disconnect with {clientName}")

    # clear cs and pit
    async def clear_CS_PIT(self):
        async with self.__CS_lock:
            self.__CS.clear()
        async with self.__PIT_lock:
            self.__PIT.clear()

    # disconnect from another node
    async def disconnect(self, targetName):
        target_ws = None
        # find target websocket
        if targetName in self.__connections[PortType.LAN]:
            target_ws = self.__connections[PortType.LAN].get(targetName)
            # remove connection from connections
            self.__connections.pop(target_ws, None)
        elif targetName in self.__connections[PortType.WAN]:
            target_ws = self.__connections[PortType.WAN].get(targetName)
            # remove connection from connections
            self.__connections.pop(target_ws, None)
        # close connection
        await target_ws.close()

    # close
    async def close(self):
        # close all connections
        for key, ws in list(self.__connections[PortType.LAN].items()):
            await ws.close()

        WAN_ws = self.__connections[PortType.WAN].get(self.__WAN_target)
        if WAN_ws:
            await WAN_ws.close()

        # clear 
        self.__CS.clear()
        self.__PIT.clear()
        self.__connections.clear()
        # close server
        self.server_task.cancel()
        self.dataTask.cancel()
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

    async def getSensorData(self):
        while True:
            try:
                if self.__connections[PortType.LAN]:
                    self.__echo("Get Sensors Data ==>")
                    for targetname, ws in self.__connections[PortType.LAN].items():
                        await self.__send_interest(targetname, ws, ".data")
            
            except Exception as e:
                self.__echo(f"An error happends in getSensorData() ==> {traceback.print_exc()}")
                
            await asyncio.sleep(5)

    async def main(self):
        self.server = websockets.serve(self.__handle_client, "0.0.0.0", self.__port)
        self.server_task = asyncio.ensure_future(self.server)
        self.__connections[PortType.LAN] = {}
        self.__connections[PortType.WAN] = {}
        self.dataTask = asyncio.create_task(self.getSensorData())
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
        return self.__connections
    
    async def sendDebug(self, target):
        if target == self.__WAN_target:
            ws = self.__connections[PortType.WAN][target]
            await ws.send(SendFormat.send_(SendFormat.INTEREST, f"{target}/.debug//T"))

        else:
            if target in self.__connections[PortType.LAN]:
                ws = self.__connections[PortType.LAN][target]
                await ws.send(SendFormat.send_(SendFormat.INTEREST, f"{target}/.debug//T"))
        return




class _Prompt():
    __cli_header = f'hub-cli@'
    @staticmethod
    def begining(name = ''):
        _Prompt.__cli_header += str(name)
        return _Prompt.__cli_header + ' >'
    
    @staticmethod
    def running_bind():
        return _Prompt.__cli_header + f'-running >'


class Command():
    SET_NAME = 'set-name' #set-name [name]
    SHOW_MSG = 'show-msg' #show-msg this is for showing information about connection
    SHUT_SHOW_MSG = 'shut-show-msg' #shut-show-msg
    CONNECT = 'connect' #connect -next_device
    SHOWCS = 'show-cs' #debug: show-cs Show Content Store
    SHOWPIT = 'show-pit' #debug: show-pit Show Pending Interest Table
    SHOWFIB = 'show-fib' #debug: show-fib Show Forward Information Base
    CLEARCS = 'clear-cs' #debug: clear-cs Clear Content Store
    CLEARPIT = 'clear-pit' #debug: clear-pit Clear Pending Interest Table
    SENDDEBUG = 'send-debug' #debug: send-debug [target]

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
            print(f'An error occurred: {traceback.print_exc()}')

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
