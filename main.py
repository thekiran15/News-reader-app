from kivy.config import Config
# Simulate mobile device window size
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')
Config.set('graphics', 'resizable', False)

import requests
from datetime import datetime
import threading
import webbrowser
import json
import os

# Kivy imports
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.image import AsyncImage, Image
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty, NumericProperty, ListProperty
from kivy.storage.jsonstore import JsonStore

# KivyMD imports
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import MDList, OneLineIconListItem, IconLeftWidget, TwoLineListItem
from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.textfield import MDTextField
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.dialog import MDDialog

# --- API key handling: works both on desktop (env var) and on a packaged Android app ---
# On Android there is no shell to `export` a variable before the app launches, so we
# fall back to a value the user enters once in the Settings screen, persisted with
# Kivy's JsonStore (stored in the app's private data directory on the device).

def get_stored_api_key():
    """Read the saved key from local device storage, if any."""
    try:
        app = App.get_running_app()
        store_path = os.path.join(app.user_data_dir, 'config.json') if app else 'config.json'
        store = JsonStore(store_path)
        if store.exists('api_key'):
            return store.get('api_key').get('value', '')
    except Exception:
        pass
    return ''

def save_api_key(key):
    """Save the API key to local device storage."""
    app = App.get_running_app()
    store_path = os.path.join(app.user_data_dir, 'config.json') if app else 'config.json'
    store = JsonStore(store_path)
    store.put('api_key', value=key)

API_URL = 'https://newsapi.org/v2/top-headlines'

# --- Optional developer default -----------------------------------------------------
# Paste a key here ONLY for your own local testing convenience. Leave it as ''
# for anything you commit to git or ship to other people — a key baked into
# source code ships to every user and can't be revoked per-user.
# Resolution order at startup: env var  >  saved on-device value  >  this default.
DEFAULT_API_KEY = 'bc9e665e0bda43e098185d6a796ef342'

# Resolved lazily at app start (see NewsReaderApp.build), not at import time, because
# App.get_running_app() and user_data_dir aren't available until the app object exists.
API_KEY = os.environ.get('NEWS_API_KEY', '')

# Categories
CATEGORIES = [
    {'name': 'General', 'icon': 'newspaper', 'value': 'general'},
    {'name': 'Business', 'icon': 'chart-line', 'value': 'business'},
    {'name': 'Entertainment', 'icon': 'filmstrip', 'value': 'entertainment'},
    {'name': 'Health', 'icon': 'hospital', 'value': 'health'},
    {'name': 'Science', 'icon': 'flask', 'value': 'science'},
    {'name': 'Sports', 'icon': 'basketball', 'value': 'sports'},
    {'name': 'Technology', 'icon': 'cellphone', 'value': 'technology'}
]

