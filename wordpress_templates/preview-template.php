<?php
/*
Template Name: 견적서 미리보기
*/

get_header(); ?>

<style>
.preview-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.preview-iframe {
    width: 100%;
    min-height: 600px;
    border: none;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

@media (max-width: 768px) {
    .preview-container {
        padding: 10px;
    }
    
    .preview-iframe {
        min-height: 500px;
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

<div class="preview-container">
    <div id="loading" class="loading-spinner">
        <div class="spinner"></div>
    </div>
    
    <iframe 
        id="preview-form"
        class="preview-iframe"
        src=""
        style="display: none;"
        onload="hideLoading()">
    </iframe>
</div>

<script>
// API 기본 URL 설정
const API_BASE_URL = 'https://api.bitekps.com';

// URL에서 fileId 파라미터 가져오기
function getFileIdFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('id');
}

// 페이지 로드 시 미리보기 설정
document.addEventListener('DOMContentLoaded', function() {
    const fileId = getFileIdFromUrl();
    
    if (fileId) {
        const iframe = document.getElementById('preview-form');
        iframe.src = `${API_BASE_URL}/preview.html?id=${fileId}`;
    } else {
        // fileId가 없으면 오류 메시지 표시
        document.getElementById('loading').innerHTML = 
            '<div style="text-align: center; color: #666;">견적서 정보를 찾을 수 없습니다.<br>견적서 작성 페이지로 돌아가주세요.</div>';
    }
});

// 로딩 숨기기
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('preview-form').style.display = 'block';
}

// iframe 로드 실패 처리
document.getElementById('preview-form').onerror = function() {
    document.getElementById('loading').innerHTML = 
        '<div style="text-align: center; color: #666;">견적서 미리보기를 불러올 수 없습니다.<br>잠시 후 다시 시도해주세요.</div>';
};

// 페이지 높이 조정
window.addEventListener('message', function(event) {
    if (event.origin !== API_BASE_URL) return;
    
    if (event.data.type === 'resize') {
        const iframe = document.getElementById('preview-form');
        iframe.style.height = event.data.height + 'px';
    }
});
</script>

<?php get_footer(); ?> 