import json
from pagermaid.listener import listener
from pagermaid.utils import Message, client, pip_install
from pagermaid.single_utils import sqlite

pip_install("edge-tts")

import edge_tts

default_config = {
    "short_name": "zh-CN-XiaoxiaoNeural",
    "style": "general",
    "rate": "+0%",
    "volume": "+0%"
}
output = "data/mtts.mp3"


async def config_check() -> dict:
    if not sqlite.get('edge-tts', {}):
        sqlite['edge-tts'] = default_config

    return sqlite['edge-tts']


async def config_set(configset, cmd) -> bool:
    config = await config_check()
    config[cmd] = configset
    sqlite['edge-tts'] = config
    return True


async def getmodel():
    headers = {'origin': 'https://azure.microsoft.com'}
    url = "https://eastus.api.speech.microsoft.com/cognitiveservices/voices/list"
    response = await client.get(url, headers)
    data = json.loads(response)
    lang_models.extend([MttsLangModel(m) for m in data])
    return lang_models


@listener(command="mtts", description="文本转语音",
          parameters="[str]\r\nmtts setname [str]\r\nmtts setrate [int]\r\nmtts setvolume [int]\r\nmtts list [str]")
async def mtts(msg: Message):
    opt = msg.arguments
    replied_msg = msg.reply_to_message
    if opt.startswith("setname "):
        model_name = opt.split(" ")[1]
        status = await config_set(model_name, "short_name")
        if not status:
            await msg.edit("❗️ tts setting  error")
        await msg.edit(
            "successfully set up mtts voice model to:{}".format(model_name))
    elif opt.startswith("setrate "):
        model_name = opt.split(" ")[1]
        status = await config_set(model_name, "rate")
        if not status:
            await msg.edit("❗️ tts setting  error")
        await msg.edit(
            "successfully set up mtts voice rate to:{}".format(model_name))
    elif opt.startswith("setvolume "):
        model_name = opt.split(" ")[1]
        status = await config_set(model_name, "volume")
        if not status:
            await msg.edit("❗️ tts setting  error")
        await msg.edit(
            "successfully set up mtts voice volume to:{}".format(model_name))
    elif opt.startswith("list "):
        tag = opt.split(" ")[1]
        try:
            voice_model = await getmodel()
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
            mp3_buffer = edge_tts.Communicate(text=opt,
                                              voice=config["short_name"],
                                              rate=config["rate"],
                                              volume=config["volume"])
        except:
            return await msg.edit("无法访问微软api，请稍后重试。")
        await mp3_buffer.save(output)

        if replied_msg is None:
            await msg.reply_voice(output)
            await msg.delete()
        else:
            await msg.reply_voice(
                output, reply_to_message_id=replied_msg.id)
            await msg.delete()
    elif replied_msg:
        config = await config_check()
        try:
            mp3_buffer = edge_tts.Communicate(text=replied_msg.text,
                                              voice=config["short_name"],
                                              rate=config["rate"],
                                              volume=config["volume"])
        except:
            return await msg.edit("无法访问微软api，请稍后重试。")
        await mp3_buffer.save(output)
        await msg.reply_voice(output,
                              reply_to_message_id=replied_msg.id)
        await msg.delete()
    elif opt is None or opt == " ":
        await msg.edit("error, please use help command to show use case")
