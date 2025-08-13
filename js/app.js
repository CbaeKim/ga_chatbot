// js/app.js

import { addUserMessage, createBotMessage, showTypingIndicator, hideTypingIndicator, getCurrentTime } from './utils.js';
import { getChatResponse } from './api.js';

// 전역 변수와 DOM 요소는 이 파일에서 관리
let lastScrollPosition = 0;
let initialViewportHeight = window.innerHeight;
const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
let keyboardHeight = 0;
let restoreScrollTimeout = null;
let isProcessing = false;
let resizeTimeout = null;

const sendButton = document.getElementById('send-button');
const userInput = document.getElementById('user-input');
const chatMessages = document.getElementById('chat-messages');

// DOMContentLoaded 이벤트 리스너를 함수로 분리
const handleDOMContentLoaded = () => {
    const initialMessage = document.getElementById('initial-bot-message');
    if (initialMessage) {
        const typingIndicator = initialMessage.querySelector('.typing-indicator');
        const messageBubble = initialMessage.querySelector('.message-bubble');
        const messageContent = initialMessage.querySelector('.message-content');

        const now = new Date();
        const timeString = now.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: true });
        const timestamp = document.createElement('span');
        timestamp.classList.add('timestamp');
        timestamp.textContent = timeString;

        messageContent.appendChild(timestamp);

        setTimeout(() => {
            if (typingIndicator) typingIndicator.style.display = 'none';
            if (messageBubble) messageBubble.style.display = 'block';
        }, 1500);
    }
};

// 키보드, 뷰포트 관련 함수들
const setAppHeight = () => {
    const doc = document.documentElement;
    const currentHeight = window.innerHeight;
    keyboardHeight = Math.max(0, initialViewportHeight - currentHeight);
    doc.style.setProperty('--app-height', `${currentHeight}px`);
};

const throttledSetAppHeight = () => {
    if (resizeTimeout) return;
    resizeTimeout = setTimeout(() => {
        setAppHeight();
        resizeTimeout = null;
    }, 16);
};

const saveScrollPosition = () => {
    lastScrollPosition = chatMessages.scrollTop;
};

const restoreScrollPosition = () => {
    if (restoreScrollTimeout) clearTimeout(restoreScrollTimeout);
    restoreScrollTimeout = setTimeout(() => {
        if (chatMessages.scrollTop !== lastScrollPosition) {
            chatMessages.scrollTop = lastScrollPosition;
        }
    }, isIOS ? 300 : 100);
};



