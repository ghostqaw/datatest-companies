from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, \
    ContextTypes, ConversationHandler
from sqlalchemy import create_engine, text
import pandas as pd
import matplotlib.pyplot as plt
import logging

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключение к базе данных с использованием SQLAlchemy
DATABASE_URL = 'postgresql+psycopg2://postgres:qaz123@localhost:5434/finance_data'
engine = create_engine(DATABASE_URL)

PASSWORD = "qaz123"  # Замените на ваш реальный пароль
AWAITING_PASSWORD, AWAITING_COMPANY_DATA = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [KeyboardButton("Выбрать компанию")],
        [KeyboardButton("Добавить новую компанию")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('Добро пожаловать! Выберите действие:', reply_markup=reply_markup)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text_received = update.message.text
    logger.info(f"Получено сообщение: {text_received}")

    if text_received == "Выбрать компанию":
        await display_companies(update, context)
        return ConversationHandler.END
    elif text_received == "Добавить новую компанию":
        await add_company(update, context)
        return AWAITING_PASSWORD
    else:
        await update.message.reply_text("Пожалуйста, выберите действие из меню.")
        return ConversationHandler.END


async def display_companies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    companies = get_companies()
    keyboard = [[InlineKeyboardButton(company, callback_data=company)] for company in companies]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите компанию:', reply_markup=reply_markup)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        company = query.data
        await query.edit_message_text(text=f"Вы выбрали: {company}")

        query = text("SELECT * FROM financial_data WHERE company = :company")
        df = pd.read_sql_query(query, engine, params={"company": company})

        if df.empty:
            await update.message.reply_text(f"Данные для компании {company} не найдены.")
            return

        df.plot(x='month', y=['income', 'expense', 'profit', 'kpn'], kind='bar')
        plt.title(f"Финансовые данные {company}")
        plt.xlabel('Месяц')
        plt.ylabel('Сумма (€)')
        plt.tight_layout()
        plt.savefig('finance_plot.png')

        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open('finance_plot.png', 'rb'))
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {e}")
        logger.error(f"Error in button handler: {e}")


async def add_company(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Запрос на добавление новой компании")
    await update.message.reply_text(
        'Введите пароль для добавления новой компании:',
        reply_markup=ReplyKeyboardMarkup([["/cancel"]], resize_keyboard=True)
    )
    return AWAITING_PASSWORD


async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_password = update.message.text
    logger.info(f"Проверка пароля: {user_password}")

    if user_password == PASSWORD:
        await update.message.reply_text(
            'Пароль верный. Введите данные новой компании в формате: "Название, Месяц, Доход, Расход, Прибыль, КПН"',
            reply_markup=ReplyKeyboardRemove()
        )
        return AWAITING_COMPANY_DATA
    else:
        await update.message.reply_text(
            'Неверный пароль. Попробуйте еще раз или нажмите /cancel для отмены.',
            reply_markup=ReplyKeyboardMarkup([["/cancel"]], resize_keyboard=True)
        )
        return AWAITING_PASSWORD


async def save_company(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        data = update.message.text.split(",")
        if len(data) == 6:
            company, month, income, expense, profit, kpn = map(str.strip, data)
            try:
                income = int(income)
                expense = int(expense)
                profit = int(profit)
                kpn = int(kpn)
            except ValueError:
                await update.message.reply_text(
                    "Ошибка: Пожалуйста, введите числовые значения для дохода, расхода, прибыли и КПН."
                )
                return AWAITING_COMPANY_DATA

            with engine.connect() as conn:
                try:
                    conn.execute(
                        text(
                            "INSERT INTO financial_data (month, income, expense, profit, kpn, company) "
                            "VALUES (:month, :income, :expense, :profit, :kpn, :company)"
                        ),
                        {"month": month, "income": income, "expense": expense, "profit": profit, "kpn": kpn, "company": company}
                    )
                    conn.commit()
                    await update.message.reply_text(
                        f"Компания '{company}' успешно добавлена! Выберите действие:",
                        reply_markup=ReplyKeyboardMarkup(
                            [["Выбрать компанию"], ["Добавить новую компанию"]],
                            resize_keyboard=True
                        )
                    )
                    return ConversationHandler.END
                except Exception as e:
                    logger.error(f"Ошибка при выполнении SQL-запроса: {e}")
                    await update.message.reply_text(f"Ошибка при добавлении компании: {e}")
                    return AWAITING_COMPANY_DATA
        else:
            await update.message.reply_text(
                "Неверный формат данных. Пожалуйста, используйте формат: 'Название, Месяц, Доход, Расход, Прибыль, КПН'"
            )
            return AWAITING_COMPANY_DATA
    except Exception as e:
        await update.message.reply_text(f"Ошибка при добавлении компании: {e}")
        logger.error(f"Ошибка при сохранении компании: {e}")
        return AWAITING_COMPANY_DATA



async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Отмена текущего процесса.")
    await update.message.reply_text(
        "Действие отменено. Выберите действие из меню.",
        reply_markup=ReplyKeyboardMarkup([["Выбрать компанию"], ["Добавить новую компанию"]], resize_keyboard=True)
    )
    return ConversationHandler.END


def get_companies():
    try:
        query = text("SELECT DISTINCT company FROM financial_data")
        with engine.connect() as conn:
            result = conn.execute(query).fetchall()
            companies = [row[0] for row in result]
        return companies
    except Exception as e:
        logger.error(f"Error retrieving companies: {e}")
        return []


def main() -> None:
    application = ApplicationBuilder().token("6704503572:AAGBnctYGW-f9di1U8hZYSMb1Mz7vSnpL7w").connect_timeout(
        60).build()

    logger.info("Бот запущен и ожидает команды...")

    # Command handlers
    application.add_handler(CommandHandler("start", start))

    # Conversation handler to manage different states
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^Добавить новую компанию$'), add_company)],
        states={
            AWAITING_PASSWORD: [
                MessageHandler(filters.Regex('^/cancel$'), cancel),  # Catch cancel in the AWAITING_PASSWORD state
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_password),
            ],
            AWAITING_COMPANY_DATA: [
                MessageHandler(filters.Regex('^/cancel$'), cancel),  # Catch cancel in the AWAITING_COMPANY_DATA state
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_company),
            ],
        },
        fallbacks=[
            CommandHandler('start', start),
            MessageHandler(filters.Regex('^/cancel$'), cancel),  # Catch cancel in any fallback
            MessageHandler(filters.TEXT & ~filters.COMMAND, cancel)  # Treat unexpected input as cancel
        ]
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling()


if __name__ == '__main__':
    main()
