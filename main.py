# kazah1242/rita-doc/RITA-Doc-f8a8586591e68dfae8848becbf1246b3e4fe8fbd/main.py

import customtkinter as ctk
import asyncio
import threading
import json
import os
import sys
import html
import re
import io
import time
from PIL import Image, ImageTk
import aiofiles
from rita_api import RitaAPI, blocks_to_markdown

try:
    from rita_ai import RitaAIAssistant
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("Warning: rita_ai.py not found or dependencies missing. AI features disabled.")

# Настройка современного внешнего вида
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master, api, loop, user_info=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.api = api
        self.loop = loop
        self.articles = []
        self.user_info = user_info or {}
        self.image_cache = []
        
        self.ai = RitaAIAssistant() if AI_AVAILABLE else None
        self.ai_indexed = False 

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- ВЕРХНЯЯ ПАНЕЛЬ (Top Bar) ---
        self.top_bar = ctk.CTkFrame(self, height=65, corner_radius=0, fg_color=("#ffffff", "#18181b"))
        self.top_bar.grid(row=0, column=0, sticky="ew")
        
        self.logo_text = ctk.CTkLabel(self.top_bar, text="RITA Docs", 
                                      font=ctk.CTkFont(size=22, weight="bold"),
                                      text_color=("#111827", "#f9fafb"))
        self.logo_text.pack(side="left", padx=25, pady=15)

        # Поиск (восстановлен и стилизован)
        self.search_entry = ctk.CTkEntry(self.top_bar, placeholder_text="🔍 Поиск статей...", 
                                         width=220, height=36, corner_radius=8,
                                         fg_color=("#f3f4f6", "#27272a"), border_width=1)
        self.search_entry.pack(side="left", padx=(10, 20))
        self.search_entry.bind("<KeyRelease>", self.filter_articles)

        self.fetch_btn = ctk.CTkButton(self.top_bar, text="Обновить", 
                                       command=self.handle_fetch_list, height=36, corner_radius=8,
                                       fg_color=("#e5e7eb", "#27272a"), text_color=("#111827", "#f9fafb"),
                                       hover_color=("#d1d5db", "#3f3f46"))
        self.fetch_btn.pack(side="left", padx=5)

        self.download_btn = ctk.CTkButton(self.top_bar, text="💾 Скачать базу (MD)", 
                                         command=self.handle_download_all, state="disabled",
                                         height=36, corner_radius=8, fg_color=("#10b981", "#059669"),
                                         hover_color=("#059669", "#047857"))
        self.download_btn.pack(side="left", padx=15)

        self.ai_toggle_btn = ctk.CTkButton(self.top_bar, text="🤖 RITA ИИ", 
                                          command=self.toggle_ai_panel, height=36, corner_radius=8,
                                          state="normal" if AI_AVAILABLE else "disabled")
        self.ai_toggle_btn.pack(side="left", padx=5)

        self.logout_btn = ctk.CTkButton(self.top_bar, text="Выйти", 
                                         command=self.master.handle_logout,
                                         height=36, width=90, corner_radius=8,
                                         fg_color="transparent", border_width=1,
                                         text_color="#ef4444", border_color="#ef4444",
                                         hover_color=("#fee2e2", "#7f1d1d"))
        self.logout_btn.pack(side="right", padx=25)

        user_name = self.user_info.get("user", {}).get("name", "Пользователь")
        self.user_label = ctk.CTkLabel(self.top_bar, text=f"👤 {user_name}", 
                                       font=ctk.CTkFont(size=14), text_color=("#4b5563", "#9ca3af"))
        self.user_label.pack(side="right", padx=15)

        # --- ОСНОВНАЯ ОБЛАСТЬ ---
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=1, column=0, sticky="nsew", padx=20, pady=15)
        
        self.main_area.grid_columnconfigure(0, weight=1) 
        self.main_area.grid_columnconfigure(1, weight=3) 
        self.main_area.grid_rowconfigure(0, weight=1)

        # 1. Оглавление
        self.toc_frame = ctk.CTkScrollableFrame(self.main_area, fg_color=("#ffffff", "#1e1e24"), corner_radius=12)
        self.toc_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # 2. Контент статьи
        self.content_frame = ctk.CTkFrame(self.main_area, fg_color=("#ffffff", "#1e1e24"), corner_radius=12)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        self.article_textbox = ctk.CTkTextbox(self.content_frame, wrap="word", fg_color="transparent")
        self.article_textbox.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.setup_text_tags(self.article_textbox._textbox, is_chat=False)
        self.article_textbox.insert("0.0", "Выберите статью слева или задайте вопрос RITA ИИ...", "p")
        self.article_textbox.configure(state="disabled")

        # 3. ИИ ЧАТ
        self.ai_panel = ctk.CTkFrame(self.main_area, fg_color=("#ffffff", "#1e1e24"), corner_radius=12, border_width=1, border_color=("#e5e7eb", "#27272a"))
        self.ai_panel.grid_columnconfigure(0, weight=1)
        self.ai_panel.grid_rowconfigure(1, weight=1)

        self.ai_header = ctk.CTkFrame(self.ai_panel, fg_color="transparent", height=50)
        self.ai_header.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        ctk.CTkLabel(self.ai_header, text="🤖 RITA Intelligence", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        ctk.CTkButton(self.ai_header, text="✕", width=25, height=25, fg_color="transparent", text_color=("#6b7280", "#9ca3af"), hover_color=("#fee2e2", "#7f1d1d"), command=self.toggle_ai_panel).pack(side="right")

        self.chat_textbox = ctk.CTkTextbox(self.ai_panel, wrap="word", fg_color=("#f9fafb", "#18181b"), corner_radius=8, border_width=1, border_color=("#e5e7eb", "#27272a"))
        self.chat_textbox.grid(row=1, column=0, sticky="nsew", padx=15, pady=10)
        self.setup_text_tags(self.chat_textbox._textbox, is_chat=True)
        self.chat_textbox.configure(state="disabled")

        self.input_area = ctk.CTkFrame(self.ai_panel, fg_color="transparent")
        self.input_area.grid(row=2, column=0, sticky="ew", padx=15, pady=(10, 15))
        
        self.chat_input = ctk.CTkEntry(self.input_area, placeholder_text="Спросите о RITA...", height=40, corner_radius=8)
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.chat_input.bind("<Return>", lambda e: self.handle_ai_query())

        self.send_btn = ctk.CTkButton(self.input_area, text="Отправить", width=80, height=40, corner_radius=8, command=self.handle_ai_query)
        self.send_btn.pack(side="right")
        
        self.ai_status_label = ctk.CTkLabel(self.ai_panel, text="ИИ готов.", font=ctk.CTkFont(size=11), text_color="#9ca3af")
        self.ai_status_label.grid(row=3, column=0, sticky="w", padx=15, pady=(0, 5))

        self.ai_panel_visible = False

        # --- СТАТУС БАР ---
        self.status_bar = ctk.CTkFrame(self, height=35, corner_radius=0, fg_color=("#ffffff", "#18181b"))
        self.status_bar.grid(row=2, column=0, sticky="ew")
        
        self.progress_bar = ctk.CTkProgressBar(self.status_bar, height=6, corner_radius=3)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=20, pady=10)
        self.progress_bar.set(0)

        self.count_label = ctk.CTkLabel(self.status_bar, text="Статей: 0", font=ctk.CTkFont(size=13, weight="bold"))
        self.count_label.pack(side="right", padx=25)

        self.log_label = ctk.CTkLabel(self.status_bar, text="Готов к работе", text_color=("#4b5563", "#9ca3af"))
        self.log_label.pack(side="right", padx=20)

    # --- ЛОГИКА ИИ ---
    def toggle_ai_panel(self):
        if not AI_AVAILABLE: return

        if self.ai_panel_visible:
            self.ai_panel.grid_remove()
            self.main_area.grid_columnconfigure(2, weight=0)
            self.ai_toggle_btn.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
            self.ai_panel_visible = False
        else:
            self.ai_panel.grid(row=0, column=2, sticky="nsew", padx=(20, 0))
            self.main_area.grid_columnconfigure(2, weight=2)
            self.ai_toggle_btn.configure(fg_color=("#2563eb", "#1d4ed8"))
            self.ai_panel_visible = True
            
            if not self.ai_indexed:
                self.ensure_ai_is_trained()

    def ensure_ai_is_trained(self):
        docs_path = self.ai.docs_dir if self.ai else "articles"
        if not os.path.exists(docs_path) or not os.listdir(docs_path):
            self.add_ai_message("assistant", "⚠️ База знаний пуста. Пожалуйста, скачайте базу (MD), чтобы я мог изучить материалы.")
            return

        self.ai_status_label.configure(text="⏳ ИИ изучает документацию...", text_color="#f59e0b")
        self.chat_input.configure(state="disabled")
        self.send_btn.configure(state="disabled")
        
        def bg_train():
            try:
                start_time = time.time()
                self.ai.build_knowledge_base()
                duration = int(time.time() - start_time)
                self.ai_indexed = True
                self.run_in_ui(self.on_ai_trained, f"🎉 Обучение завершено за {duration}с. Я готов отвечать!")
            except Exception as e:
                self.run_in_ui(self.on_ai_trained, f"❌ Ошибка обучения: {str(e)}", is_error=True)

        threading.Thread(target=bg_train, daemon=True).start()

    def on_ai_trained(self, message, is_error=False):
        self.chat_input.configure(state="normal")
        self.send_btn.configure(state="normal")
        if is_error:
            self.ai_status_label.configure(text="Ошибка обучения.", text_color="#ef4444")
        else:
            self.ai_status_label.configure(text="ИИ обучен. Готов.", text_color="#10b981")
        self.add_ai_message("assistant", message)

    def handle_ai_query(self):
        query = self.chat_input.get().strip()
        if not query or not self.ai_indexed: return
        self.chat_input.delete(0, "end")
        self.add_ai_message("user", query)
        self.ai_status_label.configure(text="⏳ RITA думает...", text_color="#f59e0b")
        self.send_btn.configure(state="disabled")

        async def do_ask():
            answer = await self.loop.run_in_executor(None, self.ai.ask, query)
            def update_ui():
                self.add_ai_message("assistant", answer)
                self.ai_status_label.configure(text="ИИ обучен. Готов.", text_color="#10b981")
                self.send_btn.configure(state="normal")
            self.run_in_ui(update_ui)
        asyncio.run_coroutine_threadsafe(do_ask(), self.loop)

    def add_ai_message(self, role, text):
        self.chat_textbox.configure(state="normal")
        timestamp = time.strftime("%H:%M")
        if role == "user":
            header = f"👤 Вы [{timestamp}]\n"
            content_tag, header_tag = "chat_user_body", "chat_user_header"
        else:
            header = f"🤖 RITA ИИ [{timestamp}]\n"
            content_tag, header_tag = "chat_ai_body", "chat_ai_header"
            
        self.chat_textbox.insert("end", header, header_tag)
        self.insert_formatted_chat_text(text, content_tag)
        self.chat_textbox.insert("end", "\n\n")
        self.chat_textbox.configure(state="disabled")
        self.chat_textbox.see("end")

    def insert_formatted_chat_text(self, text, body_tag):
        code_blocks = re.findall(r'```(.*?)```', text, re.DOTALL)
        text_parts = re.split(r'```.*?```', text, flags=re.DOTALL)
        
        for i in range(len(text_parts)):
            p_text = text_parts[i]
            bold_parts = re.split(r'\*\*(.*?)\*\*', p_text)
            for j, bit in enumerate(bold_parts):
                if j % 2 == 1: 
                    self.chat_textbox.insert("end", bit, (body_tag, "chat_bold"))
                else:
                    self.chat_textbox.insert("end", bit, body_tag)
            
            if i < len(code_blocks):
                code_text = re.sub(r'^\w+\n', '', code_blocks[i].strip()) 
                self.chat_textbox.insert("end", "\n")
                self.chat_textbox.insert("end", code_text, "chat_code")
                self.chat_textbox.insert("end", "\n")

    # --- СТАНДАРТНАЯ ЛОГИКА UI ---
    def setup_text_tags(self, tb, is_chat=False):
        font_family = "Helvetica"
        text_color = "#1f2937" if ctk.get_appearance_mode() == "Light" else "#f9fafb"
        bg_color_alt = "#f3f4f6" if ctk.get_appearance_mode() == "Light" else "#2b2b36"
        tb.tag_config("chat_bold", font=(font_family, 13, "bold"))

        if is_chat:
            chat_font = (font_family, 13)
            tb.tag_config("chat_user_header", font=(font_family, 11, "bold"), foreground="#3b82f6", spacing1=5)
            tb.tag_config("chat_ai_header", font=(font_family, 11, "bold"), foreground="#10b981", spacing1=5)
            tb.tag_config("chat_user_body", font=chat_font, foreground=text_color, lmargin1=10, lmargin2=10)
            tb.tag_config("chat_ai_body", font=chat_font, foreground=text_color, lmargin1=10, lmargin2=10)
            code_bg = "#e5e7eb" if ctk.get_appearance_mode() == "Light" else "#11181b"
            tb.tag_config("chat_code", font=("Courier New", 12), foreground=text_color, background=code_bg, lmargin1=20, lmargin2=20, spacing1=5, spacing3=5)
        else:
            tb.tag_config("h1", font=(font_family, 26, "bold"), foreground=text_color, spacing1=20, spacing3=20)
            tb.tag_config("h2", font=(font_family, 22, "bold"), foreground=text_color, spacing1=15, spacing3=10)
            tb.tag_config("h3", font=(font_family, 18, "bold"), foreground=text_color, spacing1=10, spacing3=5)
            tb.tag_config("h4", font=(font_family, 15, "bold"), foreground=text_color, spacing1=10, spacing3=5)
            tb.tag_config("p", font=(font_family, 14), foreground=text_color, spacing1=6, spacing3=6)
            tb.tag_config("li", font=(font_family, 14), foreground=text_color, lmargin1=25, lmargin2=40, spacing1=4, spacing3=4)
            tb.tag_config("table", font=("Courier New", 13), foreground=text_color, background=bg_color_alt, spacing1=5, spacing3=5)
            tb.tag_config("image_placeholder", font=(font_family, 12, "italic"), foreground="#9ca3af", justify="center", spacing1=10, spacing3=10)

    def clean_html_text(self, text):
        text = str(text)
        text = text.replace("&lt;br&gt;", "\n").replace("<br>", "\n").replace("&nbsp;", " ")
        text = html.unescape(text)
        return re.sub(r'<[^>]+>', '', text).strip()

    def format_table(self, rows):
        if not rows: return ""
        max_cols = max(len(row) for row in rows)
        col_widths = [0] * max_cols
        for row in rows:
            for i in range(max_cols):
                if i < len(row):
                    cell = self.clean_html_text(row[i])
                    col_widths[i] = max(col_widths[i], len(cell))
        col_widths = [min(w, 40) for w in col_widths]
        text = ""
        separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        text += separator + "\n"
        for r_idx, row in enumerate(rows):
            row_str = "|"
            for i in range(max_cols):
                cell_text = self.clean_html_text(row[i]) if i < len(row) else ""
                if len(cell_text) > 40: cell_text = cell_text[:37] + "..."
                row_str += " " + cell_text.ljust(col_widths[i]) + " |"
            text += row_str + "\n"
            if r_idx == 0: text += separator + "\n"
        text += separator
        return text

    def run_in_ui(self, func, *args, **kwargs):
        is_error = kwargs.get('is_error', False)
        if 'is_error' in kwargs:
            self.after(0, lambda: func(*args, is_error=is_error))
        else:
            self.after(0, lambda: func(*args))

    def log(self, message):
        self.log_label.configure(text=message)

    def handle_fetch_list(self):
        self.fetch_btn.configure(state="disabled")
        self.log("Загрузка дерева статей...")
        async def do_fetch():
            articles = await self.api.get_articles()
            if articles is not None:
                self.articles = articles
                self.run_in_ui(self.update_article_display)
            else:
                self.run_in_ui(self.log, "Ошибка загрузки списка статей")
            self.run_in_ui(lambda: self.fetch_btn.configure(state="normal"))
        asyncio.run_coroutine_threadsafe(do_fetch(), self.loop)

    def filter_articles(self, event=None):
        query = self.search_entry.get().lower()
        for widget in self.toc_frame.winfo_children(): widget.destroy()
        if not query:
            self.update_article_display()
            return
        
        # Лимит рендера, чтобы избежать фризов UI при массовом поиске O(1) Updates
        count = 0
        for art in self.articles:
            if query in art["title"].lower(): 
                self._render_single_item(art, self.toc_frame)
                count += 1
                if count >= 100: break

    def update_article_display(self):
        for widget in self.toc_frame.winfo_children(): widget.destroy()
        self.article_map = {art["id"]: art for art in self.articles}
        self.children_map = {}
        roots = []
        for art in self.articles:
            pid = art.get("parent_id")
            if pid is not None:
                if pid not in self.children_map: self.children_map[pid] = []
                self.children_map[pid].append(art)
        for art in self.articles:
            pid = art.get("parent_id")
            if pid is None or pid not in self.article_map: roots.append(art)
            
        for root in sorted(roots, key=lambda x: x["title"]): 
            self.render_node(root, self.toc_frame, 0)
            
        self.count_label.configure(text=f"Статей: {len(self.articles)}")
        self.download_btn.configure(state="normal")
        self.log("Оглавление успешно обновлено")

    def _render_single_item(self, article, container):
        frame = ctk.CTkFrame(container, fg_color="transparent", cursor="hand2")
        frame.pack(fill="x", padx=10, pady=2)
        lbl = ctk.CTkLabel(frame, text=f"📄 {article['title']}", anchor="w", font=ctk.CTkFont(size=14), cursor="hand2")
        lbl.pack(fill="x", padx=5, pady=6)
        def on_enter(e): frame.configure(fg_color=("#e5e7eb", "#27272a"))
        def on_leave(e): frame.configure(fg_color="transparent")
        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)
        lbl.bind("<Enter>", on_enter)
        lbl.bind("<Leave>", on_leave)
        frame.bind("<Button-1>", lambda e, u=article['url']: self.load_article_content(u))
        lbl.bind("<Button-1>", lambda e, u=article['url']: self.load_article_content(u))

    def render_node(self, node, parent_container, level):
        frame = ctk.CTkFrame(parent_container, fg_color="transparent")
        frame.pack(fill="x", padx=(level * 15, 0), pady=1)
        has_children = node["id"] in self.children_map
        row_frame = ctk.CTkFrame(frame, fg_color="transparent", cursor="hand2")
        row_frame.pack(fill="x")
        
        if has_children:
            node["_expanded"] = False
            btn_toggle = ctk.CTkButton(row_frame, text="›", width=24, height=30, fg_color="transparent", hover_color=("#d1d5db", "#3f3f46"), text_color=("#111827", "#f9fafb"), font=ctk.CTkFont(size=18, weight="bold"), command=lambda n=node, f=frame, l=level: self.toggle_node(n, f, l))
            btn_toggle.pack(side="left", padx=(0, 2))
            node["_btn"] = btn_toggle
            node["_child_container"] = ctk.CTkFrame(frame, fg_color="transparent")
            icon = "📁"
            font_weight = "bold"
        else:
            spacer = ctk.CTkFrame(row_frame, width=24, height=30, fg_color="transparent")
            spacer.pack(side="left", padx=(0, 2))
            icon = "📄"
            font_weight = "normal"
            
        lbl = ctk.CTkLabel(row_frame, text=f"{icon} {node['title']}", anchor="w", font=ctk.CTkFont(size=14, weight=font_weight), cursor="hand2")
        lbl.pack(side="left", fill="x", expand=True, pady=4)
        def on_enter(e): row_frame.configure(fg_color=("#e5e7eb", "#27272a"))
        def on_leave(e): row_frame.configure(fg_color="transparent")
        row_frame.bind("<Enter>", on_enter)
        row_frame.bind("<Leave>", on_leave)
        lbl.bind("<Enter>", on_enter)
        lbl.bind("<Leave>", on_leave)
        lbl.bind("<Button-1>", lambda e, u=node['url']: self.load_article_content(u))
        row_frame.bind("<Button-1>", lambda e, u=node['url']: self.load_article_content(u))

    def toggle_node(self, node, parent_frame, level):
        container = node["_child_container"]
        if node["_expanded"]:
            container.pack_forget()
            node["_btn"].configure(text="›")
            node["_expanded"] = False
        else:
            if not container.winfo_children():
                children = sorted(self.children_map[node["id"]], key=lambda x: x["title"])
                for child in children: self.render_node(child, container, level + 1)
            container.pack(fill="x")
            node["_btn"].configure(text="⌄")
            node["_expanded"] = True

    def load_article_content(self, url):
        self.article_textbox.configure(state="normal")
        self.article_textbox.delete("0.0", "end")
        self.article_textbox.insert("end", "⏳ Загрузка статьи...\n", "h2")
        self.article_textbox.configure(state="disabled")
        self.log("Получение данных статьи...")
        self.image_cache.clear()
        
        async def fetch_and_display():
            content = await self.api.get_article_content(url)
            def update_ui():
                self.article_textbox.configure(state="normal")
                self.article_textbox.delete("0.0", "end")
                if content and "data" in content and "blocks" in content["data"]:
                    title = content.get("title", "Без названия")
                    self.article_textbox.insert("end", title + "\n\n", "h1")
                    blocks = content["data"]["blocks"]
                    for i, block in enumerate(blocks):
                        b_type = block.get("type")
                        data = block.get("data", {})
                        if b_type == "header":
                            level = data.get("level", 2)
                            text = self.clean_html_text(data.get("text", ""))
                            tag = f"h{level}" if level in [1, 2, 3, 4] else "h4"
                            self.article_textbox.insert("end", text + "\n", tag)
                        elif b_type == "paragraph":
                            text = self.clean_html_text(data.get("text", ""))
                            if text: self.article_textbox.insert("end", text + "\n", "p")
                        elif b_type == "list":
                            items = data.get("items", [])
                            style = data.get("style", "unordered")
                            for j, item in enumerate(items):
                                item_content = self.clean_html_text(item.get("content", "") if isinstance(item, dict) else item)
                                prefix = f"{j+1}. " if style == "ordered" else "• "
                                self.article_textbox.insert("end", prefix + item_content + "\n", "li")
                        elif b_type == "table":
                            content_table = data.get("content", [])
                            if content_table:
                                table_str = self.format_table(content_table)
                                self.article_textbox.insert("end", table_str + "\n", "table")
                        elif b_type == "image":
                            file_info = data.get("file", {})
                            img_url = file_info.get("url", "")
                            if img_url:
                                if img_url.startswith("/"):
                                    base = self.api.base_url.replace("/api", "")
                                    img_url = base + img_url
                                mark_name = f"img_mark_{i}"
                                self.article_textbox.insert("end", "\n")
                                self.article_textbox.mark_set(mark_name, "end-1c")
                                self.article_textbox.mark_gravity(mark_name, "left")
                                self.article_textbox.insert("end", f"🖼 [Идет загрузка изображения...]\n\n", "image_placeholder")
                                asyncio.run_coroutine_threadsafe(self.fetch_and_insert_image(img_url, mark_name), self.loop)
                else:
                    self.article_textbox.insert("end", "⚠️ Ошибка: Данные статьи отсутствуют.", "p")
                self.article_textbox.configure(state="disabled")
                self.log("Статья успешно загружена")
            self.run_in_ui(update_ui)
        asyncio.run_coroutine_threadsafe(fetch_and_display(), self.loop)

    async def fetch_and_insert_image(self, url, mark_name):
        try:
            if not self.api.session: await self.api.start_session()
            async with self.api.session.get(url) as response:
                if response.status == 200:
                    img_data = await response.read()
                    image = Image.open(io.BytesIO(img_data))
                    max_width = 750
                    if image.width > max_width:
                        ratio = max_width / image.width
                        image = image.resize((max_width, int(image.height * ratio)), Image.Resampling.LANCZOS)
                    tk_photo = ImageTk.PhotoImage(image)
                    def ui_insert():
                        self.article_textbox.configure(state="normal")
                        self.image_cache.append(tk_photo)
                        try:
                            index = self.article_textbox.index(mark_name)
                            self.article_textbox._textbox.image_create(index, image=tk_photo)
                        except Exception: pass
                        self.article_textbox.configure(state="disabled")
                    self.run_in_ui(ui_insert)
        except Exception as e: print(f"Image load error {url}: {e}")

    # ========================================================
    # РЕШЕНИЕ ПРОБЛЕМЫ ЗАГРУЗКИ (Concurrency + Tree Generator)
    # ========================================================
    def handle_download_all(self):
        self.download_btn.configure(state="disabled", text="⏳ Подготовка...")
        
        async def do_download():
            save_path = self.master.settings_data.get("path", os.path.abspath("articles"))
            if not os.path.exists(save_path): os.makedirs(save_path)
            
            # Для восстановления иерархии папок 
            article_map = {a["id"]: a for a in self.articles}
            total = len(self.articles)
            downloaded = 0
            
            # Семафор: загрузка по 20 файлов параллельно вместо 1, что решает проблему со скоростью (O(1) Concurrency)
            sem = asyncio.Semaphore(20)

            async def process_article(article):
                nonlocal downloaded
                async with sem:
                    url = article["url"]
                    content = await self.api.get_article_content(url)
                    
                    if content and "data" in content and "blocks" in content["data"]:
                        md = blocks_to_markdown(content["data"]["blocks"])
                        
                        # 1. Построение безопасного пути к файлу с учетом иерархии (предотвращает перезапись одинаковых имен)
                        parts = []
                        curr = article
                        visited = set() # Защита от потенциальных циклов в бэкенде
                        
                        while curr and curr["id"] not in visited:
                            visited.add(curr["id"])
                            safe_name = re.sub(r'[\\/*?:"<>|]', "_", curr["title"]).strip()
                            if not safe_name: safe_name = f"doc_{curr['id']}"
                            parts.insert(0, safe_name)
                            curr = article_map.get(curr.get("parent_id"))
                            
                        # Создаем физические папки на диске 
                        if len(parts) > 1:
                            dir_path = os.path.join(save_path, *parts[:-1])
                            os.makedirs(dir_path, exist_ok=True)
                            filename = os.path.join(dir_path, f"{parts[-1]}.md")
                        else:
                            filename = os.path.join(save_path, f"{parts[0]}.md")
                            
                        try:
                            async with aiofiles.open(filename, mode='w', encoding='utf-8') as f:
                                await f.write(f"# {article['title']}\n\n{md}")
                        except Exception as e: 
                            print(f"Error saving {filename}: {e}")

                    downloaded += 1
                    
                    # Throttling обновлений UI, чтобы прогресс-бар не зависал при 20 одновременных загрузках
                    if downloaded % 5 == 0 or downloaded == total:
                        self.run_in_ui(self.progress_bar.set, downloaded / total)
                        self.run_in_ui(self.log, f"Скачано: {downloaded} из {total}")

            self.run_in_ui(self.log, "Начало загрузки базы...")
            self.run_in_ui(self.download_btn.configure, text="⏳ Загрузка...")
            
            # Запускаем все задачи сразу, но семафор пустит только 20 одновременно
            tasks = [process_article(a) for a in self.articles]
            await asyncio.gather(*tasks)

            self.run_in_ui(self.log, "Все файлы успешно скачаны (Дерево папок сохранено)!")
            
            if self.ai_panel_visible and AI_AVAILABLE:
                self.run_in_ui(lambda: self.add_ai_message("assistant", "📝 База обновлена. Я автоматически переобучусь при следующем запросе или вы можете перезапустить меня."))
                self.ai_indexed = False

            self.run_in_ui(lambda: self.download_btn.configure(state="normal", text="💾 Скачать базу (MD)"))
            self.run_in_ui(lambda: self.progress_bar.set(0))

        asyncio.run_coroutine_threadsafe(do_download(), self.loop)

