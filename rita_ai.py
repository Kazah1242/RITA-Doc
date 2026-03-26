import os
import re
from typing import List

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

class RitaAIAssistant:
    """
    Интеллектуальный ассистент RITA.
    Использует локальный сервер Ollama для генерации текста и 
    локальные эмбеддинги для поиска по документации.
    """
    
    def __init__(self, docs_dir: str = "articles"):
        self.docs_dir = docs_dir
        self.index_path = "rita_faiss_index"
        self.vector_store = None
        
        # 1. Локальные эмбеддинги (выполняются на CPU)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="intfloat/multilingual-e5-small"
        )
        
        # 2. Подключение к локальной Ollama (через OpenAI-совместимый API)
        # Убедись, что выполнена команда: ollama run qwen2.5:3b
        self.llm = ChatOpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama", # Заглушка для совместимости
            model="qwen2.5:3b",
            temperature=0.1,
            streaming=True
        )

        # 3. Инструкции для модели
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Ты — Senior ИИ-ассистент платформы RITA. 
Твоя задача — давать точные и лаконичные ответы на основе предоставленной документации.

ПРАВИЛА ОТВЕТА:
1. Если вопрос — просто приветствие, ответь вежливо и предложи помощь по RITA.
2. Для технических вопросов используй формат:
   - <thinking> Краткий анализ: какие файлы используем, что именно ищем. </thinking>
   - <answer> Четкий ответ с использованием Markdown. </answer>
3. Если в контексте нет информации, так и скажи: "В текущей документации информации нет". Не выдумывай факты.

КОНТЕКСТ ИЗ ДОКУМЕНТАЦИИ:
{context}"""),
            ("user", "{question}")
        ])

        self._try_load_existing_db()

    def _try_load_existing_db(self) -> None:
        """Загрузка кэша векторной базы с диска."""
        if os.path.exists(self.index_path):
            try:
                self.vector_store = FAISS.load_local(
                    self.index_path, 
                    self.embeddings, 
                    allow_dangerous_deserialization=True
                )
            except Exception:
                self.vector_store = None

    def build_knowledge_base(self, force_rebuild: bool = False) -> None:
        """Создание векторного индекса из Markdown файлов."""
        if not force_rebuild and self.vector_store is not None:
            return 

        if not os.path.exists(self.docs_dir) or not os.listdir(self.docs_dir):
            raise FileNotFoundError(f"Папка {self.docs_dir} пуста.")

        loader = DirectoryLoader(
            self.docs_dir, 
            glob="**/*.md", 
            loader_cls=TextLoader, 
            loader_kwargs={'autodetect_encoding': True}
        )
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", r"(?<=\. )", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)

        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        self.vector_store.save_local(self.index_path)

    async def ask_stream(self, query: str):
        """Асинхронный генератор для потоковой выдачи ответа."""
        if self.vector_store is None:
            yield {"status": "error", "content": "База знаний не инициализирована."}
            return

        # Поиск релевантных фрагментов (k=4 для ускорения на CPU)
        docs = self.vector_store.max_marginal_relevance_search(query, k=4, fetch_k=10)
        
        context_parts = [
            f"[Файл: {os.path.basename(doc.metadata.get('source', ''))}]\n{doc.page_content}"
            for doc in docs
        ]
        context_text = "\n\n---\n\n".join(context_parts)
        
        prompt = self.prompt_template.format_messages(context=context_text, question=query)
        
        raw_content = ""
        try:
            async for chunk in self.llm.astream(prompt):
                if chunk.content:
                    raw_content += chunk.content
                    yield self._parse_stream_state(raw_content, docs, is_final=False)
            
            yield self._parse_stream_state(raw_content, docs, is_final=True)
            
        except Exception as e:
            yield {"status": "error", "content": f"Ошибка Ollama: {str(e)}"}

    def _parse_stream_state(self, raw_content: str, docs: List, is_final: bool) -> dict:
        """Парсинг ответа на мысли и финальный текст."""
        thinking_text = ""
        answer_text = ""
        is_thinking_done = False

        # Очистка от лишних пробелов в начале потока
        raw_content = raw_content.lstrip()

        think_start = raw_content.find("<thinking>")
        if think_start != -1:
            think_end = raw_content.find("</thinking>")
            if think_end != -1:
                thinking_text = raw_content[think_start + 10:think_end].strip()
                is_thinking_done = True
            else:
                thinking_text = raw_content[think_start + 10:].strip()
                
        ans_start = raw_content.find("<answer>")
        if ans_start != -1:
            ans_end = raw_content.find("</answer>")
            if ans_end != -1:
                answer_text = raw_content[ans_start + 8:ans_end].strip()
            else:
                answer_text = raw_content[ans_start + 8:].strip()
        else:
            # Если теги еще не появились или модель их проигнорировала
            if think_start == -1:
                answer_text = raw_content.strip()

        sources = []
        if is_final and answer_text and "информации нет" not in answer_text.lower():
            sources = list(set([os.path.basename(doc.metadata.get('source', '')) for doc in docs]))

        return {
            "status": "success",
            "thinking": thinking_text,
            "answer": answer_text,
            "is_thinking_done": is_thinking_done or is_final,
            "sources": sources
        }