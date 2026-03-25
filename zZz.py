import os
import json
import asyncio
import re
import time
from datetime import datetime, timedelta
from telethon import events, TelegramClient, Button, functions, types
from telethon.errors import SessionPasswordNeededError, RPCError
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import GetDialogsRequest, ImportChatInviteRequest, CheckChatInviteRequest
from telethon.tl.types import InputPeerEmpty, Channel, Chat, User, ChatInviteAlready
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest

api_id = 22651991
api_hash = 'ecad214ecff6a5cd90fc141d4e32f597'
bot_token = "8002244062:AAEjgyVexVj0GGA1Wcg1YQdiSvuPTe_MZUw"
admin_id = 7782307068
accounts_file = 'accounts.json'
settings_file = 'settings.json'

bot = TelegramClient('BotSession', api_id, api_hash)
active_clients = {}
accounts_data = {}
bot_settings = {
    "is_paid": False,
    "dev_user": "None",
    "vip_users": {}
}

def load_accounts():
    global accounts_data
    if os.path.exists(accounts_file):
        with open(accounts_file, 'r') as f:
            try:
                accounts_data = json.load(f)
            except:
                accounts_data = {}
    else:
        accounts_data = {}

def save_accounts():
    with open(accounts_file, 'w') as f:
        json.dump(accounts_data, f, indent=4)

def load_settings():
    global bot_settings
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as f:
            try:
                bot_settings = json.load(f)
            except:
                pass
    else:
        save_settings()

def save_settings():
    with open(settings_file, 'w') as f:
        json.dump(bot_settings, f, indent=4)

def is_vip(user_id):
    user_id = str(user_id)
    if user_id == str(admin_id):
        return True
    if user_id in bot_settings["vip_users"]:
        expiry = bot_settings["vip_users"][user_id]
        if time.time() < expiry:
            return True
        else:
            del bot_settings["vip_users"][user_id]
            save_settings()
    return False

def get_main_buttons(user_id):
    user_id_str = str(user_id)
    user_accounts = accounts_data.get(user_id_str, {})
    count = len(user_accounts)
    buttons = [
        [Button.inline(f"مجموع الارقام : {count}", b'none')],
        [Button.inline('عرض الحسابات', b'overview')],
        [Button.inline('تسجيل حساب', b'add_acc'), Button.inline('قسم الرشق', b'rashq_section')],
        [Button.inline('مسح جميع الارقام', b'clear_all_confirm')]
    ]
    current_row = []
    for phone in user_accounts.keys():
        current_row.append(Button.inline(f"+{phone}", data=f"view_acc:{phone}"))
        if len(current_row) == 2:
            buttons.append(current_row)
            current_row = []
    if current_row:
        buttons.append(current_row)
    return buttons

async def start_client_monitor(user_id, phone, api_id, api_hash, session_str):
    if phone in active_clients:
        return
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    @client.on(events.NewMessage(chats=777000))
    async def handle_service_notification(event):
        code_match = re.search(r'\b(\d{5})\b', event.message.text)
        if code_match:
            code = code_match.group(1)
            await bot.send_message(int(user_id), f"**اشعار بكود جديد**\n\nالرقم: `{phone}`\nالكود: `{code}`")
            raise events.StopPropagation
    try:
        await client.start()
        active_clients[phone] = client
    except:
        if phone in active_clients:
            del active_clients[phone]

async def initialize_all_clients():
    for user_id, user_accounts in accounts_data.items():
        for phone, details in user_accounts.items():
            api_id_val = details.get('api_id')
            api_hash_val = details.get('api_hash')
            session_str = details.get('session_str')
            if api_id_val and api_hash_val and session_str:
                asyncio.create_task(start_client_monitor(user_id, phone, api_id_val, api_hash_val, session_str))

async def is_session_valid(api_id_val, api_hash_val, session_str):
    try:
        client = TelegramClient(StringSession(session_str), api_id_val, api_hash_val)
        await client.connect()
        valid = await client.is_user_authorized()
        await client.disconnect()
        return valid
    except:
        return False

