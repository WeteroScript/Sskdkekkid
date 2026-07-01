import random
from datetime import datetime
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import bot, logger
from database.file_manager import load_users, save_users, load_inventory, save_inventory
from utils.helpers import check_access, get_default_user, is_function_disabled
from states import FishingStates

# ==========================================
# ===== КОНФИГ РЫБАЛКИ =====
# ==========================================

# Удочки
FISHING_RODS = {
    "galactic": {
        "name": "Галактическая удочка",
        "emoji": "🚀",
        "base_chance": 95,
        "price": 20000000000,
        "criteria": {"fish_caught": 1500},
        "level": 5,
        "fish_per_cast": 10  # Количество рыбы за одну рыбалку
    },
    "volcanic": {
        "name": "Вулканическая удочка",
        "emoji": "🌋",
        "base_chance": 85,
        "price": 1500000000,
        "criteria": {"fish_caught": 750},
        "level": 4,
        "fish_per_cast": 5
    },
    "legendary": {
        "name": "Легендарная удочка",
        "emoji": "⭐",
        "base_chance": 70,
        "price": 500000000,
        "criteria": {"fish_caught": 250},
        "level": 3,
        "fish_per_cast": 3
    },
    "rare": {
        "name": "Редкая удочка",
        "emoji": "🔮",
        "base_chance": 65,
        "price": 150000000,
        "criteria": {"fish_caught": 50},
        "level": 2,
        "fish_per_cast": 1
    },
    "basic": {
        "name": "Базовая удочка",
        "emoji": "🎣",
        "base_chance": 55,
        "price": 0,
        "criteria": {"default": True},
        "level": 1,
        "fish_per_cast": 1
    }
}

# Снасти (НЕ ТРАТЯТСЯ, но могут сломаться!)
FISHING_TACKLE = {
    "galactic": {
        "name": "Галактическая снасть",
        "emoji": "🚀",
        "price": 7500000000,
        "criteria": {"rod": "galactic"},
        "level": 5,
        "break_chance": 0.05  # 5% шанс поломки
    },
    "volcanic": {
        "name": "Вулканическая снасть",
        "emoji": "🌋",
        "price": 1500000000,
        "criteria": {"rod": "volcanic"},
        "level": 4,
        "break_chance": 0.05
    },
    "legendary": {
        "name": "Легендарная снасть",
        "emoji": "⭐",
        "price": 350000000,
        "criteria": {"rod": "legendary"},
        "level": 3,
        "break_chance": 0.05
    },
    "rare": {
        "name": "Редкая снасть",
        "emoji": "🔮",
        "price": 75000000,
        "criteria": {"rod": "rare"},
        "level": 2,
        "break_chance": 0.05
    },
    "basic": {
        "name": "Базовая снасть",
        "emoji": "🎣",
        "price": 0,
        "criteria": {"default": True},
        "level": 1,
        "break_chance": 0
    }
}

# Приманки (5 штук для каждой удочки)
FISHING_BAITS = {
    "galactic": [
        {"name": "Квантовая крошка", "price": 500000000, "bonus": 40},
        {"name": "Звёздная пыль", "price": 150000000, "bonus": 30},
        {"name": "Метеоритный песок", "price": 95000000, "bonus": 20},
        {"name": "Тёмная материя", "price": 85000000, "bonus": 15},
        {"name": "Солнечный луч", "price": 70000000, "bonus": 10}
    ],
    "volcanic": [
        {"name": "Лавовый червь", "price": 50000000, "bonus": 40},
        {"name": "Пепельный мотыль", "price": 35000000, "bonus": 25},
        {"name": "Магмовый опарыш", "price": 25000000, "bonus": 20},
        {"name": "Кратерная креветка", "price": 20000000, "bonus": 15},
        {"name": "Огненный нектар", "price": 15000000, "bonus": 10}
    ],
    "legendary": [
        {"name": "Золотая муха", "price": 25000000, "bonus": 40},
        {"name": "Жемчужная крупа", "price": 15000000, "bonus": 30},
        {"name": "Бриллиантовый червь", "price": 10000000, "bonus": 20},
        {"name": "Древний мотыль", "price": 8000000, "bonus": 15},
        {"name": "Королевский нектар", "price": 5000000, "bonus": 10}
    ],
    "rare": [
        {"name": "Серебряный опарыш", "price": 5000000, "bonus": 40},
        {"name": "Бронзовый червь", "price": 2500000, "bonus": 30},
        {"name": "Мраморная муха", "price": 2000000, "bonus": 20},
        {"name": "Янтарный мотыль", "price": 1500000, "bonus": 15},
        {"name": "Изумрудный нектар", "price": 1000000, "bonus": 10}
    ],
    "basic": [
        {"name": "Обычный червяк", "price": 15000, "bonus": 40},
        {"name": "Хлебный мякиш", "price": 7500, "bonus": 30},
        {"name": "Муха-дрозофила", "price": 5000, "bonus": 20},
        {"name": "Тесто", "price": 2500, "bonus": 15},
        {"name": "Универсальный нектар", "price": 1000, "bonus": 10}
    ]
}

# Рыбы по удочкам
FISH_DATA = {
    "galactic": [
        {"name": "Квантовый тунец", "price": 5000000, "chance": 65},
        {"name": "Звёздный скат", "price": 15000000, "chance": 60},
        {"name": "Чёрная дыра-рыба", "price": 50000000, "chance": 50},
        {"name": "Планетарная камбала", "price": 100000000, "chance": 45},
        {"name": "Комета-окунь", "price": 150000000, "chance": 35},
        {"name": "Астероидная сельдь", "price": 350000000, "chance": 25},
        {"name": "Гравитационный сом", "price": 750000000, "chance": 5},
        {"name": "Тёмный угорь", "price": 2500000000, "chance": 1},
        {"name": "Космический ёрш", "price": 5500000000, "chance": 0.2},
        {"name": "Пульсар-карась", "price": 7500000000, "chance": 0.05}
    ],
    "volcanic": [
        {"name": "Лавовый лосось", "price": 75000000, "chance": 60},
        {"name": "Огненный карп", "price": 150000000, "chance": 50},
        {"name": "Пепельная форель", "price": 250670670, "chance": 45},
        {"name": "Магмовый сом", "price": 350000000, "chance": 35},
        {"name": "Кратерный окунь", "price": 500000000, "chance": 25},
        {"name": "Вулканическая щука", "price": 750000000, "chance": 10},
        {"name": "Раскалённая плотва", "price": 1700670670, "chance": 1},
        {"name": "Серный судак", "price": 2500000000, "chance": 0.5},
        {"name": "Извергающий ёрш", "price": 3500000000, "chance": 0.3},
        {"name": "Жар-карась", "price": 5500000000, "chance": 0.09}
    ],
    "legendary": [
        {"name": "Королевский лосось", "price": 3500000, "chance": 60},
        {"name": "Серебряный судак", "price": 5000000, "chance": 45},
        {"name": "Бриллиантовая щука", "price": 7500000, "chance": 25},
        {"name": "Нефритовый окунь", "price": 15000000, "chance": 15},
        {"name": "Аметистовый сазан", "price": 750000000, "chance": 0.5},
        {"name": "Рубиновый ёрш", "price": 1500000000, "chance": 0.2}
    ],
    "rare": [
        {"name": "Жемчужный карась", "price": 1200000, "chance": 60},
        {"name": "Золотистый ёрш", "price": 7500000, "chance": 30},
        {"name": "Медный сом", "price": 15000000, "chance": 15},
        {"name": "Стальной окунь", "price": 250000000, "chance": 0.5},
        {"name": "Бирюзовый пескарь", "price": 500000000, "chance": 0.2}
    ],
    "basic": [
        {"name": "Карась", "price": 300000, "chance": 22},
        {"name": "Плотва", "price": 330000, "chance": 18},
        {"name": "Окунь", "price": 350000, "chance": 16},
        {"name": "Ёрш", "price": 450000, "chance": 13},
        {"name": "Пескарь", "price": 500000, "chance": 11},
        {"name": "Краснопёрка", "price": 1000000, "chance": 8},
        {"name": "Линь", "price": 2500000, "chance": 6},
        {"name": "Уклейка", "price": 3550000, "chance": 4},
        {"name": "Густера", "price": 7500000, "chance": 2},
        {"name": "Вьюн", "price": 150000000, "chance": 0.1}
    ]
}

