from datetime import datetime
from lunar_python import Solar, Lunar
from pagermaid.listener import listener
from pagermaid.utils import Message


@listener(
    is_plugin=True,
    outgoing=True,
    command="lunar",
    description="查询今日黄历"
)
async def lunar(msg: Message):
    try:
        solar = Solar.fromDate(datetime.now())
        lunar = Lunar.fromDate(datetime.now())
    except:
        return await msg.edit("可能未安装模块，请使用`pip3 install lunar_python`安装")
    yiji = "宜："
    for i in lunar.getDayYi():
    	yiji += f"{i} "
    yiji += "\r\n忌："
    for i in lunar.getDayJi():
    	yiji += f"{i} "
    await msg.edit(f"{solar.toFullString()}\r\n\r\n{lunar.toFullString()}\r\n{yiji}")
