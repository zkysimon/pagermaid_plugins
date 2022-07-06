from sys import exit
from pagermaid.listener import listener
from pagermaid.utils import Message, execute
from pagermaid.single_utils import sqlite


@listener(
    is_plugin=True,
    outgoing=True,
    command="prefixes",
    description="更改命令前缀",
    parameters="[符号1|符号2|...] / reset"
)
async def prefixes(msg: Message):
    prefixes = msg.arguments
    reset = ",|，"
    if prefixes == "reset":
        prefixes == reset
    if not sqlite.get("prefixes", {}) or sqlite["prefixes"]["prefixes"] == reset:
        old_prefixes = reset
    else:
        old_prefixes = sqlite["prefixes"]["prefixes"]
    result = await execute(f"sed -i \'s/pattern = fr\"^({old_prefixes})/pattern = fr\"^({prefixes})/g\' pagermaid/listener.py")
    sqlite["prefixes"] = {"prefixes": prefixes}
    if len(result) > 0:
        await msg.edit(result)
    await msg.edit("修改成功，重启中。")
    exit(0)
    return
