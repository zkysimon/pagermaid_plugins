from pyrogram import Client
from pagermaid.listener import listener
from pagermaid.utils import Message, client, execute


async def obtain_message(context) -> str:
    reply = context.reply_to_message
    message = context.arguments
    if reply and not message:
        message = reply.text
    return message


async def get_api(api: str) -> str:
    tmp = ""
    resp = await client.get(api)
    if resp.status_code == 200:
        data = resp.json()
        tmp = "ip:{}\r\nasn:{}\r\norganization:{}\r\ncountry:{}\r\ntype:{}".format(data["ip"], data["asn"]["number"], data["asn"]["organization"], data["country"]["name"], data["type"]["is"])
    if tmp:
        return tmp
    else:
    	return "😂 No Response ~"


@listener(
    is_plugin=True,
    outgoing=True,
    command="ip",
    description="查询ip信息",
    parameters="[ip]/me"
)
async def ip(_: Client, msg: Message):
    address = await obtain_message(msg)
    if not address:
        return await msg.edit("请输入要查询的ip")
    elif address == "me":
        address = ""
    api = "https://ip.186526.xyz/{}?type=json&format=true".format(address)
    text = await get_api(api)
    await msg.edit(f"`{text}`")


@listener(
    is_plugin=True,
    outgoing=True,
    command="route",
    description="besttrace 路由回程追踪",
    parameters="[ip]"
)
async def route(_: Client, msg: Message):
    ip = await obtain_message(msg)
    await msg.edit("正在路由追踪中，请稍候。")
    result = await execute(f"mkdir -p shell && cd shell && wget -q https://raw.githubusercontent.com/fscarmen/tools/main/return_pure.sh -O return.sh && bash return.sh {ip}")
    if result:
        if len(result) > 4096:
            await attach_log(result, msg.chat.id, f"{ip}.log", msg.id)
            return
        await msg.edit(result)
    else:
        return
