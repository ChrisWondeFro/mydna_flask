from app import create_app
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve

app = create_app()

if __name__ == '__main__':
    config = Config()
    config.bind = ["localhost:8000"]
    asyncio.run(serve(app, config))
