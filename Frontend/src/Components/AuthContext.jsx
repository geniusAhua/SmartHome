import forge from 'node-forge';

import React, { useEffect, useRef } from 'react';
import { useState, createContext } from "react";
import { isEmpty } from '../Const/Const';

const MyAuthContext = createContext();

const MyAuthProvider = ({ children }) => {
    const _user = localStorage.getItem("user");
    const [user, setUser] = useState(JSON.parse(_user));
    const [publicKeyTemp, setPublicKeyTemp] = useState(null);

    const login = (userName, ndnAdress, password, callback) => {
        const _user_ = {userName, ndnAdress, password};
        localStorage.setItem("user", JSON.stringify(_user_));
        setUser(_user_);
        if (callback) callback();
    }

    const logout = (callback) => {
        setUser(null);
        localStorage.removeItem("user");
        if (callback) callback();
    }


    //useEffect(() => {
    //    const user = localStorage.getItem("user");
    //    console.log("user: " + isEmpty(user));
    //}, []);


    let values = { login, logout, user, publicKeyTemp, setPublicKeyTemp };
    return (
        <MyAuthContext.Provider value={values}>
            {children}
        </MyAuthContext.Provider>
    );
};

export { MyAuthProvider, MyAuthContext };