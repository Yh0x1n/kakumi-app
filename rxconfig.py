import reflex as rx

config = rx.Config(
    app_name="kakumi_app",
    api_url="http://app.kakumitm.com:8000",
    backend_path="/api",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    db_url="sqlite:///kakumi.db"
)