class NewsCard(MDCard):
    """Card for displaying news article with properly sized image"""
    title = StringProperty('')
    source = StringProperty('')
    date = StringProperty('')
    image_url = StringProperty('')
    news_data = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(100)  # Compact height
        self.padding = dp(8)
        self.spacing = dp(8)
        self.elevation = 1
        self.radius = dp(8)
        self.md_bg_color = (1, 1, 1, 1)
        
        # Image container (left side - 30% width for better visibility)
        img_container = BoxLayout(
            size_hint_x=0.3,  # Increased to 30% for better image display
            size_hint_y=1
        )
        
        # Create a proper image widget with constraints
        if self.image_url and self.image_url.strip():
            # Use a container to properly size the image
            img_wrapper = BoxLayout()
            self.img = AsyncImage(
                source=self.image_url,
                size_hint=(1, 1),
                fit_mode='fill'  # Use fit_mode instead of deprecated properties
            )
            # Set background color for image area
            self.img.color = [0.95, 0.95, 0.95, 1]
            img_wrapper.add_widget(self.img)
            img_container.add_widget(img_wrapper)
        else:
            # Placeholder with icon - centered in a colored box
            # FIXED: Use canvas to create rounded rectangle with background color
            placeholder_box = BoxLayout()
            
            # Create background with canvas
            with placeholder_box.canvas.before:
                Color(0.95, 0.95, 0.95, 1)  # Light gray background
                self.bg_rect = RoundedRectangle(
                    pos=placeholder_box.pos,
                    size=placeholder_box.size,
                    radius=[dp(6), dp(6), dp(6), dp(6)]
                )
            
            # Bind position and size updates
            placeholder_box.bind(
                pos=self.update_bg_rect,
                size=self.update_bg_rect
            )
            
            self.img = MDIconButton(
                icon='newspaper',
                theme_text_color="Secondary",
                size_hint=(None, None),
                size=(dp(32), dp(32)),  # Larger icon
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
                disabled=True
            )
            placeholder_box.add_widget(self.img)
            img_container.add_widget(placeholder_box)
        
        # Text container (right side - 70% width)
        text_container = MDBoxLayout(
            orientation='vertical',
            size_hint_x=0.7,  # Adjusted to 70%
            spacing=dp(4),
            padding=[dp(4), 0, 0, 0]
        )
        
        # Title - FIXED: Always set text color based on theme
        self.title_label = MDLabel(
            text=self.title,
            font_style='Body2',
            theme_text_color="Primary",  # Use theme color
            size_hint_y=0.65,
            halign='left',
            valign='top',
            shorten=True,
            shorten_from='right',
            max_lines=2,
            font_size='13sp'
        )
        
        # Source and date container
        meta_container = BoxLayout(
            size_hint_y=0.35,
            spacing=dp(4)
        )
        
        # Source - FIXED: Always set text color based on theme
        source_box = BoxLayout(size_hint_x=0.6)
        self.source_label = MDLabel(
            text=self.source[:18] + "..." if len(self.source) > 18 else self.source,
            font_style='Caption',
            theme_text_color="Secondary",  # Use theme color
            halign='left',
            font_size='11sp',
            max_lines=1
        )
        source_box.add_widget(self.source_label)
        
        # Date - FIXED: Always set text color based on theme
        date_box = BoxLayout(size_hint_x=0.4)
        self.date_label = MDLabel(
            text=self.format_date(self.date),
            font_style='Caption',
            theme_text_color="Secondary",  # Use theme color
            halign='right',
            font_size='11sp',
            max_lines=1
        )
        date_box.add_widget(self.date_label)
        
        meta_container.add_widget(source_box)
        meta_container.add_widget(date_box)
        
        text_container.add_widget(self.title_label)
        text_container.add_widget(meta_container)
        
        self.add_widget(img_container)
        self.add_widget(text_container)
        
        # Bind updates
        self.bind(
            title=self.update_title,
            source=self.update_source,
            date=self.update_date,
            image_url=self.update_image
        )
        
        # Apply theme colors
        self.apply_theme_colors()
    
    def update_bg_rect(self, instance, value):
        """Update the background rectangle position and size"""
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size
    
    def apply_theme_colors(self):
        """Apply theme colors to all text elements"""
        app = MDApp.get_running_app()
        if app:
            # Update text colors based on theme
            self.title_label.theme_text_color = "Primary"
            self.source_label.theme_text_color = "Secondary"
            self.date_label.theme_text_color = "Secondary"
            
            # Update card background based on theme
            if app.theme_cls.theme_style == "Light":
                self.md_bg_color = (1, 1, 1, 1)
            else:
                self.md_bg_color = (0.15, 0.15, 0.15, 1)
    
    def update_title(self, instance, value):
        self.title_label.text = value
    
    def update_source(self, instance, value):
        self.source_label.text = value[:18] + "..." if len(value) > 18 else value
    
    def update_date(self, instance, value):
        self.date_label.text = self.format_date(value)
    
    def update_image(self, instance, value):
        if value and value.strip():
            # Clear current image container
            img_container = self.children[1]  # Image container is second child (0-based indexing)
            img_container.clear_widgets()
            
            # Create new image
            img_wrapper = BoxLayout()
            self.img = AsyncImage(
                source=value,
                size_hint=(1, 1),
                fit_mode='fill'  # Use fit_mode instead of deprecated properties
            )
            self.img.color = [0.95, 0.95, 0.95, 1]
            img_wrapper.add_widget(self.img)
            img_container.add_widget(img_wrapper)
    
    def format_date(self, date_str):
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
            now = datetime.now()
            if dt.date() == now.date():
                diff = now - dt
                hours = diff.seconds // 3600
                if hours > 0:
                    return f"{hours}h ago"
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
            return dt.strftime('%b %d')
        except:
            return date_str[:10] if date_str else ""
    
    def on_release(self):
        """Handle card tap"""
        if self.news_data:
            app = MDApp.get_running_app()
            app.add_to_history(self.news_data)
            app.show_article(self.news_data)