@bot.on(events.NewMessage)
async def check_access(event):
    if not event.is_private:
        return
    user_id = event.sender_id
    if user_id == admin_id:
        return
    if bot_settings["is_paid"] and not is_vip(user_id):
        dev_btn = [Button.url("المطور", f"https://t.me/{bot_settings['dev_user']}")] if bot_settings['dev_user'] != "None" else []
        await event.respond("عذرا البوت مدفوع راسل المطور", buttons=dev_btn)
        raise events.StopPropagation

@bot.on(events.CallbackQuery)
async def check_access_callback(event):
    user_id = event.sender_id
    if user_id == admin_id:
        return
    if bot_settings["is_paid"] and not is_vip(user_id):
        await event.answer("عذرا البوت مدفوع", alert=True)
        raise events.StopPropagation

@bot.on(events.NewMessage(pattern='/admin'))
async def admin_panel(event):
    if event.sender_id != admin_id:
        return
    paid_status = "✅" if bot_settings["is_paid"] else "❌"
    buttons = [
        [Button.inline(f"البوت مدفوع {paid_status}", b'toggle_paid')],
        [Button.inline("تحديد يوزر مطور", b'set_dev_user')],
        [Button.inline("قسم الـvip", b'vip_section')],
        [Button.inline("الرجوع للقائمة الرئيسية", b'main_menu')]
    ]
    await event.respond("- لوحة التحكم بالبوت -", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'toggle_paid'))
async def toggle_paid(event):
    bot_settings["is_paid"] = not bot_settings["is_paid"]
    save_settings()
    paid_status = "✅" if bot_settings["is_paid"] else "❌"
    buttons = [
        [Button.inline(f"البوت مدفوع {paid_status}", b'toggle_paid')],
        [Button.inline("تحديد يوزر مطور", b'set_dev_user')],
        [Button.inline("قسم الـvip", b'vip_section')],
        [Button.inline("الرجوع للقائمة الرئيسية", b'main_menu')]
    ]
    await event.edit("- لوحة التحكم بالبوت -", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'set_dev_user'))
async def set_dev_user(event):
    async with bot.conversation(event.sender_id, timeout=300) as convo:
        await convo.send_message("- ارسل يوزر المطور بدون @ -")
        msg = await convo.get_response()
        bot_settings["dev_user"] = msg.text.strip().replace('@', '')
        save_settings()
        await convo.send_message(f"- تم تحديد المطور: @{bot_settings['dev_user']} -", buttons=[[Button.inline("رجوع", b'admin_back')]])

@bot.on(events.CallbackQuery(pattern=b'vip_section'))
async def vip_section(event):
    buttons = [
        [Button.inline("تفعيل", b'vip_activate')],
        [Button.inline("إلغاء تفعيل", b'vip_deactivate')],
        [Button.inline("رجوع", b'admin_back')]
    ]
    await event.edit("- قسم الـVIP -", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'vip_activate'))
async def vip_activate(event):
    async with bot.conversation(event.sender_id, timeout=300) as convo:
        await convo.send_message("- الان ارسل ايدي الشخص -")
        target_id = (await convo.get_response()).text.strip()
        buttons = [
            [Button.inline("ساعات", data=f"vip_h:{target_id}"), Button.inline("ايام", data=f"vip_d:{target_id}")]
        ]
        await convo.send_message("- اختر نوع المده -", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=r"vip_(h|d):(.+)"))
async def vip_duration(event):
    type_dur = event.data.decode().split(":")[0].split("_")[1]
    target_id = event.data.decode().split(":")[1]
    async with bot.conversation(event.sender_id, timeout=300) as convo:
        await convo.send_message("- الان ارسل المده -")
        duration_val = (await convo.get_response()).text.strip()
        try:
            val = int(duration_val)
            if type_dur == 'h':
                expiry = time.time() + (val * 3600)
                msg_part = f"{val} ساعة"
            else:
                expiry = time.time() + (val * 86400)
                msg_part = f"{val} يوم"
            bot_settings["vip_users"][str(target_id)] = expiry
            save_settings()
            await convo.send_message(f"تم تفعيل VIP للايدي {target_id} لمدة {msg_part}")
            try:
                await bot.send_message(int(target_id), f"تم تفعيل اشتراكك في البوت لمدة {msg_part}")
            except:
                pass
        except:
            await convo.send_message("حدث خطأ في القيمة")

