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
    command="ipcheck",
    description="ip被墙检测",
    parameters="[ip:port]"
)
async def ipcheck(message: Message):
    msg = await obtain_message(message)
    await message.edit("请稍后。。。")
    i = msg.split(":")
    if not i[1]:
        i.append("443")
    result = await check_ip_port(i[0], i[1])
    in_icmp = "可用" if result["icmp"] == 'success' else "不可用"
    in_tcp = "可用" if result["tcp"] == 'success' else "不可用"
    out_icmp = "可用" if result["outside_icmp"] == 'success' else "不可用"
    out_tcp = "可用" if result["outside_icmp"] == 'success' else "不可用"
    await message.edit(f"IP：{i[0]}，port：{i[1]}\n"
                       f"国内检测结果：ICMP{in_icmp}；TCP{in_tcp}\n"
                       f"国外检测结果：ICMP{out_icmp}；TCP{out_tcp}")


async def check_ip_port(ip: str, port: str):
    url = "https://www.toolsdaquan.com/toolapi/public/ipchecking"
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
        "referer": "https://www.toolsdaquan.com/ipcheck/",
        "x-requested-with": "XMLHttpRequest"
    }
    resp = await client.post(f"{url}/{ip}/{port}", headers=headers)
    if resp.status_code == 200:
        inner_data = resp.json()
    else:
        resp.raise_for_status()
    resp2 = await client.post(f"{url}2/{ip}/{port}", headers=headers)
    if resp2.status_code == 200:
        outer_data = resp2.json()
        inner_data.update(outer_data)
    else:
        resp2.raise_for_status()
    return inner_data
