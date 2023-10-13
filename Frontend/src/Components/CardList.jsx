import "./CardList.css"
import { Container, Row, Col, Card } from "react-bootstrap";
import { useContext, useEffect, useMemo } from "react";
import { WsContext } from "./WsContext";
import { MyAuthContext } from "./AuthContext";
import forge from 'node-forge';

import { COMMAND_SWITCH, COMMAND_TEMPERATURE, formatINTEREST, SENSORS_DATA_FILE, SENSORS_FILE } from "../Const/Const";
import Refrigerator from "./Refrigerator";
import HumiTemper from "./HumiTemper";
import LightSensor from "./LightSernsor";
import Heater from "./Heater";
import AirConditioner from "./AirConditioner";

const CardList = ({JSON_sensors, JSON_sensors_data}) => {
    const ws = useContext(WsContext);
    const {user, publicKeyTemp } = useContext(MyAuthContext);

    const encrypt_format_to_hub = (plaintext) => {
        let encrypt = publicKeyTemp.encrypt(plaintext, "RSA-OAEP", {md: forge.md.sha256.create()});
        let encrypt_b64 = forge.util.encode64(encrypt);
        // replace all the '/' with '|'
        let modifiedEncrypt_b64 = encrypt_b64.replace(/\//g, '|');
        return modifiedEncrypt_b64;
    };

    const handleSwitch = (ndnAdress, status) => {
        let userName = user.userName;
        let encryptedUserName = encrypt_format_to_hub(userName);
        if (status == "on") status = "off";
        else status = "on";
        let format_msg = formatINTEREST((user.ndnAdress + "/" + ndnAdress), COMMAND_SWITCH, status + "//" + encryptedUserName);
        ws.webSocket.sendMessage(format_msg);
    }

    const handleTemperature = (ndnAdress, temperature) => {
        let userName = user.userName;
        let encryptedUserName = encrypt_format_to_hub(userName);
        let format_msg = formatINTEREST((user.ndnAdress + "/" + ndnAdress), COMMAND_TEMPERATURE, temperature + "//" + encryptedUserName);
        ws.webSocket.sendMessage(format_msg);
    }

    const COMPONENTS_MAP = {
        "Refrigerator": <Refrigerator onSwitch={handleSwitch}/>,
        "HumiTemper": <HumiTemper/>,
        "LightSensor": <LightSensor/>,
        "Heater": <Heater onSwitch={handleSwitch} afterChange={handleTemperature}/>,
        "Air-conditioner": <AirConditioner onSwitch={handleSwitch}/>,
    }

    const ComponentToRender = ({sensorType, sensordata}) => {
        const Component = COMPONENTS_MAP[sensorType];
        return <Component sensordata={sensordata} />
    }

    const { setSensorsTemp, setSensorsDataTemp, sensorsTemp, sensorsDataTemp} = useContext(WsContext);

    useEffect(() => {
        console.log(sensorsDataTemp);
        console.log(sensorsTemp);
        console.log(publicKeyTemp);
    }, [sensorsDataTemp])

    if(sensorsDataTemp == null || sensorsTemp == null){
        return null;
    }
    return (
        <>
            <Container className="card-container p-5">
                <Row className="g-4">
                    {
                        Object.keys(sensorsTemp).map((category) => {
                            return(
                                <Col xs={12} md={6} lg={4} key={category} id={category}>
                                    <Card className="device-card">
                                        <Card.Img className="card-state-icon" variant="top" src={require("../IMG/status.png")} />
                                        <Card.Img key={category} className="card-device-icon" variant="top" src={require("../IMG/" + sensorsTemp[category].type + ".png")} />
                                        <Card.Body>
                                            <Card.Title className="device-name">
                                                <strong>{sensorsTemp[category].name}</strong>
                                            </Card.Title>
                                            <Card.Text className="device-info">
                                                {
                                                    sensorsTemp[category].type == "HumiTemper" ? 
                                                    <HumiTemper key={category} ndnAdress={category} sensordata={sensorsDataTemp[sensorsTemp[category].name]}/> : 
                                                    sensorsTemp[category].type == "LightSensor" ? 
                                                    <LightSensor key={category} ndnAdress={category} sensordata={sensorsDataTemp[sensorsTemp[category].type]}/> : 
                                                    sensorsTemp[category].type == "Refrigerator" ? 
                                                    <Refrigerator key={category} ndnAdress={category} sensordata={sensorsDataTemp[sensorsTemp[category].name]} onSwitch={handleSwitch}/> : 
                                                    sensorsTemp[category].type == "Heater" ? 
                                                    <Heater key={category} ndnAdress={category} sensordata={sensorsDataTemp[sensorsTemp[category].name]} onSwitch={handleSwitch} afterChange={handleTemperature}/> : 
                                                    <AirConditioner key={category} ndnAdress={category} sensordata={sensorsDataTemp[sensorsTemp[category].name]} onSwitch={handleSwitch}/>
                                                }
                                            </Card.Text>
                                        </Card.Body>
                                    </Card>
                                </Col>
                            );
                        })
                    }
                </Row>
            </Container>
        </>
    );
}

export default CardList;