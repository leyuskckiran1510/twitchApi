import logging
import os
import subprocess
from enum import Enum

from dotenv import load_dotenv
from twitchAPI.chat import ChatCommand, ChatMessage, ChatSub
from twitchAPI.type import AuthScope

from twitch import TwitchTv

logger = logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s](%(asctime)s) | [ %(message)s ]",
)

load_dotenv()

APP_ID = os.environ.get("ID", "")
APP_SECRET = os.environ.get("CODE", "")
USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]
TARGET_CHANNEL = "leyuskc"


class Urgency(int, Enum):
    LOW = 0
    NORMAL = 1
    CRITICAL = 2


twitch_bot = TwitchTv(
    app_id=APP_ID,
    app_secret=APP_SECRET,
    channel_name=TARGET_CHANNEL,
    user_scope=USER_SCOPE,
    save_auth=True,
)


def send_notificaiton(user: str, msg: str, urgency: Urgency):
    __urgency_table = ["low", "normal", "critical"]
    subprocess.call(["notify-send", "-u", f"{__urgency_table[urgency]}", "-t", "3000", user, msg])


@twitch_bot.on_message
async def on_message(msg: ChatMessage):
    send_notificaiton(msg.user.name, msg.text, Urgency.NORMAL)


@twitch_bot.on_sub
async def on_sub(sub: ChatSub):
    send_notificaiton(
        sub.chat.username if sub.chat.username else "",
        sub.sub_message,
        Urgency.CRITICAL,
    )


@twitch_bot.command(command_name="reply")
async def test_command(cmd: ChatCommand):
    if len(cmd.parameter) == 0:
        await cmd.reply("you did not tell me what to reply with")
    else:
        await cmd.reply(f"{cmd.user.name}: {cmd.parameter}")


twitch_bot.start()
