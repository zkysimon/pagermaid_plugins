from pagermaid import bot
from pagermaid.listener import listener
from pagermaid.single_utils import Message, sqlite
from pyrogram.raw.functions.messages import GetStickerSet
from pyrogram.raw.types import InputStickerSetShortName
from pyrogram.types import ReplyKeyboardMarkup


class CannotToStickerSetError(Exception):
    """
        Occurs when program cannot change a message to a sticker set
    """

    def __init__(self):
        super().__init__(
            "无法将此消息转换为贴纸"
        )


class NoStickerSetNameError(Exception):
    """
        Occurs when no username is provided
    """

    def __init__(self):
        super().__init__(
            "请先设置用户名"
        )


async def unblock_sticker_bot():
    await bot.unblock_user("Stickers")


async def get_all_packs(message: Message):
    async with message.bot.conversation(429000) as conv:
        await conv.ask("/start")
        await conv.mark_as_read()
        await conv.ask("/cancel")
        await conv.mark_as_read()
        await conv.ask("/addsticker")
        msg: Message = await conv.ask("/addsticker")
        await conv.mark_as_read()
        await conv.ask("/cancel")
        await conv.mark_as_read()
    if isinstance(msg.reply_markup, ReplyKeyboardMarkup):
        packs = []
        keyboard = msg.reply_markup.keyboard
        for i in keyboard:
            packs.extend(j for j in i if isinstance(j, str))
        return packs
    return []


async def get_pack(name: str):
    try:
        return await bot.invoke(GetStickerSet(
            stickerset=InputStickerSetShortName(short_name=name),
            hash=0
        ))
    except Exception as e:  # noqa
        raise NoStickerSetNameError() from e


async def config_check() -> dict:
    if not sqlite.get("stickers", {}):
        sqlite["stickers"] = {"pack": ""}
    return sqlite["stickers"]


class Sticker:
    message: Message
    sticker_set: str
    emoji: str
    should_forward: Message

    def __init__(self, message: Message, sticker_set: str = "", emoji: str = "😀",
                 should_forward: Message = None):
        self.message = message
        self.sticker_set = sticker_set
        self.emoji = emoji
        self.should_forward = should_forward

    async def generate_sticker_set(self, pack):
        if not self.sticker_set:
            self.sticker_set = pack

    async def process_sticker(self, test: bool = False):
        if self.should_forward and self.should_forward.sticker and \
                not self.should_forward.sticker.is_video and not self.should_forward.sticker.is_animated:
            if not test:
                await self.should_forward.forward("Stickers")
            self.emoji = self.should_forward.sticker.emoji
            return
        raise CannotToStickerSetError()

    async def add_sticker(self):
        async with self.message.bot.conversation(429000) as conv:
            await conv.ask("/start")
            await conv.mark_as_read()
            await conv.ask("/cancel")
            await conv.mark_as_read()
            await conv.ask("/addsticker")
            await conv.ask("/addsticker")
            await conv.mark_as_read()
            await conv.ask(self.sticker_set)
            await conv.mark_as_read()
            await self.process_sticker()
            await conv.ask(self.emoji)
            await conv.mark_as_read()
            await conv.ask("/done")
            await conv.mark_as_read()

    async def to_sticker_set(self):
        pack = await config_check()
        await self.generate_sticker_set(pack["pack"])
        if not self.sticker_set:
            raise NoStickerSetNameError()
        packs = await get_all_packs(self.message)
        if self.sticker_set not in packs:
            raise NoStickerSetNameError()
        await self.add_sticker()


@listener(command="s",
          need_admin=True)
async def sticker(message: Message):
    pack = await config_check()
    if message.parameter[0] == "set":
        pack["pack"] = message.parameter[1]
        sqlite["stickers"] = pack
        return
    await unblock_sticker_bot()
    one_sticker = Sticker(message, should_forward=message.reply_to_message)
    try:
        await one_sticker.process_sticker(test=True)
        await one_sticker.to_sticker_set()
    except Exception as e:
        return await message.edit(f"收藏到贴纸包失败：{e}")
    await message.edit("收藏到贴纸包成功")
