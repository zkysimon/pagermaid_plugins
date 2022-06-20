from pyrogram import Client
from pagermaid.listener import listener
from pagermaid.utils import Message, execute


@listener(
    is_plugin=True,
    outgoing=True,
    command="dc",
    description="用户或机器人分配的 DC"
)
async def dc(_: Client, msg: Message):
    reply = msg.reply_to_message
    if msg.arguments:
        return await msg.edit("您好像输入了一个无效的参数。")
    try:
        if reply:
            user = await _.get_users(reply.from_user.id)
        else:
            user = await _.get_me()
    except:
        msg.edit("请回复一名用户或者机器人使用。")
    if user.dc_id:
        await msg.edit(f"所在数据中心为: **DC{user.dc_id}**")
    else:
        await msg.edit("需要先设置头像并且对我可见。")


@listener(
    is_plugin=True,
    outgoing=True,
    command="pingdc",
    description="查询到各个DC区的延时"
)
async def pingdc(_: Client, msg: Message):
    DCs = {
        1: "149.154.175.50",
        2: "149.154.167.51",
        3: "149.154.175.100",
        4: "149.154.167.91",
        5: "91.108.56.130"
    }
    data = []
    for dc in range(1, 6):
        result = await execute(f"ping -c 1 {DCs[dc]} | awk -F '/' " + "'END {print $5}'")
        data.append(result.replace('\n', '') if result else '-1')

    await msg.edit(
        f"🇺🇸 DC1(迈阿密): `{data[0]}ms`\n"
        f"🇳🇱 DC2(阿姆斯特丹): `{data[1]}ms`\n"
        f"🇺🇸 DC3(迈阿密): `{data[2]}ms`\n"
        f"🇳🇱 DC4(阿姆斯特丹): `{data[3]}ms`\n"
        f"🇸🇬 DC5(新加坡): `{data[4]}ms`"
    )