class HeadlinesScreen(MDScreen):
    """Main news screen"""
    current_page = NumericProperty(1)
    loading_more = BooleanProperty(False)
    loading = BooleanProperty(False)
    current_category = StringProperty('general')
    category_name = StringProperty('General')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'headlines'
        
        # Main layout
        self.main_layout = MDBoxLayout(orientation='vertical')
        
        # Top App Bar
        self.top_bar = MDTopAppBar(
            title=f"News - {self.category_name}",
            elevation=4,
            left_action_items=[["menu", self.toggle_nav_drawer]],
            right_action_items=[
                ["refresh", self.refresh_news],
                ["weather-sunny", self.toggle_theme]
            ]
        )
        
        # News list container
        self.scroll_view = ScrollView(do_scroll_x=False)
        self.news_container = MDBoxLayout(
            orientation='vertical',
            spacing=dp(8),
            size_hint_y=None,
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        self.news_container.bind(minimum_height=self.news_container.setter('height'))
        self.scroll_view.add_widget(self.news_container)
        
        # Add all widgets to main layout
        self.main_layout.add_widget(self.top_bar)
        self.main_layout.add_widget(self.scroll_view)
        self.add_widget(self.main_layout)
        
        # Create navigation drawer
        self.nav_drawer = self.create_navigation_drawer()
        
        # Bind scroll event
        self.scroll_view.bind(on_scroll_stop=self.check_scroll_position)
        
        # Load initial news
        Clock.schedule_once(lambda dt: self.load_news(), 0.5)
    
    def create_navigation_drawer(self):
        """Create navigation drawer for categories"""
        drawer = MDNavigationDrawer(
            id="nav_drawer",
            radius=(0, dp(10), dp(10), 0),
        )
        
        # Header
        drawer_header = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(120),
            padding=dp(20)
        )
        drawer_header.add_widget(MDLabel(
            text="News Categories",
            font_style="H5",
            halign="center"
        ))
        drawer_header.add_widget(MDLabel(
            text="Select a category",
            font_style="Subtitle1",
            theme_text_color="Secondary",
            halign="center"
        ))
        
        # Category list
        category_list = MDList()
        for category in CATEGORIES:
            item = OneLineIconListItem(
                text=category['name'],
                on_release=lambda x, cat=category: self.on_category_selected(cat['value'], cat['name'])
            )
            item.add_widget(IconLeftWidget(icon=category['icon']))
            category_list.add_widget(item)
        
        # Add close button
        close_button = MDRaisedButton(
            text="Close",
            size_hint_x=0.8,
            pos_hint={'center_x': 0.5},
            on_release=lambda x: self.toggle_nav_drawer()
        )
        
        # Main drawer content
        drawer_content = MDBoxLayout(orientation='vertical', spacing=dp(10))
        drawer_content.add_widget(drawer_header)
        drawer_content.add_widget(category_list)
        drawer_content.add_widget(close_button)
        
        drawer.add_widget(drawer_content)
        return drawer
    
    def toggle_nav_drawer(self, *args):
        """Toggle navigation drawer"""
        if not hasattr(self, 'nav_drawer_added'):
            # Add drawer to window
            Window.add_widget(self.nav_drawer)
            self.nav_drawer_added = True
        
        if self.nav_drawer.state == "open":
            self.nav_drawer.set_state("close")
        else:
            self.nav_drawer.set_state("open")
    
    def on_category_selected(self, category_value, category_name):
        """Handle category selection - FIXED: Update text colors when loading new category"""
        if category_value != self.current_category:
            self.current_category = category_value
            self.category_name = category_name
            self.top_bar.title = f"News - {category_name}"
            self.current_page = 1
            self.load_news()
        
        # Close drawer
        self.nav_drawer.set_state("close")
    
    def check_scroll_position(self, instance, value):
        """Check if scrolled to bottom for infinite scroll"""
        if instance.scroll_y <= 0.01 and not self.loading_more and not self.loading:
            self.load_more_news()
    
    def load_more_news(self):
        """Load more news for infinite scroll"""
        if self.loading_more or self.loading:
            return
        
        self.loading_more = True
        self.current_page += 1
        
        # Add loading indicator
        loading_box = BoxLayout(size_hint_y=None, height=dp(40))
        loading_box.add_widget(MDLabel(
            text='Loading more...',
            halign='center',
            font_style="Body1",
            font_size='12sp',
            theme_text_color="Primary"  # FIXED: Set theme color
        ))
        self.news_container.add_widget(loading_box)
        
        # Fetch more news
        threading.Thread(target=self.fetch_news, args=(True,)).start()
    
    def refresh_news(self, *args):
        """Refresh current news"""
        self.current_page = 1
        self.load_news()
    
    def load_news(self):
        """Load news for current category"""
        if self.loading:
            return
        
        self.loading = True
        
        # Clear and show loading
        self.news_container.clear_widgets()
        loading_box = BoxLayout(size_hint_y=None, height=dp(80))
        loading_label = MDLabel(
            text='Loading news...',
            halign='center',
            font_style="H5",
            theme_text_color="Primary"  # FIXED: Set theme color
        )
        loading_box.add_widget(loading_label)
        self.news_container.add_widget(loading_box)
        
        # Fetch news in background thread
        threading.Thread(target=self.fetch_news, args=(False,)).start()
    
    def fetch_news(self, append=False):
        """Fetch news from API"""
        app = MDApp.get_running_app()
        if not app.api_key:
            Clock.schedule_once(
                lambda dt: self.show_error(
                    "No API key set. Go to Settings to add your NewsAPI.org key.", append
                ), 0
            )
            return

        params = {
            'apiKey': app.api_key,
            'country': 'us',
            'category': self.current_category,
            'pageSize': 15,
            'page': self.current_page
        }
        
        try:
            response = requests.get(API_URL, params=params, timeout=15)
            response.raise_for_status()
            news_data = response.json().get('articles', [])
            
            # Update UI on main thread
            Clock.schedule_once(lambda dt: self.display_news(news_data, append), 0)
            
        except requests.exceptions.RequestException as e:
            Clock.schedule_once(lambda dt, e=e: self.show_error(f"Network error: {str(e)}", append), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt, e=e: self.show_error(f"Error: {str(e)}", append), 0)
    
    def display_news(self, news_data, append):
        """Display news articles - FIXED: Apply theme colors to all cards"""
        if not append:
            self.news_container.clear_widgets()
        elif self.news_container.children:
            # Remove loading indicator if it's the last widget
            last_widget = self.news_container.children[-1]
            if isinstance(last_widget, BoxLayout) and len(last_widget.children) == 1:
                if isinstance(last_widget.children[0], MDLabel):
                    if 'Loading' in last_widget.children[0].text:
                        self.news_container.remove_widget(last_widget)
        
        if not news_data:
            no_news = BoxLayout(size_hint_y=None, height=dp(80))
            no_news_label = MDLabel(
                text='No news available',
                halign='center',
                font_style="H6",
                theme_text_color="Primary"  # FIXED: Set theme color
            )
            no_news.add_widget(no_news_label)
            self.news_container.add_widget(no_news)
        else:
            for item in news_data:
                news_card = NewsCard(
                    title=item.get('title', 'No Title') or 'No Title',
                    source=item.get('source', {}).get('name', 'Unknown') or 'Unknown',
                    date=item.get('publishedAt', '') or '',
                    image_url=item.get('urlToImage', '') or ''
                )
                news_card.news_data = item
                # Apply theme colors immediately
                news_card.apply_theme_colors()
                self.news_container.add_widget(news_card)
        
        # Update loading states
        self.loading = False
        self.loading_more = False
    
    def show_error(self, error_msg, append):
        """Show error message"""
        if not append:
            self.news_container.clear_widgets()
            error_box = BoxLayout(size_hint_y=None, height=dp(80))
            error_label = MDLabel(
                text=error_msg,
                halign='center',
                font_style="Body1",
                theme_text_color="Error"  # FIXED: Set theme color
            )
            error_box.add_widget(error_label)
            self.news_container.add_widget(error_box)
        
        # Update loading states
        self.loading = False
        self.loading_more = False
    
    def toggle_theme(self, *args):
        """Toggle between light and dark theme - FIXED: Update all cards when theme changes"""
        app = MDApp.get_running_app()
        if app.theme_cls.theme_style == "Light":
            app.theme_cls.theme_style = "Dark"
            app.theme_cls.primary_palette = "BlueGray"
            # Update theme icon
            self.top_bar.right_action_items[1] = ["weather-night", self.toggle_theme]
            # Update window color
            Window.clearcolor = (0.1, 0.1, 0.1, 1)
        else:
            app.theme_cls.theme_style = "Light"
            app.theme_cls.primary_palette = "Blue"
            # Update theme icon
            self.top_bar.right_action_items[1] = ["weather-sunny", self.toggle_theme]
            # Update window color
            Window.clearcolor = (1, 1, 1, 1)
        
        # Update bottom navigation
        app.bottom_nav.update_theme()
        
        # FIXED: Update all news cards when theme changes
        self.update_all_cards_theme()
    
    def update_all_cards_theme(self):
        """Update theme colors for all news cards"""
        for widget in self.news_container.children:
            if isinstance(widget, NewsCard):
                widget.apply_theme_colors()

