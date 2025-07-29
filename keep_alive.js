// 서버 활성 상태 유지 스크립트
// 브라우저에서 실행하여 서버가 슬립 모드로 전환되는 것을 방지

const KEEP_ALIVE_INTERVAL = 10 * 60 * 1000; // 10분마다
const SERVER_URL = 'https://auto-estimate.onrender.com';

function keepAlive() {
    fetch(`${SERVER_URL}/ping`)
        .then(response => response.json())
        .then(data => {
            console.log('Keep-alive ping:', data.pong);
        })
        .catch(error => {
            console.error('Keep-alive failed:', error);
        });
}

// 페이지 로드 시 즉시 실행
keepAlive();

// 주기적으로 실행
setInterval(keepAlive, KEEP_ALIVE_INTERVAL);

console.log('Keep-alive script started. Server will stay active.'); 