@bot.on(events.CallbackQuery(pattern=b'vip_deactivate'))
async def vip_deactivate(event):
    async with bot.conversation(event.sender_id, timeout=300) as convo:
        await convo.send_message("- ارسل ايدي الشخص لالغاء تفعيله -")
        target_id = (await convo.get_response()).text.strip()
        if str(target_id) in bot_settings["vip_users"]:
            del bot_settings["vip_users"][str(target_id)]
            save_settings()
            await convo.send_message("- تم الغاء التفعيل بنجاح -")
        else:
            await convo.send_message("- الشخص ليس مفعلا -")

@bot.on(events.CallbackQuery(pattern=b'admin_back'))
async def admin_back(event):
    paid_status = "✅" if bot_settings["is_paid"] else "❌"
    buttons = [
        [Button.inline(f"البوت مدفوع {paid_status}", b'toggle_paid')],
        [Button.inline("تحديد يوزر مطور", b'set_dev_user')],
        [Button.inline("قسم الـvip", b'vip_section')],
        [Button.inline("الرجوع للقائمة الرئيسية", b'main_menu')]
    ]
    await event.edit("- لوحة التحكم بالبوت -", buttons=buttons)

async def show_accounts_overview(event):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    if not user_accounts:
        return await event.answer("- لم يتم اضافة اي حسابات في البوت.", alert=True)
    text = '**مرحبا في قسم حساباتك اذهب لمعرفة ارقامك** \n هناك زر يحتوي علي الرقم وزر يحتوي علي حالته'
    buttons = []
    for phone in user_accounts.keys():
        details = user_accounts[phone]
        status = 'نشط' if await is_session_valid(details.get('api_id'), details.get('api_hash'), details.get('session_str')) else 'غير نشط'
        buttons.append([Button.inline(f'{phone} | {status}', data=f'view_acc:{phone}')])
    buttons.append([Button.inline("رجوع", data="main_menu")])
    await event.edit(text, buttons=buttons)

async def show_account_details(event, phone):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    if phone in user_accounts:
        details = user_accounts[phone]
        text = f"إعدادات الحساب: `+{phone}`\nكلمة المرور: `{details.get('password', 'لا يوجد')}`"
        buttons = [
            [Button.inline("جلب الكود 📥", data=f"get_code:{phone}")],
            [Button.inline("حذف الرقم 🗑️", data=f"confirm_del:{phone}")],
            [Button.inline("رجوع", data="main_menu")]
        ]
        await event.edit(text, buttons=buttons)
    else:
        await event.answer("الحساب غير موجود.", alert=True)

async def show_delete_confirmation(event, phone):
    text = f"هل أنت متأكد من حذف الرقم +{phone}؟"
    buttons = [[Button.inline("نعم، متأكد", data=f"exec_del:{phone}"), Button.inline("إلغاء", data="main_menu")]]
    await event.edit(text, buttons=buttons)

async def delete_account(event, phone):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    if phone in user_accounts:
        if phone in active_clients:
            client = active_clients.pop(phone)
            try: await client.disconnect()
            except: pass
        del user_accounts[phone]
        if not user_accounts:
            del accounts_data[user_id]
        save_accounts()
        await event.edit(f"تم حذف الرقم +{phone} بنجاح.", buttons=[[Button.inline("رجوع", data="main_menu")]])
    else:
        await event.answer("خطأ في عملية الحذف.")

