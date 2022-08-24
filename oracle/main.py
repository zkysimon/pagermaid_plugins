import asyncio
from pagermaid.listener import listener
from pagermaid.single_utils import sqlite
from pagermaid.utils import Message, client


class Oracle:
    alive: int
    death: int
    void: int

    def __init__(self):
        self.alive = self.death = self.void = 0

    async def login(self, tenant):
        url = f"https://myservices-{tenant}.console.oraclecloud.com/mycloud/cloudportal/gettingStarted"
        try:
            resp = await client.head(url)
            if resp.status_code == 302:
                self.alive += 1
            else:
                self.death += 1
        except:
            self.void += 1

    async def api(self, tenant):
        url = f"https://login.ap-tokyo-1.oraclecloud.com/v1/tenantMetadata/{tenant}"
        resp = await client.get(url).json()
        if not resp["identityProviders"] and not resp["flights"]["isHenosisEnabled"]:
            self.void += 1
        region = resp.json().get("tenantHomeRegionUrl")
        if not region:
            region = "https://login.ap-tokyo-1.oraclecloud.com/"
        checkurl = f"{region}v2/domains?tenant={tenant}"
        result = (await client.get(checkurl)).json()
        if result:
            self.alive += 1
        else:
            self.death += 1

    async def clean(self):
        self.alive = self.death = self.void = 0


async def obtain_message(context) -> str:
    reply = context.reply_to_message
    message = context.arguments
    if reply and not message:
        message = reply.text
    return message


async def config_check() -> dict:
    if not sqlite.get("oracle", {}):
        sqlite["oracle"] = {
            "method": "api",
            "tenant": []
        }
    return sqlite["oracle"]


check = Oracle()


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
        tenant = msg[4:].split(" ")
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
        tenant = msg[4:].split(" ")
        if not tenant:
            return await message.edit("请填入租户名")
        config = await config_check()
        count = 0
        for i in tenant:
            config["tenant"].remove(i)
            count += 1
        if count < 1:
            return await message.edit("删除失败")
        sqlite["oracle"] = config
        return await message.edit(f"{count}个租户名删除成功")
    elif msg.startswith("delall"):
        config = await config_check()
        config["tenant"] = []
        sqlite["oracle"] = config
        return await message.edit("所有租户名已删除")
    elif msg == "list":
        config = await config_check()
        result = "当前已添加租户名有："
        for i in config["tenant"]:
            result += f"{i} "
        await message.edit(result)
        await asyncio.sleep(10)
        await message.delete()
    elif msg == "change":
        config = await config_check()
        if config["method"] == "api":
            config["method"] = "login"
        else:
            config["method"] = "api"
        sqlite["oracle"] = config
    elif not msg:
        config = await config_check()
        task_list = []
        for i in config["tenant"]:
            if config["method"] == "api":
                result = check.api(i)
            else:
                result = check.login(i)
            task = asyncio.create_task(result)
            task_list.append(task)
        await asyncio.gather(*task_list)
        text = f"通过{config['method']}方式检测：\n你的甲骨文：{check.alive}个账号活着，{check.death}个账号已死"
        await message.edit(text)
        await check.clean()
        await asyncio.sleep(10)
        await message.delete()
    else:
        if " " in msg:
            return await message.edit("请输入单个租户名")
        config = await config_check()
        if config["method"] == "api":
            await check.api(msg)
        else:
            await check.login(msg)
        if check.alive:
            await message.edit("该租户名存在")
        elif check.void:
            await message.edit("该租户名不存在")
        elif check.death:
            await message.edit("该租户名已死")
        else:
            await message.edit("API出错，请稍后重试")
        await check.clean()
