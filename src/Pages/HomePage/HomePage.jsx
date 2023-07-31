import React, { useState, useEffect } from 'react';
import anime from 'animejs';
import './HomePage.css';
import CardList from '../../Components/CardList';
import MyNavbar from '../../Components/MyNavbar';

function HomePage() {
    //Gradient background colours
    const color1 = '#D4FFEC';
    const color2 = '#57F2CC';
    const color3 = '#4596FB';

  useEffect(() => {
    //Background scrolls smoothly with multiple gradient colours
    const timeline = anime.timeline({
        targets: '#gradient stop#s1',
        stopColor: [
            { value: [color1, color1], duration: 480, },
            { value: [color2, color2], duration: 520, },
            { value: [color3, color3], duration: 520, },
        ],
        easing: 'linear',
        autoplay: false,
    }, 0).add({
        targets: '#gradient stop#s2',
        offset:[
            {value: ['48%', '0%'], duration: 480,},
            {value: ['48%', '0%'], duration: 520,},
            {value: ['48%', '0%'], duration: 520,},
        ],
        stopColor: [
            { value: [color2, color2], duration: 480, },
            { value: [color3, color3], duration: 520, },
            { value: [color1, color1], duration: 520, },
            //{ value: color2, duration: 520, },
        ],
        easing: 'linear',
        autoplay: false,
    }, 0).add({
        targets: '#gradient stop#s3',
        offset:[
            {value: ['100%', '52%'], duration: 480},
            {value: ['100%', '52%'], duration: 520,},
            {value: ['100%', '52%'], duration: 520,}
        ],
        stopColor: [
            { value: [color3, color3], duration: 480, },
            { value: [color1, color1], duration: 520, },
            { value: [color2, color2], duration: 520, },
            //{ value: color3, duration: 520, },
        ],
        easing: 'linear',
        autoplay: false,
    }, 0).add({
        targets: '#gradient stop#s4',
        stopColor: [
            { value: color1, duration: 480, },
            { value: color2, duration: 520, },
            { value: color3, duration: 520, },
        ],
        easing: 'linear',
        autoplay: false,
        
    }, 0);

    const handleScroll = () => {
        const scroll = window.scrollY / (document.documentElement.scrollHeight - window.innerHeight);
        timeline.seek(timeline.duration * scroll);
    };

    window.addEventListener('scroll', handleScroll);

    // 清除事件监听器
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  return (
    <div className="home-page">
        <svg className='background-svg'>
            <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop id="s1" offset="0%" style={{stopColor:color1}}/>
                    <stop id="s2" offset="48%" style={{stopColor:color2}}/>
                    <stop id="s3" offset="100%" style={{stopColor:color3}}/>
                    <stop id="s4" offset="100%" style={{stopColor:color3}}/>
                </linearGradient>
            </defs>
            <rect width="100%" height="100%" fill="url(#gradient)"/>
        </svg>

        <div className="home-page-main-container">
            <MyNavbar/>
            <CardList/>
        </div>
    </div>
  );
}

export default HomePage;
