"""OpenRouter 사용 예제"""

from app.common.llm import OpenRouterClient


def example_basic_usage():
    """기본 사용 예제"""
    # 클라이언트 초기화 (환경변수에서 API 키 자동 로드)
    client = OpenRouterClient()

    # 간단한 채팅
    response = client.simple_chat(
        prompt="Python에서 리스트 컴프리헨션을 설명해주세요.",
        model="claude-3-sonnet",  # 또는 "gpt-4", "gemini-pro" 등
    )
    print(response)


def example_chat_completion():
    """Chat Completion API 사용 예제"""
    client = OpenRouterClient()

    # 대화형 메시지로 호출
    messages = [
        {"role": "system", "content": "당신은 친절한 AI 어시스턴트입니다."},
        {"role": "user", "content": "안녕하세요!"},
    ]

    response = client.chat_completion(
        model="claude-3-sonnet",
        messages=messages,
        temperature=0.7,
        max_tokens=500,
    )

    print(response.choices[0].message.content)


def example_streaming():
    """스트리밍 응답 예제"""
    client = OpenRouterClient()

    messages = [
        {"role": "user", "content": "파이썬의 장점을 5가지만 알려주세요."}
    ]

    print("스트리밍 응답:")
    for chunk in client.chat_completion_stream(
        model="claude-3-sonnet",
        messages=messages,
    ):
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()


def example_multiple_models():
    """여러 모델 비교 예제"""
    client = OpenRouterClient()

    prompt = "AI의 미래에 대해 한 문장으로 말해주세요."
    models = ["claude-3-sonnet", "gpt-4", "gemini-pro"]

    for model in models:
        try:
            response = client.simple_chat(prompt=prompt, model=model)
            print(f"\n{model}:")
            print(response)
        except Exception as e:
            print(f"\n{model}: 오류 - {e}")


def example_with_custom_config():
    """커스텀 설정으로 초기화 예제"""
    client = OpenRouterClient(
        api_key="your-api-key-here",  # 또는 환경변수 사용
        app_name="MyApp",
        site_url="https://myapp.com",
    )

    response = client.simple_chat(
        prompt="Hello!",
        model="claude-3-sonnet",
    )
    print(response)


if __name__ == "__main__":
    # 실행할 예제를 선택하세요
    print("=== 기본 사용 예제 ===")
    # example_basic_usage()

    print("\n=== Chat Completion 예제 ===")
    # example_chat_completion()

    print("\n=== 스트리밍 예제 ===")
    # example_streaming()

    print("\n=== 여러 모델 비교 예제 ===")
    # example_multiple_models()

    print("\n각 예제의 주석을 해제하고 OPENROUTER_API_KEY 환경변수를 설정하여 실행하세요.")
