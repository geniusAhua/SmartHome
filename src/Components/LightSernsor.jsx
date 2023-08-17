import { Col, Row, Container } from "react-bootstrap";

const LightSensor = ({ sensordata, ndnAdress }) => {
    return(
        <>
            <div className="light-sensor sensor-data-container">
                <Container className="p-2">
                    <Row>
                        <Col md="auto">Brightness:{sensordata.name}</Col>
                        <Col className="text-center">{sensordata.brightness}</Col>
                    </Row>
                </Container>
            </div>
        </>
    );
}

export default LightSensor;