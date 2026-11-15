import aiosqlite

DB_NAME = "bot_database.db"

async def init_db():
    """Ініціалізація бази даних та створення таблиць"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблиця користувачів
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                queue TEXT DEFAULT '1.1'
            )
        """)
        await db.commit()

async def add_user(user_id: int, username: str):
    """Додавання користувача до бази, якщо його ще немає"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username) 
            VALUES (?, ?)
        """, (user_id, username))
        await db.commit()

async def update_user_queue(user_id: int, queue: str):
    """Оновлення обраної черги відключень для користувача"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE users SET queue = ? WHERE user_id = ?
        """, (queue, user_id))
        await db.commit()

async def get_user_queue(user_id: int) -> str:
    """Отримання поточної черги користувача"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT queue FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "1.1"

async def get_all_users():
    """Отримання списку всіх користувачів (для розсилок)"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, queue FROM users") as cursor:
            return await cursor.fetchall()
          
