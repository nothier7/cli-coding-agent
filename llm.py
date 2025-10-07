import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()
MODEL = os.getenv("MODEL", "gpt-5-codex")