async def get_latest_code(api_id_val, api_hash_val, session_str):
    client = TelegramClient(StringSession(session_str), api_id_val, api_hash_val)
    try:
        await client.connect()
        async for msg in client.iter_messages(777000, limit=1):
            code_match = re.search(r'\b(\d{5})\b', msg.text)
            if code_match: return code_match.group(1)
        return "لم يتم العثور على كود"
    except Exception as e: return f"خطأ: {str(e)}"
    finally: await client.disconnect()

async def handle_code_request(event, phone):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    if phone in user_accounts:
        details = user_accounts[phone]
        await event.answer("جاري جلب الكود...", alert=False)
        try:
            code = await get_latest_code(details['api_id'], details['api_hash'], details['session_str'])
            text = f"الرقم: `+{phone}`\nآخر كود وصل: `{code}`"
        except:
            text = "فشل في جلب الكود، تأكد من أن الحساب نشط."
        buttons = [[Button.inline("تحديث الكود 🔄", data=f"get_code:{phone}")], [Button.inline("رجوع", data="main_menu")]]
        await event.edit(text, buttons=buttons)

async def register_new_account(event):
    new_api_id = 1724716
    new_api_hash = '00b2d8f59c12c1b9a4bc63b70b461b2f'
    async with bot.conversation(event.sender_id, timeout=300) as convo:
        await convo.send_message("- الان ارسل رقمك -")
        phone_reply = await convo.get_response()
        phone = phone_reply.text.strip().replace('+', '').replace(' ', '')
        client = TelegramClient(StringSession(), new_api_id, new_api_hash)
        try:
            await client.connect()
            await client.send_code_request(phone)
            await convo.send_message("- الان ارسل الكود الذي وصلك -")
            code_reply = await convo.get_response()
            code = code_reply.text.strip()
            password = "لا شئ"
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                await convo.send_message("- الان ارسل التحقق -")
                pwd_reply = await convo.get_response()
                password = pwd_reply.text.strip()
                await client.sign_in(password=password)
            session_str = client.session.save()
            await convo.send_message("- تم التسجيل بنجاح -", buttons=[[Button.inline("رجوع", data='main_menu')]])
            return {phone: {'api_id': new_api_id, 'api_hash': new_api_hash, 'session_str': session_str, 'password': password}}
        except Exception as e:
            await convo.send_message(f"خطأ: {str(e)}", buttons=[[Button.inline("رجوع", data='main_menu')]])
            return None
        finally: await client.disconnect()

@bot.on(events.CallbackQuery(pattern=b'rashq_section'))
async def rashq_section(event):
    buttons = [
        [Button.inline("رشق قناة", b'rashq_join'), Button.inline("مغادره قناة", b'rashq_leave')],
        [Button.inline("جلب جلسه", b'get_session_menu'), Button.inline("ارسال رسائل جماعيه", b'broadcast_msg')],
        [Button.inline("نسخه احتياطي", b'backup_data'), Button.inline("حضر وحذف البوتات", b'bots_management_menu')],
        [Button.inline("رجوع", b'main_menu')]
    ]
    await event.edit("- اهلا بك في قسم الرشق -", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'rashq_join'))
async def rashq_join(event):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    async with bot.conversation(event.sender_id, timeout=300) as convo:
        await convo.send_message("- الان ارسل معرف القناة -")
        target = (await convo.get_response()).text.strip()
        count = 0
        for phone, details in user_accounts.items():
            try:
                client = active_clients.get(phone)
                if not client:
                    client = TelegramClient(StringSession(details['session_str']), details['api_id'], details['api_hash'])
                    await client.connect()
                if 't.me/+' in target or 't.me/joinchat/' in target:
                    await client(ImportChatInviteRequest(target.split('/')[-1].replace('+', '')))
                else:
                    await client(JoinChannelRequest(target))
                count += 1
            except: continue
        await convo.send_message(f"- تم رشق القناة {count} عضو -", buttons=[[Button.inline("رجوع", b'main_menu')]])

