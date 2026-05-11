import telebot
import requests
from bs4 import BeautifulSoup
import re
import time

token = '8650394526:AAHhTIeXyapUlG2DfOHL9mOfhxy6b4d82VA'
bot = telebot.TeleBot(token)

currency_cache = {}

def parse_sravni_currencies():
    """Парсинг валют с сайта с защитой от ошибок"""
    if currency_cache:  # Если уже спарсили — возвращаем из кэша
        return currency_cache
    
    url = "https://www.sravni.ru/valjuty/info/spisok-valjut-mira/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Ищем таблицу (на сайте обычно одна основная таблица с валютами)
        table = soup.find("table")
        if not table:
            print("Таблица не найдена на сайте")
            return {}
        
        result = {}
        rows = table.find_all("tr")[1:]  # Пропускаем заголовок
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            
            # Левая ячейка: одна или несколько стран через <br>
            countries_raw = cells[0].get_text(separator="|").strip()
            currency = cells[1].get_text(strip=True)
            
            # Разбиваем страны, если их несколько в одной строке
            countries = [c.strip() for c in countries_raw.split("|") if c.strip()]
            
            for country in countries:
                # Нормализуем: нижний регистр, убираем лишние пробелы
                key = re.sub(r"\s+", " ", country.lower().strip())
                result[key] = currency
        
        currency_cache.update(result)  # Сохраняем в кэш
        print(f"Успешно спаршено {len(result)} валют")  # Отладка
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"Ошибка сети: {e}")
        return {}
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return {}
# Команда /start
@bot.message_handler(commands=["start"])
def send_welcome(message):
    user = message.from_user
    nik = f"@{user.username}"
    bot.reply_to(message, f"👋 Привет, {nik}! Бот запущен.")
    bot.reply_to(message, "Если вы здесь впервые, введите команду /help")
# Команда /help
@bot.message_handler(commands=["help"])
def send_help(message):
    bot.reply_to(message, "Данный бот позволяет вам узнать валюты мира!")
    bot.reply_to(message, "Для получении информации о том, в какой стране какая валюта используется в ходу, введите команду /валюта поставте пробел и введите название страны с большой буквы")
    bot.reply_to(message, "Пример: /валюта Россия")
# Команда /валюта
@bot.message_handler(commands=["валюта"])
def get_currence(message):
    try:
        print(f"Получена команда от {message.from_user.username}: {message.text}")  # Отладка
        
        # Извлекаем название страны из команды: "/валюта Россия" → "Россия"
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            bot.reply_to(message, "Укажите название страны.\nПример: `/валюта Япония`", parse_mode="Markdown")
            return
        
        country_input = args[1].strip()
        country_key = re.sub(r"\s+", " ", country_input.lower())
        
        # Отвечаем, что начали поиск (чтобы пользователь не ждал в тишине)
        bot.reply_to(message, f" Ищу валюту для страны '{country_input}'...")
        
        # Парсим (или берём из кэша)
        currencies = parse_sravni_currencies()
        
        if not currencies:
            bot.reply_to(message, "Не удалось загрузить данные. Проверьте подключение к интернету или попробуйте позже.")
            return
        
        # Точный поиск
        if country_key in currencies:
            currency = currencies[country_key]
            bot.reply_to(message, f"✅ {country_input} → **{currency}**", parse_mode="Markdown")
            return
        
        # Нечёткий поиск: если точного совпадения нет, ищем подстроку
        matches = [c for c in currencies.keys() if country_key in c or c in country_key]
        
        if matches:
            # Берём первый наиболее подходящий вариант
            best_match = matches[0]
            original_name = best_match.title()  # Возвращаем в читаемом виде
            currency = currencies[best_match]
            bot.reply_to(message, f" Возможно, вы имели в виду **{original_name}**:\n {currency}", parse_mode="Markdown")
        else:
            # Показываем похожие названия для подсказки
            suggestions = [c.title() for c in list(currencies.keys())[:5]]  # Первые 5 стран для примера
            suggestions_text = ", ".join(suggestions[:3])
            bot.reply_to(message, f" Страна «{country_input}» не найдена в базе.\n\n Примеры стран в базе: {suggestions_text}\n\nПроверьте написание или попробуйте на английском.", parse_mode="Markdown")
            
    except Exception as e:
        print(f"Ошибка в валюта: {e}")
        bot.reply_to(message, f" Произошла ошибка: {str(e)[:100]}\nПопробуйте позже.")



# Запуск бота с защитой от падений
if __name__ == "__main__":
    print("🤖 Бот запущен...")
    print("Доступные команды: /start, /help, /валюта [страна]")
    
    while True:
        try:
            # Запускаем бота с параметрами для стабильности
            bot.polling(
                none_stop=True,      # Не останавливаться при ошибках
                interval=0,          # Интервал между запросами
                timeout=20,          # Таймаут запроса
                long_polling_timeout=20  # Таймаут длинного опроса
            )
            # Бот очень часто зависал пришлось напихать команд для проверок стабильности работы
        except KeyboardInterrupt:
            print("\n👋 Бот остановлен пользователем")
            break
        except Exception as e:
            print(f"❌ Бот упал с ошибкой: {e}")
            print("🔄 Перезапуск через 15 секунд...")
            time.sleep(15)