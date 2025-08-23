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
        // 첫 번째 API 호출 - 챗봇 응답 받기
        console.log('=== 첫 번째 API 호출 시작 ===');
        const response = await fetch('/request/rag_model/lcel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: jsonString
        });

        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const chatResponse = await response.text();
        console.log('=== 챗봇 응답 받음 ===');
        console.log('Chat response:', chatResponse);

        // 두 번째 API 호출 - 로그 삽입
        console.log('=== 두 번째 API 호출 시작 (로그 삽입) ===');
        try {
            const logData = {
                input_text: messageText,
                chat_response: chatResponse
            };
            
            console.log('Log data to insert:', logData);
            console.log('Log data JSON:', JSON.stringify(logData));
            
            const logResponse = await fetch('/db/insert_row', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(logData)
            });
            
            console.log('Log insert response status:', logResponse.status);
            console.log('Log insert response headers:', logResponse.headers);
            
            // 응답 내용을 항상 읽어서 확인
            const responseText = await logResponse.text();
            console.log('Log insert response body:', responseText);
            
            if (logResponse.ok) {
                console.log('✅ 로그 삽입 성공');
                console.log('Success response:', responseText);
            } else {
                console.error('❌ 로그 삽입 실패');
                console.error('Error status:', logResponse.status);
                console.error('Error response:', responseText);
                
                // 에러 응답이 JSON인지 확인
                try {
                    const errorJson = JSON.parse(responseText);
                    console.error('Error details:', errorJson);
                } catch (e) {
                    console.error('Error response is not JSON:', responseText);
                }
            }
            
        } catch (logError) {
            console.error('❌ 로그 삽입 API 호출 오류:', logError);
            console.error('Error details:', logError.message);
            console.error('Error stack:', logError.stack);
        }
        
        // 챗봇 응답 반환
        return chatResponse;

    } catch (error) {
        console.error('메인 API 호출 오류:', error);
        throw error;
    }
}