// 메시지 전송 로직
const sendMessage = () => {
    const messageText = userInput.value.trim();
    if (messageText === '' || isProcessing) {
        return;
    }

    isProcessing = true;
    sendButton.disabled = true;
    sendButton.classList.add('processing');
    sendButton.innerHTML = '<span style="font-size: 1.2em;">■</span>';

    addUserMessage(messageText);
    userInput.value = '';
    showTypingIndicator();

    getChatResponse(messageText)
        .then(fullResponse => {
            console.log('받은 응답:', fullResponse);
            console.log('응답 타입:', typeof fullResponse);
            hideTypingIndicator();

            const { messageBubble, messageWrapper } = createBotMessage();

            // 백엔드에서 문자열 "\n"을 보내는 경우 실제 줄바꿈으로 변환
            let finalMarkdown = fullResponse.replace(/\\n/g, '\n');
            
            console.log('변환된 마크다운:', finalMarkdown);
            console.log('변환된 마크다운 타입:', typeof finalMarkdown);

            // LaTeX 수식을 임시로 보호 (marked.js가 건드리지 않도록)
            const mathPlaceholders = [];
            let mathIndex = 0;
            
            console.log('수식 보호 전 마크다운:', finalMarkdown.substring(0, 500) + '...');
            
            // 디스플레이 수식 보호 (\[...\])
            finalMarkdown = finalMarkdown.replace(/\\\[([\s\S]*?)\\\]/g, (match, content) => {
                const placeholder = `MATHPLACEHOLDER_DISPLAY_${mathIndex}_MATHPLACEHOLDER`;
                mathPlaceholders[mathIndex] = `\\[${content}\\]`;
                console.log(`디스플레이 수식 ${mathIndex} 보호:`, match, '->', placeholder);
                mathIndex++;
                return placeholder;
            });
            
            // 인라인 수식 보호 (\(...\))
            finalMarkdown = finalMarkdown.replace(/\\\(([\s\S]*?)\\\)/g, (match, content) => {
                const placeholder = `MATHPLACEHOLDER_INLINE_${mathIndex}_MATHPLACEHOLDER`;
                mathPlaceholders[mathIndex] = `\\(${content}\\)`;
                console.log(`인라인 수식 ${mathIndex} 보호:`, match, '->', placeholder);
                mathIndex++;
                return placeholder;
            });
            
            console.log('수식 보호 후 마크다운:', finalMarkdown.substring(0, 500) + '...');

            // marked.js를 사용하여 마크다운을 HTML로 변환 (기본 렌더러 사용)
            let finalHtml = marked.parse(finalMarkdown, { gfm: true });
            
            // 보호된 수식들을 다시 복원
            console.log('수식 플레이스홀더 개수:', mathPlaceholders.length);
            console.log('수식 플레이스홀더들:', mathPlaceholders);
            
            for (let i = 0; i < mathPlaceholders.length; i++) {
                const displayPlaceholder = `MATHPLACEHOLDER_DISPLAY_${i}_MATHPLACEHOLDER`;
                const inlinePlaceholder = `MATHPLACEHOLDER_INLINE_${i}_MATHPLACEHOLDER`;
                
                console.log(`플레이스홀더 ${i} 복원 시도:`, displayPlaceholder, inlinePlaceholder);
                
                if (finalHtml.includes(displayPlaceholder)) {
                    console.log(`디스플레이 플레이스홀더 ${i} 발견, 복원:`, mathPlaceholders[i]);
                    finalHtml = finalHtml.replace(new RegExp(displayPlaceholder, 'g'), mathPlaceholders[i]);
                }
                if (finalHtml.includes(inlinePlaceholder)) {
                    console.log(`인라인 플레이스홀더 ${i} 발견, 복원:`, mathPlaceholders[i]);
                    finalHtml = finalHtml.replace(new RegExp(inlinePlaceholder, 'g'), mathPlaceholders[i]);
                }
            }
            
            console.log('수식 복원 후 HTML:', finalHtml.substring(0, 500) + '...');
            
            console.log('마크다운 변환 결과:', finalHtml);
            console.log('마크다운 변환 결과 타입:', typeof finalHtml);

            messageBubble.innerHTML = finalHtml;

            // 타임스탬프 추가
            const timestamp = document.createElement('span');
            timestamp.classList.add('timestamp');
            timestamp.textContent = getCurrentTime();
            messageWrapper.querySelector('.message-content').appendChild(timestamp);

            // MathJax 렌더링
            const renderMath = () => {
                if (window.MathJax && window.MathJax.typesetPromise) {
                    console.log('MathJax 렌더링 시작');
                    MathJax.typesetPromise([messageBubble])
                        .then(() => {
                            console.log('MathJax 렌더링 완료');
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        })
                        .catch(err => {
                            console.error('MathJax 렌더링 오류:', err);
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        });
                } else {
                    console.log('MathJax 사용 불가, 일반 스크롤');
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            };

            // MathJax가 로드되지 않았다면 잠시 기다린 후 다시 시도
            if (window.MathJax) {
                renderMath();
            } else {
                setTimeout(renderMath, 100);
            }
        })
        .catch(error => {
            hideTypingIndicator();

            const { messageBubble, messageWrapper } = createBotMessage();
            const timestamp = document.createElement('span');
            timestamp.classList.add('timestamp');
            timestamp.textContent = getCurrentTime();
            messageWrapper.querySelector('.message-content').appendChild(timestamp);

            messageBubble.innerHTML = '<span style="color: red;">오류가 발생했습니다. 다시 시도해주세요.</span>';
            console.error('API 호출 오류:', error);
        })
        .finally(() => {
            isProcessing = false;
            sendButton.disabled = false;
            sendButton.classList.remove('processing');
            sendButton.textContent = '전송';
            if (window.innerWidth > 768) {
                userInput.focus();
            }
        });
};

// 이벤트 리스너 등록
document.addEventListener('DOMContentLoaded', handleDOMContentLoaded);
sendButton.addEventListener('click', sendMessage);
userInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
        if (window.innerWidth <= 768) {
            userInput.blur();
        }
    }
});

if ('visualViewport' in window) {
    window.visualViewport.addEventListener('resize', throttledSetAppHeight);
} else {
    window.addEventListener('resize', throttledSetAppHeight);
}

window.addEventListener('orientationchange', () => {
    setTimeout(() => {
        initialViewportHeight = window.innerHeight;
        setAppHeight();
    }, 500);
});

userInput.addEventListener('focusin', () => {
    if (isIOS) document.body.classList.add('keyboard-open');
});

userInput.addEventListener('focusout', () => {
    if (isIOS) {
        document.body.classList.remove('keyboard-open');
        setTimeout(() => chatMessages.scrollTop = chatMessages.scrollHeight, 300);
    } else {
        setTimeout(() => chatMessages.scrollTop = chatMessages.scrollHeight, 100);
    }
});

document.addEventListener('touchstart', () => {
    if (keyboardHeight === 0) saveScrollPosition();
}, { passive: true });

setAppHeight();