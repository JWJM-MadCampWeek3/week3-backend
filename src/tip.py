

from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.schema import BaseOutputParser
import os

class CommaOutputParser(BaseOutputParser):
    def parse(self,text):
        item = text.strip().split(",")
        return list(map(str.strip,item))

load_dotenv()

openai_api_key = os.environ.get("OPENAI_API_KEY")

chat = ChatOpenAI(temperature=0.1,model_name='gpt-3.5-turbo')

# gpt-4

template = ChatPromptTemplate.from_messages([
    ("system", "너는 사용자가 백준 문제를 풀때 tip을 주는 tip machine이야. 문제번호를 받으면 그 문제를 어떻게 풀면 좋을지 tip을 차례대로 작성해줘. {number}번 문제에 대한 tip을 드리겠습니다 라고만 답변을 시작해야돼."),
    ("human","백준 {number}번 문제를 풀기위한 tip을 차례대로 작성해줘."),
])







def tip(number):
    chat = ChatOpenAI(temperature=0.1,model_name='gpt-4')
    try:
        

        # Pass the formatted string into the chat prompt template
        prompt = template.format_messages(number=number)
        
        # Invoke the OpenAI Chat model
        # chat_response = chat_.invoke(prompt)
        chat_response = chat.invoke(prompt)
        return chat_response
    except Exception as e:
        error_message = str(e) or "An error occurred during the AI response generation."
        return {"error": error_message}
