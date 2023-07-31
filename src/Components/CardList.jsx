import "./CardList.css"
import { Container, Row, Col, Card } from "react-bootstrap";

const CardList = ({data}) => {
    return (
        <>
            <Container className="card-container p-5">
                <Row className="g-4">
                    {
                        Array.from({ length: 12 }).map((_, idx) => (
                            <Col xs={12} md={6} lg={4} key={idx}>
                                <Card className="device-card">
                                    <Card.Img className="card-state-icon" variant="top" src="holder.js/100px180" />
                                    <Card.Img className="card-device-icon" variant="top" src="holder.js/100px180" />
                                    <Card.Body>
                                        <Card.Title className="device-name">
                                            <strong>Card title</strong>
                                        </Card.Title>
                                        <Card.Text className="device-info">
                                            This is a wider card with supporting text below as a natural lead-in to
                                            additional content. This content is a little bit longer.
                                        </Card.Text>
                                    </Card.Body>
                                </Card>
                            </Col>
                        ))
                    }
                </Row>
            </Container>
        </>
    );
}

export default CardList;