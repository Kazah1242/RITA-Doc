import os
from typing import List
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

class RitaAIAssistant:
    def __init__(self, docs_dir: str = "articles"):
        self.docs_dir = docs_dir
        self.vector_store = None
        
        # Используем легковесную мультиязычную модель для векторов (скачается автоматически ~300мб)
        # Она работает локально и не требует интернета/API ключей
        self.embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small")
        
        # Настройка клиента нейросети (LLM). 
        # По умолчанию настроено на локальный Ollama или LM Studio (бесплатно, работает локально)
        # Если есть ключ OpenAI, просто поменяй base_url на None и впиши api_key="твой_ключ"
        self.llm = ChatOpenAI(
            base_url="http://localhost:1234/v1", # Замени на свой endpoint, если нужно
            api_key="not-needed",
            model="local-model", # Имя модели
            temperature=0.0      # Температура 0.0 делает ответы максимально точными и строгими
        )

        # Строгий системный промпт для предотвращения галлюцинаций
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "Ты — профессиональный ИИ-ассистент разработчика по системе RITA. "
                       "Твоя задача — отвечать на вопросы пользователя, используя ТОЛЬКО предоставленный контекст из документации. "
                       "Если в контексте нет информации для ответа, прямо скажи: 'В документации RITA нет информации об этом'. "
                       "Не выдумывай методы, классы или API, которых нет в тексте. "
                       "Отвечай четко, используй Markdown для оформления кода и списков.\n\n"
                       "КОНТЕКСТ:\n{context}"),
            ("user", "{question}")
        ])

    def build_knowledge_base(self):
        """Читает скачанные MD файлы и создает векторную базу данных"""
        if not os.path.exists(self.docs_dir) or not os.listdir(self.docs_dir):
            raise FileNotFoundError(f"Папка {self.docs_dir} пуста или не существует. Сначала скачайте базу.")

        # Загружаем все .md файлы
        loader = DirectoryLoader(self.docs_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'autodetect_encoding': True})
        documents = loader.load()

        # Разбиваем текст на чанки (кусочки), чтобы они влезали в контекст нейросети
        # Перекрытие (chunk_overlap) в 100 символов нужно, чтобы не разрывать контекст на полуслове
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", "(?<=\. )", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)

        # Создаем и сохраняем векторную базу в оперативной памяти
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)

    def ask(self, query: str) -> str:
        """Поиск информации и генерация ответа"""
        if self.vector_store is None:
            return "❌ База знаний не инициализирована. Нажмите 'Обучить ИИ'."

        # 1. Ищем топ-4 самых релевантных куска документации
        docs = self.vector_store.similarity_search(query, k=4)
        
        # 2. Собираем их в один текст
        context_text = "\n\n---\n\n".join([doc.page_content for doc in docs])
        
        # 3. Формируем запрос
        prompt = self.prompt_template.format_messages(context=context_text, question=query)
        
        # 4. Получаем ответ от LLM
        try:
            response = self.llm.invoke(prompt)
            
            # Добавляем ссылки на источники (откуда ИИ взял информацию)
            sources = list(set([os.path.basename(doc.metadata.get('source', '')) for doc in docs]))
            source_str = f"\n\n*Источники: {', '.join(sources)}*" if sources else ""
            
            return response.content + source_str
            
        except Exception as e:
            return f"❌ Ошибка вызова нейросети: {str(e)}\nУбедитесь, что сервер LLM запущен."