@bot.on(events.CallbackQuery(pattern=b'rashq_leave'))
async def rashq_leave(event):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    async with bot.conversation(event.sender_id, timeout=300) as convo:
        await convo.send_message("- الان ارسل معرف القناة -")
        target = (await convo.get_response()).text.strip()
        count = 0
        for phone, details in user_accounts.items():
            try:
                client = active_clients.get(phone)
                if not client:
                    client = TelegramClient(StringSession(details['session_str']), details['api_id'], details['api_hash'])
                    await client.connect()
                if 't.me/+' in target or 't.me/joinchat/' in target:
                    res = await client(CheckChatInviteRequest(target.split('/')[-1].replace('+', '')))
                    if hasattr(res, 'chat'):
                        await client(LeaveChannelRequest(res.chat.id))
                    elif isinstance(res, ChatInviteAlready):
                        await client(LeaveChannelRequest(res.chat.id))
                else:
                    await client(LeaveChannelRequest(target))
                count += 1
            except: continue
        await convo.send_message(f"- تم المغادره {count}", buttons=[[Button.inline("رجوع", b'main_menu')]])

@bot.on(events.CallbackQuery(pattern=b'get_session_menu'))
async def get_session_menu(event):
    buttons = [[Button.inline("جلسه رقم محدد", b'session_specific'), Button.inline("جميع الارقام", b'session_all')], [Button.inline("رجوع", b'rashq_section')]]
    await event.edit("اختر نوع جلب الجلسة:", buttons=buttons)

async def format_session_info(phone, details):
    client = TelegramClient(StringSession(details['session_str']), details['api_id'], details['api_hash'])
    await client.connect()
    me = await client.get_me()
    res = f"Session: `{details['session_str']}`\n- phone - : `{phone}`\n- user - : `@{me.username if me.username else 'None'}`\n- id - : `{me.id}`\n\n"
    await client.disconnect()
    return res

@bot.on(events.CallbackQuery(pattern=b'session_specific'))
async def session_specific(event):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    if not user_accounts:
        return await event.answer("لا توجد ارقام مسجلة.", alert=True)
    buttons = []
    current_row = []
    for phone in user_accounts.keys():
        current_row.append(Button.inline(f"+{phone}", data=f"sel_sess:{phone}"))
        if len(current_row) == 2:
            buttons.append(current_row)
            current_row = []
    if current_row:
        buttons.append(current_row)
    buttons.append([Button.inline("رجوع", b'get_session_menu')])
    await event.edit("اختر الرقم الذي تريد جلب جلسته:", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=r"sel_sess:(.+)"))
async def handle_sel_sess(event):
    phone = event.data.decode().split(":")[1]
    buttons = [
        [Button.inline("جلب جلسه", data=f"do_sess:{phone}")],
        [Button.inline("رجوع", b'session_specific')]
    ]
    await event.edit(f"الرقم المختار: +{phone}", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=r"do_sess:(.+)"))
async def handle_do_sess(event):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    phone = event.data.decode().split(":")[1]
    if phone in user_accounts:
        try:
            info = await format_session_info(phone, user_accounts[phone])
            await event.edit(info, buttons=[[Button.inline("رجوع", b'session_specific')]])
        except Exception as e:
            await event.edit(f"حدث خطأ: {str(e)}", buttons=[[Button.inline("رجوع", b'session_specific')]])
    else:
        await event.answer("الرقم غير موجود.", alert=True)

@bot.on(events.CallbackQuery(pattern=b'session_all'))
async def session_all(event):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    full_info = ""
    for phone, details in user_accounts.items():
        try: full_info += await format_session_info(phone, details)
        except: continue
    if full_info:
        if len(full_info) > 4000:
            with open("sessions.txt", "w") as f: f.write(full_info)
            await bot.send_file(event.sender_id, "sessions.txt", caption="جميع الجلسات")
            os.remove("sessions.txt")
        else: await bot.send_message(event.sender_id, full_info)
    else: await event.answer("لا يوجد بيانات.")

