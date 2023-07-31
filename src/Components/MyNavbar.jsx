import "./MyNavbar.css"
import { useContext } from "react";
import { MyAuthContext } from "./AuthContext";
import { Navbar, Nav } from "react-bootstrap";

const MyNavbar = () => {
    const {user, logout} = useContext(MyAuthContext);

    const handleLogout = () => {
        logout();
    };

    return (
        <div className="my-navbar-container">
            <Navbar className="my-navbar" variant="dark">
                <Nav className="user_name-container">
                <Navbar.Brand className="user_name" href="#">{user.userName}</Navbar.Brand>
                </Nav>
            
                <Nav className="logout-container">
                    <Nav.Link href="login" onClick={handleLogout}>Logout</Nav.Link>
                </Nav>
            </Navbar>
        </div>
    );
};

export default MyNavbar;