class HistoryItem(TwoLineListItem):
    """Item for displaying history entries"""
    def __init__(self, article_data, **kwargs):
        super().__init__(**kwargs)
        # Ensure article_data is a dictionary
        if isinstance(article_data, dict):
            title = article_data.get('title', 'No Title')
            
            # FIX: Handle source properly - it might be a string in history entries
            source = article_data.get('source', 'Unknown')
            if isinstance(source, dict):
                source = source.get('name', 'Unknown')
            
            date = article_data.get('publishedAt', '')
            
            self.text = title[:50] + "..." if len(title) > 50 else title
            self.secondary_text = f"{source} • {self.format_date(date)}"
            self.article_data = article_data
        else:
            # If article_data is not a dict, use defaults
            self.text = "Invalid article data"
            self.secondary_text = "Unknown source • Unknown date"
            self.article_data = {}
        
        self._no_ripple_effect = False
    
    def format_date(self, date_str):
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
            return dt.strftime('%b %d, %Y %I:%M %p')
        except:
            return date_str[:10] if date_str else "Unknown"

class HistoryScreen(MDScreen):
    """History screen for viewed articles"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'history'
        
        # Main layout
        self.main_layout = MDBoxLayout(orientation='vertical')
        
        # Top App Bar
        self.top_bar = MDTopAppBar(
            title="Reading History",
            elevation=4,
            left_action_items=[["arrow-left", self.go_back]],
            right_action_items=[["delete", self.clear_history]]
        )
        
        # History list container
        self.scroll_view = ScrollView(do_scroll_x=False)
        self.history_container = MDList(
            spacing=dp(5),
            size_hint_y=None,
            padding=[dp(10), dp(10), dp(10), dp(10)]
        )
        self.history_container.bind(minimum_height=self.history_container.setter('height'))
        self.scroll_view.add_widget(self.history_container)
        
        # Add all widgets
        self.main_layout.add_widget(self.top_bar)
        self.main_layout.add_widget(self.scroll_view)
        self.add_widget(self.main_layout)
        
        # Load history when screen is shown
        self.bind(on_pre_enter=self.load_history)
    
    def go_back(self, *args):
        """Go back to news screen"""
        self.manager.current = 'headlines'
    
    def clear_history(self, *args):
        """Clear all reading history"""
        app = MDApp.get_running_app()
        app.clear_history()
        self.load_history()
    
    def load_history(self, *args):
        """Load reading history"""
        self.history_container.clear_widgets()
        
        app = MDApp.get_running_app()
        history = app.get_history()
        
        if not history:
            # Placeholder message
            no_history = BoxLayout(size_hint_y=None, height=dp(100))
            no_history_label = MDLabel(
                text="No reading history yet.\nRead some articles to see them here!",
                halign='center',
                font_style="H6",
                theme_text_color="Primary",  # FIXED: Set theme color
                size_hint_y=None,
                height=dp(100)
            )
            no_history.add_widget(no_history_label)
            self.history_container.add_widget(no_history)
        else:
            for article in history:  # History is already stored newest first
                item = HistoryItem(article)
                item.bind(on_release=lambda x, article=article: self.open_article(article))
                self.history_container.add_widget(item)
    
    def open_article(self, article_data):
        """Open article from history"""
        app = MDApp.get_running_app()
        app.show_article(article_data)

class SettingsScreen(MDScreen):
    """Settings screen"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'settings'
        
        # Main layout
        self.main_layout = MDBoxLayout(orientation='vertical')
        
        # Top App Bar
        self.top_bar = MDTopAppBar(
            title="Settings",
            elevation=4,
            left_action_items=[["arrow-left", self.go_back]]
        )
        
        # Settings content
        self.scroll_view = ScrollView(do_scroll_x=False)
        self.settings_container = MDBoxLayout(
            orientation='vertical',
            spacing=dp(20),
            size_hint_y=None,
            padding=[dp(20), dp(20), dp(20), dp(20)]
        )
        self.settings_container.bind(minimum_height=self.settings_container.setter('height'))
        self.scroll_view.add_widget(self.settings_container)
        
        # Theme setting card
        theme_card = MDCard(
            orientation='vertical',
            padding=dp(15),
            spacing=dp(10),
            size_hint_y=None,
            height=dp(120),
            radius=dp(10)
        )
        theme_card.add_widget(MDLabel(
            text="Theme",
            font_style="H6",
            size_hint_y=None,
            height=dp(30),
            theme_text_color="Primary"  # FIXED: Set theme color
        ))
        
        theme_buttons = BoxLayout(spacing=dp(10))
        light_btn = MDRaisedButton(
            text="Light",
            size_hint_x=0.5,
            on_release=lambda x: self.set_light_theme()
        )
        dark_btn = MDRaisedButton(
            text="Dark",
            size_hint_x=0.5,
            on_release=lambda x: self.set_dark_theme()
        )
        theme_buttons.add_widget(light_btn)
        theme_buttons.add_widget(dark_btn)
        theme_card.add_widget(theme_buttons)
        
        # API key card - lets the user set/update their NewsAPI.org key on-device
        api_key_card = MDCard(
            orientation='vertical',
            padding=dp(15),
            spacing=dp(10),
            size_hint_y=None,
            height=dp(140),
            radius=dp(10)
        )
        api_key_card.add_widget(MDLabel(
            text="NewsAPI.org Key",
            font_style="H6",
            size_hint_y=None,
            height=dp(30),
            theme_text_color="Primary"
        ))
        app = MDApp.get_running_app()
        self.api_key_field = MDTextField(
            text=app.api_key or '',
            hint_text="Paste your API key",
            password=True,
            size_hint_y=None,
            height=dp(48)
        )
        api_key_card.add_widget(self.api_key_field)
        save_key_btn = MDRaisedButton(
            text="Save Key",
            on_release=lambda x: self.save_api_key()
        )
        api_key_card.add_widget(save_key_btn)

        # Country selection card
        country_card = MDCard(
            orientation='vertical',
            padding=dp(15),
            spacing=dp(10),
            size_hint_y=None,
            height=dp(100),
            radius=dp(10)
        )
        country_card.add_widget(MDLabel(
            text="Country",
            font_style="H6",
            size_hint_y=None,
            height=dp(30),
            theme_text_color="Primary"  # FIXED: Set theme color
        ))
        country_card.add_widget(MDLabel(
            text="USA (default)",
            font_style="Body1",
            theme_text_color="Secondary"
        ))
        
        # About card
        about_card = MDCard(
            orientation='vertical',
            padding=dp(15),
            spacing=dp(10),
            size_hint_y=None,
            height=dp(150),
            radius=dp(10)
        )
        about_card.add_widget(MDLabel(
            text="About",
            font_style="H6",
            size_hint_y=None,
            height=dp(30),
            theme_text_color="Primary"  # FIXED: Set theme color
        ))
        about_card.add_widget(MDLabel(
            text="News Reader v1.0\nMade with KivyMD\nAPI: NewsAPI.org",
            font_style="Body1",
            theme_text_color="Secondary"
        ))
        
        # Add all cards
        self.settings_container.add_widget(theme_card)
        self.settings_container.add_widget(api_key_card)
        self.settings_container.add_widget(country_card)
        self.settings_container.add_widget(about_card)
        
        # Add all widgets
        self.main_layout.add_widget(self.top_bar)
        self.main_layout.add_widget(self.scroll_view)
        self.add_widget(self.main_layout)
    
    def go_back(self, *args):
        """Go back to news screen"""
        self.manager.current = 'headlines'

    def save_api_key(self):
        """Save the API key entered by the user and refresh headlines"""
        key = self.api_key_field.text.strip()
        app = MDApp.get_running_app()
        app.api_key = key
        save_api_key(key)
        Snackbar(text="API key saved" if key else "API key cleared").open()
        app.headlines_screen.refresh_news()

    def set_light_theme(self):
        """Set light theme"""
        app = MDApp.get_running_app()
        app.theme_cls.theme_style = "Light"
        app.theme_cls.primary_palette = "Blue"
        Window.clearcolor = (1, 1, 1, 1)
        # Update bottom navigation
        app.bottom_nav.update_theme()
        # Update headlines screen cards
        app.headlines_screen.update_all_cards_theme()
    
    def set_dark_theme(self):
        """Set dark theme"""
        app = MDApp.get_running_app()
        app.theme_cls.theme_style = "Dark"
        app.theme_cls.primary_palette = "BlueGray"
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        # Update bottom navigation
        app.bottom_nav.update_theme()
        # Update headlines screen cards
        app.headlines_screen.update_all_cards_theme()