# Слегка стилизованный экран авторизации
class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_login = on_login
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Обновлен дизайн карточки
        self.card = ctk.CTkFrame(self, fg_color=("#ffffff", "#24242a"), corner_radius=16, border_width=1, border_color=("#e5e7eb", "#3f3f46"))
        self.card.grid(row=0, column=0, padx=20, pady=20, ipadx=40, ipady=40)
        
        self.title_label = ctk.CTkLabel(self.card, text="Вход в RITA Docs", font=ctk.CTkFont(size=28, weight="bold"), text_color=("#1f2937", "#f9fafb"))
        self.title_label.pack(pady=(20, 40))
        
        self.login_entry = ctk.CTkEntry(self.card, placeholder_text="Логин", width=300, height=45, corner_radius=8, border_width=1, fg_color=("#f3f4f6", "#2b2b36"))
        self.login_entry.pack(pady=(0, 15))
        
        self.password_entry = ctk.CTkEntry(self.card, placeholder_text="Пароль", show="*", width=300, height=45, corner_radius=8, border_width=1, fg_color=("#f3f4f6", "#2b2b36"))
        self.password_entry.pack(pady=(0, 15))
        
        self.remember_var = ctk.BooleanVar(value=self.master.settings_data.get("remember", True))
        self.remember_cb = ctk.CTkCheckBox(self.card, text="Оставаться в системе", variable=self.remember_var, font=ctk.CTkFont(size=13), checkbox_width=20, checkbox_height=20, border_width=2, corner_radius=4)
        self.remember_cb.pack(anchor="w", padx=25, pady=(0, 25))
        
        self.login_button = ctk.CTkButton(self.card, text="Войти", command=self.handle_login, width=300, height=45, corner_radius=8, font=ctk.CTkFont(size=15, weight="bold"))
        self.login_button.pack(pady=(0, 10))
        
        self.error_label = ctk.CTkLabel(self.card, text="", text_color="#ef4444", font=ctk.CTkFont(size=12))
        self.error_label.pack()

    def handle_login(self):
        login = self.login_entry.get().strip()
        password = self.password_entry.get().strip()
        if not login or not password:
            self.error_label.configure(text="Введите логин и пароль")
            return
        self.login_button.configure(state="disabled", text="Авторизация...")
        self.error_label.configure(text="")
        self.master.update_settings({"remember": self.remember_var.get()})
        self.on_login(login, password)

    def reset_ui(self):
        self.login_button.configure(state="normal", text="Войти")

class RitaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RITA ETL Pipeline")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")
        try: self.state('zoomed')
        except: self.attributes('-zoomed', True)
        self.api = RitaAPI()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()
        self.current_frame = None
        self.settings_file = "app_settings.json"
        self.settings_data = self.load_settings()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.check_initial_auth()

    def run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def check_initial_auth(self):
        async def verify():
            if self.settings_data.get("remember", False):
                is_valid, user_info = await self.api.verify_saved_session()
                if is_valid:
                    self.after(0, lambda: self.show_dashboard(user_info))
                    return
            self.after(0, self.show_login)
        asyncio.run_coroutine_threadsafe(verify(), self.loop)

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f: return json.load(f)
            except: pass
        return {"path": os.path.abspath("articles"), "remember": True}

    def update_settings(self, new_data):
        self.settings_data.update(new_data)
        with open(self.settings_file, 'w', encoding='utf-8') as f: json.dump(self.settings_data, f)

    def handle_login_action(self, login, password):
        async def do_login():
            success, result = await self.api.login(login, password)
            if success:
                if not self.settings_data.get("remember"): self.api.clear_session_data()
                self.after(0, lambda: self.show_dashboard(result))
            else:
                self.after(0, lambda: self.current_frame.error_label.configure(text=result))
                self.after(0, self.current_frame.reset_ui)
        asyncio.run_coroutine_threadsafe(do_login(), self.loop)

    def handle_logout(self):
        self.api.clear_session_data()
        self.show_login()

    def switch_frame(self, frame_class, **kwargs):
        if self.current_frame: self.current_frame.destroy()
        self.current_frame = frame_class(self, **kwargs)
        self.current_frame.pack(fill="both", expand=True)

    def show_login(self): self.switch_frame(LoginFrame, on_login=self.handle_login_action)
    def show_dashboard(self, user_info=None): self.switch_frame(DashboardFrame, api=self.api, loop=self.loop, user_info=user_info)

    def on_closing(self):
        async def close():
            await self.api.close_session()
            self.loop.stop()
        asyncio.run_coroutine_threadsafe(close(), self.loop)
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = RitaApp()
    app.mainloop()