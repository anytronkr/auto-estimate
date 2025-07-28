<?php
/*
Template Name: 견적서 작성
*/

get_header(); ?>

<style>
.estimate-form-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.estimate-form-iframe {
    width: 100%;
    min-height: 800px;
    border: none;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

@media (max-width: 768px) {
    .estimate-form-container {
        padding: 10px;
    }
    
    .estimate-form-iframe {
        min-height: 600px;
    }
}

/* 로딩 스피너 */
.loading-spinner {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 200px;
}

.spinner {
    border: 4px solid #f3f3f3;
    border-top: 4px solid #3498db;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>

<div class="estimate-form-container">
    <div id="loading" class="loading-spinner">
        <div class="spinner"></div>
    </div>
    
    <iframe 
        id="estimate-form"
        class="estimate-form-iframe"
        src="https://api.bitekps.com/estimate_form.html"
        style="display: none;"
        onload="hideLoading()">
    </iframe>
</div>

<script>
// API 기본 URL 설정
const API_BASE_URL = 'https://api.bitekps.com';

// 로딩 숨기기
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('estimate-form').style.display = 'block';
}

// iframe 로드 실패 처리
document.getElementById('estimate-form').onerror = function() {
    document.getElementById('loading').innerHTML = 
        '<div style="text-align: center; color: #666;">견적서 작성 폼을 불러올 수 없습니다.<br>잠시 후 다시 시도해주세요.</div>';
};

// 페이지 로드 시 iframe 높이 조정
window.addEventListener('message', function(event) {
    if (event.origin !== API_BASE_URL) return;
    
    if (event.data.type === 'resize') {
        const iframe = document.getElementById('estimate-form');
        iframe.style.height = event.data.height + 'px';
    }
});
</script>

<?php get_footer(); ?> 