@bot.on(events.CallbackQuery(pattern=b'broadcast_msg'))
async def broadcast_msg(event):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    async with bot.conversation(event.sender_id, timeout=600) as convo:
        await convo.send_message("- الان ارسل المعرف -")
        targets_raw = (await convo.get_response()).text.strip().split()
        await convo.send_message("- الان ارسل الرساله -")
        message = await convo.get_response()
        for target in targets_raw:
            count = 0
            for phone, details in user_accounts.items():
                try:
                    client = active_clients.get(phone)
                    if not client:
                        client = TelegramClient(StringSession(details['session_str']), details['api_id'], details['api_hash'])
                        await client.connect()
                    await client.send_message(target, message)
                    count += 1
                except: continue
            await convo.send_message(f"- تم ارسال الرساله {target} - {count}")

@bot.on(events.CallbackQuery(pattern=b'backup_data'))
async def backup_data(event):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    active_count = sum(1 for phone in user_accounts if phone in active_clients)
    data = json.dumps(user_accounts, indent=4)
    stats = f"إحصائيات حساباتك:\nعدد الحسابات: {len(user_accounts)}\nعدد النشطة: {active_count}"
    with open("backup.json", "w") as f: f.write(data)
    await bot.send_file(event.sender_id, "backup.json", caption=stats)
    os.remove("backup.json")

@bot.on(events.CallbackQuery(pattern=b'leave_channels_menu'))
async def leave_channels_menu(event):
    buttons = [[Button.inline("قناة محدده", b'leave_specific'), Button.inline("مغادره كل قنوات", b'leave_all_ch')], [Button.inline("رجوع", b'main_menu')]]
    await event.edit("اختر خيار المغادرة:", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'leave_specific'))
async def leave_specific(event):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    async with bot.conversation(event.sender_id, timeout=300) as convo:
        await convo.send_message("- الان ارسل معرف القناة -")
        target = (await convo.get_response()).text.strip()
        count = 0
        for phone, details in user_accounts.items():
            try:
                client = active_clients.get(phone)
                if not client:
                    client = TelegramClient(StringSession(details['session_str']), details['api_id'], details['api_hash'])
                    await client.connect()
                if 't.me/+' in target or 't.me/joinchat/' in target:
                    res = await client(CheckChatInviteRequest(target.split('/')[-1].replace('+', '')))
                    if hasattr(res, 'chat'):
                        await client(LeaveChannelRequest(res.chat.id))
                    elif isinstance(res, ChatInviteAlready):
                        await client(LeaveChannelRequest(res.chat.id))
                else:
                    await client(LeaveChannelRequest(target))
                count += 1
            except: continue
        await convo.send_message(f"- تم المغادره {count}")

@bot.on(events.CallbackQuery(pattern=b'leave_all_ch'))
async def leave_all_ch(event):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    await event.answer("جاري المغادرة من جميع القنوات...", alert=False)
    for phone, details in user_accounts.items():
        try:
            client = active_clients.get(phone)
            if not client:
                client = TelegramClient(StringSession(details['session_str']), details['api_id'], details['api_hash'])
                await client.connect()
            async for dialog in client.iter_dialogs():
                if dialog.is_channel or dialog.is_group:
                    await client(LeaveChannelRequest(dialog.id))
        except: continue
    await bot.send_message(event.sender_id, "تمت مغادرة جميع القنوات والمجموعات من كافة الحسابات.")

@bot.on(events.CallbackQuery(pattern=b'bots_management_menu'))
async def bots_management_menu(event):
    buttons = [[Button.inline("بوت محدد", b'block_bot_specific'), Button.inline("حذف جميع البوتات", b'block_all_bots')], [Button.inline("رجوع", b'rashq_section')]]
    await event.edit("قسم إدارة البوتات:", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'block_bot_specific'))
