from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from config import ADMIN_IDS
import logging
import asyncio
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
router = Router()


# FSM States
class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_revoke_user_id = State()  # Premium bekor qilish uchun
    waiting_for_days = State()
    waiting_for_broadcast = State()
    waiting_for_grant_user = State()


def is_admin(user_id: int) -> bool:
    """Admin tekshirish"""
    return user_id in ADMIN_IDS


def get_admin_keyboard():
    """Admin panel klaviaturasi"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
                InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton(text="💎 Premium", callback_data="admin_premium"),
                InlineKeyboardButton(text="🔍 Qidirish", callback_data="admin_find_user")
            ],
            [
                InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_panel"),
                InlineKeyboardButton(text="❌ Yopish", callback_data="admin_close")
            ]
        ]
    )


def get_premium_manage_keyboard():
    """Premium boshqaruv klaviaturasi"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Berish", callback_data="admin_grant_premium"),
                InlineKeyboardButton(text="➖ Bekor qilish", callback_data="admin_revoke_premium")
            ],
            [
                InlineKeyboardButton(text="📋 Ro'yxat", callback_data="admin_premium_list")
            ],
            [
                InlineKeyboardButton(text="💎 Tezkor berish", callback_data="admin_quick_premium")
            ],
            [
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_panel")
            ]
        ]
    )


@router.message(F.text == "/admin")
async def cmd_admin(message: Message):
    """Admin panel"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Sizda admin huquqlari yo'q!")
        return
    
    await message.answer(
        "🔐 <b>Admin Panel</b>\n\n"
        "Xush kelibsiz, Admin!\n\n"
        "Quyidagi funksiyalardan foydalanishingiz mumkin:\n"
        "• 📊 Bot statistikasi\n"
        "• 👥 Foydalanuvchilar ro'yxati\n"
        "• 💎 Premium boshqaruv\n"
        "• 📢 Barcha foydalanuvchilarga xabar\n"
        "• 🔍 Foydalanuvchi qidirish\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=get_admin_keyboard(),
        parse_mode='HTML'
    )


@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    """Admin panel"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin emas!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔐 <b>Admin Panel</b>\n\n"
        "Xush kelibsiz, Admin!\n\n"
        "Quyidagi funksiyalardan foydalanishingiz mumkin:\n"
        "• 📊 Bot statistikasi\n"
        "• 👥 Foydalanuvchilar ro'yxati\n"
        "• 💎 Premium boshqaruv\n"
        "• 📢 Barcha foydalanuvchilarga xabar\n"
        "• 🔍 Foydalanuvchi qidirish\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=get_admin_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Bot statistikasi"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin emas!", show_alert=True)
        return
    
    try:
        all_users = await db.get_all_active_users()
        total_users = len(all_users)
        
        premium_count = 0
        for user_id in all_users:
            if await db.is_premium(user_id):
                premium_count += 1
        
        free_count = total_users - premium_count
        
        text = f"""
📊 <b>Bot Statistikasi</b>

👥 <b>Foydalanuvchilar:</b>
• Jami: {total_users}
• 💎 Premium: {premium_count}
• 🆓 Free: {free_count}

📈 <b>Konversiya:</b>
• Premium %: {(premium_count/total_users*100) if total_users > 0 else 0:.1f}%

🕐 <b>Oxirgi yangilanish:</b>
{datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_stats")],
                    [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_panel")]
                ]
            ),
            parse_mode='HTML'
        )
        await callback.answer("✅ Statistika yangilandi")
        
    except Exception as e:
        logger.error(f"Admin stats xatolik: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Foydalanuvchilar ro'yxati"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin emas!", show_alert=True)
        return
    
    try:
        all_users = await db.get_all_active_users()
        
        recent_users = []
        for user_id in all_users[-10:]:
            user = await db.get_user(user_id)
            if not user:
                continue
            is_premium = await db.is_premium(user_id)
            
            username = user.get('username', 'N/A')
            first_name = user.get('first_name', 'N/A')
            status = "💎" if is_premium else "🆓"
            
            recent_users.append(f"\n{status} {first_name} (@{username}) - {user_id}")
        
        text = f"""
