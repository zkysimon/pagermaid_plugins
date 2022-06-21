from pagermaid.listener import listener
from pagermaid.utils import Message, client


async def obtain_message(context) -> str:
    reply = context.reply_to_message
    message = context.arguments
    if reply and not message:
        message = reply.text
    return message


@listener(
    is_plugin=True,
    outgoing=True,
    command="icp",
    description="查询icp备案消息",
    parameters="[domain]"
)
async def icp(context: Message):
    domain = await obtain_message(context)
    if not domain:
        return await context.edit("请输入/回复域名")
    await context.edit("正在获取中 . . .")
    try:
        req = await client.get(f"https://api.kukuqaq.com/icp?keyword={domain}")
    except:
        return await context.edit("出错了呜呜呜 ~ 试了好多次都无法访问到 API 服务器 。")
    if req.status_code == 200:
        result = req.json()
        return await context.edit(f'域名：`{result[0]["domain"]}`\r\n单位名称：`{result[0]["unitName"]}`\r\n备案号：`{result[0]["licence"]}`')