async def block_bot_specific(event):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    async with bot.conversation(event.sender_id, timeout=300) as convo:
        await convo.send_message("- لان ارسل معرف البوت -")
        target = (await convo.get_response()).text.strip()
        count = 0
        for phone, details in user_accounts.items():
            try:
                client = active_clients.get(phone)
                if not client:
                    client = TelegramClient(StringSession(details['session_str']), details['api_id'], details['api_hash'])
                    await client.connect()
                await client(BlockRequest(target))
                count += 1
            except: continue
        await convo.send_message(f"تم حضر البوت {count}")

@bot.on(events.CallbackQuery(pattern=b'block_all_bots'))
async def block_all_bots(event):
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    await event.answer("جاري حذف وحظر جميع البوتات...", alert=False)
    for phone, details in user_accounts.items():
        try:
            client = active_clients.get(phone)
            if not client:
                client = TelegramClient(StringSession(details['session_str']), details['api_id'], details['api_hash'])
                await client.connect()
            async for dialog in client.iter_dialogs():
                if isinstance(dialog.entity, User) and dialog.entity.bot:
                    await client(BlockRequest(dialog.id))
                    await client.delete_dialog(dialog.id)
        except: continue
    await bot.send_message(event.sender_id, "تم حذف جميع بوتات بل حسابات مسجله")

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    name = user.first_name
    await event.respond(f'اهلا بك عزيزي {name}•', buttons=get_main_buttons(event.sender_id))

@bot.on(events.CallbackQuery(pattern=b'main_menu'))
async def show_main_menu(event):
    user = await event.get_sender()
    name = user.first_name
    await event.edit(f'اهلا بك عزيزي {name}•', buttons=get_main_buttons(event.sender_id))

@bot.on(events.CallbackQuery(pattern=b'overview'))
async def handle_overview(event):
    await show_accounts_overview(event)

@bot.on(events.CallbackQuery(pattern=r"view_acc:(.+)"))
async def handle_view(event):
    phone = event.data.decode().split(":")[1]
    await show_account_details(event, phone)

@bot.on(events.CallbackQuery(pattern=r"confirm_del:(.+)"))
async def handle_confirm(event):
    phone = event.data.decode().split(":")[1]
    await show_delete_confirmation(event, phone)

@bot.on(events.CallbackQuery(pattern=r"exec_del:(.+)"))
async def handle_exec_del(event):
    phone = event.data.decode().split(":")[1]
    await delete_account(event, phone)

@bot.on(events.CallbackQuery(pattern=r"get_code:(.+)"))
async def handle_code(event):
    phone = event.data.decode().split(":")[1]
    await handle_code_request(event, phone)

@bot.on(events.CallbackQuery(pattern=b'clear_all_confirm'))
async def handle_clear_confirm(event):
    await event.edit("هل انت متأكد من حذف جميع الأرقام؟", buttons=[[Button.inline("موافق، حذف الكل", b'clear_all_exec'), Button.inline("إلغاء", b'main_menu')]])

@bot.on(events.CallbackQuery(pattern=b'clear_all_exec'))
async def handle_clear_exec(event):
    global accounts_data, active_clients
    user_id = str(event.sender_id)
    user_accounts = accounts_data.get(user_id, {})
    for phone in list(user_accounts.keys()):
        if phone in active_clients:
            client = active_clients.pop(phone)
            try: await client.disconnect()
            except: pass
    if user_id in accounts_data:
        del accounts_data[user_id]
    save_accounts()
    await event.edit("تم حذف جميع الحسابات من النظام.", buttons=[[Button.inline("رجوع", b'main_menu')]])

@bot.on(events.CallbackQuery(pattern=b'add_acc'))
async def handle_add(event):
    user_id = str(event.sender_id)
    acc = await register_new_account(event)
    if acc:
        if user_id not in accounts_data:
            accounts_data[user_id] = {}
        accounts_data[user_id].update(acc)
        save_accounts()
        for p, i in acc.items():
            asyncio.create_task(start_client_monitor(user_id, p, i['api_id'], i['api_hash'], i['session_str']))

async def main():
    load_accounts()
    load_settings()
    await bot.start(bot_token=bot_token)
    await initialize_all_clients()
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())