👥 <b>Foydalanuvchilar</b>

📋 <b>Jami:</b> {len(all_users)} ta

<b>So'nggi 10 ta:</b>
{''.join(recent_users)}

💡 Aniq foydalanuvchini qidirish uchun "🔍 Qidirish" tugmasini bosing.
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔍 Qidirish", callback_data="admin_find_user")],
                    [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_panel")]
                ]
            ),
            parse_mode='HTML'
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Admin users xatolik: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)


@router.callback_query(F.data == "admin_premium")
async def admin_premium(callback: CallbackQuery):
    """Premium boshqaruv"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin emas!", show_alert=True)
        return
    
    text = """
💎 <b>Premium Boshqaruv</b>

<b>Mavjud amallar:</b>
• ➕ Premium berish (qo'lda)
• ➖ Premium bekor qilish
• 📋 Premium foydalanuvchilar ro'yxati
• 💎 Tezkor berish (7/30/90/365 kun)

<b>Tezkor Premium:</b>
Eng ko'p ishlatiladigan muddatlar uchun!
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_premium_manage_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "admin_quick_premium")
async def quick_premium_menu(callback: CallbackQuery):
    """Tezkor premium berish menyu"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin emas!", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="7️⃣ 7 kun", callback_data="quick_premium_7"),
                InlineKeyboardButton(text="🔟 30 kun", callback_data="quick_premium_30")
            ],
            [
                InlineKeyboardButton(text="📅 90 kun", callback_data="quick_premium_90"),
                InlineKeyboardButton(text="📆 365 kun", callback_data="quick_premium_365")
            ],
            [
                InlineKeyboardButton(text="♾️ Abadiy", callback_data="quick_premium_forever")
            ],
            [
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_premium")
            ]
        ]
    )
    
    await callback.message.edit_text(
        "💎 <b>Tezkor Premium berish</b>\n\n"
        "Muddatni tanlang, keyin User ID kiriting:",
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith("quick_premium_"))
async def quick_premium_select(callback: CallbackQuery, state: FSMContext):
    """Tezkor premium - muddat tanlash"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin emas!", show_alert=True)
        return
    
    period = callback.data.replace("quick_premium_", "")
    
    days_map = {
        "7": 7,
        "30": 30,
        "90": 90,
        "365": 365,
        "forever": 36500
    }
    
    days = days_map.get(period, 30)
    period_text = {
        "7": "7 kun",
        "30": "30 kun (1 oy)",
        "90": "90 kun (3 oy)",
        "365": "365 kun (1 yil)",
        "forever": "Abadiy"
    }.get(period, "30 kun")
    
    await state.update_data(quick_premium_days=days)
    
    await callback.message.edit_text(
        f"💎 <b>Tezkor Premium: {period_text}</b>\n\n"
        f"Foydalanuvchi ID'sini kiriting:\n\n"
        f"Misol: <code>123456789</code>\n\n"
        f"Yoki /cancel bekor qilish uchun",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.waiting_for_grant_user)
    await callback.answer()


@router.message(F.text == "/cancel")
async def cancel_admin_action(message: Message, state: FSMContext):
    """Admin amalini bekor qilish"""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    await message.answer("❌ Amal bekor qilindi")


