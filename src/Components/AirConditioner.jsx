import { useEffect, useState } from "react"
import { Button, Col, Container, Row } from "react-bootstrap"

const AirConditioner = ({sensordata, onSwitch, ndnAdress}) => {
    const [status, setStatus] = useState(null)

    let handleSwitch = (e) => {
        e.stopPropagation();
        if(onSwitch != null) onSwitch(ndnAdress, status)
    }

    useEffect(() => {
        setStatus(sensordata.status)
    }, [sensordata.status])

    return(
        <>
            <div className="air-conditioner sensor-data-container">
                <Container className="p-2">
                    <Row>
                        <Col md="auto">State:</Col>
                        <Col className="text-center">{status}</Col>
                    </Row>
                    <Row>
                        <Button variant={status == "off" ? "primary" : "info"} size="sm" onClick={handleSwitch}>turn {status == "off" ? "on" : "off"}</Button>
                    </Row>
                </Container>
            </div>
        </>
    );
}

export default AirConditioner;