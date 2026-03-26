# filename: rita_ai.py
import os
import re
from typing import List

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings # Обновленный импорт без DeprecationWarning
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

class RitaAIAssistant:
    def __init__(self, docs_dir: str = "articles"):
        self.docs_dir = docs_dir
        self.index_path = "rita_faiss_index" # Кэш базы на диске
        self.vector_store = None
        
        # Локальная модель эмбеддингов
        self.embeddings = HuggingFaceEmbeddings(
            model_name="intfloat/multilingual-e5-small"
        )
        
        # Облачная LLM (StepFun 3.5 Flash) через OpenRouter
        api_key = os.getenv("OPENROUTER_API_KEY", "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")
        
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            model="stepfun/step-3.5-flash:free", # Бесплатная модель StepFun
            temperature=0.0, 
            default_headers={"HTTP-Referer": "http://localhost:5000", "X-Title": "RITA Docs"}
        )

        # Промпт с "Цепочкой рассуждений" (Chain of Thought)
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Ты — Senior системный аналитик и ИИ-ассистент по документации RITA.
Твоя абсолютная цель — дать 100% точный ответ, основанный ИСКЛЮЧИТЕЛЬНО на предоставленном контексте.

ТВОЙ АЛГОРИТМ РАБОТЫ (СТРОГО ОБЯЗАТЕЛЕН):
1. Сначала создай блок <thinking>...</thinking>. Внутри него:
   - Проанализируй вопрос пользователя.
   - Найди в предоставленном контексте точные цитаты или факты, относящиеся к вопросу.
   - Оцени, достаточно ли информации для ответа. Если информации нет, прямо скажи об этом себе.
2. Затем создай блок <answer>...</answer>. Внутри него:
   - Напиши финальный, понятный ответ в формате Markdown.
   - Если в <thinking> ты понял, что информации нет, твой ответ должен быть: "К сожалению, в текущей документации RITA нет информации по этому вопросу." Не выдумывай ничего от себя.

ПРЕДОСТАВЛЕННЫЙ КОНТЕКСТ ИЗ ДОКУМЕНТАЦИИ:
{context}"""),
            ("user", "{question}")
        ])

        self._try_load_existing_db()

    def _try_load_existing_db(self) -> None:
        """Загрузка существующего FAISS индекса с диска."""
        if os.path.exists(self.index_path):
            print("📦 Найден кэш векторной базы. Загрузка...")
            self.vector_store = FAISS.load_local(
                self.index_path, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
            print("✅ База знаний успешно загружена из кэша!")

    def build_knowledge_base(self, force_rebuild: bool = False) -> None:
        """Чтение файлов, векторизация и сохранение индекса."""
        if not force_rebuild and self.vector_store is not None:
            return 

        if not os.path.exists(self.docs_dir) or not os.listdir(self.docs_dir):
            raise FileNotFoundError(f"Папка {self.docs_dir} пуста или не существует.")

        print("🔄 Создание новой базы знаний. Чтение файлов...")
        loader = DirectoryLoader(
            self.docs_dir, 
            glob="**/*.md", 
            loader_cls=TextLoader, 
            loader_kwargs={'autodetect_encoding': True}
        )
        documents = loader.load()

        # ИСПРАВЛЕНА СИНТАКСИЧЕСКАЯ ОШИБКА: добавлена 'r' перед строкой с регулярным выражением
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", r"(?<=\. )", " ", ""] 
        )
        chunks = text_splitter.split_documents(documents)

        print("🧠 Векторизация и сохранение индекса на диск...")
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        self.vector_store.save_local(self.index_path)

    def ask(self, query: str) -> str:
        """Поиск фрагментов и генерация ответа через облако."""
        if self.vector_store is None:
            return "❌ База знаний не инициализирована. Пожалуйста, обновите документацию."

        docs = self.vector_store.similarity_search(query, k=6)
        
        context_parts = [
            f"[Файл: {os.path.basename(doc.metadata.get('source', 'Неизвестный файл'))}]\n{doc.page_content}"
            for doc in docs
        ]
        context_text = "\n\n---\n\n".join(context_parts)
        
        prompt = self.prompt_template.format_messages(context=context_text, question=query)
        
        try:
            response = self.llm.invoke(prompt)
            raw_content = response.content
            return self._parse_and_format_response(raw_content, docs)
        except Exception as e:
            return f"❌ Ошибка вызова нейросети: {str(e)}\nУбедитесь, что API-ключ OpenRouter введен верно."

    def _parse_and_format_response(self, raw_content: str, docs: List) -> str:
        """Парсинг Chain of Thought и финального ответа."""
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', raw_content, re.DOTALL | re.IGNORECASE)
        answer_match = re.search(r'<answer>(.*?)</answer>', raw_content, re.DOTALL | re.IGNORECASE)
        
        if answer_match:
            answer_text = answer_match.group(1).strip()
        else:
            answer_text = re.sub(r'<thinking>.*?</thinking>', '', raw_content, flags=re.DOTALL).strip()
            if not answer_text:
                answer_text = raw_content

        thinking_text = thinking_match.group(1).strip() if thinking_match else ""
        
        final_output = ""
        if thinking_text:
            formatted_thinking = thinking_text.replace('\n', '\n> ')
            final_output += f"💭 **Ход мыслей ИИ:**\n> {formatted_thinking}\n\n---\n\n"
            
        final_output += answer_text
        
        sources = list(set([os.path.basename(doc.metadata.get('source', '')) for doc in docs]))
        if sources:
            final_output += f"\n\n📚 *Источники: {', '.join(sources)}*"
            
        return final_output