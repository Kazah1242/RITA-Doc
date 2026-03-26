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
    def __init__(self, docs_dir: str = "articles"):
        self.docs_dir = docs_dir
        self.index_path = "rita_faiss_index"
        self.vector_store = None
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name="intfloat/multilingual-e5-small"
        )
        
        api_key = os.getenv("OPENROUTER_API_KEY", "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")
        
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            model="stepfun/step-3.5-flash:free",
            temperature=0.0, 
            streaming=True, # ВАЖНО: Включаем потоковую передачу данных!
            default_headers={"HTTP-Referer": "http://localhost:5000", "X-Title": "RITA Docs"}
        )

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Ты — Senior ИИ-ассистент платформы RITA. 
Твоя цель - давать точные ответы на основе документации.

АЛГОРИТМ:
1. Если пользователь просто здоровается - поздоровайся и предложи помощь. (Теги <thinking> не нужны).
2. На технические вопросы отвечай так:
   - ОБЯЗАТЕЛЬНО начни с <thinking>...</thinking>. Подробно разбери запрос и найди факты в контексте.
   - Затем напиши <answer>...</answer> с красивым ответом в Markdown.
   - Если информации в контексте нет, честно скажи об этом.

КОНТЕКСТ ДОКУМЕНТАЦИИ:
{context}"""),
            ("user", "{question}")
        ])

        self._try_load_existing_db()

    def _try_load_existing_db(self) -> None:
        if os.path.exists(self.index_path):
            self.vector_store = FAISS.load_local(self.index_path, self.embeddings, allow_dangerous_deserialization=True)

    def build_knowledge_base(self, force_rebuild: bool = False) -> None:
        if not force_rebuild and self.vector_store is not None:
            return 
        if not os.path.exists(self.docs_dir) or not os.listdir(self.docs_dir):
            raise FileNotFoundError(f"Папка {self.docs_dir} пуста.")

        loader = DirectoryLoader(self.docs_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'autodetect_encoding': True})
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150, separators=["\n\n", "\n", r"(?<=\. )", " ", ""])
        chunks = text_splitter.split_documents(documents)

        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        self.vector_store.save_local(self.index_path)

    async def ask_stream(self, query: str):
        """Асинхронный генератор, который стримит ответ в реальном времени."""
        if self.vector_store is None:
            yield {"status": "error", "content": "❌ База знаний не инициализирована."}
            return

        docs = self.vector_store.max_marginal_relevance_search(query, k=5, fetch_k=15)
        context_parts = [f"[Файл: {os.path.basename(doc.metadata.get('source', 'Неизвестный файл'))}]\n{doc.page_content}" for doc in docs]
        context_text = "\n\n---\n\n".join(context_parts)
        prompt = self.prompt_template.format_messages(context=context_text, question=query)
        
        raw_content = ""
        try:
            # Читаем поток данных от нейросети
            async for chunk in self.llm.astream(prompt):
                if chunk.content:
                    raw_content += chunk.content
                    yield self._parse_stream_state(raw_content, docs, is_final=False)
            
            # Финальный вызов (когда генерация завершена)
            yield self._parse_stream_state(raw_content, docs, is_final=True)
            
        except Exception as e:
            yield {"status": "error", "content": f"❌ Ошибка вызова нейросети: {str(e)}"}

    def _parse_stream_state(self, raw_content: str, docs: List, is_final: bool) -> dict:
        """Парсит сырой текст на лету, вытаскивая мысли и сам ответ."""
        thinking_text = ""
        answer_text = ""
        is_thinking_done = False

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
            if think_start == -1 and not raw_content.startswith("<"):
                 answer_text = raw_content

        sources = list(set([os.path.basename(doc.metadata.get('source', '')) for doc in docs])) if docs else []
        
        return {
            "status": "success",
            "thinking": thinking_text,
            "answer": answer_text,
            "is_thinking_done": is_thinking_done or is_final,
            "sources": sources if (is_final and "К сожалению" not in answer_text and answer_text) else []
        }