from sys import exit
from pagermaid.listener import listener
from pagermaid.utils import Message, execute
from pagermaid.modules.reload import reload_all

@listener(
    is_plugin=True,
    outgoing=True,
    command="prefixes",
    description="更改命令前缀",
    parameters="[旧符号] [新符号]"
)
async def prefixes(msg: Message):
    arg = msg.arguments
    if not arg:
        return msg.edit("参数错误")
    old_prefixes = msg.arguments.split(" ")[0]
    new_prefixes = msg.arguments.split(" ")[1]
    result = await execute(f"sed -i \'s/pattern = fr\"^{old_prefixes}/pattern = fr\"^{new_prefixes}/g\' pagermaid/listener.py")
    if len(result) > 0:
        await msg.edit(result)
    await msg.edit("修改成功，重启中。")
    exit(1)
