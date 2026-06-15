import reflex as rx

config = rx.Config(
    app_name="kakumi_app",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    db_url="sqlite:///kakumi.db"
)