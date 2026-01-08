from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN
import logging

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot va Dispatcher
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# OPTIMIZED: Dispatcher fsm_strategy
dp.fsm.strategy = "user"  # Per user FSM storage

# Scheduler
scheduler = AsyncIOScheduler()
