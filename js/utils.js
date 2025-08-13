// js/utils.js

const chatMessages = document.getElementById('chat-messages');
let typingIndicatorElement = null;

/**
 * 현재 시간을 "오전/오후 HH:MM" 형식으로 반환합니다.
 * @returns {string} 포맷된 시간 문자열
 */
export function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: true });
}

/**
 * 사용자의 메시지를 화면에 추가합니다.
 * @param {string} messageText 사용자가 입력한 메시지
 */
export function addUserMessage(messageText) {
    const messageWrapper = document.createElement('div');
    messageWrapper.classList.add('message-wrapper', 'user');

    const messageContent = document.createElement('div');
    messageContent.classList.add('message-content');

    const messageBubble = document.createElement('div');
    messageBubble.classList.add('message-bubble', 'user');
    messageBubble.textContent = messageText;

    const timestamp = document.createElement('span');
    timestamp.classList.add('timestamp');
    timestamp.textContent = getCurrentTime();

    messageContent.appendChild(messageBubble);
    messageContent.appendChild(timestamp);
    messageWrapper.appendChild(messageContent);

    chatMessages.appendChild(messageWrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * 봇의 메시지를 화면에 추가합니다. Markdown과 LaTeX를 렌더링합니다.
 * @param {string} text 봇이 보낸 메시지
 */
export function addBotMessage(text) {
    const messageWrapper = document.createElement('div');
    messageWrapper.classList.add('message-wrapper', 'bot');

    const profileIcon = document.createElement('div');
    profileIcon.classList.add('profile-icon');

    const messageContent = document.createElement('div');
    messageContent.classList.add('message-content');

    const username = document.createElement('span');
    username.classList.add('username');
    username.textContent = 'GA Assistant';

    const messageBubble = document.createElement('div');
    messageBubble.classList.add('message-bubble', 'bot');
    
    // Markdown 처리
    if (typeof marked !== 'undefined') {
        const processedText = text.replace(/\[([^\[\]]+)\]/g, (_, inner) => `$$${inner}$$`);
        messageBubble.innerHTML = marked.parse(processedText);
    } else {
        messageBubble.textContent = text;
    }

    const timestamp = document.createElement('span');
    timestamp.classList.add('timestamp');
    timestamp.textContent = getCurrentTime();

    messageContent.appendChild(username);
    messageContent.appendChild(messageBubble);
    messageContent.appendChild(timestamp);
    messageWrapper.appendChild(profileIcon);
    messageWrapper.appendChild(messageContent);

    chatMessages.appendChild(messageWrapper);
    
    // MathJax 렌더링
    if (window.MathJax) {
        MathJax.typesetPromise([messageBubble])
            .then(() => chatMessages.scrollTop = chatMessages.scrollHeight)
            .catch((err) => {
                console.error('MathJax rendering error:', err);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            });
    } else {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

/**
 * '메시지 입력 중...' 표시를 화면에 추가합니다.
 */
export function showTypingIndicator() {
    const messageWrapper = document.createElement('div');
    messageWrapper.classList.add('message-wrapper', 'bot');
    messageWrapper.id = 'typing-indicator-wrapper';

    const profileIcon = document.createElement('div');
    profileIcon.classList.add('profile-icon');

    const messageContent = document.createElement('div');
    messageContent.classList.add('message-content');

    const username = document.createElement('span');
    username.classList.add('username');
    username.textContent = 'GA Assistant';

    const typingIndicator = document.createElement('div');
    typingIndicator.classList.add('typing-indicator');
    typingIndicator.innerHTML = '<span></span><span></span><span></span>';

    messageContent.appendChild(username);
    messageContent.appendChild(typingIndicator);
    messageWrapper.appendChild(profileIcon);
    messageWrapper.appendChild(messageContent);

    chatMessages.appendChild(messageWrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    typingIndicatorElement = messageWrapper;
}

/**
 * '메시지 입력 중...' 표시를 화면에서 제거합니다.
 */
export function hideTypingIndicator() {
    if (typingIndicatorElement) {
        typingIndicatorElement.remove();
        typingIndicatorElement = null;
    }
}

/**
 * 봇 메시지를 위한 기본 DOM 구조를 생성하고, 내용을 채울 수 있는 bubble과 전체 wrapper를 반환합니다.
 * @returns {{messageBubble: HTMLElement, messageWrapper: HTMLElement}} 생성된 DOM 요소
 */
export function createBotMessage() {
    const messageWrapper = document.createElement('div');
    messageWrapper.classList.add('message-wrapper', 'bot');

    const profileIcon = document.createElement('div');
    profileIcon.classList.add('profile-icon');

    const messageContent = document.createElement('div');
    messageContent.classList.add('message-content');

    const username = document.createElement('span');
    username.classList.add('username');
    username.textContent = 'GA Assistant';

    const messageBubble = document.createElement('div');
    messageBubble.classList.add('message-bubble', 'bot');

    messageContent.appendChild(username);
    messageContent.appendChild(messageBubble);
    messageWrapper.appendChild(profileIcon);
    messageWrapper.appendChild(messageContent);

    chatMessages.appendChild(messageWrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return { messageBubble, messageWrapper };
}
