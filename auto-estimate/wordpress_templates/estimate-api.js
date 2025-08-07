/**
 * 워드프레스 견적서 API 연동 JavaScript
 * FastAPI 서버와 통신하는 함수들을 제공합니다.
 */

// API 기본 URL 설정
const API_BASE_URL = 'https://api.bitekps.com';

/**
 * 견적서 데이터를 FastAPI 서버로 전송
 * @param {Object} data - 견적서 데이터
 * @returns {Promise<Object>} - 서버 응답
 */
async function submitEstimate(data) {
    try {
        const response = await fetch(`${API_BASE_URL}/estimate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('견적서 제출 실패:', error);
        throw error;
    }
}

/**
 * PDF 생성 요청
 * @param {Object} data - PDF 생성에 필요한 데이터
 * @returns {Promise<Object>} - 서버 응답
 */
async function generatePDF(data) {
    try {
        const response = await fetch(`${API_BASE_URL}/collect-data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('PDF 생성 실패:', error);
        throw error;
    }
}

/**
 * 서버 상태 확인
 * @returns {Promise<Object>} - 서버 상태
 */
async function checkServerStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/test`);
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('서버 상태 확인 실패:', error);
        return { status: 'error', message: error.message };
    }
}

/**
 * iframe 메시지 처리
 * @param {string} type - 메시지 타입
 * @param {Object} data - 메시지 데이터
 */
function sendMessageToIframe(type, data) {
    const iframe = document.querySelector('iframe');
    if (iframe && iframe.contentWindow) {
        iframe.contentWindow.postMessage({
            type: type,
            data: data
        }, API_BASE_URL);
    }
}

/**
 * URL 파라미터 가져오기
 * @param {string} paramName - 파라미터 이름
 * @returns {string|null} - 파라미터 값
 */
function getUrlParameter(paramName) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(paramName);
}

/**
 * 페이지 이동
 * @param {string} page - 이동할 페이지
 * @param {Object} params - URL 파라미터
 */
function navigateToPage(page, params = {}) {
    const baseUrl = window.location.origin;
    const paramString = new URLSearchParams(params).toString();
    const url = paramString ? `${baseUrl}/${page}/?${paramString}` : `${baseUrl}/${page}/`;
    window.location.href = url;
}

/**
 * 오류 메시지 표시
 * @param {string} message - 오류 메시지
 * @param {string} type - 메시지 타입 (error, warning, success)
 */
function showMessage(message, type = 'error') {
    // 워드프레스 알림 시스템 사용 또는 커스텀 알림
    if (typeof wp !== 'undefined' && wp.data && wp.data.dispatch) {
        // WordPress Gutenberg 알림 사용
        wp.data.dispatch('core/notices').createNotice(
            type,
            message,
            {
                isDismissible: true,
                type: type === 'error' ? 'error' : 'success'
            }
        );
    } else {
        // 기본 alert 사용
        alert(message);
    }
}

/**
 * 로딩 상태 표시/숨기기
 * @param {boolean} show - 표시 여부
 * @param {string} message - 로딩 메시지
 */
function toggleLoading(show, message = '처리 중...') {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        if (show) {
            loadingElement.style.display = 'flex';
            loadingElement.innerHTML = `
                <div class="spinner"></div>
                <div style="margin-left: 10px;">${message}</div>
            `;
        } else {
            loadingElement.style.display = 'none';
        }
    }
}

/**
 * 견적서 작성 완료 처리
 * @param {Object} estimateData - 견적서 데이터
 */
async function handleEstimateComplete(estimateData) {
    try {
        toggleLoading(true, '견적서를 생성하고 있습니다...');
        
        // 견적서 데이터 전송
        const estimateResult = await submitEstimate(estimateData);
        
        if (estimateResult.success) {
            // 미리보기 페이지로 이동
            navigateToPage('auto-quote/preview', { id: estimateResult.fileId });
        } else {
            showMessage('견적서 생성에 실패했습니다.', 'error');
        }
    } catch (error) {
        showMessage('견적서 처리 중 오류가 발생했습니다.', 'error');
        console.error('견적서 완료 처리 실패:', error);
    } finally {
        toggleLoading(false);
    }
}

/**
 * PDF 생성 완료 처리
 * @param {Object} pdfData - PDF 생성 데이터
 */
async function handlePDFGeneration(pdfData) {
    try {
        toggleLoading(true, 'PDF를 생성하고 있습니다...');
        
        // PDF 생성 요청
        const pdfResult = await generatePDF(pdfData);
        
        if (pdfResult.success) {
            // PDF 공유 페이지로 이동
            navigateToPage('auto-quote/pdf-sharing', { id: pdfResult.pdfId });
        } else {
            showMessage('PDF 생성에 실패했습니다.', 'error');
        }
    } catch (error) {
        showMessage('PDF 생성 중 오류가 발생했습니다.', 'error');
        console.error('PDF 생성 처리 실패:', error);
    } finally {
        toggleLoading(false);
    }
}

// 전역 함수로 노출 (워드프레스에서 사용)
window.EstimateAPI = {
    submitEstimate,
    generatePDF,
    checkServerStatus,
    sendMessageToIframe,
    getUrlParameter,
    navigateToPage,
    showMessage,
    toggleLoading,
    handleEstimateComplete,
    handlePDFGeneration
};

// 페이지 로드 시 서버 상태 확인
document.addEventListener('DOMContentLoaded', function() {
    // 서버 상태 확인 (선택사항)
    checkServerStatus().then(status => {
        if (status.status === 'error') {
            console.warn('API 서버 연결 상태:', status.message);
        }
    });
}); 