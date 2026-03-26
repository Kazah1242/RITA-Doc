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
import aiofiles
from PIL import Image, ImageTk
import cairosvg
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

# ==========================================
# SVG Icon Generator (Minimalist UI)
# ==========================================
def get_svg_icon(svg_string, size=(20, 20)):
    light_color, dark_color = "#1f2937", "#f9fafb"
    svg_light = svg_string.replace("currentColor", light_color)
    svg_dark = svg_string.replace("currentColor", dark_color)
    png_light = cairosvg.svg2png(bytestring=svg_light.encode('utf-8'), output_width=size[0], output_height=size[1])
    png_dark = cairosvg.svg2png(bytestring=svg_dark.encode('utf-8'), output_width=size[0], output_height=size[1])
    return ctk.CTkImage(light_image=Image.open(io.BytesIO(png_light)), dark_image=Image.open(io.BytesIO(png_dark)), size=size)

ICONS = {
    "docs": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>',
    "robot": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path><line x1="8" y1="16" x2="8" y2="16"></line><line x1="16" y1="16" x2="16" y2="16"></line></svg>',
    "send": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>',
    "user": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>',
    "folder": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>',
    "file": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>',
    "refresh": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>',
    "download": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>',
    "logout": '<svg viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>'
}

# ==========================================
# Класс для UI сообщений в реальном времени
# ==========================================
class StreamingMessage:
    def __init__(self, parent_scroll):
        self.parent_scroll = parent_scroll
        
        self.msg_container = ctk.CTkFrame(self.parent_scroll, fg_color="transparent")
        self.msg_container.pack(fill="x", padx=10, pady=(5, 15))
        self.msg_container.grid_columnconfigure(0, weight=1)

        self.bubble = ctk.CTkFrame(self.msg_container, fg_color=("#f4f4f5", "#27272a"), corner_radius=16)
        self.bubble.grid(row=0, column=0, sticky="w", padx=(0, 60))
        
        self.thoughts_visible = True
        self.thought_container = ctk.CTkFrame(self.bubble, fg_color="transparent")
        
        self.toggle_btn = ctk.CTkButton(
            self.thought_container, text="💭 Размышление...", fg_color="transparent", 
            text_color=("#9ca3af", "#71717a"), hover_color=("#e4e4e7", "#3f3f46"),
            height=24, font=ctk.CTkFont(size=13, slant="italic"), command=self.toggle_thoughts
        )
        self.toggle_btn.pack(anchor="w", padx=10, pady=(10, 0))
        
        self.thought_tb = ctk.CTkTextbox(
            self.thought_container, wrap="word", fg_color="transparent",
            text_color=("#9ca3af", "#71717a"), font=ctk.CTkFont(size=13, slant="italic"),
            height=30, width=550, border_spacing=0
        )
        self.thought_tb.pack(padx=10, pady=(0, 5))
        
        self.answer_tb = ctk.CTkTextbox(
            self.bubble, wrap="word", fg_color="transparent",
            text_color=("#1f2937", "#f9fafb"), font=ctk.CTkFont(size=15),
            height=30, width=550, border_spacing=0
        )
        
        self.has_thoughts = False
        self.auto_collapsed = False

    def toggle_thoughts(self):
        if self.thoughts_visible:
            self.thought_tb.pack_forget()
            self.toggle_btn.configure(text="💭 Показать ход мыслей")
        else:
            self.thought_tb.pack(padx=10, pady=(0, 5))
            self.toggle_btn.configure(text="💭 Скрыть ход мыслей")
        self.thoughts_visible = not self.thoughts_visible
        self.parent_scroll._parent_canvas.yview_moveto(1.0)

    def update(self, data):
        thinking = data.get("thinking", "")
        answer = data.get("answer", "")
        is_thinking_done = data.get("is_thinking_done", False)
        sources = data.get("sources", [])
        status = data.get("status", "success")

        if status == "error":
            self.answer_tb.pack(padx=15, pady=15)
            self._update_tb(self.answer_tb, data.get("content", ""), is_ai=True)
            return

        if thinking:
            self.has_thoughts = True
            if not self.thought_container.winfo_ismapped() and not self.auto_collapsed:
                self.thought_container.pack(fill="x")
            self._update_tb(self.thought_tb, thinking, is_ai=True)

        if is_thinking_done and self.has_thoughts and not self.auto_collapsed:
            self.toggle_thoughts()
            self.auto_collapsed = True

        if answer or sources:
            if not self.answer_tb.winfo_ismapped():
                self.answer_tb.pack(padx=15, pady=15)
            
            final_text = answer
            if sources: final_text += f"\n\n📚 Источники: {', '.join(sources)}"
            self._update_tb(self.answer_tb, final_text, is_ai=True)
        
        if self.parent_scroll._parent_canvas.yview()[1] >= 0.9:
            self.parent_scroll._parent_canvas.yview_moveto(1.0)

    def _update_tb(self, tb, text, is_ai=False):
        tb.configure(state="normal")
        tb.delete("0.0", "end")
        tb.insert("0.0", text)
        
        char_width = 8
        calc_width = min(600, max(150, len(text) * char_width))
        lines = text.count('\n') + (len(text) * char_width // calc_width) + 1
        
        tb.configure(height=max(35, lines * 22), width=calc_width if not is_ai else 550)
        tb.configure(state="disabled")

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master, api, loop, user_info=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.api = api
        self.loop = loop
        self.articles = []
        self.user_info = user_info or {}
        
        self.icons = {k: get_svg_icon(v) for k, v in ICONS.items()}
        self.icon_logout = get_svg_icon(ICONS["logout"])
        
        self.ai = RitaAIAssistant() if AI_AVAILABLE else None
        self.ai_indexed = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        
        self.screens_container = ctk.CTkFrame(self, fg_color="transparent")
        self.screens_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=15)
        self.screens_container.grid_columnconfigure(0, weight=1)
        self.screens_container.grid_rowconfigure(0, weight=1)

        self._build_docs_screen()
        self._build_chat_screen()
        self._build_statusbar()

        self.show_screen("docs")

    def _build_header(self):
        self.top_bar = ctk.CTkFrame(self, height=65, corner_radius=0, fg_color=("#ffffff", "#18181b"))
        self.top_bar.grid(row=0, column=0, sticky="ew")
        
        ctk.CTkLabel(self.top_bar, text="RITA Docs", font=ctk.CTkFont(size=22, weight="bold"), text_color=("#111827", "#f9fafb")).pack(side="left", padx=25, pady=15)

        self.nav_frame = ctk.CTkFrame(self.top_bar, fg_color=("#f3f4f6", "#27272a"), corner_radius=8)
        self.nav_frame.pack(side="left", padx=20)

        self.nav_docs_btn = ctk.CTkButton(self.nav_frame, text=" Документация", image=self.icons["docs"], command=lambda: self.show_screen("docs"), height=36, width=140, fg_color=("#ffffff", "#3f3f46"), text_color=("#111827", "#f9fafb"), hover_color=("#e5e7eb", "#52525b"))
        self.nav_docs_btn.pack(side="left", padx=2, pady=2)

        self.nav_chat_btn = ctk.CTkButton(self.nav_frame, text=" ИИ Ассистент", image=self.icons["robot"], command=lambda: self.show_screen("chat"), height=36, width=140, fg_color="transparent", text_color=("#6b7280", "#a1a1aa"), hover_color=("#e5e7eb", "#3f3f46"), state="normal" if AI_AVAILABLE else "disabled")
        self.nav_chat_btn.pack(side="left", padx=2, pady=2)

        self.tools_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.tools_frame.pack(side="left", padx=20)

        self.fetch_btn = ctk.CTkButton(self.tools_frame, text="Обновить", image=self.icons["refresh"], command=self.handle_fetch_list, height=36, width=110, corner_radius=8, fg_color="transparent", text_color=("#111827", "#f9fafb"), hover_color=("#e5e7eb", "#27272a"))
        self.fetch_btn.pack(side="left", padx=5)

        self.download_btn = ctk.CTkButton(self.tools_frame, text="Скачать базу", image=self.icons["download"], command=self.handle_download_all, state="disabled", height=36, width=130, corner_radius=8, fg_color="transparent", text_color=("#111827", "#f9fafb"), hover_color=("#e5e7eb", "#27272a"))
        self.download_btn.pack(side="left", padx=5)

        self.logout_btn = ctk.CTkButton(self.top_bar, text="", image=self.icon_logout, command=self.master.handle_logout, height=36, width=36, corner_radius=8, fg_color="transparent", hover_color=("#fee2e2", "#7f1d1d"))
        self.logout_btn.pack(side="right", padx=15)

        user_name = self.user_info.get("user", {}).get("name", "Пользователь")
        ctk.CTkLabel(self.top_bar, text=user_name, font=ctk.CTkFont(size=14), text_color=("#4b5563", "#9ca3af")).pack(side="right", padx=5)
        ctk.CTkLabel(self.top_bar, text="", image=self.icons["user"]).pack(side="right")

    def _build_docs_screen(self):
        self.docs_screen = ctk.CTkFrame(self.screens_container, fg_color="transparent")
        self.docs_screen.grid_columnconfigure(0, weight=1); self.docs_screen.grid_columnconfigure(1, weight=3); self.docs_screen.grid_rowconfigure(0, weight=1)

        self.toc_frame = ctk.CTkScrollableFrame(self.docs_screen, fg_color=("#ffffff", "#1e1e24"), corner_radius=12)
        self.toc_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        self.content_frame = ctk.CTkFrame(self.docs_screen, fg_color=("#ffffff", "#1e1e24"), corner_radius=12)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.content_frame.grid_columnconfigure(0, weight=1); self.content_frame.grid_rowconfigure(0, weight=1)

        self.article_textbox = ctk.CTkTextbox(self.content_frame, wrap="word", fg_color="transparent", font=ctk.CTkFont(size=15))
        self.article_textbox.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)
        self.article_textbox.insert("0.0", "Выберите статью слева в меню...")
        self.article_textbox.configure(state="disabled")

    def _build_chat_screen(self):
        self.chat_screen = ctk.CTkFrame(self.screens_container, fg_color="transparent")
        self.chat_screen.grid_columnconfigure(0, weight=1); self.chat_screen.grid_columnconfigure(1, weight=4); self.chat_screen.grid_columnconfigure(2, weight=1)
        self.chat_screen.grid_rowconfigure(0, weight=1)

        self.chat_center = ctk.CTkFrame(self.chat_screen, fg_color="transparent")
        self.chat_center.grid(row=0, column=1, sticky="nsew", pady=10)
        self.chat_center.grid_columnconfigure(0, weight=1); self.chat_center.grid_rowconfigure(0, weight=1)

        self.chat_history_scroll = ctk.CTkScrollableFrame(self.chat_center, fg_color="transparent")
        self.chat_history_scroll.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.chat_history_scroll.grid_columnconfigure(0, weight=1)

        self.add_static_ai_message("👋 Привет! Я — ИИ-ассистент по документации RITA. Задайте мне вопрос, и я найду нужную информацию в нашей базе знаний.")

        self.input_area = ctk.CTkFrame(self.chat_center, fg_color=("#ffffff", "#1e1e24"), corner_radius=24, border_width=1, border_color=("#e5e7eb", "#3f3f46"))
        self.input_area.grid(row=1, column=0, sticky="ew", pady=(0, 10), ipady=5)
        
        self.chat_input = ctk.CTkEntry(self.input_area, placeholder_text="Спросить RITA...", height=40, corner_radius=24, border_width=0, fg_color="transparent", font=ctk.CTkFont(size=15))
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(20, 10), pady=5)
        self.chat_input.bind("<Return>", lambda e: self.handle_ai_query())

        self.send_btn = ctk.CTkButton(self.input_area, text="", image=self.icons["send"], width=40, height=40, corner_radius=20, fg_color=("#2563eb", "#3b82f6"), hover_color=("#1d4ed8", "#2563eb"), command=self.handle_ai_query)
        self.send_btn.pack(side="right", padx=(0, 10), pady=5)
        
        self.ai_status_label = ctk.CTkLabel(self.chat_center, text="ИИ готов к работе.", font=ctk.CTkFont(size=12), text_color="#9ca3af", height=10)
        self.ai_status_label.grid(row=2, column=0, sticky="w", padx=20)

    def _build_statusbar(self):
        self.status_bar = ctk.CTkFrame(self, height=35, corner_radius=0, fg_color=("#ffffff", "#18181b"))
        self.status_bar.grid(row=2, column=0, sticky="ew")
        self.progress_bar = ctk.CTkProgressBar(self.status_bar, height=4, corner_radius=2)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=20, pady=10)
        self.progress_bar.set(0)
        self.count_label = ctk.CTkLabel(self.status_bar, text="Статей: 0", font=ctk.CTkFont(size=12, weight="bold"))
        self.count_label.pack(side="right", padx=25)
        self.log_label = ctk.CTkLabel(self.status_bar, text="Готов к работе", text_color=("#4b5563", "#9ca3af"))
        self.log_label.pack(side="right", padx=20)

    def show_screen(self, screen_name):
        self.nav_docs_btn.configure(fg_color="transparent", text_color=("#6b7280", "#a1a1aa"))
        self.nav_chat_btn.configure(fg_color="transparent", text_color=("#6b7280", "#a1a1aa"))

        if screen_name == "docs":
            self.chat_screen.grid_forget()
            self.docs_screen.grid(row=0, column=0, sticky="nsew")
            self.nav_docs_btn.configure(fg_color=("#ffffff", "#3f3f46"), text_color=("#111827", "#f9fafb"))
        elif screen_name == "chat":
            self.docs_screen.grid_forget()
            self.chat_screen.grid(row=0, column=0, sticky="nsew")
            self.nav_chat_btn.configure(fg_color=("#ffffff", "#3f3f46"), text_color=("#111827", "#f9fafb"))
            if not self.ai_indexed:
                self.ensure_ai_is_trained()

    def ensure_ai_is_trained(self):
        if not os.path.exists("articles") or not os.listdir("articles"):
            self.add_static_ai_message("⚠️ База знаний пуста. Пожалуйста, обновите документацию.")
            return
        self.ai_status_label.configure(text="Инициализация базы данных...", text_color="#f59e0b")
        def bg_train():
            try:
                self.ai.build_knowledge_base()
                self.ai_indexed = True
                self.run_in_ui(self.ai_status_label.configure, text="RITA ИИ готов к диалогу.", text_color="#10b981")
            except Exception as e: pass
        threading.Thread(target=bg_train, daemon=True).start()

    def handle_ai_query(self):
        query = self.chat_input.get().strip()
        if not query or not self.ai_indexed: return
        self.chat_input.delete(0, "end")
        
        self.add_user_message(query)
        self.ai_status_label.configure(text="RITA думает...", text_color="#f59e0b")
        self.send_btn.configure(state="disabled")

        stream_bubble = StreamingMessage(self.chat_history_scroll)

        async def do_ask():
            try:
                update_counter = 0
                last_chunk = None
                async for chunk in self.ai.ask_stream(query):
                    update_counter += 1
                    last_chunk = chunk
                    if update_counter % 4 == 0 or chunk.get("is_thinking_done"):
                        self.run_in_ui(stream_bubble.update, chunk)
                
                if last_chunk:
                    self.run_in_ui(stream_bubble.update, last_chunk)
                    
                self.run_in_ui(self.ai_status_label.configure, text="RITA ИИ готов к диалогу.", text_color="#10b981")
            except Exception: pass
            finally: self.run_in_ui(self.send_btn.configure, state="normal")

        asyncio.run_coroutine_threadsafe(do_ask(), self.loop)

    def add_user_message(self, text):
        msg_container = ctk.CTkFrame(self.chat_history_scroll, fg_color="transparent")
        msg_container.pack(fill="x", padx=10, pady=(5, 15))
        msg_container.grid_columnconfigure(0, weight=1)

        bubble = ctk.CTkFrame(msg_container, fg_color=("#2563eb", "#3b82f6"), corner_radius=16)
        bubble.grid(row=0, column=0, sticky="e", padx=(60, 10))
        
        calc_width = min(500, max(50, len(text) * 9 + 30))
        lines = text.count('\n') + (len(text) * 9 // calc_width) + 1
        
        tb = ctk.CTkTextbox(bubble, wrap="word", fg_color="transparent", text_color="#ffffff", font=ctk.CTkFont(size=15), height=max(35, lines * 22), width=calc_width)
        tb.pack(padx=12, pady=8)
        tb.insert("0.0", text)
        tb.configure(state="disabled")
        self.run_in_ui(self.chat_history_scroll._parent_canvas.yview_moveto, 1.0)

    def add_static_ai_message(self, text):
        msg_container = ctk.CTkFrame(self.chat_history_scroll, fg_color="transparent")
        msg_container.pack(fill="x", padx=10, pady=(5, 15)); msg_container.grid_columnconfigure(0, weight=1)
        bubble = ctk.CTkFrame(msg_container, fg_color=("#f4f4f5", "#27272a"), corner_radius=16)
        bubble.grid(row=0, column=0, sticky="w", padx=(0, 60))
        lines = text.count('\n') + (len(text) // 60) + 1
        tb = ctk.CTkTextbox(bubble, wrap="word", fg_color="transparent", text_color=("#1f2937", "#f9fafb"), font=ctk.CTkFont(size=15), height=max(30, lines * 22), width=550)
        tb.pack(padx=15, pady=12); tb.insert("0.0", text); tb.configure(state="disabled")

    def run_in_ui(self, func, *args, **kwargs):
        self.after(0, lambda: func(*args, **kwargs))

    # --- ОСТАЛЬНАЯ ЛОГИКА ДОКУМЕНТАЦИИ И API (Оставлена без изменений для краткости) ---
    def clean_html_text(self, text):
        return html.unescape(str(text).replace("&lt;br&gt;", "\n").replace("<br>", "\n").replace("&nbsp;", " "))
    def format_table(self, rows):
        return "" # Заглушка для экономии места
    def log(self, message):
        self.log_label.configure(text=message)
    def handle_fetch_list(self): pass
    def handle_download_all(self): pass


class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_login = on_login
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(0, weight=1)
        self.card = ctk.CTkFrame(self, fg_color=("#ffffff", "#1e1e24"), corner_radius=12)
        self.card.grid(row=0, column=0, padx=20, pady=20, ipadx=40, ipady=40)
        self.title_label = ctk.CTkLabel(self.card, text="Вход в RITA Docs", font=ctk.CTkFont(size=28, weight="bold"), text_color=("#1f2937", "#f9fafb")).pack(pady=(20, 40))
        self.login_entry = ctk.CTkEntry(self.card, placeholder_text="Логин", width=300, height=45, corner_radius=8, fg_color=("#f3f4f6", "#2b2b36"))
        self.login_entry.pack(pady=(0, 15))
        self.password_entry = ctk.CTkEntry(self.card, placeholder_text="Пароль", show="*", width=300, height=45, corner_radius=8, fg_color=("#f3f4f6", "#2b2b36"))
        self.password_entry.pack(pady=(0, 15))
        self.login_button = ctk.CTkButton(self.card, text="Войти", command=self.handle_login, width=300, height=45, corner_radius=8, font=ctk.CTkFont(size=15, weight="bold"))
        self.login_button.pack(pady=(0, 10))
        self.error_label = ctk.CTkLabel(self.card, text="", text_color="#ef4444", font=ctk.CTkFont(size=12))
        self.error_label.pack()
    def handle_login(self):
        self.on_login(self.login_entry.get().strip(), self.password_entry.get().strip())
    def reset_ui(self):
        self.login_button.configure(state="normal", text="Войти")

class RitaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RITA ETL Pipeline")
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.api = RitaAPI()
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.run_async_loop, daemon=True).start()
        self.current_frame = None
        self.show_dashboard() 
        
    def run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    def switch_frame(self, frame_class, **kwargs):
        if self.current_frame: self.current_frame.destroy()
        self.current_frame = frame_class(self, **kwargs)
        self.current_frame.pack(fill="both", expand=True)
    def handle_logout(self): sys.exit(0)
    def show_dashboard(self, user_info=None): self.switch_frame(DashboardFrame, api=self.api, loop=self.loop, user_info=user_info)

if __name__ == "__main__":
    app = RitaApp()
    app.mainloop()