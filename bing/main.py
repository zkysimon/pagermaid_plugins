from pagermaid.listener import listener
from pagermaid.utils import Message, client
from pyrogram import Client


subscription_key = "c3000517c9384cceb9225c0dc1f6bdcb"
search_url = "https://api.bing.microsoft.com/v7.0/search"


async def obtain_message(context) -> str:
    reply = context.reply_to_message
    message = context.arguments
    if reply and not message:
        message = reply.text
    return message


async def bing_search(query):
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}
    params = {"q": query, "mkt": "zh-cn"}
    response = await client.get(search_url, headers=headers, params=params)
    result = response.json()
    results = ""
    for i in result['webPages']['value']:
        title = i['name'][0:30] + '...'
        link = i['url']
        results += f"\n[{title}]({link}) \n"
    print(results)
    return results


@listener(
    is_plugin=True,
    outgoing=True,
    command="bing",
    description="使用 bing 查询",
    parameters="[搜索内容]"
)
async def bing(_: Client, context: Message):
    msg = await obtain_message(context)
    await context.edit("正在拉取结果 . . .")
    if not msg:
        return await context.edit("请输入要查询的内容。。。")
    query = msg.replace(' ', '+')
    results = await bing_search(query)
    await context.edit(f"**bing** |`{query}`| 🎙 🔍 \n{results}", disable_web_page_preview=True)
