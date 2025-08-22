// ===== JavaScript 완전 디버깅 =====

export async function getChatResponse(messageText, history) {
    console.log('=== 함수 시작 디버깅 ===');
    console.log('messageText:', messageText);
    console.log('history parameter:', history);
    console.log('history type:', typeof history);
    console.log('history is array:', Array.isArray(history));
    console.log('history length:', history ? history.length : 'N/A');
    
    // history 내용 상세 확인
    if (history && history.length > 0) {
        console.log('history content:');
        history.forEach((item, index) => {
            console.log(`  [${index}]:`, item);
        });
    }

    const chatData = {
        input_text: messageText,
        history: history || []
    };

    console.log('=== chatData 생성 후 ===');
    console.log('chatData:', chatData);
    console.log('chatData.history:', chatData.history);
    console.log('chatData.history type:', typeof chatData.history);
    
    const jsonString = JSON.stringify(chatData);
    console.log('=== JSON 직렬화 후 ===');
    console.log('JSON string:', jsonString);
    
    // JSON 다시 파싱해서 확인
    const reparsed = JSON.parse(jsonString);
    console.log('Reparsed data:', reparsed);
    console.log('Reparsed history:', reparsed.history);
    console.log('Reparsed history type:', typeof reparsed.history);

    try {
        const response = await fetch('/request/rag_model/lcel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: jsonString  // 이미 문자열이므로 다시 stringify 안함
        });

        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const fullResponse = await response.text();
        return fullResponse;

    } catch (error) {
        console.error('API 호출 오류:', error);
        throw error;
    }
}