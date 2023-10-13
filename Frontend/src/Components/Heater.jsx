import { useEffect, useState } from "react"
import { Button, Col, Container, Row } from "react-bootstrap"
import { Form } from "react-bootstrap"


const Heater = ({sensordata, afterChange, onSwitch, ndnAdress}) => {
    const [temperature, setTemperature] = useState(0)
    const [status, setStatus] = useState(null)

    let handleChanges = (e) => {
        if(afterChange != null) afterChange(ndnAdress, e.target.value)
    }

    let handleSwitch = (e) => {
        e.stopPropagation();
        if(onSwitch != null) onSwitch(ndnAdress, status)
    }

    useEffect(() => {
        setTemperature(sensordata.temperature)
    }, [sensordata.temperature])

    useEffect(() => {
        setStatus(sensordata.status)
    }, [sensordata.status])

    return(
        <>
            <div className="heater sensor-data-container">
                <Container className="p-2">
                    <Row>
                        <Col className="text-center" md="auto">State:</Col>
                        <Col className="text-center">{status}</Col>
                    </Row>
                    <Row>
                        <Button variant={status == "off" ? "primary" : "info"} size="sm" onClick={handleSwitch}>turn {status == "off" ? "on" : "off"}</Button>
                    </Row>
                    <Row>
                        <Col md="auto" className="text-center">Temperature:</Col>
                        <Col className="text-center"><Form.Label>{temperature}°C</Form.Label></Col>
                    </Row>
                    <Row>
                        <Form.Range min="20" max="30" value={temperature}
                        disabled={status == "off" ? true : false}
                        onChange={e => setTemperature(e.target.value)}
                        onMouseUp={handleChanges}
                        onTouchEnd={handleChanges}/>
                    </Row>
                </Container>
            </div>
        </>
    )
}

export default Heater;