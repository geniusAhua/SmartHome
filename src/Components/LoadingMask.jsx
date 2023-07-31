import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import anime from 'animejs';
import './LoadingMask.css';

const LoadingMask = forwardRef(({ animationDuration = 2500, timeout = 5000, onTimeout }, ref) => {
    //Initiate
    const [isShown, setIsShown] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const timeoutId = useRef(null);

    //Blur Hook
    let setBlur = function(blur){
        document.getElementsByClassName('glassmorphism-loading-bord')[0].style.setProperty('--b', blur.value + 'px');
    }
    let blur = {value: 0};

    //Animation maskIn
    const __animation_loading = anime({
        targets: '.glassmorphism-loading-bord',
        height: {
            value: '100%',
            duration: animationDuration,
            easing: 'easeOutBounce'
        },
        autoplay: false,
    })
    const __animation_loading_blur = anime({
        targets: blur,
        value: [0, 20],
        duration: animationDuration,
        easing: 'linear',
        round: 1,
        update: function(el) {
            setBlur(blur);
        },
        autoplay: false,
    });
    //Animation maskOut
    const __animation_loading_finish = anime({
        targets: '.glassmorphism-loading-bord',
        height: {
            value: '0%',
            duration: animationDuration,
            easing: 'easeInElastic',
        },
        autoplay: false,
    });
    const __animation_loading_finish_blur = anime({
        targets: blur,
        value: [20, 0],
        duration: animationDuration,
        easing: 'linear',
        update: function(el) {
            setBlur(blur);
        },
        autoplay: false,
    });

    //Forbid scroll
    const body = document.body;
    function stop(){
        body.style.position = 'fixed';
    };

    function move(){
        body.style.position = 'relative';
    };

    //Timeout
    const startTimeout = () => {
        //console.log("start timeout " + isLoading + " " + isShown);
        timeoutId.current = setTimeout(() => {
            if(isLoading){
                //console.log("Loading timeout");
                if(onTimeout != null) onTimeout();
                setIsLoading(false);
            }
        }, animationDuration + timeout);
    };
    //Clear timeout
    const clearTimeOut = () => {
        if(timeoutId.current){
            clearTimeout(timeoutId.current);
            timeoutId.current = null;
        }
    };

    //Loading API
    useImperativeHandle(ref, () => ({
        playLoading: (loadingState) => {
            clearTimeOut();

            if(loadingState && !isShown){
                setIsLoading(true);
            }
            else if(!loadingState && isShown){
                setIsLoading(false);
            }
        }
    }));

    //load animation
    function play_loading(__isLoading){
        if(__isLoading && !isShown) {
            startTimeout()
            stop();
            setIsShown(isShown => !isShown);
             __animation_loading.play();
            __animation_loading_blur.play();
        }
        else if(!__isLoading && isShown) {
            move();
            __animation_loading_finish.play();
            __animation_loading_finish_blur.play();
            setTimeout(() => {
                setIsShown(isShown => !isShown);
            }, animationDuration);
        }
    };

    useEffect(() => {
        console.log("start rendering: " + isLoading + " " + isShown);


        play_loading(isLoading);
        if(!isLoading) clearTimeOut();
    }, [isLoading]);

    return(
        <>
            <div className="glassmorphism-loading-bord" style={{display: isShown ? "block" : "none"}}>
                <div className='wave-container'>
                    <fc-wave-filter mode="img">
                        <img className="loading-icon" alt="" src={require("../IMG/loading-icon.png")}/>
                    </fc-wave-filter>
                </div>
            </div>
        </>
    );

});

export default LoadingMask;