@router.callback_query(F.data == "admin_grant_premium")
async def start_grant_premium(callback: CallbackQuery, state: FSMContext):
    """Premium berish - boshlash"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin emas!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "➕ <b>Premium berish</b>\n\n"
        "Foydalanuvchi ID'sini kiriting:\n\n"
        "Misol: <code>123456789</code>",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.waiting_for_grant_user)
    await callback.answer()


@router.message(AdminStates.waiting_for_grant_user)
async def process_grant_user(message: Message, state: FSMContext):
    """Premium berish - user ID"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    try:
        user_id = int(message.text.strip())
        
        # User mavjudligini tekshirish
        user = await db.get_user(user_id)
        if not user:
            await message.answer(
                f"❌ <b>Foydalanuvchi topilmadi!</b>\n\n"
                f"ID: <code>{user_id}</code>\n\n"
                f"Foydalanuvchi botga /start yuborishi kerak!",
                parse_mode='HTML'
            )
            await state.clear()
            return
        
        username = user.get('username', 'N/A')
        first_name = user.get('first_name', 'N/A')
        
        # Tezkor premium uchun kunlarni tekshirish
        data = await state.get_data()
        quick_days = data.get('quick_premium_days')
        
        if quick_days:
            # Tezkor premium - darhol berish
            await state.update_data(grant_user_id=user_id)
            
            await message.answer(
                f"⏳ <b>Premium berilmoqda...</b>\n\n"
                f"👤 {first_name} (@{username})\n"
                f"📅 Muddat: {quick_days} kun",
                parse_mode='HTML'
            )
            
            success = await db.set_premium(user_id, quick_days)
            
            await asyncio.sleep(2)
            
            if success:
                is_premium_now = await db.is_premium(user_id)
                expiry = datetime.now(timezone.utc) + timedelta(days=quick_days)
                
                await message.answer(
                    f"✅✅✅ <b>Premium berildi!</b>\n\n"
                    f"👤 User: {first_name}\n"
                    f"📅 Muddat: {quick_days} kun\n"
                    f"📆 Tugash: {expiry.strftime('%d.%m.%Y')}\n"
                    f"💎 Status: {'AKTIV' if is_premium_now else 'TEKSHIRILMOQDA'}",
                    parse_mode='HTML'
                )
                
                # Xabar yuborish
                try:
                    await message.bot.send_message(
                        user_id,
                        f"🎉 <b>Tabriklaymiz!</b>\n\n"
                        f"Sizga {quick_days} kunlik Premium berildi!\n\n"
                        f"💎 Premium tugmasini bosib tekshiring!",
                        parse_mode='HTML'
                    )
                except:
                    pass
            else:
                await message.answer("❌ Premium berilmadi! Loglarni tekshiring.")
            
            await state.clear()
            return
        
        # Oddiy premium - kunlarni so'rash
        await state.update_data(grant_user_id=user_id)
        
        await message.answer(
            f"👤 <b>Foydalanuvchi topildi:</b>\n"
            f"• ID: <code>{user_id}</code>\n"
            f"• Ism: {first_name}\n"
            f"• Username: @{username}\n\n"
            f"Necha kunlik Premium berasiz?\n\n"
            f"<b>Misollar:</b>\n"
            f"• <code>7</code> - 1 hafta\n"
            f"• <code>30</code> - 1 oy\n"
            f"• <code>365</code> - 1 yil",
            parse_mode='HTML'
        )
        await state.set_state(AdminStates.waiting_for_days)
        
    except ValueError:
        await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting.")
        await state.clear()
    except Exception as e:
        logger.error(f"process_grant_user xatolik: {e}", exc_info=True)
        await message.answer(f"❌ Xatolik: {e}")
        await state.clear()


@router.message(AdminStates.waiting_for_days)
async def process_grant_days(message: Message, state: FSMContext):
    """Premium berish - kunlar"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    try:
        days = int(message.text.strip())
        
        if days <= 0:
            await message.answer("❌ Kunlar soni musbat bo'lishi kerak!")
            return
        
        data = await state.get_data()
        user_id = data.get('grant_user_id')
        
        if not user_id:
            await message.answer("❌ User ID topilmadi. /admin ni qaytadan boshing.")
            await state.clear()
            return
        
        logger.info("="*60)
        logger.info(f"ADMIN {message.from_user.id} gives premium to {user_id} for {days} days")
        
        await message.answer(
            f"⏳ <b>Premium berilmoqda...</b>\n\nKuting...",
            parse_mode='HTML'
        )
        
        success = await db.set_premium(user_id, days)
        
        await asyncio.sleep(2)
        
        if success:
            is_premium_now = await db.is_premium(user_id)
            expiry = datetime.now(timezone.utc) + timedelta(days=days)
            
            await message.answer(
                f"✅✅✅ <b>Premium berildi!</b>\n\n"
                f"👤 User: <code>{user_id}</code>\n"
                f"📅 Muddat: {days} kun\n"
                f"📆 Tugash: {expiry.strftime('%d.%m.%Y')}\n"
                f"💎 Status: {'AKTIV' if is_premium_now else 'TEKSHIRILMOQDA'}",
                parse_mode='HTML'
            )
            
            # Xabar yuborish
            try:
                await message.bot.send_message(
                    user_id,
                    f"🎉 <b>Tabriklaymiz!</b>\n\n"
                    f"Sizga {days} kunlik Premium berildi!\n\n"
                    f"💎 Premium tugmasini bosib tekshiring!",
                    parse_mode='HTML'
                )
            except:
                pass
        else:
            await message.answer("❌ Premium berilmadi! Loglarni tekshiring.")
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
    except Exception as e:
        logger.error(f"EXCEPTION: {e}", exc_info=True)
        await message.answer(f"❌ Xatolik: {e}")
        await state.clear()


@router.callback_query(F.data == "admin_revoke_premium")
async def start_revoke_premium(callback: CallbackQuery, state: FSMContext):
    """Premium bekor qilish"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin emas!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "➖ <b>Premium bekor qilish</b>\n\n"
        "Foydalanuvchi ID'sini kiriting:\n\n"
        "Misol: <code>123456789</code>",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.waiting_for_revoke_user_id)
    await callback.answer()


