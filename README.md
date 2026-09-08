
# News Reader App

A mobile-style news reader built with Kivy and KivyMD, powered by NewsAPI.org
(https://newsapi.org).

Features 
--------
- Browse top headlines by category (General, Business, Entertainment, Health,
  Science, Sports, Technology)
- Infinite scroll pagination
- Light/Dark theme toggle
- Article detail view with "Open in Browser" option
- Reading history (auto-saved locally, last 50 articles)
- Bottom navigation: Headlines, History, Settings

Requirements
------------
    pip install kivy kivymd requests

Setup 
-----
1. Get a free API key from https://newsapi.org
2. Replace the API_KEY value below with your own key.
3. Run:
    python main.py

Project Structure
------------------
    main.py               - App entry point (all screens & logic, this file)
    news_history.json     - Auto-generated reading history (created on first run)

Screens
-------
    Headlines  - Main feed with category filter via nav drawer
    Article    - Full article view with image, source, date, description
    History    - List of previously read articles
    Settings   - Theme switcher, country info, about

Notes
-----
- Default country is set to 'us'. Change the 'country' param in
  HeadlinesScreen.fetch_news() to localize results.
- History is stored in news_history.json in the app's working directory.

### Author

Kiran S B

⭐ If you like this project, give it a star!
