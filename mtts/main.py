import os
from pagermaid.listener import listener
from pagermaid.utils import Message, client
from pymtts import async_Mtts
from pagermaid.single_utils import sqlite


default_config = {
    "short_name": "zh-CN-XiaoxiaoNeural",
    "style": "general",
    "rate": 0,
    "pitch": 0,
    "kmhz": 24
}


async def config_check() -> dict:
    if not sqlite.get('mtts', {}):
        sqlite['mtts'] = default_config

    return sqlite['mtts']


async def config_set(configset, cmd) -> bool:
    config = await config_check()
    config[cmd] = configset
    sqlite['mtts'] = config
    return True


async def save_audio(buffer: bytes) -> str:
    with open(os.path.join(os.getcwd(), "data", "mtts.mp3"), "wb") as f:
        f.write(buffer)
        return os.path.join(os.getcwd(), "data", "mtts.mp3")


@listener(command="mtts", description="文本转语音",
          parameters="[str]\r\nmtts setname [str]\r\nmtts setstyle [str]\r\nmtts setrate [int]\r\nmtts setpitch [int]\r\nmtts list [str]")
async def mtts(msg: Message):
    cmtts = async_Mtts()
    opt = msg.arguments
    replied_msg = msg.reply_to_message
    if opt.startswith("setname "):
        model_name = opt.split(" ")[1]
        status = await config_set(model_name, "short_name")
        if not status:
            await msg.edit("❗️ tts setting  error")
        await msg.edit(
            "successfully set up mtts voice model to:{}".format(model_name))
    elif opt.startswith("setstyle "):
        model_name = opt.split(" ")[1]
        status = await config_set(model_name, "style")
        if not status:
            await msg.edit("❗️ tts setting  error")
        await msg.edit(
            "successfully set up mtts voice style to:{}".format(model_name))
    elif opt.startswith("setrate "):
        model_name = opt.split(" ")[1]
        status = await config_set(model_name, "rate")
        if not status:
            await msg.edit("❗️ tts setting  error")
        await msg.edit(
            "successfully set up mtts voice rate to:{}".format(model_name))
    elif opt.startswith("setpitch "):
        model_name = opt.split(" ")[1]
        status = await config_set(model_name, "pitch")
        if not status:
            await msg.edit("❗️ tts setting  error")
        await msg.edit(
            "successfully set up mtts voice pitch to:{}".format(model_name))
    elif opt.startswith("list "):
        tag = opt.split(" ")[1]
        try:
            voice_model = await cmtts.get_lang_models()
        except:
            return await msg.edit("无法访问微软api，请稍后重试。")
        s = "code | local name | Gender | LocaleName\r\n"
        for model in voice_model:
            if tag in model.ShortName or tag in model.Locale or tag in model.LocaleName:
                s += "{} | {} | {} | {}\r\n".format(model.ShortName,
                                                    model.LocalName,
                                                    model.Gender,
                                                    model.LocaleName)
        await msg.edit(s)
    elif opt and opt != " ":
        config = await config_check()
        try:
            mp3_buffer = await cmtts.mtts(text=opt,
                                          short_name=config["short_name"],
                                          style=config["style"],
                                          rate=config["rate"],
                                          pitch=config["pitch"],
                                          kmhz=config["kmhz"])
        except:
            return await msg.edit("无法访问微软api，请稍后重试。")
        mp3_path = await save_audio(mp3_buffer)

        if replied_msg is None:
            await msg.reply_voice(mp3_path)
            await msg.delete()
        else:
            await msg.reply_voice(
                mp3_path, reply_to_message_id=replied_msg.id)
            await msg.delete()
    elif replied_msg:
        config = await config_check()
        try:
            mp3_buffer = await cmtts.mtts(text=replied_msg.text,
                                          short_name=config["short_name"],
                                          style=config["style"],
                                          rate=config["rate"],
                                          pitch=config["pitch"],
                                          kmhz=config["kmhz"])
        except:
            return await msg.edit("无法访问微软api，请稍后重试。")
        mp3_path = await save_audio(mp3_buffer)
        await msg.reply_voice(mp3_path,
                              reply_to_message_id=replied_msg.id)
        await msg.delete()
    elif opt is None or opt == " ":
        await msg.edit("error, please use help command to show use case")