@router.message(AdminStates.waiting_for_revoke_user_id)
async def process_revoke_premium(message: Message, state: FSMContext):
    """Premium bekor qilish - jarayon"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    try:
        user_id = int(message.text.strip())
        
        await db.remove_premium(user_id)
        
        await message.answer(
            f"✅ <b>Premium bekor qilindi!</b>\n\n"
            f"👤 Foydalanuvchi: <code>{user_id}</code>",
            parse_mode='HTML'
        )
        
        try:
            await message.bot.send_message(
                user_id,
                "⚠️ <b>Premium obunangiz bekor qilindi</b>\n\n"
                "Endi siz Free versiyadan foydalanasiz.",
                parse_mode='HTML'
            )
        except:
            pass
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting.")
        await state.clear()


@router.callback_query(F.data == "admin_premium_list")
async def admin_premium_list(callback: CallbackQuery):
    """Premium foydalanuvchilar ro'yxati"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin emas!", show_alert=True)
        return
    
    try:
        all_users = await db.get_all_active_users()
        premium_users = []
        
        for user_id in all_users:
            if await db.is_premium(user_id):
                user = await db.get_user(user_id)
                if not user:
                    continue
                    
                username = user.get('username', 'N/A')
                first_name = user.get('first_name', 'N/A')
                premium_until = user.get('premium_until')
                
                if premium_until:
                    date_str = premium_until.strftime('%d.%m.%Y')
                else:
                    date_str = "Abadiy"
                
                premium_users.append(
                    f"\n💎 {first_name} (@{username})"
                    f"\n   ID: {user_id}"
                    f"\n   Tugash: {date_str}"
                )
        
        if premium_users:
            text = f"""
📋 <b>Premium Foydalanuvchilar</b>

Jami: {len(premium_users)} ta
{''.join(premium_users[:10])}
"""
            if len(premium_users) > 10:
                text += f"\n\n... va yana {len(premium_users) - 10} ta"
        else:
            text = "📋 <b>Premium foydalanuvchilar yo'q</b>"
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_premium")]
                ]
            ),
            parse_mode='HTML'
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Premium list xatolik: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)


@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Broadcast boshlash"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin emas!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 <b>Barcha foydalanuvchilarga xabar yuborish</b>\n\n"
        "Yubormoqchi bo'lgan xabaringizni yozing:\n\n"
        "⚠️ Xabar HTML formatda bo'lishi mumkin.\n\n"
        "Bekor qilish: /cancel",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.answer()


