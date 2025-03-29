from gemini_handler import GeminiHandler, KeyRotationStrategy, Strategy

# Khởi tạo handler với chiến lược tối ưu
handler = GeminiHandler(
    config_path="config.yaml",
    content_strategy=Strategy.FALLBACK,
    key_strategy=KeyRotationStrategy.SMART_COOLDOWN
)

def chat_with_user():
    print("Chatbot: Xin chào! Tôi có thể giúp gì cho bạn?")
    
    while True:
        user_input = input("Bạn: ")
        if user_input.lower() in ["tạm biệt", "bye", "exit"]:
            print("Chatbot: Tạm biệt! Hẹn gặp lại!")
            break
            
        # Tạo phản hồi với xử lý lỗi
        response = handler.generate_content(
            prompt=f"User: {user_input}\nChatbot:",
            model_name="gemini-2.0-flash-exp"
        )
        
        if response['success']:
            print(f"Chatbot: {response['text']}")
        else:
            # Thử lại với model khác nếu gặp lỗi
            fallback_response = handler.generate_content(
                prompt=f"User: {user_input}\nChatbot:",
                model_name="gemini-1.5-flash"
            )
            
            if fallback_response['success']:
                print(f"Chatbot: {fallback_response['text']}")
            else:
                print("Chatbot: Xin lỗi, tôi đang gặp vấn đề kỹ thuật. Vui lòng thử lại sau.")

# Chạy chatbot
if __name__ == "__main__":
    chat_with_user()
