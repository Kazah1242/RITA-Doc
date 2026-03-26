import aiohttp
import asyncio
import json
import os
import aiofiles
from datetime import datetime

class RitaAPI:
    def __init__(self, base_url="https://dd.atomrita.ru/api"):
        self.base_url = base_url
        self.session = None
        self.session_file = "rita_session.json"

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.load_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def load_session(self):
        if os.path.exists(self.session_file):
            async with aiofiles.open(self.session_file, mode='r') as f:
                try:
                    data = await f.read()
                    cookies = json.loads(data)
                    self.session.cookie_jar.update_cookies(cookies)
                except:
                    pass

    async def save_session(self):
        cookies = {}
        for cookie in self.session.cookie_jar:
            cookies[cookie.key] = cookie.value
        async with aiofiles.open(self.session_file, mode='w') as f:
            await f.write(json.dumps(cookies))

    async def login(self, login, password):
        url = f"{self.base_url}/login"
        payload = {"login": login, "password": password}
        async with self.session.post(url, json=payload) as response:
            if response.status == 200:
                await self.save_session()
                # Get user info from heartbeat or response if available
                user_info = await self.heartbeat()
                return True, user_info
            return False, f"Login failed: {response.status}"

    async def get_articles(self):
        url = f"{self.base_url}/article/list"
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                # Filter articles and keep ID and parent_id
                filtered = [
                    {
                        "id": item["id"],
                        "url": item["url"],
                        "title": item["title"],
                        "parent_id": item.get("parent_id")
                    }
                    for item in data
                    if "(Удалена)" not in item.get("title", "")
                ]
                return filtered
            return None

    async def get_article_content(self, article_url):
        url = f"{self.base_url}/article/{article_url}"
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.json()
            return None

    async def heartbeat(self):
        url = f"{self.base_url}/user/heartbeat"
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.json()
            return None

def blocks_to_markdown(blocks):
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
                if i == 0: # Header separator
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
        
        md_output.append("") # Spacing
        
    return "\n".join(md_output)