# Допустимые категории приманок
VALID_BAIT_CATEGORIES = ["galactic", "volcanic", "legendary", "rare", "basic"]


def register_fishing_handlers(dp):

    # ==========================================
    # ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
    # ==========================================

    def get_default_fishing_data() -> dict:
        """Возвращает чистую структуру данных рыбалки"""
        return {
            "rod": "basic",
            "tackle": "basic",
            "bait": None,
            "fish_caught": 0,
            "total_fish": 0,
            "fish_inventory": {},
            "rods": {"basic": True},
            "tackles": {"basic": True}
        }

    def validate_fishing_data(fishing: dict) -> dict:
        """Проверяет и восстанавливает данные рыбалки"""
        if not isinstance(fishing, dict):
            logger.error(f"Ошибка типа данных рыбалки: {type(fishing)}")
            return get_default_fishing_data()

        defaults = get_default_fishing_data()

        for key, default_value in defaults.items():
            if key not in fishing:
                fishing[key] = default_value
                continue

            if key == "bait":
                if fishing[key] is not None and not isinstance(fishing[key], str):
                    fishing[key] = None
                continue

            if not isinstance(fishing[key], type(default_value)):
                logger.warning(f"Неверный тип для fishing.{key}")
                fishing[key] = default_value
                continue

            if isinstance(default_value, dict):
                if not fishing[key]:
                    fishing[key] = default_value
                elif not all(isinstance(v, bool) for v in fishing[key].values()):
                    fishing[key] = {k: v for k, v in fishing[key].items()
                                    if isinstance(v, bool)}

        return fishing

    def get_bait_bonus(bait_name: str = None) -> int:
        """Получает бонус приманки с проверкой валидности"""
        if not bait_name:
            return 0

        for category, baits in FISHING_BAITS.items():
            for bait in baits:
                if bait["name"] == bait_name:
                    return bait.get("bonus", 0)

        logger.warning(f"Приманка не найдена: {bait_name}")
        return 0

    def get_bait_category(bait_name: str = None):
        """Получает категорию приманки (для какой удочки/снасти она предназначена) по названию"""
        if not bait_name:
            return None

        for category, baits in FISHING_BAITS.items():
            for bait in baits:
                if bait["name"] == bait_name:
                    return category

        return None

    async def get_fishing_data(user_id: str):
        """Получает и проверяет данные рыбалки пользователя"""
        try:
            users = await load_users()
            user = users.get(user_id, get_default_user())
            fishing = user.get("fishing", {})

            fishing = validate_fishing_data(fishing)

            user["fishing"] = fishing
            users[user_id] = user
            await save_users(users)

            return fishing
        except Exception as e:
            logger.error(f"Ошибка загрузки данных рыбалки для {user_id}: {e}")
            return get_default_fishing_data()

    async def save_fishing_data(user_id: str, fishing_data: dict):
        """Сохраняет данные рыбалки пользователя"""
        try:
            users = await load_users()
            user = users.get(user_id, get_default_user())
            user["fishing"] = fishing_data
            users[user_id] = user
            await save_users(users)
        except Exception as e:
            logger.error(f"Ошибка сохранения данных рыбалки: {e}")

    async def get_fishing_inventory(user_id: str) -> list:
        """Получает инвентарь приманок"""
        try:
            inventory = await load_inventory()
            return inventory.get(user_id, [])
        except Exception as e:
            logger.error(f"Ошибка загрузки инвентаря: {e}")
            return []

    async def add_to_inventory(user_id: str, item: str):
        """Добавляет предмет в инвентарь"""
        try:
            inventory = await load_inventory()
            if user_id not in inventory:
                inventory[user_id] = []
            inventory[user_id].append(item)
            await save_inventory(inventory)
        except Exception as e:
            logger.error(f"Ошибка добавления в инвентарь: {e}")

    async def remove_from_inventory(user_id: str, item: str) -> bool:
        """Удаляет предмет из инвентаря"""
        try:
            inventory = await load_inventory()
            if user_id not in inventory:
                return False
            if item in inventory[user_id]:
                inventory[user_id].remove(item)
                await save_inventory(inventory)
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка удаления из инвентаря: {e}")
            return False

    def get_fish(rod_key: str, bait_bonus: int = 0) -> dict:
        """Ловит рыбу с учётом приманки"""
        fish_list = FISH_DATA.get(rod_key, FISH_DATA["basic"])

        if not fish_list:
            logger.error(f"Нет рыб для удочки: {rod_key}")
            return {"name": "Неизвестная рыба", "price": 0, "chance": 100}

        modified_fish_list = []

        for fish in fish_list:
            base_chance = fish["chance"]

            if base_chance < 10:
                modified_chance = base_chance * (1 + bait_bonus / 100)
            elif base_chance < 30:
                modified_chance = base_chance * (1 + bait_bonus / 200)
            else:
                modified_chance = base_chance * (1 + bait_bonus / 300)

            modified_fish_list.append({
                "name": fish["name"],
                "price": fish["price"],
                "chance": modified_chance
            })

        total_chance = sum(f["chance"] for f in modified_fish_list)

        if total_chance <= 0:
            logger.error(f"Ошибка шансов для удочки {rod_key}")
            return modified_fish_list[0]

        for fish in modified_fish_list:
            fish["chance"] = (fish["chance"] / total_chance) * 100

        roll = random.random() * 100
        cumulative = 0.0

        for fish in modified_fish_list:
            cumulative += fish["chance"]
            if roll <= cumulative:
                return fish

        logger.warning(f"Резервная рыба для {rod_key}")
        return modified_fish_list[-1]

    # ==========================================
    # ===== ГЛАВНОЕ МЕНЮ РЫБАЛКИ =====
    # ==========================================

    @dp.callback_query(F.data == "work_fishing")
    async def fishing_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return

        if await is_function_disabled("job_5"):
            await callback.answer("⛔ Эта работа остановлена администратором!", show_alert=True)
            return

        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)

            rod_key = fishing.get("rod", "basic")
            rod = FISHING_RODS.get(rod_key, FISHING_RODS["basic"])
            tackle_key = fishing.get("tackle", "basic")
            tackle = FISHING_TACKLE.get(tackle_key, FISHING_TACKLE["basic"])
            bait_name_display = fishing.get("bait") or "Не выбрана"

            warning = ""
            if tackle_key != rod_key:
                warning = (
                    f"\n⛔ **Нельзя рыбачить!** Снасть не подходит к удочке "
                    f"(нужна «{FISHING_TACKLE.get(rod_key, FISHING_TACKLE['basic'])['name']}»).\n"
                )
            elif rod_key != "basic" and not fishing.get("bait"):
                warning = "\n⛔ **Нельзя рыбачить!** Не выбрана приманка.\n"

            text = (
                f"🎣 **РЫБАЛКА**\n\n"
                f"🎣 Удочка: {rod['emoji']} {rod['name']}\n"
                f"   🎯 Шанс: {rod['base_chance']}%\n"
                f"   🐟 Рыб за раз: {rod.get('fish_per_cast', 1)}\n"
                f"🔧 Снасть: {tackle['emoji']} {tackle['name']}\n"
                f"   💥 Шанс поломки: {int(tackle.get('break_chance', 0) * 100)}%\n"
                f"🐛 Приманка: {bait_name_display}\n"
                f"{warning}"
                f"🐟 Поймано рыб: {fishing.get('fish_caught', 0)}\n"
                f"📦 Всего рыб: {fishing.get('total_fish', 0)}\n\n"
                f"Выберите действие:"
            )

            keyboard = [
                [InlineKeyboardButton(text="🎣 Рыбачить", callback_data="fishing_cast")],
                [InlineKeyboardButton(text="🏪 Магазин", callback_data="fishing_shop")],
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="fishing_settings")],
                [InlineKeyboardButton(text="📊 Статистика", callback_data="fishing_stats")],
                [InlineKeyboardButton(text="ℹ️ Информация", callback_data="fishing_info")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="works")]
            ]

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_menu: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== РЫБАЧИТЬ =====
    # ==========================================

    @dp.callback_query(F.data == "fishing_cast")
    async def fishing_cast(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)

            rod_key = fishing.get("rod", "basic")
            rod = FISHING_RODS.get(rod_key, FISHING_RODS["basic"])
            tackle_key = fishing.get("tackle", "basic")
            bait_name = fishing.get("bait")

            # ===== Проверка: снасть должна соответствовать удочке =====
            # У каждой удочки есть своя "родная" снасть (ключи совпадают).
            # Если снасть не подходит к текущей удочке - рыбачить нельзя.
            if tackle_key != rod_key:
                required_tackle = FISHING_TACKLE.get(rod_key, FISHING_TACKLE["basic"])
                await callback.answer(
                    f"⛔ Нельзя рыбачить!\n\n"
                    f"🎣 {rod['name']} требует снасть «{required_tackle['emoji']} {required_tackle['name']}».\n"
                    f"Смените снасть в Настройках/Магазине.",
                    show_alert=True
                )
                return

            # ===== Проверка: без приманки нельзя рыбачить (кроме бесплатной удочки) =====
            if rod_key != "basic" and not bait_name:
                await callback.answer(
                    "⛔ Без приманки рыбачить нельзя!\n\n"
                    "Выберите приманку в Настройках (Магазин → Приманки).",
                    show_alert=True
                )
                return

            # ===== Проверка: приманка должна подходить к текущей удочке =====
            if bait_name:
                bait_category = get_bait_category(bait_name)
                if bait_category != rod_key:
                    fishing["bait"] = None
                    await save_fishing_data(user_id, fishing)
                    await callback.answer(
                        f"⛔ Эта приманка не подходит для «{rod['name']}»!\n\n"
                        f"Нужна приманка категории «{rod['emoji']} {rod['name']}». "
                        f"Приманка снята, выберите подходящую.",
                        show_alert=True
                    )
                    return

            # Проверка снасти на поломку (5%)
            tackle = FISHING_TACKLE.get(tackle_key, FISHING_TACKLE["basic"])
            break_chance = tackle.get("break_chance", 0)
            
            tackle_broken = False
            if break_chance > 0 and random.random() < break_chance:
                tackle_broken = True
                # Удаляем снасть у пользователя
                if "tackles" in fishing and tackle_key in fishing["tackles"]:
                    del fishing["tackles"][tackle_key]
                # Сбрасываем на базовую снасть
                fishing["tackle"] = "basic"
                await save_fishing_data(user_id, fishing)

            # Проверяем приманку
            bait_bonus = 0
            bait_available = 0
            if bait_name:
                inventory = await get_fishing_inventory(user_id)
                bait_item = f"Приманка: {bait_name}"
                bait_available = inventory.count(bait_item)

                if bait_available <= 0:
                    fishing["bait"] = None
                    await save_fishing_data(user_id, fishing)
                    await callback.answer("❌ У вас нет выбранной приманки!", show_alert=True)
                    return

                bait_bonus = get_bait_bonus(bait_name)
                if bait_bonus == 0:
                    fishing["bait"] = None
                    await save_fishing_data(user_id, fishing)
                    await callback.answer("⚠️ Приманка повреждена, выбор отменён.", show_alert=True)
                    return

            # Количество рыб за одну рыбалку
            fish_per_cast = rod.get("fish_per_cast", 1)
            catch_chance = rod["base_chance"] + bait_bonus
            catch_chance = min(catch_chance, 100)

            caught_fish = []
            total_price = 0
            bait_spent = 0
            ran_out_of_bait = False

            for _ in range(fish_per_cast):
                # Если приманка обязательна (не базовая удочка) и закончилась - дальше ловить нельзя
                if rod_key != "basic" and bait_name and bait_available - bait_spent <= 0:
                    ran_out_of_bait = True
                    break

                roll = random.randint(1, 100)

                if roll <= catch_chance:
                    fish = get_fish(rod_key, bait_bonus)
                    await add_to_inventory(user_id, fish["name"])
                    caught_fish.append(fish)
                    total_price += fish["price"]

                    fishing["fish_caught"] = fishing.get("fish_caught", 0) + 1
                    fishing["total_fish"] = fishing.get("total_fish", 0) + 1

                    if "fish_inventory" not in fishing:
                        fishing["fish_inventory"] = {}
                    fishing["fish_inventory"][fish["name"]] = fishing["fish_inventory"].get(fish["name"], 0) + 1

                    # Тратим 1 приманку ИМЕННО за 1 пойманную рыбу
                    if bait_name and bait_available - bait_spent > 0:
                        await remove_from_inventory(user_id, bait_item)
                        bait_spent += 1

                        # Если приманка закончилась после этой поимки - дальше без бонуса (для базовой)
                        # или прекращаем (для остальных удочек, проверяется в начале следующей итерации)
                        if bait_available - bait_spent <= 0:
                            bait_bonus = 0
                            catch_chance = rod["base_chance"]

            # Если приманка закончилась полностью - снимаем её с выбора
            bait_fully_used = bool(bait_name) and (bait_available - bait_spent <= 0)
            if bait_fully_used:
                fishing["bait"] = None

            await save_fishing_data(user_id, fishing)

            # Формируем сообщение
            bonus_text = f" (+{bait_bonus}% от приманки)" if bait_bonus > 0 else ""
            tackle_break_text = "\n\n💥 **СНАСТЬ СЛОМАЛАСЬ!**\nПридётся купить новую в магазине." if tackle_broken else ""
            bait_spent_text = f"\n🐛 Потрачено приманки: {bait_spent} шт." if bait_spent > 0 else ""
            bait_out_text = ""
            if ran_out_of_bait:
                bait_out_text = "\n\n⚠️ Приманка закончилась во время рыбалки, дальнейшие забросы прерваны."
            elif bait_fully_used:
                bait_out_text = "\n\n⚠️ Приманка закончилась! Выберите новую в Настройках."

            if caught_fish:
                fish_text = "\n".join([f"🐟 {f['name']} ({f['price']:,.0f}₽)" for f in caught_fish])
                text = (
                    f"🎣 **УЛОВ!**\n\n"
                    f"{fish_text}\n\n"
                    f"💰 Всего: {total_price:,.0f}₽\n"
                    f"📊 Шанс поимки: {catch_chance}%{bonus_text}"
                    f"{bait_spent_text}"
                    f"{tackle_break_text}"
                    f"{bait_out_text}"
                )
            else:
                text = (
                    f"🎣 **НИЧЕГО НЕ ПОЙМАЛИ!**\n\n"
                    f"😔 Рыба ушла...\n"
                    f"📊 Шанс поимки: {catch_chance}%{bonus_text}"
                    f"{bait_spent_text}"
                    f"{tackle_break_text}"
                    f"{bait_out_text}"
                )

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎣 Рыбачить ещё", callback_data="fishing_cast")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="work_fishing")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_cast: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== МАГАЗИН =====
    # ==========================================

    @dp.callback_query(F.data == "fishing_shop")
    async def fishing_shop(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            keyboard = [
                [InlineKeyboardButton(text="🎣 Удочки", callback_data="fishing_rods")],
                [InlineKeyboardButton(text="🔧 Снасти", callback_data="fishing_tackle_shop")],
                [InlineKeyboardButton(text="🐛 Приманки", callback_data="fishing_baits_menu")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="work_fishing")]
            ]

            await callback.message.edit_text(
                "🏪 **МАГАЗИН РЫБАЛКИ**\n\nВыберите категорию:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_shop: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== УДОЧКИ =====
    # ==========================================

    @dp.callback_query(F.data == "fishing_rods")
    async def fishing_rods(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            current_rod = fishing.get("rod", "basic")

            text = "🎣 **УДОЧКИ (МАГАЗИН)**\n\n_Здесь можно только покупать. Менять активную удочку — в Настройках._\n\n"
            keyboard = []

            for key, rod in FISHING_RODS.items():
                is_owned = fishing.get("rods", {}).get(key, False) or key == "basic"
                is_current = key == current_rod

                status = "✅ ВЫБРАНА" if is_current else "✅ Куплена" if is_owned else "❌ Нет"
                text += f"{rod['emoji']} {rod['name']} - {status}\n"
                text += f"   🎯 Шанс: {rod['base_chance']}%\n"
                text += f"   🐟 Рыб за раз: {rod.get('fish_per_cast', 1)}\n"

                if key != "basic":
                    criteria = rod.get("criteria", {})
                    if "fish_caught" in criteria:
                        text += f"   🐟 Нужно поймать: {criteria['fish_caught']} рыб\n"
                    text += f"   💰 Цена: {rod['price']:,.0f}₽\n"

                text += "\n"

                if not is_owned and key != "basic":
                    fish_caught = fishing.get("fish_caught", 0)
                    required = rod.get("criteria", {}).get("fish_caught", 0)
                    if fish_caught >= required:
                        keyboard.append([InlineKeyboardButton(
                            text=f"💰 Купить {rod['emoji']} {rod['name']} ({rod['price']:,.0f}₽)",
                            callback_data=f"fsh_buy_rod_{key}"
                        )])
                    else:
                        text_btn = f"🔒 {rod['name']} (нужно {required} рыб)"
                        keyboard.append([InlineKeyboardButton(
                            text=text_btn,
                            callback_data="fishing_rods_locked"
                        )])

            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_shop")])

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_rods: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data == "fishing_rods_locked")
    async def fishing_rods_locked(callback: types.CallbackQuery):
        await callback.answer("🔒 Недостаточно пойманных рыб!", show_alert=True)

    @dp.callback_query(F.data.startswith("fsh_sel_rod_"))
    async def fishing_select_rod(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            rod_key = callback.data.replace("fsh_sel_rod_", "")
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)

            if not fishing.get("rods", {}).get(rod_key, False) and rod_key != "basic":
                await callback.answer("❌ У вас нет этой удочки!", show_alert=True)
                return

            fishing["rod"] = rod_key
            await save_fishing_data(user_id, fishing)

            rod = FISHING_RODS.get(rod_key, FISHING_RODS["basic"])
            await callback.answer(f"✅ Выбрана {rod['name']}!", show_alert=True)

            await fishing_settings_rods(callback)
        except Exception as e:
            logger.error(f"Ошибка в fishing_select_rod: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data.startswith("fsh_buy_rod_"))
    async def fishing_buy_rod(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            rod_key = callback.data.replace("fsh_buy_rod_", "")
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            fishing = await get_fishing_data(user_id)

            rod = FISHING_RODS.get(rod_key)
            if not rod:
                await callback.answer("❌ Удочка не найдена!", show_alert=True)
                return

            if fishing.get("rods", {}).get(rod_key, False):
                await callback.answer("❌ Удочка уже куплена!", show_alert=True)
                return

            if user["money"] < rod["price"]:
                await callback.answer(
                    f"❌ Недостаточно средств!\nНужно: {rod['price']:,.0f}₽\nЕсть: {user['money']:,.0f}₽",
                    show_alert=True
                )
                return

            user["money"] -= rod["price"]
            users[user_id] = user

            if "rods" not in fishing:
                fishing["rods"] = {}
            fishing["rods"][rod_key] = True

            await save_users(users)
            await save_fishing_data(user_id, fishing)

            await callback.answer(f"✅ Куплена {rod['name']}!", show_alert=True)
            await fishing_rods(callback)
        except Exception as e:
            logger.error(f"Ошибка в fishing_buy_rod: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== СНАСТИ =====
    # ==========================================

    @dp.callback_query(F.data == "fishing_tackle_shop")
    async def fishing_tackle_shop(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            current_tackle = fishing.get("tackle", "basic")
            current_rod = fishing.get("rod", "basic")

            text = "🔧 **СНАСТИ (МАГАЗИН)**\n\n_Здесь можно только покупать. Менять активную снасть — в Настройках._\n\n"
            keyboard = []

            for key, tackle in FISHING_TACKLE.items():
                is_owned = fishing.get("tackles", {}).get(key, False) or key == "basic"
                is_current = key == current_tackle

                status = "✅ ВЫБРАНА" if is_current else "✅ Куплена" if is_owned else "❌ Нет"
                text += f"{tackle['emoji']} {tackle['name']} - {status}\n"
                text += f"   💥 Шанс поломки: {int(tackle.get('break_chance', 0) * 100)}%\n"

                if key != "basic":
                    criteria = tackle.get("criteria", {})
                    if "rod" in criteria:
                        rod_needed = FISHING_RODS.get(criteria["rod"], {}).get("name", "Неизвестно")
                        text += f"   🎣 Нужна: {rod_needed}\n"
                    text += f"   💰 Цена: {tackle['price']:,.0f}₽\n"

                text += "\n"

                if not is_owned and key != "basic":
                    can_buy = False
                    if "rod" in tackle.get("criteria", {}):
                        required_rod = tackle["criteria"]["rod"]
                        if fishing.get("rods", {}).get(required_rod, False) or current_rod == required_rod:
                            can_buy = True
                    elif "default" in tackle.get("criteria", {}):
                        can_buy = True

                    if can_buy:
                        keyboard.append([InlineKeyboardButton(
                            text=f"💰 Купить {tackle['emoji']} {tackle['name']} ({tackle['price']:,.0f}₽)",
                            callback_data=f"fsh_buy_tck_{key}"
                        )])
                    else:
                        keyboard.append([InlineKeyboardButton(
                            text=f"🔒 {tackle['name']} (нужна удочка)",
                            callback_data="fishing_tackle_locked"
                        )])

            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_shop")])

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_tackle_shop: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data == "fishing_tackle_locked")
    async def fishing_tackle_locked(callback: types.CallbackQuery):
        await callback.answer("🔒 Сначала купите нужную удочку!", show_alert=True)

    @dp.callback_query(F.data.startswith("fsh_sel_tck_"))
    async def fishing_select_tackle(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            tackle_key = callback.data.replace("fsh_sel_tck_", "")
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)

            if not fishing.get("tackles", {}).get(tackle_key, False) and tackle_key != "basic":
                await callback.answer("❌ У вас нет этой снасти!", show_alert=True)
                return

            fishing["tackle"] = tackle_key
            await save_fishing_data(user_id, fishing)

            tackle = FISHING_TACKLE.get(tackle_key, FISHING_TACKLE["basic"])
            await callback.answer(f"✅ Выбрана {tackle['name']}!", show_alert=True)

            await fishing_settings_tackle(callback)
        except Exception as e:
            logger.error(f"Ошибка в fishing_select_tackle: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data.startswith("fsh_buy_tck_"))
    async def fishing_buy_tackle(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            tackle_key = callback.data.replace("fsh_buy_tck_", "")
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            fishing = await get_fishing_data(user_id)

            tackle = FISHING_TACKLE.get(tackle_key)
            if not tackle:
                await callback.answer("❌ Снасть не найдена!", show_alert=True)
                return

            if fishing.get("tackles", {}).get(tackle_key, False):
                await callback.answer("❌ Снасть уже куплена!", show_alert=True)
                return

            if user["money"] < tackle["price"]:
                await callback.answer(
                    f"❌ Недостаточно средств!\nНужно: {tackle['price']:,.0f}₽\nЕсть: {user['money']:,.0f}₽",
                    show_alert=True
                )
                return

            user["money"] -= tackle["price"]
            users[user_id] = user

            if "tackles" not in fishing:
                fishing["tackles"] = {}
            fishing["tackles"][tackle_key] = True

            await save_users(users)
            await save_fishing_data(user_id, fishing)

            await callback.answer(f"✅ Куплена {tackle['name']}!", show_alert=True)
            await fishing_tackle_shop(callback)
        except Exception as e:
            logger.error(f"Ошибка в fishing_buy_tackle: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== ПРИМАНКИ =====
    # ==========================================

    @dp.callback_query(F.data == "fishing_baits_menu")
    async def fishing_baits_menu(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            keyboard = [
                [InlineKeyboardButton(text="🚀 Галактические", callback_data="fsh_bcat_galactic")],
                [InlineKeyboardButton(text="🌋 Вулканические", callback_data="fsh_bcat_volcanic")],
                [InlineKeyboardButton(text="⭐ Легендарные", callback_data="fsh_bcat_legendary")],
                [InlineKeyboardButton(text="🔮 Редкие", callback_data="fsh_bcat_rare")],
                [InlineKeyboardButton(text="🎣 Базовые", callback_data="fsh_bcat_basic")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_shop")]
            ]

            await callback.message.edit_text(
                "🐛 **ПРИМАНКИ**\n\nВыберите категорию:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_baits_menu: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data.startswith("fsh_bcat_"))
    async def fishing_baits_category(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            category = callback.data.replace("fsh_bcat_", "")

            if category not in FISHING_BAITS:
                logger.error(f"Неизвестная категория приманок: {category}")
                await callback.answer("❌ Неизвестная категория!", show_alert=True)
                return

            baits = FISHING_BAITS[category]

            if not baits:
                await callback.answer("❌ Нет приманок в этой категории!", show_alert=True)
                return

            user_id = str(callback.from_user.id)
            inventory = await get_fishing_inventory(user_id)

            bait_counts = {}
            for item in inventory:
                if item.startswith("Приманка: "):
                    bait_name = item.replace("Приманка: ", "")
                    bait_counts[bait_name] = bait_counts.get(bait_name, 0) + 1

            category_names = {
                "galactic": "🚀 ГАЛАКТИЧЕСКИЕ",
                "volcanic": "🌋 ВУЛКАНИЧЕСКИЕ",
                "legendary": "⭐ ЛЕГЕНДАРНЫЕ",
                "rare": "🔮 РЕДКИЕ",
                "basic": "🎣 БАЗОВЫЕ"
            }

            text = f"🐛 **{category_names.get(category, category.upper())} ПРИМАНКИ**\n\n"
            keyboard = []

            for idx, bait in enumerate(baits):
                count = bait_counts.get(bait["name"], 0)
                count_text = f" [в инв: {count}]" if count > 0 else ""
                text += f"• {bait['name']}{count_text}\n"
                text += f"   💰 Цена: {bait['price']:,.0f}₽\n"
                text += f"   📈 Бонус: +{bait['bonus']}%\n\n"

                callback_data = f"fsh_bopt_{category}_{idx}"
                keyboard.append([InlineKeyboardButton(
                    text=f"🛒 {bait['name']} ({bait['price']:,.0f}₽)",
                    callback_data=callback_data
                )])

            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_baits_menu")])

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_baits_category: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    def _get_category_and_bait(category: str, bait_index: int):
        """Возвращает (category, bait) либо (None, None), если что-то не так"""
        if category not in FISHING_BAITS:
            return None, None
        baits = FISHING_BAITS[category]
        if bait_index < 0 or bait_index >= len(baits):
            return None, None
        return category, baits[bait_index]

    async def _do_buy_bait(user_id: str, bait: dict, quantity: int):
        """
        Покупает quantity штук приманки bait для пользователя user_id.
        Возвращает (success: bool, error_text: str|None, new_balance: float|None)
        """
        price_total = bait["price"] * quantity
        bait_name = bait["name"]

        users = await load_users()
        user = users.get(user_id, get_default_user())

        if user["money"] < price_total:
            return False, (
                f"❌ Недостаточно средств!\n"
                f"Нужно: {price_total:,.0f}₽ (за {quantity} шт.)\n"
                f"Есть: {user['money']:,.0f}₽"
            ), None

        user["money"] -= price_total
        users[user_id] = user
        await save_users(users)

        for _ in range(quantity):
            await add_to_inventory(user_id, f"Приманка: {bait_name}")

        return True, None, user["money"]

    @dp.callback_query(F.data.startswith("fsh_bopt_"))
    async def fishing_bait_options(callback: types.CallbackQuery):
        """Меню действий для конкретной приманки: купить 1 / ввести число / назад"""
        if not await check_access(callback):
            return

        try:
            data = callback.data.replace("fsh_bopt_", "")
            parts = data.rsplit("_", 1)
            if len(parts) != 2:
                await callback.answer("❌ Ошибка!", show_alert=True)
                return

            category, bait_index_raw = parts
            try:
                bait_index = int(bait_index_raw)
            except ValueError:
                await callback.answer("❌ Ошибка!", show_alert=True)
                return

            category, bait = _get_category_and_bait(category, bait_index)
            if not bait:
                await callback.answer("❌ Приманка не найдена!", show_alert=True)
                return

            user_id = str(callback.from_user.id)
            inventory = await get_fishing_inventory(user_id)
            count = inventory.count(f"Приманка: {bait['name']}")

            text = (
                f"🐛 **{bait['name']}**\n\n"
                f"💰 Цена за штуку: {bait['price']:,.0f}₽\n"
                f"📈 Бонус: +{bait['bonus']}%\n"
                f"📦 У вас сейчас: {count} шт.\n\n"
                f"Выберите действие:"
            )

            keyboard = [
                [InlineKeyboardButton(text="1️⃣ Купить 1 штуку", callback_data=f"fsh_bbuy1_{category}_{bait_index}")],
                [InlineKeyboardButton(text="🔢 Ввести своё число", callback_data=f"fsh_bcustom_{category}_{bait_index}")],
                [InlineKeyboardButton(text="🔙 Назад в магазин", callback_data=f"fsh_bcat_{category}")]
            ]

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_bait_options: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data.startswith("fsh_bbuy1_"))
    async def fishing_buy_bait_one(callback: types.CallbackQuery):
        """Покупка ровно 1 штуки приманки"""
        if not await check_access(callback):
            return

        try:
            data = callback.data.replace("fsh_bbuy1_", "")
            parts = data.rsplit("_", 1)
            if len(parts) != 2:
                await callback.answer("❌ Ошибка при покупке!", show_alert=True)
                return

            category, bait_index_raw = parts
            try:
                bait_index = int(bait_index_raw)
            except ValueError:
                await callback.answer("❌ Ошибка при покупке!", show_alert=True)
                return

            category, bait = _get_category_and_bait(category, bait_index)
            if not bait:
                await callback.answer("❌ Приманка не найдена!", show_alert=True)
                return

            user_id = str(callback.from_user.id)
            success, error_text, new_balance = await _do_buy_bait(user_id, bait, 1)

            if not success:
                await callback.answer(error_text, show_alert=True)
                return

            await callback.answer(
                f"✅ Куплена: {bait['name']} x1!\n💰 Осталось: {new_balance:,.0f}₽",
                show_alert=True
            )

            await fishing_bait_options(callback)
        except Exception as e:
            logger.error(f"Ошибка в fishing_buy_bait_one: {e}", exc_info=True)
            await callback.answer("⚠️ Критическая ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data.startswith("fsh_bcustom_"))
    async def fishing_buy_bait_custom_start(callback: types.CallbackQuery, state: FSMContext):
        """Запрашивает у пользователя количество приманки для покупки"""
        if not await check_access(callback):
            return

        try:
            data = callback.data.replace("fsh_bcustom_", "")
            parts = data.rsplit("_", 1)
            if len(parts) != 2:
                await callback.answer("❌ Ошибка!", show_alert=True)
                return

            category, bait_index_raw = parts
            try:
                bait_index = int(bait_index_raw)
            except ValueError:
                await callback.answer("❌ Ошибка!", show_alert=True)
                return

            category, bait = _get_category_and_bait(category, bait_index)
            if not bait:
                await callback.answer("❌ Приманка не найдена!", show_alert=True)
                return

            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            max_affordable = int(user["money"] // bait["price"]) if bait["price"] > 0 else 0

            await state.clear()

            sent = await callback.message.edit_text(
                f"🔢 **ВВОД КОЛИЧЕСТВА**\n\n"
                f"🐛 Приманка: {bait['name']}\n"
                f"💰 Цена за штуку: {bait['price']:,.0f}₽\n"
                f"💳 Ваш баланс: {user['money']:,.0f}₽\n"
                f"📈 Максимум можно купить: {max_affordable} шт.\n\n"
                f"✏️ Напишите в чат количество штук для покупки.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отмена", callback_data=f"fsh_bopt_{category}_{bait_index}")]
                ]),
                parse_mode="Markdown"
            )

            await state.update_data(
                bait_category=category,
                bait_index=bait_index,
                bait_menu_chat_id=callback.message.chat.id,
                bait_menu_message_id=callback.message.message_id
            )
            await state.set_state(FishingStates.waiting_for_bait_quantity)
        except Exception as e:
            logger.error(f"Ошибка в fishing_buy_bait_custom_start: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.message(FishingStates.waiting_for_bait_quantity)
    async def fishing_buy_bait_custom_amount(message: types.Message, state: FSMContext):
        """Обрабатывает введённое пользователем количество приманки и покупает её"""
        try:
            if not await check_access(message):
                await state.clear()
                return

            user_id = str(message.from_user.id)
            state_data = await state.get_data()
            category = state_data.get("bait_category")
            bait_index = state_data.get("bait_index")

            category, bait = _get_category_and_bait(category, bait_index) if category is not None else (None, None)
            if not bait:
                await state.clear()
                await message.answer(
                    "❌ Приманка не найдена! Откройте магазин заново.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 В магазин", callback_data="fishing_baits_menu")]
                    ])
                )
                return

            raw = message.text.strip().replace(" ", "").replace(",", "")

            if not raw.isdigit() or int(raw) <= 0:
                await message.answer(
                    "❌ Введите корректное положительное число!\nНапример: 1, 5, 10",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"fsh_bopt_{category}_{bait_index}")]
                    ])
                )
                return

            quantity = int(raw)

            success, error_text, new_balance = await _do_buy_bait(user_id, bait, quantity)

            menu_chat_id = state_data.get("bait_menu_chat_id")
            menu_message_id = state_data.get("bait_menu_message_id")

            if not success:
                await message.answer(
                    error_text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔢 Попробовать снова", callback_data=f"fsh_bcustom_{category}_{bait_index}")],
                        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"fsh_bopt_{category}_{bait_index}")]
                    ])
                )
                return

            await state.clear()

            if menu_chat_id and menu_message_id:
                try:
                    await bot.delete_message(chat_id=menu_chat_id, message_id=menu_message_id)
                except Exception as close_err:
                    logger.warning(f"Не удалось закрыть меню покупки приманки: {close_err}")

            await message.answer(
                f"✅ **Куплено: {bait['name']} x{quantity}!**\n\n"
                f"💰 Потрачено: {bait['price'] * quantity:,.0f}₽\n"
                f"💳 Остаток: {new_balance:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🛒 Купить ещё", callback_data=f"fsh_bopt_{category}_{bait_index}")],
                    [InlineKeyboardButton(text="🔙 В магазин", callback_data="fishing_baits_menu")],
                    [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_main")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Критическая ошибка покупки приманки: {e}", exc_info=True)
            await state.clear()
            await message.answer(
                "⚠️ Произошла ошибка при покупке!\nПопробуйте позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 В магазин", callback_data="fishing_baits_menu")]
                ])
            )

    # ==========================================
    # ===== НАСТРОЙКИ =====
    # ==========================================

    @dp.callback_query(F.data == "fishing_settings")
    async def fishing_settings(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)

            rod_key = fishing.get("rod", "basic")
            rod = FISHING_RODS.get(rod_key, FISHING_RODS["basic"])
            tackle_key = fishing.get("tackle", "basic")
            tackle = FISHING_TACKLE.get(tackle_key, FISHING_TACKLE["basic"])
            current_bait = fishing.get("bait") or "Не выбрана"

            text = (
                f"⚙️ **НАСТРОЙКИ РЫБАЛКИ**\n\n"
                f"🎣 Удочка: {rod['emoji']} {rod['name']}\n"
                f"🔧 Снасть: {tackle['emoji']} {tackle['name']}\n"
                f"🐛 Приманка: {current_bait}\n\n"
                f"Выберите раздел, чтобы сменить экипировку "
                f"среди уже приобретённого:"
            )

            keyboard = [
                [InlineKeyboardButton(text="🎣 Удочки", callback_data="fishing_settings_rods")],
                [InlineKeyboardButton(text="🔧 Снасти", callback_data="fishing_settings_tackle")],
                [InlineKeyboardButton(text="🐛 Приманки", callback_data="fishing_settings_baits")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="work_fishing")]
            ]

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_settings: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ----- Настройки: Удочки (выбор среди купленных) -----

    @dp.callback_query(F.data == "fishing_settings_rods")
    async def fishing_settings_rods(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            current_rod = fishing.get("rod", "basic")

            text = "🎣 **УДОЧКИ — НАСТРОЙКИ**\n\n_Выберите удочку среди уже приобретённых:_\n\n"
            keyboard = []

            owned_rods = [key for key in FISHING_RODS
                          if key == "basic" or fishing.get("rods", {}).get(key, False)]

            for key in owned_rods:
                rod = FISHING_RODS[key]
                is_current = key == current_rod
                status = "✅ ВЫБРАНА" if is_current else "📦 В наличии"
                text += f"{rod['emoji']} {rod['name']} - {status}\n"

                if not is_current:
                    keyboard.append([InlineKeyboardButton(
                        text=f"📌 Выбрать {rod['emoji']} {rod['name']}",
                        callback_data=f"fsh_sel_rod_{key}"
                    )])

            if len(owned_rods) <= 1:
                text += "\n_У вас пока нет других удочек. Купите их в Магазине._"

            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_settings")])

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_settings_rods: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ----- Настройки: Снасти (выбор среди купленных) -----

    @dp.callback_query(F.data == "fishing_settings_tackle")
    async def fishing_settings_tackle(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            current_tackle = fishing.get("tackle", "basic")

            text = "🔧 **СНАСТИ — НАСТРОЙКИ**\n\n_Выберите снасть среди уже приобретённых:_\n\n"
            keyboard = []

            owned_tackles = [key for key in FISHING_TACKLE
                              if key == "basic" or fishing.get("tackles", {}).get(key, False)]

            for key in owned_tackles:
                tackle = FISHING_TACKLE[key]
                is_current = key == current_tackle
                status = "✅ ВЫБРАНА" if is_current else "📦 В наличии"
                text += f"{tackle['emoji']} {tackle['name']} - {status}\n"

                if not is_current:
                    keyboard.append([InlineKeyboardButton(
                        text=f"📌 Выбрать {tackle['emoji']} {tackle['name']}",
                        callback_data=f"fsh_sel_tck_{key}"
                    )])

            if len(owned_tackles) <= 1:
                text += "\n_У вас пока нет других снастей. Купите их в Магазине._"

            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_settings")])

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_settings_tackle: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ----- Настройки: Приманки (выбор активной приманки) -----

    @dp.callback_query(F.data == "fishing_settings_baits")
    async def fishing_settings_baits(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)

            rod_key = fishing.get("rod", "basic")
            rod = FISHING_RODS.get(rod_key, FISHING_RODS["basic"])
            current_bait = fishing.get("bait") or "Не выбрана"

            inventory = await get_fishing_inventory(user_id)

            bait_counts = {}
            for item in inventory:
                if item.startswith("Приманка: "):
                    bait_name = item.replace("Приманка: ", "")
                    # Показываем только приманки, подходящие к текущей удочке
                    if get_bait_category(bait_name) == rod_key:
                        bait_counts[bait_name] = bait_counts.get(bait_name, 0) + 1

            unique_baits = list(bait_counts.keys())

            text = (
                f"🐛 **ПРИМАНКИ — НАСТРОЙКИ**\n\n"
                f"🎣 Удочка: {rod['emoji']} {rod['name']}\n"
                f"🐛 Текущая приманка: {current_bait}\n"
                f"📦 Подходящих приманок: {len(unique_baits)}\n\n"
                f"Выберите приманку для следующей рыбалки "
                f"(подходят только приманки категории «{rod['name']}»):"
            )

            keyboard = []

            if unique_baits:
                for idx, bait_name in enumerate(unique_baits[:10]):
                    is_selected = bait_name == fishing.get("bait")
                    count = bait_counts[bait_name]
                    keyboard.append([InlineKeyboardButton(
                        text=f"{'✅' if is_selected else '🐛'} {bait_name} (x{count})",
                        callback_data=f"fsh_sel_bait_{idx}"
                    )])
            else:
                if rod_key == "basic":
                    text += "\n_У вас нет приманок. Купите их в магазине._"
                else:
                    text += (
                        f"\n_У вас нет приманок категории «{rod['name']}». "
                        f"Без подходящей приманки рыбачить этой удочкой нельзя! "
                        f"Купите их в магазине._"
                    )

            if fishing.get("bait"):
                keyboard.append([InlineKeyboardButton(
                    text="❌ Снять приманку",
                    callback_data="fishing_remove_bait"
                )])

            keyboard.append([InlineKeyboardButton(
                text="🛒 Купить приманки",
                callback_data="fishing_baits_menu"
            )])
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_settings")])

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_settings_baits: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data.startswith("fsh_sel_bait_"))
    async def fishing_select_bait(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            bait_index = int(callback.data.replace("fsh_sel_bait_", ""))
            user_id = str(callback.from_user.id)

            fishing = await get_fishing_data(user_id)
            rod_key = fishing.get("rod", "basic")

            inventory = await get_fishing_inventory(user_id)

            bait_counts = {}
            for item in inventory:
                if item.startswith("Приманка: "):
                    bait_name = item.replace("Приманка: ", "")
                    # Та же фильтрация, что и в fishing_settings_baits, чтобы индексы совпадали
                    if get_bait_category(bait_name) == rod_key:
                        bait_counts[bait_name] = bait_counts.get(bait_name, 0) + 1

            unique_baits = list(bait_counts.keys())

            if bait_index >= len(unique_baits):
                await callback.answer("❌ Приманка не найдена!", show_alert=True)
                return

            bait_name = unique_baits[bait_index]

            fishing["bait"] = bait_name
            await save_fishing_data(user_id, fishing)

            await callback.answer(f"✅ Выбрана: {bait_name}!", show_alert=True)
            await fishing_settings_baits(callback)
        except (ValueError, Exception) as e:
            logger.error(f"Ошибка в fishing_select_bait: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data == "fishing_remove_bait")
    async def fishing_remove_bait(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            fishing["bait"] = None
            await save_fishing_data(user_id, fishing)

            await callback.answer("✅ Приманка снята!", show_alert=True)
            await fishing_settings_baits(callback)
        except Exception as e:
            logger.error(f"Ошибка в fishing_remove_bait: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== СТАТИСТИКА =====
    # ==========================================

    @dp.callback_query(F.data == "fishing_stats")
    async def fishing_stats(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)

            rod_key = fishing.get("rod", "basic")
            rod = FISHING_RODS.get(rod_key, FISHING_RODS["basic"])

            tackle_key = fishing.get("tackle", "basic")
            tackle = FISHING_TACKLE.get(tackle_key, FISHING_TACKLE["basic"])

            fish_inventory = fishing.get("fish_inventory", {})

            text = (
                f"📊 **СТАТИСТИКА РЫБАЛКИ**\n\n"
                f"🎣 Удочка: {rod['emoji']} {rod['name']}\n"
                f"🔧 Снасть: {tackle['emoji']} {tackle['name']}\n"
                f"🐟 Всего поймано: {fishing.get('total_fish', 0)}\n"
                f"📦 Разных рыб: {len(fish_inventory)}\n\n"
                f"**Топ-5 рыб:**\n"
            )

            sorted_fish = sorted(fish_inventory.items(), key=lambda x: x[1], reverse=True)[:5]
            if sorted_fish:
                for name, count in sorted_fish:
                    text += f"• {name}: {count} шт.\n"
            else:
                text += "• Нет рыб\n"

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="work_fishing")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_stats: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== ИНФОРМАЦИЯ =====
    # ==========================================

    @dp.callback_query(F.data == "fishing_info")
    async def fishing_info(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            text = (
                "ℹ️ **ИНФОРМАЦИЯ О РЫБАЛКЕ**\n\n"
                "**🎣 УДОЧКИ:**\n"
                "1. 🚀 Галактическая (95%) - 1500 рыб, 20B₽, 10 рыб/раз\n"
                "2. 🌋 Вулканическая (85%) - 750 рыб, 1.5B₽, 5 рыб/раз\n"
                "3. ⭐ Легендарная (70%) - 250 рыб, 500M₽, 3 рыбы/раз\n"
                "4. 🔮 Редкая (65%) - 50 рыб, 150M₽, 1 рыба/раз\n"
                "5. 🎣 Базовая (55%) - бесплатно, 1 рыба/раз\n\n"
                "**🔧 СНАСТИ:**\n"
                "• Каждой удочке нужна своя снасть того же типа "
                "(например, Галактической удочке - только Галактическая снасть)!\n"
                "• Если снасть не подходит к удочке - рыбачить нельзя ⛔\n"
                "• Есть 5% шанс поломки при рыбалке!\n"
                "• При поломке нужно покупать новую\n\n"
                "**🐛 ПРИМАНКИ (тратятся 1 раз):**\n"
                "• Для каждой удочки своя категория приманок!\n"
                "• Без приманки нельзя рыбачить (кроме Базовой удочки) ⛔\n"
                "• Увеличивают шанс редкой рыбы\n"
                "• Выбираются в настройках\n"
                "• Покупаются в магазине\n\n"
                "**🐟 РЫБЫ:**\n"
                "• Разные для каждой удочки\n"
                "• Редкие стоят дороже\n"
                "• Продаются у Скупщика"
            )

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="work_fishing")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_info: {e}", exc_info=True)
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()
