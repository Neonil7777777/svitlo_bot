import aiosqlite

DB_NAME = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                address TEXT DEFAULT 'Вишнева'
            )
        """)
        await db.commit()

async def add_user(user_id: int, username: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username) 
            VALUES (?, ?)
        """, (user_id, username))
        await db.commit()

async def update_user_address(user_id: int, address: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE users SET address = ? WHERE user_id = ?
        """, (address, user_id))
        await db.commit()

async def get_user_address(user_id: int) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT address FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "Вишнева"
          
