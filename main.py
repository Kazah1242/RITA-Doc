import customtkinter as ctk
import asyncio
import threading
import json
import os
import sys
from datetime import datetime
from PIL import Image, ImageTk
from rita_api import RitaAPI, blocks_to_markdown
import aiofiles
import tkinter as tk

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login, **kwargs):
        super().__init__(master, **kwargs)
        self.on_login = on_login

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 4), weight=1)

        # Modern glassmorphism container
        self.container = ctk.CTkFrame(self, fg_color=("#f0f0f0", "#1a1a1a"), corner_radius=20)
        self.container.grid(row=1, column=0, padx=40, pady=40)

        # Logo with animation effect
        try:
            self.logo_img = ctk.CTkImage(light_image=Image.open("icon.png"),
                                        dark_image=Image.open("icon.png"),
                                        size=(120, 120))
            self.logo_label = ctk.CTkLabel(self.container, image=self.logo_img, text="")
            self.logo_label.pack(pady=(0, 20))
            # Add subtle animation
            self.animate_logo()
        except:
            pass

        # Modern title with gradient effect simulation
        self.title_label = ctk.CTkLabel(self.container, text="✨ RITA ETL Pipeline", 
                                        font=ctk.CTkFont(size=28, weight="bold"),
                                        text_color=("#2c3e50", "#ecf0f1"))
        self.title_label.pack(pady=(0, 40))

        # Modern input fields with better styling
        self.login_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.login_frame.pack(pady=10, fill="x", padx=40)
        
        self.login_label = ctk.CTkLabel(self.login_frame, text="👤 Логин", 
                                       font=ctk.CTkFont(size=14),
                                       anchor="w")
        self.login_label.pack(fill="x", pady=(0, 5))
        
        self.login_entry = ctk.CTkEntry(self.login_frame, placeholder_text="Введите логин", 
                                       width=350, height=50, corner_radius=10,
                                       border_width=2, border_color=("#3498db", "#2980b9"))
        self.login_entry.pack(pady=(0, 20))
        
        self.password_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.password_frame.pack(pady=10, fill="x", padx=40)
        
        self.password_label = ctk.CTkLabel(self.password_frame, text="🔒 Пароль", 
                                           font=ctk.CTkFont(size=14),
                                           anchor="w")
        self.password_label.pack(fill="x", pady=(0, 5))
        
        self.password_entry = ctk.CTkEntry(self.password_frame, placeholder_text="Введите пароль", 
                                          show="*", width=350, height=50, corner_radius=10,
                                          border_width=2, border_color=("#3498db", "#2980b9"))
        self.password_entry.pack(pady=(0, 30))

        # Modern animated login button
        self.login_button = ctk.CTkButton(self.container, text="🚀 Войти", 
                                          command=self.handle_login, 
                                          width=350, height=55,
                                          corner_radius=15,
                                          font=ctk.CTkFont(size=18, weight="bold"),
                                          fg_color=("#3498db", "#2980b9"),
                                          hover_color=("#2980b9", "#1f538d"),
                                          border_width=0)
        self.login_button.pack(pady=20)
        
        # Add button hover animation
        self.setup_button_animation(self.login_button)

        # Modern error label with better styling
        self.error_label = ctk.CTkLabel(self.container, text="", 
                                       text_color="#e74c3c",
                                       font=ctk.CTkFont(size=12))
        self.error_label.pack(pady=10)

    def animate_logo(self):
        """Subtle logo animation"""
        try:
            current_size = self.logo_label.cget("image")._size
            new_size = (current_size[0] + 2, current_size[1] + 2) if current_size[0] < 130 else (120, 120)
            self.logo_label.configure(image=ctk.CTkImage(light_image=Image.open("icon.png"),
                                                        dark_image=Image.open("icon.png"),
                                                        size=new_size))
            self.after(50, self.animate_logo)
        except:
            pass
    
    def setup_button_animation(self, button):
        """Setup button hover animations"""
        def on_enter(e):
            button.configure(fg_color=("#2980b9", "#1f538d"))
        
        def on_leave(e):
            button.configure(fg_color=("#3498db", "#2980b9"))
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
    
    def handle_login(self):
        login = self.login_entry.get()
        password = self.password_entry.get()
        if not login or not password:
            self.error_label.configure(text="⚠️ Введите логин и пароль")
            # Shake animation for error
            self.shake_animation(self.container)
            return
        
        # Loading animation
        self.login_button.configure(text="⏳ Вход...")
        self.on_login(login, password)
    
    def shake_animation(self, widget):
        """Shake animation for error feedback"""
        original_x = widget.winfo_x()
        for _ in range(5):
            widget.place(x=original_x + 5, y=widget.winfo_y())
            self.after(50, lambda: widget.place(x=original_x - 5, y=widget.winfo_y()))
            self.after(100, lambda: widget.place(x=original_x, y=widget.winfo_y()))

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        
        # Modern header with gradient effect
        self.header_frame = ctk.CTkFrame(self, fg_color=("#3498db", "#2980b9"), corner_radius=15)
        self.header_frame.pack(fill="x", padx=30, pady=(30, 20))
        
        self.label = ctk.CTkLabel(self.header_frame, text="⚙️ Настройки ETL", 
                                 font=ctk.CTkFont(size=24, weight="bold"),
                                 text_color="white")
        self.label.pack(pady=20)

        # Modern settings container
        self.settings_container = ctk.CTkFrame(self, fg_color=("#f8f9fa", "#2c2c2c"), corner_radius=15)
        self.settings_container.pack(fill="both", expand=True, padx=30, pady=20)
        
        # Path Setting with modern styling
        self.path_frame = ctk.CTkFrame(self.settings_container, fg_color="transparent")
        self.path_frame.pack(fill="x", padx=30, pady=20)
        
        self.path_label = ctk.CTkLabel(self.path_frame, text="📁 Папка для сохранения статей:", 
                                      font=ctk.CTkFont(size=16, weight="bold"),
                                      anchor="w")
        self.path_label.pack(fill="x", pady=(0, 10))
        
        self.path_entry = ctk.CTkEntry(self.path_frame, width=500, height=45, corner_radius=10,
                                      border_width=2, border_color=("#3498db", "#2980b9"))
        self.path_entry.insert(0, self.master.settings_data.get("path", os.path.abspath("articles")))
        self.path_entry.pack(fill="x")

        # Delay Setting with modern styling
        self.delay_frame = ctk.CTkFrame(self.settings_container, fg_color="transparent")
        self.delay_frame.pack(fill="x", padx=30, pady=20)
        
        self.delay_label = ctk.CTkLabel(self.delay_frame, text="⏱️ Задержка между запросами (сек):", 
                                       font=ctk.CTkFont(size=16, weight="bold"),
                                       anchor="w")
        self.delay_label.pack(fill="x", pady=(0, 10))
        
        self.delay_entry = ctk.CTkEntry(self.delay_frame, width=150, height=45, corner_radius=10,
                                       border_width=2, border_color=("#3498db", "#2980b9"))
        self.delay_entry.insert(0, str(self.master.settings_data.get("delay", 0.3)))
        self.delay_entry.pack(anchor="w")

        # Auth Settings with modern checkbox
        self.auth_frame = ctk.CTkFrame(self.settings_container, fg_color="transparent")
        self.auth_frame.pack(fill="x", padx=30, pady=20)
        
        self.remember_var = ctk.BooleanVar(value=self.master.settings_data.get("remember", False))
        self.remember_cb = ctk.CTkCheckBox(self.auth_frame, text="🔐 Запомнить меня", 
                                          variable=self.remember_var,
                                          font=ctk.CTkFont(size=14),
                                          checkbox_width=25, checkbox_height=25,
                                          border_width=2,
                                          fg_color=("#3498db", "#2980b9"),
                                          hover_color=("#2980b9", "#1f538d"))
        self.remember_cb.pack(anchor="w", pady=10)

        # Modern button container
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=30)

        self.save_btn = ctk.CTkButton(self.btn_frame, text="💾 Сохранить", 
                                      command=self.handle_save,
                                      width=150, height=50, corner_radius=12,
                                      font=ctk.CTkFont(size=16, weight="bold"),
                                      fg_color=("#27ae60", "#229954"),
                                      hover_color=("#229954", "#1e8449"))
        self.save_btn.pack(side="left", padx=10)
        
        self.setup_button_animation(self.save_btn)

        self.logout_btn = ctk.CTkButton(self.btn_frame, text="🚪 Выйти", 
                                        command=self.master.handle_logout,
                                        width=150, height=50, corner_radius=12,
                                        font=ctk.CTkFont(size=16, weight="bold"),
                                        fg_color=("#e74c3c", "#c0392b"),
                                        hover_color=("#c0392b", "#a93226"))
        self.logout_btn.pack(side="left", padx=10)
        
        self.setup_button_animation(self.logout_btn)
    
    def setup_button_animation(self, button):
        """Setup button hover animations"""
        def on_enter(e):
            current_fg = button.cget("fg_color")
            if "green" in str(current_fg):
                button.configure(fg_color=("#229954", "#1e8449"))
            elif "red" in str(current_fg):
                button.configure(fg_color=("#c0392b", "#a93226"))
        
        def on_leave(e):
            current_fg = button.cget("fg_color")
            if "green" in str(current_fg):
                button.configure(fg_color=("#27ae60", "#229954"))
            elif "red" in str(current_fg):
                button.configure(fg_color=("#e74c3c", "#c0392b"))
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def handle_save(self):
        new_settings = {
            "path": self.path_entry.get(),
            "delay": float(self.delay_entry.get()),
            "remember": self.remember_var.get()
        }
        self.master.update_settings(new_settings)
        self.master.show_dashboard()

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master, api, loop, user_info=None, **kwargs):
        super().__init__(master, **kwargs)
        self.api = api
        self.loop = loop
        self.articles = []
        self.user_info = user_info or {}

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Modern sidebar with gradient
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, 
                                    fg_color=("#2c3e50", "#1a252f"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Logo section with animation
        self.logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.logo_frame.pack(pady=(20, 10))
        
        try:
            self.logo_img = ctk.CTkImage(light_image=Image.open("icon.png"),
                                        dark_image=Image.open("icon.png"),
                                        size=(60, 60))
            self.logo_label = ctk.CTkLabel(self.logo_frame, image=self.logo_img, text="")
            self.logo_label.pack()
        except:
            pass
        
        self.logo_text = ctk.CTkLabel(self.logo_frame, text="🚀 RITA Docs", 
                                      font=ctk.CTkFont(size=22, weight="bold"),
                                      text_color="white")
        self.logo_text.pack(pady=(10, 0))

        # User Info Section
        self.user_frame = ctk.CTkFrame(self.sidebar, fg_color=("#34495e", "#2c3e50"), corner_radius=10)
        self.user_frame.pack(fill="x", padx=15, pady=20)
        
        user_display = "👤 Пользователь"
        if self.user_info and "user" in self.user_info:
            user_data = self.user_info.get("user", {})
            user_display = f"👤 {user_data.get('name', f'ID: {user_data.get('id', '???')}')}"
        
        self.user_label = ctk.CTkLabel(self.user_frame, text=user_display, 
                                       font=ctk.CTkFont(size=14), 
                                       text_color="white",
                                       wraplength=220)
        self.user_label.pack(pady=15, padx=10)

        # Modern action buttons
        self.actions_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.actions_frame.pack(fill="x", padx=15, pady=10)
        
        self.fetch_btn = ctk.CTkButton(self.actions_frame, text="🔄 Обновить список", 
                                       command=self.handle_fetch_list,
                                       height=45, corner_radius=10,
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       fg_color=("#3498db", "#2980b9"),
                                       hover_color=("#2980b9", "#1f538d"))
        self.fetch_btn.pack(fill="x", pady=5)
        self.setup_button_animation(self.fetch_btn)

        self.download_btn = ctk.CTkButton(self.actions_frame, text="📥 Скачать всё", 
                                         command=self.handle_download_all, 
                                         state="disabled", 
                                         height=45, corner_radius=10,
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         fg_color=("#27ae60", "#229954"),
                                         hover_color=("#229954", "#1e8449"))
        self.download_btn.pack(fill="x", pady=5)
        self.setup_button_animation(self.download_btn)

        # Settings button at bottom
        self.settings_btn = ctk.CTkButton(self.sidebar, text="⚙️ Настройки", 
                                         fg_color="transparent", 
                                         border_width=2, 
                                         border_color=("#95a5a6", "#7f8c8d"),
                                         text_color=("#ecf0f1", "#bdc3c7"),
                                         command=lambda: self.master.show_settings(),
                                         height=40, corner_radius=8,
                                         font=ctk.CTkFont(size=13))
        self.settings_btn.pack(side="bottom", pady=20, padx=15)
        self.setup_button_animation(self.settings_btn)

        # Main Content Area
        self.main_container = ctk.CTkFrame(self, fg_color=("#f8f9fa", "#1a1a1a"))
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Modern top bar with search
        self.top_bar = ctk.CTkFrame(self.main_container, fg_color=("#ffffff", "#2c2c2c"), corner_radius=15)
        self.top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        self.search_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.search_frame.pack(fill="x", padx=20, pady=15)
        
        self.search_label = ctk.CTkLabel(self.search_frame, text="🔍 Поиск:", 
                                        font=ctk.CTkFont(size=14, weight="bold"))
        self.search_label.pack(side="left", padx=(0, 10))
        
        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Поиск по статьям...", 
                                        width=400, height=40, corner_radius=8,
                                        border_width=2, border_color=("#3498db", "#2980b9"))
        self.search_entry.pack(side="left", padx=(0, 20))
        self.search_entry.bind("<KeyRelease>", self.filter_articles)

        self.count_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.count_frame.pack(side="right", padx=20)
        
        self.count_label = ctk.CTkLabel(self.count_frame, text="📄 Статей: 0", 
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       text_color=("#2c3e50", "#ecf0f1"))
        self.count_label.pack()

        # Modern scrollable article list
        self.article_frame = ctk.CTkScrollableFrame(self.main_container, 
                                                   label_text="📚 Список доступных статей",
                                                   fg_color=("#ffffff", "#2c2c2c"),
                                                   corner_radius=15,
                                                   label_font=ctk.CTkFont(size=16, weight="bold"))
        self.article_frame.grid(row=1, column=0, sticky="nsew")
        
        # Modern bottom status bar
        self.bottom_frame = ctk.CTkFrame(self.main_container, fg_color=("#34495e", "#2c3e50"), corner_radius=15)
        self.bottom_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))
        
        self.progress_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=20, pady=(15, 10))
        
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="⏳ Прогресс:", 
                                         font=ctk.CTkFont(size=12),
                                         text_color="white")
        self.progress_label.pack(side="left", padx=(0, 10))
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, 
                                              progress_color=("#3498db", "#2980b9"))
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 20))
        self.progress_bar.set(0)

        self.log_label = ctk.CTkLabel(self.bottom_frame, text="✅ Готов к работе", 
                                     font=ctk.CTkFont(size=12),
                                     text_color="white")
        self.log_label.pack(pady=(0, 15))

    def setup_button_animation(self, button):
        """Setup button hover animations"""
        def on_enter(e):
            current_fg = button.cget("fg_color")
            if isinstance(current_fg, tuple):
                # Handle tuple colors (light/dark mode)
                if "blue" in str(current_fg):
                    button.configure(fg_color=("#2980b9", "#1f538d"))
                elif "green" in str(current_fg):
                    button.configure(fg_color=("#229954", "#1e8449"))
            else:
                # Handle single colors
                if "blue" in str(current_fg):
                    button.configure(fg_color="#2980b9")
                elif "green" in str(current_fg):
                    button.configure(fg_color="#229954")
        
        def on_leave(e):
            current_fg = button.cget("fg_color")
            if isinstance(current_fg, tuple):
                if "blue" in str(current_fg):
                    button.configure(fg_color=("#3498db", "#2980b9"))
                elif "green" in str(current_fg):
                    button.configure(fg_color=("#27ae60", "#229954"))
            else:
                if "blue" in str(current_fg):
                    button.configure(fg_color="#3498db")
                elif "green" in str(current_fg):
                    button.configure(fg_color="#27ae60")
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def log(self, message):
        self.log_label.configure(text=message)

    def handle_fetch_list(self):
        async def do_fetch():
            async with self.api as api:
                self.after(0, lambda: self.log("🔄 Загрузка списка..."))
                articles = await api.get_articles()
                if articles:
                    self.articles = articles
                    self.after(0, self.update_article_display)
                else:
                    self.after(0, lambda: self.log("❌ Ошибка загрузки списка"))
        asyncio.run_coroutine_threadsafe(do_fetch(), self.loop)

    def filter_articles(self, event=None):
        query = self.search_entry.get().lower()
        if query:
            for widget in self.article_frame.winfo_children():
                widget.destroy()
            for art in self.articles:
                if query in art["title"].lower():
                    # Modern article item with hover effect
                    item_frame = ctk.CTkFrame(self.article_frame, fg_color=("#f8f9fa", "#2c2c2c"), corner_radius=8)
                    item_frame.pack(fill="x", padx=10, pady=5)
                    
                    lbl = ctk.CTkLabel(item_frame, text=f"📄 {art['title']}", 
                                     anchor="w", cursor="hand2", 
                                     text_color=("#3498db", "#5dade2"),
                                     font=ctk.CTkFont(size=13))
                    lbl.pack(fill="x", padx=15, pady=10)
                    
                    # Add hover animation
                    def on_enter(e, frame=item_frame):
                        frame.configure(fg_color=("#e3f2fd", "#1a237e"))
                    def on_leave(e, frame=item_frame):
                        frame.configure(fg_color=("#f8f9fa", "#2c2c2c"))
                    
                    item_frame.bind("<Enter>", on_enter)
                    item_frame.bind("<Leave>", on_leave)
                    lbl.bind("<Enter>", on_enter)
                    lbl.bind("<Leave>", on_leave)
        else:
            self.update_article_display()

    def update_article_display(self, sort_by=None):
        # Clear existing
        for widget in self.article_frame.winfo_children():
            widget.destroy()
        
        # Build tree mapping
        self.article_map = {art["id"]: art for art in self.articles}
        self.children_map = {}
        roots = []
        
        # 1. Сначала собираем все связи
        for art in self.articles:
            pid = art.get("parent_id")
            if pid is not None:
                if pid not in self.children_map:
                    self.children_map[pid] = []
                self.children_map[pid].append(art)

        # 2. Определяем корни: только те, у кого НЕТ родителя в нашем списке
        for art in self.articles:
            pid = art.get("parent_id")
            if pid is None or pid not in self.article_map:
                roots.append(art)

        # 3. Сортировка корней: сначала по номеру (1., 2.), затем по алфавиту
        def root_sort_key(x):
            title = x["title"]
            import re
            match = re.match(r"(\d+)", title)
            if match:
                return (0, int(match.group(1)), title)
            return (1, 0, title)

        sorted_roots = sorted(roots, key=root_sort_key)

        # 4. Рендерим
        for root in sorted_roots:
            self.render_node(root, self.article_frame, 0)
            
        self.count_label.configure(text=f"📄 Статей: {len(self.articles)}")
        self.download_btn.configure(state="normal")
        self.log(f"✅ Загружено {len(self.articles)} статей")

    def render_node(self, node, parent_container, level):
        # Modern article item with gradient background
        bg_color = ("#ffffff", "#2c2c2c") if level == 0 else ("#f8f9fa", "#1a1a1a")
        frame = ctk.CTkFrame(parent_container, fg_color=bg_color, corner_radius=8)
        frame.pack(fill="x", padx=(15 if level > 0 else 0, 0), pady=3)
        
        display_text = node['title']
        has_children = node["id"] in self.children_map
        
        # Modern styling with icons
        icon = "📁" if has_children else "📄"
        text_color = ("#2c3e50", "#ecf0f1") if level == 0 else ("#34495e", "#bdc3c7")
        
        if level == 0:
            font = ctk.CTkFont(size=14, weight="bold")
        else:
            font = ctk.CTkFont(size=13)

        if has_children:
            node["_expanded"] = False
            # Modern expandable button with icons
            btn = ctk.CTkButton(frame, text=f"{'📂' if not node['_expanded'] else '📂'}  {icon} {display_text}", 
                                anchor="w", 
                                fg_color="transparent",
                                text_color=text_color,
                                hover_color=("#e3f2fd", "#1a237e"),
                                font=font,
                                height=32,
                                corner_radius=6,
                                command=lambda n=node, l=level: self.toggle_node_optimized(n, frame, l))
            btn.pack(fill="x", padx=10, pady=5)
            
            # Container for children (initially empty)
            child_container = ctk.CTkFrame(frame, fg_color="transparent")
            node["_child_container"] = child_container
            node["_btn"] = btn
        else:
            # Modern article label with hover effect
            lbl_frame = ctk.CTkFrame(frame, fg_color="transparent")
            lbl_frame.pack(fill="x", padx=10, pady=5)
            
            lbl = ctk.CTkLabel(lbl_frame, text=f"  {icon} {display_text}", 
                               anchor="w", cursor="hand2", 
                               text_color=text_color,
                               font=ctk.CTkFont(size=13))
            lbl.pack(fill="x")
            
            # Add hover animation
            def on_enter(e, f=frame):
                f.configure(fg_color=("#e3f2fd", "#1a237e"))
            def on_leave(e, f=frame):
                f.configure(fg_color=bg_color)
            
            frame.bind("<Enter>", on_enter)
            frame.bind("<Leave>", on_leave)
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)

    def toggle_node_optimized(self, node, parent_frame, level):
        container = node["_child_container"]
        if node["_expanded"]:
            container.pack_forget()
            node["_btn"].configure(text=f"📂  📁 {node['title']}")
            node["_expanded"] = False
        else:
            if not container.winfo_children():
                # Lazy render children
                children = sorted(self.children_map[node["id"]], key=lambda x: x["title"])
                for child in children:
                    self.render_node(child, container, level + 1)
            
            container.pack(fill="x", padx=(20, 0))
            node["_btn"].configure(text=f"📂  📂 {node['title']}")
            node["_expanded"] = True

    def handle_download_all(self):
        async def do_download():
            save_path = self.master.get_save_path()
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            
            async with self.api as api:
                heartbeat_task = asyncio.create_task(self.run_heartbeat(api))
                total = len(self.articles)
                for i, article in enumerate(self.articles):
                    url = article["url"]
                    self.after(0, lambda u=url: self.log(f"📥 Скачивание: {u}"))
                    content = await api.get_article_content(url)
                    if content and "blocks" in content:
                        md = blocks_to_markdown(content["blocks"])
                        filename = os.path.join(save_path, f"{url}.md")
                        async with aiofiles.open(filename, mode='w') as f:
                            await f.write(f"# {article['title']}\n\n{md}")
                    self.after(0, lambda p=(i+1)/total: self.progress_bar.set(p))
                    await asyncio.sleep(0.3)
                heartbeat_task.cancel()
                self.after(0, lambda: self.log("🎉 Все статьи скачаны!"))
        asyncio.run_coroutine_threadsafe(do_download(), self.loop)

    async def run_heartbeat(self, api):
        try:
            while True:
                await asyncio.sleep(120)
                await api.heartbeat()
        except asyncio.CancelledError:
            pass

class RitaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Critical for Linux taskbar icon
        try:
            self.title("🚀 RITA Documentation Manager")
            self.wm_class("rita-docs", "RITA-Docs")
        except:
            pass

        self.geometry("1200x800")
        self.minsize(1000, 600)
        
        # Set modern appearance with dark/light mode support
        ctk.set_appearance_mode("dark")  # Dark mode for modern look
        ctk.set_default_color_theme("blue")

        # Set icon
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                self.icon_photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, self.icon_photo)
        except Exception as e:
            print(f"Icon error: {e}")

        self.api = RitaAPI()
        self.loop = asyncio.new_event_loop()
        
        self.current_frame = None
        self.settings_file = "app_settings.json"
        self.settings_data = self.load_settings()
        
        # Animation settings
        self.animation_speed = 150  # milliseconds
        
        # Если есть сохраненные данные, пытаемся войти сразу
        self.show_login()
        if self.settings_data.get("remember") and self.settings_data.get("login") and self.settings_data.get("password"):
            self.after(100, lambda: self.handle_login_action(self.settings_data["login"], self.settings_data["password"]))

        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"path": os.path.abspath("articles"), "delay": 0.3, "remember": False}

    def update_settings(self, new_data):
        self.settings_data.update(new_data)
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings_data, f)

    def handle_logout(self):
        # Очищаем сохраненные данные при выходе
        if "login" in self.settings_data: del self.settings_data["login"]
        if "password" in self.settings_data: del self.settings_data["password"]
        self.settings_data["remember"] = False
        self.update_settings(self.settings_data)
        self.show_login()

    def run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def show_login(self):
        self.fade_out_current_frame()
        self.after(self.animation_speed, lambda: self._show_login_frame())
    
    def _show_login_frame(self):
        if self.current_frame: 
            self.current_frame.destroy()
        self.current_frame = LoginFrame(self, on_login=self.handle_login_action)
        self.current_frame.pack(fill="both", expand=True)
        self.fade_in_current_frame()
        
        # Предзаполнение данных если они есть
        if self.settings_data.get("login"):
            self.current_frame.login_entry.insert(0, self.settings_data["login"])
        if self.settings_data.get("password"):
            self.current_frame.password_entry.insert(0, self.settings_data["password"])

    def show_dashboard(self, user_info=None):
        self.fade_out_current_frame()
        self.after(self.animation_speed, lambda: self._show_dashboard_frame(user_info))
    
    def _show_dashboard_frame(self, user_info):
        if self.current_frame: 
            self.current_frame.destroy()
        self.current_frame = DashboardFrame(self, self.api, self.loop, user_info=user_info)
        self.current_frame.pack(fill="both", expand=True)
        self.fade_in_current_frame()

    def show_settings(self):
        self.fade_out_current_frame()
        self.after(self.animation_speed, self._show_settings_frame)
    
    def _show_settings_frame(self):
        if self.current_frame: 
            self.current_frame.destroy()
        self.current_frame = SettingsFrame(self)
        self.current_frame.pack(fill="both", expand=True)
        self.fade_in_current_frame()
    
    def fade_out_current_frame(self):
        """Fade out animation for current frame"""
        if self.current_frame:
            try:
                self.current_frame.configure(alpha=0.5)
            except:
                pass
    
    def fade_in_current_frame(self):
        """Fade in animation for current frame"""
        if self.current_frame:
            try:
                self.current_frame.configure(alpha=1.0)
            except:
                pass

    def get_save_path(self):
        return self.settings_data.get("path", os.path.abspath("articles"))

    def handle_login_action(self, login, password):
        async def do_login():
            async with self.api as api:
                success, data = await api.login(login, password)
                if success:
                    # Сохраняем данные если стоит галочка
                    if self.settings_data.get("remember"):
                        self.update_settings({"login": login, "password": password})
                    self.after(0, lambda: self.show_dashboard(user_info=data))
                else:
                    self.after(0, lambda: self.current_frame.error_label.configure(text=f"❌ {data}"))
        asyncio.run_coroutine_threadsafe(do_login(), self.loop)

if __name__ == "__main__":
    app = RitaApp()
    app.mainloop()
