import aiohttp
import json
import os
import aiofiles

class RitaAPI:
    def __init__(self, base_url="https://dd.atomrita.ru/api"):
        self.base_url = base_url
        self.session = None
        self.session_file = "rita_session.json"

    async def start_session(self):
        """Инициализирует глобальную сессию aiohttp."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            await self.load_session()

    async def close_session(self):
        """Закрывает сессию при выходе из приложения."""
        if self.session:
            await self.session.close()

    async def load_session(self):
        """Загружает cookies из локального файла."""
        if os.path.exists(self.session_file):
            try:
                async with aiofiles.open(self.session_file, mode='r') as f:
                    data = await f.read()
                    cookies = json.loads(data)
                    self.session.cookie_jar.update_cookies(cookies)
            except Exception as e:
                print(f"Failed to load session: {e}")

    async def save_session(self):
        """Сохраняет текущие cookies в файл."""
        cookies = {}
        for cookie in self.session.cookie_jar:
            cookies[cookie.key] = cookie.value
        try:
            async with aiofiles.open(self.session_file, mode='w') as f:
                await f.write(json.dumps(cookies))
        except Exception as e:
            print(f"Failed to save session: {e}")

    def clear_session_data(self):
        """Очищает локальный файл сессии (при логауте)."""
        if os.path.exists(self.session_file):
            os.remove(self.session_file)
        if self.session:
            self.session.cookie_jar.clear()

    async def verify_saved_session(self):
        """Проверяет, валидна ли сохраненная сессия."""
        await self.start_session()
        if not os.path.exists(self.session_file):
            return False, None
        
        user_info = await self.heartbeat()
        if user_info:
            return True, user_info
        return False, None

    async def login(self, login, password):
        """Авторизация и получение новых cookies."""
        await self.start_session()
        url = f"{self.base_url}/login"
        payload = {"login": login, "password": password}
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    await self.save_session()
                    user_info = await self.heartbeat()
                    return True, user_info
                return False, f"Ошибка авторизации: Код {response.status}"
        except Exception as e:
            return False, f"Ошибка сети: {str(e)}"

    async def get_articles(self):
        """Получение списка статей."""
        url = f"{self.base_url}/article/list"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return [
                        {
                            "id": item["id"],
                            "url": item["url"],
                            "title": item["title"],
                            "parent_id": item.get("parent_id")
                        }
                        for item in data if "(Удалена)" not in item.get("title", "")
                    ]
        except Exception:
            pass
        return None

    async def get_article_content(self, article_url):
        """Получение контента конкретной статьи."""
        url = f"{self.base_url}/article/{article_url}"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
        except Exception:
            pass
        return None

    async def heartbeat(self):
        """Пинг сервера для подтверждения валидности сессии."""
        url = f"{self.base_url}/user/heartbeat"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
        except Exception:
            pass
        return None

def blocks_to_markdown(blocks):
    """Преобразование блоков редактора в Markdown."""
    md_output = []
    for block in blocks:
        b_type = block.get("type")
        data = block.get("data", {})
        
        if b_type == "header":
            level = data.get("level", 1)
            text = data.get("text", "")
            md_output.append(f"{'#' * level} {text}")
            
        elif b_type == "paragraph":
            text = data.get("text", "").replace("<br>", "\n").replace("&lt;br&gt;", "\n")
            md_output.append(text)
            
        elif b_type == "table":
            content = data.get("content", [])
            if not content:
                continue
            for i, row in enumerate(content):
                md_output.append("| " + " | ".join(map(str, row)) + " |")
                if i == 0:
                    md_output.append("| " + " | ".join(["---"] * len(row)) + " |")
                    
        elif b_type == "list":
            items = data.get("items", [])
            style = data.get("style", "unordered")
            for i, item in enumerate(items):
                content = item.get("content", "") if isinstance(item, dict) else item
                prefix = f"{i+1}." if style == "ordered" else "-"
                md_output.append(f"{prefix} {content}")

        elif b_type == "image":
            file_info = data.get("file", {})
            url = file_info.get("url", "")
            caption = data.get("caption", "")
            md_output.append(f"![{caption}]({url})")
            if caption:
                md_output.append(f"\n*{caption}*")
                
        md_output.append("")
    return "\n".join(md_output)