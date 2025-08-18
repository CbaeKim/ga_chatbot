// js/api.js

/**
 * 챗봇 API에 메시지를 보내고 응답을 받습니다.
 * @param {string} messageText 사용자 입력 메시지
* @param {Array} history 대화 기록
 * @returns {Promise<string>} 전체 봇 응답 메시지
 */
export async function getChatResponse(messageText, history) {
    const chatData = {
        input_text: messageText
        // 임시로 히스토리 비활성화: history: JSON.stringify(history)
    };

    try {
        console.log('API 호출 시작:', messageText, history);

        const response = await fetch('/request/rag_model/lcel?' + new URLSearchParams(chatData).toString());

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // 응답 타입 확인
        const contentType = response.headers.get('content-type');
        console.log('Content-Type:', contentType);
        
        let fullResponse;
        if (contentType && contentType.includes('application/json')) {
            // JSON 응답인 경우
            const jsonResponse = await response.json();
            console.log('JSON 응답:', jsonResponse);
            fullResponse = jsonResponse.message || jsonResponse.content || JSON.stringify(jsonResponse);
        } else {
            // 텍스트 응답인 경우
            fullResponse = await response.text();
        }
        
        console.log('API 응답 완료:', fullResponse.length, '자');
        console.log('API 응답 내용:', fullResponse);
        console.log('API 응답 타입:', typeof fullResponse);
        
        // 안전장치: 만약 객체라면 문자열로 변환
        if (typeof fullResponse === 'object') {
            console.warn('응답이 객체입니다. 문자열로 변환합니다.');
            fullResponse = JSON.stringify(fullResponse);
        }

        // DB insert
        const dbData = {
            input_text: messageText,
            chat_response: fullResponse
        };

        // async 함수 내에서 Promise를 기다리지 않으려면 await를 제거합니다.
        // DB insert의 성공 여부가 main 로직에 영향을 주지 않는 경우
        fetch('/db/insert_row', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dbData)
        }).catch(error => {
            console.error('DB insert failed:', error);
        });

        return fullResponse;

    } catch (error) {
        console.error('API 호출 예외:', error);
        const errorMessage = '죄송합니다. 답변을 가져오는 중 오류가 발생했습니다. 다시 시도해주세요.';
        // Promise를 반환하는 함수이므로 throw 대신 Promise.reject를 사용합니다.
        throw new Error(errorMessage);
    }
}