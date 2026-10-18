"""Run the terminal chat interface."""

from bot.chat import ChatBot
from bot.utils import configure_logging
from config import API_KEY, MODEL_NAME


def main() -> None:
    """Start the interactive terminal chat loop."""
    configure_logging()
    print("Meme Bot is ready. Type 'quit' to leave.")
    if not MODEL_NAME:
        print("Add MODEL_NAME=your-Gemma-4-26B-A4B-IT-model-id to .env before chatting.")
    elif not API_KEY:
        print("Add API_KEY=your_provider_api_key to .env before chatting.")
    bot = ChatBot()
    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBot: Catch you later.")
            break
        if message.lower() in {"quit", "exit"}:
            print("Bot: Catch you later.")
            break
        if not message:
            continue
        result = bot.handle(message)
        print(f"Bot: {result.reply}")
        if result.image_path:
            print(f"Meme: {result.image_path}")


if __name__ == "__main__":
    main()
