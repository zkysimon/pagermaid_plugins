import asyncio
from pagermaid.listener import listener
from pagermaid.single_utils import sqlite
from pagermaid.utils import Message, client


async def obtain_message(context) -> str:
    reply = context.reply_to_message
    message = context.arguments
    if reply and not message:
        message = reply.text
    return message


async def config_check() -> dict:
    if not sqlite.get("oracle", {}):
        sqlite["oracle"] = {"tenant": []}
    return sqlite["oracle"]


@listener(
    is_plugin=True,
    outgoing=True,
    command="oracle",
    description="查询oracle账号存活情况",
    parameters="[tenant]/[add tenant]/[del tenant]/[delall]"
)
async def oracle(message: Message):
    msg = await obtain_message(message)
    await message.edit("请稍后。。。")
    if msg.startswith("add "):
        tenant = msg.lstrip("add ").split(" ")
        if not tenant:
            return await message.edit("请填入租户名")
        config = await config_check()
        count = 0
        for i in tenant:
            if i not in config["tenant"]:
                config["tenant"].append(i)
                count += 1
        if count < 1:
            return await message.edit("添加失败")
        sqlite["oracle"] = config
        return await message.edit(f"{count}个租户名添加成功")
    elif msg.startswith("del "):
        if not sqlite.get("oracle", {}):
            return await message.edit("请先添加租户名")
        tenant = msg.lstrip("del ").split(" ")
        if not tenant:
            return await message.edit("请填入租户名")
        config = await config_check()
        count = 0
        for i in tenant:
            config["tenant"].remove(i)
            count += 1
        if count < 1:
            return await message.edit("添加失败")
        sqlite["oracle"] = config
        return await message.edit(f"{count}个租户名删除成功")
    elif msg.startswith("delall"):
        config = await config_check()
        config["tenant"] = []
        sqlite["oracle"] = config
        return await message.edit("所有租户名已删除")
    elif not msg:
        t = f = 0
        config = await config_check()
        tenant = config["tenant"]
        task_list = []
        for i in tenant:
            url = f"https://login.ap-tokyo-1.oraclecloud.com/v1/tenantMetadata/{i}"
            result = check((await client.get(url)).json().get("tenantHomeRegionUrl"), i)
            if result:
                t += 1
            else:
                f += 1
            task = asyncio.create_task(result)
            task_list.append(task)
        await asyncio.gather(*task_list)
        await message.edit(f"你的甲骨文还有{t}个账号活着，{f}个账号已死")
    else:
        if " " in msg:
            return await message.edit("请输入单个租户名")
        url = f"https://login.ap-tokyo-1.oraclecloud.com/v1/tenantMetadata/{msg}"
        if await check((await client.get(url)).json().get("tenantHomeRegionUrl"), msg):
            return await message.edit("该账号存活")
        return await message.edit("该账号已死")


async def check(region, tenant):
    if not region:
        region = "https://login.ap-tokyo-1.oraclecloud.com/"
    checkurl = f"{region}v2/domains?tenant={tenant}"
    return (await client.get(checkurl)).json()
