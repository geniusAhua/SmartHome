import { useContext, useEffect, useRef, useState } from 'react';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';

import {useNavigate, useLocation } from 'react-router-dom';


import './EntryPage.css';
import { MyAuthContext } from '../../Components/AuthContext';


function ContinueButton({ onClick, isClicked }) {
    let handleClick = (e) => {
        e.stopPropagation();

        if (onClick != null) onClick();
    }

    return (
        <Button disabled={isClicked} className="entry-page__continue-button" onClick={handleClick} variant="primary" size="sm">
            {isClicked ? "Loading" : "Continue"}
        </Button>
    );
}


function EntryPage({ onSubmit, isSubmiting }) {
    const [userName, setUserName] = useState("");
    const [ndnAdress, setNdnAdress] = useState("");
    const [password, setPassword] = useState("");
    
    let location = useLocation();
    let navigate = useNavigate();
    let from = location.state?.from?.pathname || "/";
    let {logout} = useContext(MyAuthContext);

    const styleTitleContainer = {
        height: "30%"
    }

    const handleUserNameChange = (e) => {
        setUserName(e.target.value);
    }

    const handleNdnAdressChange = (e) => {
        setNdnAdress(e.target.value);
    }

    const handlePasswordChange = (e) => {
        setPassword(e.target.value);
    }

    let handleClick = (e) => {
        onSubmit(userName, ndnAdress, password, from, navigate);
    };

    useEffect(() => {
        logout();
    }, []);


    return (
        <>
            <div className="entry-page">
                <div className="backgrd-img"></div>
                <div className="form-container">
                    <div className="glassmorphism">
                        <div className="title__container" style={styleTitleContainer}>
                            <div className="entry-page__title title-style">Smart Home</div>
                            <div className="entry-page__subtitle title-style">Makes your life Better</div>
                        </div>
                        <Form className="entry-page__form">
                            <Form.Group className="mb-3" controlId="userName">
                                <Form.Label className="input-label">Your Device Name</Form.Label>
                                <Form.Control className="entry-input" type="text" placeholder="Enter Your Device Name" value={userName} onChange={handleUserNameChange} />
                            </Form.Group>
                            <Form.Group className="mb-3" controlId="NDNAdress">
                                <Form.Label className="input-label">NDN Adress of Family Hub</Form.Label>
                                <Form.Control className="entry-input" type="text" placeholder="Enter NDN Adress" value={ndnAdress} onChange={handleNdnAdressChange} />
                            </Form.Group>
                            <Form.Group className="mb-3" controlId="password">
                                <Form.Label className="input-label">Password</Form.Label>
                                <Form.Control className="entry-input" type="password" placeholder="Password" value={password} onChange={handlePasswordChange} />
                            </Form.Group>

                            <div className="entry-page__buttons">
                                <ContinueButton isClicked={isSubmiting} onClick={handleClick} />
                            </div>
                        </Form>
                    </div>
                </div>
            </div>
        </>
    );
}

export default EntryPage;