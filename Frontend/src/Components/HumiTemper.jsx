import { Col, Row, Container } from "react-bootstrap";

const HumiTemper = ({sensordata, ndnAdress}) => {
    return(
        <>
            <div className="humi-temper sensor-data-container">
                <Container className="p-2">
                    <Row>
                        <Col md="auto" className="text-center">Humidity:</Col>
                        <Col className="text-center">{sensordata.humidity}</Col>
                    </Row>
                    <Row>
                        <Col md="auto">Temperature:</Col>
                        <Col className="text-center">{sensordata.temperature}</Col>
                    </Row>
                </Container>
            </div>
        </>
    );
}

export default HumiTemper;