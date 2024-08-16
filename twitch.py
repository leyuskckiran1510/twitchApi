import asyncio
import logging
import pickle
import time
from pathlib import Path
from threading import Event
from time import sleep
from typing import Any, Callable, Coroutine

from twitchAPI.chat import Chat, ChatCommand, ChatMessage, ChatSub, EventData
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope, ChatEvent

logger = logging.getLogger()


class AuthenticationError(Exception):
    """Raises when authentication failes, should not be catched"""

    ...


class TwitchTv:
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        channel_name: str,
        user_scope: list[AuthScope],
        save_auth: bool,
        auth_save_file_name: Path = Path("authtoken.pkl"),
    ) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.channel_name = channel_name
        self.user_scope = user_scope
        self.save_auth = save_auth
        self.exit_flag = Event()
        if auth_save_file_name.suffix != ".pkl":
            auth_save_file_name = Path(f"{auth_save_file_name}.pkl")
        self.auth_save_file_name = auth_save_file_name
        logger.info("Setting up Twtich Object")
        self.twitch = Twitch(self.app_id, self.app_secret)
        self.authenticator = UserAuthenticator(self.twitch, self.user_scope)
        asyncio.run(self._setup())

    async def _setup(self):
        logger.info(f"Authenticating using APP_ID={self.app_id}, APP_SECRET=xxxxxxxxxxxxx")
        token, refresh_token = await self.auth_it()
        if not token:
            raise AuthenticationError("Failed To Authenticate")
        logger.info("Sucessfully Authenticated. ")
        logger.info("Setting up user Authentication. ")
        await self.twitch.set_user_authentication(token, self.user_scope, refresh_token)
        self.chat = await Chat(self.twitch)
        self.chat.register_event(ChatEvent.READY, self.on_ready)

    async def on_ready(self, ready_event: EventData):
        logger.info("Bot is Ready.")
        await ready_event.chat.join_room(self.channel_name)

    def on_message(self, func: Callable[[ChatMessage], Coroutine[Any, Any, None]]):
        async def inject_logger(msg: ChatMessage):
            logger.info("New Message")
            await func(msg)

        self.chat.register_event(ChatEvent.MESSAGE, inject_logger)

    def on_sub(self, func: Callable[[ChatSub], Coroutine[Any, Any, None]]):
        async def inject_logger(sub: ChatSub):
            logger.info("New Subscription")
            await func(sub)

        self.chat.register_event(ChatEvent.SUB, inject_logger)

    def command(self, command_name: str):
        def inner_deco(func: Callable[[ChatCommand], Coroutine[Any, Any, None]]):
            async def inject_logger(command: ChatCommand):
                logger.info("New Subscription")
                await func(command)

            self.chat.register_command(command_name, inject_logger)

        return inner_deco

    async def auth_it(self) -> tuple[str, str]:
        if self.auth_save_file_name.exists():
            with open(self.auth_save_file_name, "rb") as fp:
                token, ref_token = pickle.load(fp)
                return token, ref_token
        authenticated = await self.authenticator.authenticate()
        if not authenticated:
            logger.error("Failed To Authenticate. Please retry")
            return "", ""

        if self.save_auth:
            logger.info("Auth Save is enabled.")
            logger.info("Saving Auth To File...")
            with open(self.auth_save_file_name, "wb") as fp:
                pickle.dump(authenticated, fp)

        return authenticated

    async def _start(self):
        logger.info("Starting Bot... [invoke self.stop for early stop]")
        self.chat.start()
        while not self.exit_flag.is_set():
            try:
                self.exit_flag.wait(0.2)
            except KeyboardInterrupt:
                logger.info("Closing Bot...")
                self.exit_flag.set()

        self.chat.stop()
        await self.twitch.close()
        logger.info("Sucessfully Closed.")

    def stop(self):
        self.exit_flag.set()

    def start(self):
        asyncio.run(self._start())