class ArticleScreen(MDScreen):
    """Article detail screen with fixed source handling"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'article'
        
        # Main layout
        self.main_layout = MDBoxLayout(orientation='vertical')
        
        # Top App Bar
        self.top_bar = MDTopAppBar(
            title="Article",
            elevation=4,
            left_action_items=[["arrow-left", self.go_back]],
            right_action_items=[
                ["open-in-new", self.open_in_browser],
                ["share-variant", self.share_article]
            ]
        )
        
        # Article content container
        self.scroll_view = ScrollView(do_scroll_x=False)
        self.content_container = MDBoxLayout(
            orientation='vertical',
            spacing=dp(15),
            size_hint_y=None,
            padding=[dp(15), dp(15), dp(15), dp(15)]
        )
        self.content_container.bind(minimum_height=self.content_container.setter('height'))
        self.scroll_view.add_widget(self.content_container)
        
        # Add all widgets
        self.main_layout.add_widget(self.top_bar)
        self.main_layout.add_widget(self.scroll_view)
        self.add_widget(self.main_layout)
    
    def go_back(self, *args):
        """Go back to news screen"""
        self.manager.current = 'headlines'
        # Show bottom navigation again
        app = MDApp.get_running_app()
        app.bottom_nav.opacity = 1
    
    def show_article(self, article_data):
        """Display article content - FIXED to handle both formats"""
        self.content_container.clear_widgets()
        
        # Image
        if article_data.get('urlToImage'):
            img_container = BoxLayout(size_hint_y=None, height=dp(200))  # Increased height
            try:
                img = AsyncImage(
                    source=article_data['urlToImage'],
                    size_hint=(1, 1),
                    fit_mode='fill'  # Use fit_mode instead of deprecated properties
                )
                img.color = [0.95, 0.95, 0.95, 1]
            except:
                # Fallback to placeholder
                img = MDIconButton(
                    icon='newspaper',
                    theme_text_color="Secondary",
                    size_hint=(1, 1),
                    disabled=True
                )
            img_container.add_widget(img)
            self.content_container.add_widget(img_container)
        
        # Title
        title = MDLabel(
            text=article_data.get('title', ''),
            size_hint_y=None,
            font_style="H5",
            halign='center',
            theme_text_color="Primary"
        )
        title.bind(texture_size=lambda inst, size: setattr(inst, 'height', size[1] + dp(20)))
        self.content_container.add_widget(title)
        
        # Meta information - FIXED to handle both string and dict source
        meta = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        
        # Source - Handle both string and dictionary formats
        source_box = BoxLayout(spacing=dp(5))
        source = article_data.get('source', 'Unknown')
        
        # Check if source is a dictionary
        if isinstance(source, dict):
            source_name = source.get('name', 'Unknown')
        else:
            source_name = str(source)
        
        source_label = MDLabel(
            text=f"Source: {source_name}",
            font_style="Body2",
            theme_text_color="Secondary",
            halign='left'
        )
        source_box.add_widget(source_label)
        
        # Date
        date_box = BoxLayout(spacing=dp(5))
        date_str = article_data.get('publishedAt', '')
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
            date_str = dt.strftime('%b %d, %Y %I:%M %p')
        except:
            pass
        date_label = MDLabel(
            text=date_str,
            font_style="Body2",
            theme_text_color="Secondary",
            halign='right'
        )
        date_box.add_widget(date_label)
        
        meta.add_widget(source_box)
        meta.add_widget(date_box)
        self.content_container.add_widget(meta)
        
        # Description/Content
        desc = article_data.get('description', '') or ''
        cont = article_data.get('content', '') or ''
        full = f"{desc}\n\n{cont}"
        
        # Clean up content
        if '[' in full and ']' in full:
            full = full.split('[')[0].strip()
        
        body = MDLabel(
            text=full,
            size_hint_y=None,
            font_style="Body1",
            halign='left',
            theme_text_color="Primary"
        )
        body.bind(texture_size=lambda inst, size: setattr(inst, 'height', size[1] + dp(20)))
        self.content_container.add_widget(body)
        
        # Store current article URL
        self.current_article_url = article_data.get('url', '')
    
    def open_in_browser(self, *args):
        """Open article in browser"""
        if hasattr(self, 'current_article_url') and self.current_article_url:
            webbrowser.open(self.current_article_url)
    
    def share_article(self, *args):
        """Share article"""
        # Placeholder for share functionality
        print("Share article functionality would be implemented here")

class BottomNavigation(MDBoxLayout):
    """Bottom navigation bar with proper icon colors"""
    def __init__(self, screen_manager, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(56)
        self.screen_manager = screen_manager
        
        # Set background color
        self.update_background_color()
        
        # Navigation buttons - use custom colors to ensure visibility
        self.news_btn = self.create_icon_button('newspaper', 'headlines')
        self.history_btn = self.create_icon_button('history', 'history')
        self.settings_btn = self.create_icon_button('cog', 'settings')
        
        # Add buttons with spacing
        self.add_widget(BoxLayout(size_hint_x=0.15))
        self.add_widget(self.news_btn)
        self.add_widget(BoxLayout(size_hint_x=0.25))
        self.add_widget(self.history_btn)
        self.add_widget(BoxLayout(size_hint_x=0.25))
        self.add_widget(self.settings_btn)
        self.add_widget(BoxLayout(size_hint_x=0.15))
        
        # Set initial active button
        self.set_active_button('headlines')
    
    def create_icon_button(self, icon, screen_name):
        """Create an icon button with proper styling"""
        btn = MDIconButton(
            icon=icon,
            on_release=lambda x: self.switch_screen(screen_name)
        )
        # Set custom colors for visibility
        btn.icon_color = (0.2, 0.6, 1, 1) if MDApp.get_running_app().theme_cls.theme_style == "Light" else (1, 1, 1, 1)
        return btn
    
    def switch_screen(self, screen_name):
        """Switch to a different screen"""
        self.screen_manager.current = screen_name
        self.set_active_button(screen_name)
    
    def set_active_button(self, screen_name):
        """Highlight the active navigation button"""
        # Colors for active/inactive states
        active_color = (0.2, 0.6, 1, 1)  # Blue
        inactive_color_light = (0.5, 0.5, 0.5, 1)  # Gray for light theme
        inactive_color_dark = (0.8, 0.8, 0.8, 1)  # Light gray for dark theme
        
        # Get current theme
        app = MDApp.get_running_app()
        is_dark = app.theme_cls.theme_style == "Dark"
        inactive_color = inactive_color_dark if is_dark else inactive_color_light
        
        # Reset all buttons
        self.news_btn.icon_color = active_color if screen_name == 'headlines' else inactive_color
        self.history_btn.icon_color = active_color if screen_name == 'history' else inactive_color
        self.settings_btn.icon_color = active_color if screen_name == 'settings' else inactive_color
    
    def update_background_color(self):
        """Update bottom navigation background color"""
        app = MDApp.get_running_app()
        if app.theme_cls.theme_style == "Light":
            self.md_bg_color = (0.95, 0.95, 0.95, 1)  # Light gray
        else:
            self.md_bg_color = (0.15, 0.15, 0.15, 1)  # Dark gray
    
    def update_theme(self):
        """Update bottom navigation colors when theme changes"""
        self.update_background_color()
        self.set_active_button(self.screen_manager.current)
        # Force a redraw
        self.canvas.ask_update()

class NewsReaderApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history_file = 'news_history.json'
        self.history = self.load_history()
    
    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"

        # Resolve the API key: env var wins (handy for desktop dev), then whatever
        # was saved on-device via Settings, then a developer-set default (if any).
        self.api_key = (
            os.environ.get('NEWS_API_KEY', '')
            or get_stored_api_key()
            or DEFAULT_API_KEY
        )

        # Create screen manager
        self.screen_manager = MDScreenManager()
        
        # Create screens
        self.headlines_screen = HeadlinesScreen()
        self.history_screen = HistoryScreen()
        self.settings_screen = SettingsScreen()
        self.article_screen = ArticleScreen()
        
        # Add screens to manager
        self.screen_manager.add_widget(self.headlines_screen)
        self.screen_manager.add_widget(self.history_screen)
        self.screen_manager.add_widget(self.settings_screen)
        self.screen_manager.add_widget(self.article_screen)
        
        # Create main layout with bottom navigation
        self.main_layout = MDBoxLayout(orientation='vertical')
        
        # Add screen manager
        self.main_layout.add_widget(self.screen_manager)
        
        # Add bottom navigation
        self.bottom_nav = BottomNavigation(self.screen_manager)
        self.main_layout.add_widget(self.bottom_nav)
        
        return self.main_layout
    
    def show_article(self, data):
        """Show article detail screen"""
        self.article_screen.show_article(data)
        self.screen_manager.current = 'article'
        # Hide bottom navigation on article screen
        self.bottom_nav.opacity = 0
    
    def add_to_history(self, article_data):
        """Add article to reading history - FIXED to save source as string"""
        # Extract source name properly
        source = article_data.get('source', {})
        if isinstance(source, dict):
            source_name = source.get('name', '')
        else:
            source_name = str(source)
        
        # Create a simplified version of article data for history
        history_entry = {
            'title': article_data.get('title', ''),
            'source': source_name,  # Save as string, not dictionary
            'publishedAt': article_data.get('publishedAt', ''),
            'url': article_data.get('url', ''),
            'urlToImage': article_data.get('urlToImage', ''),
            'description': article_data.get('description', ''),
            'timestamp': datetime.now().isoformat()  # Add when article was viewed
        }
        
        # Remove duplicates (based on URL)
        url = article_data.get('url', '')
        self.history = [h for h in self.history if h.get('url') != url]
        
        # Add new entry at beginning (newest first)
        self.history.insert(0, history_entry)
        
        # Keep only last 50 articles
        if len(self.history) > 50:
            self.history = self.history[:50]
        
        # Save to file
        self.save_history()
        
        # Refresh history screen if it's visible
        if self.screen_manager.current == 'history':
            self.history_screen.load_history()
    
    def get_history(self):
        """Get reading history"""
        return self.history
    
    def clear_history(self):
        """Clear all reading history"""
        self.history = []
        self.save_history()
    
    def load_history(self):
        """Load history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    # Ensure data is a list
                    if isinstance(data, list):
                        return data
        except Exception as e:
            print(f"Error loading history: {e}")
        return []
    
    def save_history(self):
        """Save history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def on_start(self):
        """Called when app starts"""
        # Apply initial theme to window
        if self.theme_cls.theme_style == "Light":
            Window.clearcolor = (1, 1, 1, 1)
        else:
            Window.clearcolor = (0.1, 0.1, 0.1, 1)

        # If no API key was resolved (no env var, nothing saved, no default),
        # jump straight to Settings and prompt the user instead of making them
        # find their own way there after seeing an error on the headlines screen.
        if not self.api_key:
            self.screen_manager.current = 'settings'
            self.bottom_nav.set_active_button('settings')
            dialog = MDDialog(
                title="Add your NewsAPI.org key",
                text=(
                    "No API key is set yet. Paste your free key from "
                    "newsapi.org into the field below and tap Save Key "
                    "to start seeing headlines."
                ),
                buttons=[MDFlatButton(text="GOT IT", on_release=lambda x: dialog.dismiss())]
            )
            dialog.open()

if __name__ == '__main__':
    NewsReaderApp().run()