@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    """Broadcast yuborish"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    broadcast_text = message.text
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yuborish", callback_data="broadcast_confirm"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")
            ]
        ]
    )
    
    await state.update_data(broadcast_text=broadcast_text)
    await message.answer(
        f"📢 <b>Xabarni tasdiqlang:</b>\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{broadcast_text}\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"Barcha foydalanuvchilarga yuborilsinmi?",
        reply_markup=keyboard,
        parse_mode='HTML'
    )


@router.callback_query(F.data == "broadcast_confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Broadcast ni tasdiqlash va yuborish"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin emas!", show_alert=True)
        return
    
    data = await state.get_data()
    broadcast_text = data.get('broadcast_text')
    
    await callback.message.edit_text("📤 Xabar yuborilmoqda...")
    
    all_users = await db.get_all_active_users()
    success = 0
    failed = 0
    
    for user_id in all_users:
        try:
            await callback.bot.send_message(user_id, broadcast_text, parse_mode='HTML')
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            logger.debug(f"Broadcast xatolik {user_id}: {e}")
    
    await callback.message.edit_text(
        f"✅ <b>Broadcast yakunlandi!</b>\n\n"
        f"📊 Statistika:\n"
        f"• Yuborildi: {success}\n"
        f"• Xatolik: {failed}\n"
        f"• Jami: {len(all_users)}",
        parse_mode='HTML'
    )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Broadcast ni bekor qilish"""
    await callback.message.edit_text("❌ Broadcast bekor qilindi")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "admin_find_user")
async def find_user(callback: CallbackQuery):
    """Foydalanuvchi qidirish"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin emas!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔍 <b>Foydalanuvchi qidirish</b>\n\n"
        "Foydalanuvchi ID'sini kiriting:\n\n"
        "Misol: <code>123456789</code>\n\n"
        "Yoki /admin ga qaytish",
        parse_mode='HTML'
    )
    await callback.answer()


@router.message(F.text.regexp(r'^\d{5,}$'), StateFilter(None))
async def search_user_by_id(message: Message):
    """ID bo'yicha qidirish"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        user_id = int(message.text.strip())
        user = await db.get_user(user_id)
        
        if not user:
            await message.answer(f"❌ Foydalanuvchi {user_id} topilmadi!")
            return
        
        is_premium = await db.is_premium(user_id)
        user_filter = await db.get_user_filter(user_id)
        
        username = user.get('username', 'N/A')
        first_name = user.get('first_name', 'N/A')
        last_name = user.get('last_name', 'N/A')
        created_at = user.get('created_at')
        premium_until = user.get('premium_until')
        
        text = f"""
👤 <b>Foydalanuvchi ma'lumotlari:</b>

📋 <b>Asosiy:</b>
- ID: <code>{user_id}</code>
- Ism: {first_name} {last_name or ''}
- Username: @{username}
- Status: {'💎 Premium' if is_premium else '🆓 Free'}
- Ro'yxatdan o'tgan: {created_at.strftime('%d.%m.%Y') if created_at else 'N/A'}
"""
        
        if is_premium and premium_until:
            text += f"• Premium tugashi: {premium_until.strftime('%d.%m.%Y %H:%M')}\n"
        
        if user_filter:
            keywords = user_filter.get('keywords', [])
            text += f"\n⚙️ <b>Sozlamalar:</b>\n"
            text += f"• Kalit so'zlar: {', '.join(keywords) if keywords else 'Yo\'q'}\n"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="➕ Premium berish", callback_data="admin_grant_premium"),
                    InlineKeyboardButton(text="➖ Premium olish", callback_data="admin_revoke_premium")
                ],
                [
                    InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")
                ]
            ]
        )
        
        await message.answer(text, reply_markup=keyboard, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Search user xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi!")

@router.callback_query(F.data.startswith("delete_vacancy_"))
async def process_delete_vacancy(callback: CallbackQuery):
    """Vakansiyani o'chirish (Admin)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin emas!", show_alert=True)
        return

    vacancy_id = callback.data.replace("delete_vacancy_", "")
    
    try:
        success = await db.delete_vacancy(vacancy_id)
        
        if success:
            await callback.answer("✅ Vakansiya o'chirildi!", show_alert=True)
            # Xabarni o'chirish yoki yangilash
            await callback.message.delete()
        else:
            await callback.answer("❌ O'chirishda xatolik! Bazada topilmadi.", show_alert=True)
            
    except Exception as e:
        logger.error(f"Delete vacancy error: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)


@router.callback_query(F.data == "admin_close")
async def close_admin(callback: CallbackQuery):
    """Admin panelni yopish"""
    await callback.message.delete()
    await callback.answer()