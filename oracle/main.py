from pagermaid.listener import listener
from pagermaid.utils import Message, client
from pagermaid.single_utils import sqlite


async def obtain_message(context) -> str:
    reply = context.reply_to_message
    message = context.arguments
    if reply and not message:
        message = reply.text
    return message


@listener(
    is_plugin=True,
    outgoing=True,
    command="oracle",
    description="查询oracle账号存活情况",
    parameters="[tenant]/[add tenant]/[del tenant]/[delall]"
)
async def oracle(message: Message):
    msg = await obtain_message(message)
    if msg.startswith("add "):
        if not sqlite.get('oracle', []):
            sqlite["oracle"] = []
        tenant = msg.lstrip("add ").split(" ")
        if not tenant:
            message.edit("请填入租户名")
        for i in tenant:
            sqlite["oracle"].append(i)
        message.edit("添加成功")
    elif msg.startswith("del "):
        if not sqlite.get('oracle', []):
            return message.edit("请先添加邮箱")
        tenant = msg.lstrip("del ").split(" ")
        if not tenant:
            message.edit("请填入租户名")
        for i in tenant:
            sqlite["oracle"].remove(i)
        message.edit("删除成功")
    elif msg.startswith("delall"):
        sqlite["oracle"] = []
        return
    elif not msg:
        t = f = 0
        tenant = sqlite["oracle"]
        for i in tenant:
            if await check(i):
                t += 1
            else:
                f += 1
        await message.edit(f"你的甲骨文还有{t}个账号活着，{f}个账号已死")
    else:
        tenant = msg.split(" ")
        if tenant[1]:
            await message.edit("请输入单个租户名")
        if await check(tenant[0]):
            await message.edit("该账号存活")


async def check(tenant):
    url = f"https://login.ap-tokyo-1.oraclecloud.com/v1/tenantMetadata/{tenant}"
    region = (await client.get(url)).json().get("tenantHomeRegionUrl")
    if not region:
        region = "https://login.ap-tokyo-1.oraclecloud.com/"
    checkurl = f"{region}v2/domains?tenant={tenant}"
    return (await client.get(checkurl)).json()
