"""
PMCaptcha - A PagerMaid-Pyro plugin by cloudreflection
v2 rewritten by Sam
https://t.me/cloudreflection_channel/268
ver 2022/07/01
"""

import re
import time
import html
import asyncio
import inspect
import traceback
from dataclasses import dataclass, field
from io import BytesIO
from typing import Optional, Callable, Union, Dict, List

from pyrogram.errors import FloodWait
from pyrogram.enums.chat_type import ChatType
from pyrogram.enums.parse_mode import ParseMode
from pyrogram.raw.functions.account import UpdateNotifySettings, ReportPeer
from pyrogram.raw.functions.messages import DeleteHistory
from pyrogram.raw.types import InputNotifyPeer, InputPeerNotifySettings, InputReportReasonSpam
from pyrogram.types import User

from pagermaid import bot
from pagermaid.config import Config
from pagermaid.sub_utils import Sub
from pagermaid.utils import Message
from pagermaid.listener import listener
from pagermaid.single_utils import sqlite

cmd_name = "pmcaptcha"
version = "2.01"

# Log Collect
log_collect_bot = "CloudreflectionPmcaptchabot"
img_captcha_bot = "PagerMaid_Sam_Bot"

whitelist = Sub("pmcaptcha.success")

punishment_queue = asyncio.Queue()
punishment_task: Optional[asyncio.Task] = None

challenge_task: Dict[int, asyncio.Task] = {}
curr_captcha: Dict[int, Union["MathChallenge", "ImageChallenge"]] = {}


async def log(message: str, remove_prefix: bool = False):
    if not Config.LOG:
        return
    message = message if remove_prefix else " ".join(("[PMCaptcha]", message))
    try:
        await bot.send_message(Config.LOG_ID, message, ParseMode.HTML)
    except Exception as e:  # noqa
        print(f"Err: {e}\n{traceback.format_exc()}")


def lang(lang_id: str, lang_code: str = Config.LANGUAGE) -> str:
    lang_code = lang_code or "en"
    return lang_dict.get(lang_id)[1 if lang_code.startswith("zh") else 0]


def code(text: str) -> str:
    return f"<code>{text}</code>"


def italic(text: str) -> str:
    return f"<i>{text}</i>"


def bold(text: str) -> str:
    return f"<b>{text}</b>"


def gen_link(text: str, url: str) -> str:
    return f"<a href=\"{url}\">{text}</a>"


lang_dict = {
    # region General
    "no_cmd_given": [
        "Please use this command in private chat, or add parameters to execute.",
        "?????????????????????????????????????????????????????????"
    ],
    "invalid_user_id": [
        "Invalid User ID",
        "?????????????????????????????? ID"
    ],
    "invalid_param": [
        "Invalid Parameter",
        "???????????????"
    ],
    "enabled": [
        "Enabled",
        "??????"
    ],
    "disabled": [
        "Disabled",
        "??????"
    ],
    "none": [
        "None",
        "???"
    ],
    "tip_edit": [
        f"You can edit this by using {code('%s')}",
        f"???????????????????????? {code('%s')}"
    ],
    "tip_run_in_pm": [
        "You can only run this command in private chat, or by adding parameters.",
        "??????????????????????????????????????????????????????"
    ],
    # endregion

    # region Plugin
    "plugin_desc": [
        "Captcha for PM\nPlease use %s to see available commands.",
        f"????????????????????????\n????????? %s ??????????????????"
    ],
    # endregion

    # region Vocabs
    "vocab_msg": [
        "Message",
        "??????"
    ],
    "vocab_array": [
        "List",
        "??????"
    ],
    "vocab_bool": [
        "Boolean",
        "y / n"
    ],
    "vocab_int": [
        "Integer",
        "??????"
    ],
    "vocab_cmd": [
        "Command",
        "??????"
    ],
    # endregion

    # region Verify
    "verify_verified": [
        "Verified user",
        "???????????????"
    ],
    "verify_unverified": [
        "Unverified user",
        "???????????????"
    ],
    "verify_blocked": [
        "You were blocked.",
        "???????????????"
    ],
    "verify_log_punished": [
        "User %s has been %s.",
        "???????????? %s ??????`%s`??????"
    ],
    "verify_challenge": [
        "Please answer this question to prove you are human (1 chance)",
        "????????????????????????????????????????????? (????????????)"
    ],
    "verify_challenge_timed": [
        "You have %i seconds.",
        "?????? %i ????????????????????????"
    ],
    "verify_passed": [
        "Verification passed.",
        "????????????"
    ],
    "verify_failed": [
        "Verification failed.",
        "????????????"
    ],
    # endregion

    # region Help
    "cmd_param": [
        "Parameter",
        "??????"
    ],
    "cmd_param_optional": [
        "Optional",
        "??????"
    ],
    "cmd_alias": [
        "Alias",
        "??????/????????????"
    ],
    "cmd_detail": [
        f"Do {code(f',{cmd_name} h [command]')} for details",
        f"????????????????????? {code(f',{cmd_name} h [????????????]')}",
    ],
    "cmd_not_found": [
        "Command Not Found",
        "???????????????"
    ],
    "cmd_list": [
        "Command List",
        "????????????"
    ],
    "priority": [
        "Priority",
        "?????????"
    ],
    # endregion

    # region Check
    "user_verified": [
        f"User {code('%i')} {italic('verified')}",
        f"?????? {code('%i')} {italic('?????????')}"
    ],
    "user_unverified": [
        f"User {code('%i')} {bold('unverified')}",
        f"?????? {code('%i')} {bold('?????????')}"
    ],
    # endregion

    # region Add / Delete
    "add_whitelist_success": [
        f"User {code('%i')} added to whitelist",
        f"?????? {code('%i')} ?????????????????????"
    ],
    "remove_verify_log_success": [
        f"Removed User {code('%i')}'s verify record",
        f"??????????????? {code('%i')} ???????????????"
    ],
    "verify_log_not_found": [
        f"Verify record not found for User {code('%i')}",
        f"??????????????? {code('%i')} ???????????????"
    ],
    # endregion

    # region Unstuck
    "unstuck_success": [
        f"User {code('%i')} has removed from challenge mode",
        f"?????? {code('%i')} ?????????????????????"
    ],
    "not_stuck": [
        f"User {code('%i')} is not stuck",
        f"?????? {code('%i')} ??????????????????"
    ],
    # endregion

    # region Welcome
    "welcome_curr_rule": [
        "Current welcome rule",
        "?????????????????????????????????"
    ],
    "welcome_set": [
        "Welcome message set.",
        "???????????????????????????"
    ],
    "welcome_reset": [
        "Welcome message reset.",
        "???????????????????????????"
    ],
    # endregion

    # region Whitelist
    "whitelist_curr_rule": [
        "Current whitelist rule",
        "?????????????????????"
    ],
    "whitelist_set": [
        "Keywords whitelist set.",
        "???????????????????????????"
    ],
    "whitelist_reset": [
        "Keywords whitelist reset.",
        "???????????????????????????"
    ],
    # endregion

    # region Blacklist
    "blacklist_curr_rule": [
        "Current blacklist rule",
        "?????????????????????"
    ],
    "blacklist_set": [
        "Keywords blacklist set.",
        "???????????????????????????"
    ],
    "blacklist_reset": [
        "Keywords blacklist reset.",
        "???????????????????????????"
    ],
    "blacklist_triggered": [
        "Blacklist rule triggered",
        "???????????????????????????"
    ],
    # endregion

    # region Timeout
    "timeout_curr_rule": [
        "Current timeout: %i second(s)",
        "??????????????????: %i ???"
    ],
    "timeout_set": [
        "Verification timeout has been set to %i seconds.",
        "?????????????????????????????? %i ???"
    ],
    "timeout_off": [
        "Verification timeout disabled.",
        "???????????????????????????"
    ],
    "timeout_exceeded": [
        "Verification timeout.",
        "????????????"
    ],
    # endregion

    # region Disable PM
    "disable_pm_curr_rule": [
        "Current disable PM status: %s",
        "????????????????????????: ???%s"
    ],
    "disable_pm_tip_exception": [
        "This feature will automatically allow contents and whitelist users.",
        "???????????????????????????????????????????????????"
    ],
    "disable_pm_set": [
        f"Disable private chat has been set to {bold('%s')}.",
        f"????????????????????????{bold('%s')}"
    ],
    "disable_pm_enabled": [
        "Owner has private chat disabled.",
        "????????????????????????"
    ],
    # endregion

    # region Stats
    "stats_display": [
        "PMCaptcha has verified %i users in total.\n%i users has passed, %i users has been blocked.",
        "???????????????????????????????????? %i ???\n?????????????????? %i ???????????? %i ???"
    ],
    "stats_reset": [
        "Statistics has been reset.",
        "???????????????"
    ],
    # endregion

    # region Action
    "action_param_name": [
        "Action",
        "??????"
    ],
    "action_curr_rule": [
        "Current action rule",
        "????????????????????????"
    ],
    "action_set": [
        f"Action has been set to {bold('%s')}.",
        f"????????????????????????{bold('%s')}??????"
    ],
    "action_set_none": [
        "Action has been set to none.",
        "???????????????????????????????????????"
    ],
    "action_ban": [
        "Ban",
        "??????"
    ],
    "action_delete": [
        "Ban and delete",
        "?????????????????????"
    ],
    "action_archive": [
        "Ban and archive",
        "???????????????"
    ],
    # endregion

    # region Report
    "report_curr_rule": [
        "Current report state: %s",
        "?????????????????????: %s"
    ],
    "report_set": [
        f"Report has been set to {bold('%s')}.",
        f"????????????????????????{bold('%s')}"
    ],
    # endregion

    # region Premium
    "premium_curr_rule": [
        "Current premium user rule",
        "?????? Premium ????????????"
    ],
    "premium_set_allow": [
        f"Telegram Premium users will be allowed to {bold('bypass')} the captcha.",
        f"???{bold('??????')} Telegram Premium ??????{bold('????????????')}"
    ],
    "premium_set_ban": [
        f"Telegram Premium users will be {bold('banned')} from private chat.",
        f"???{bold('??????')} Telegram Premium ????????????"
    ],
    "premium_set_only": [
        f"{bold('Only allowed')} Telegram Premium users to private chat.",
        f"???{bold('?????????')} Telegram Premium ????????????"
    ],
    "premium_set_none": [
        "Nothing will do to Telegram Premium",
        "????????? Telegram Premium ????????????????????????"
    ],
    "premium_only": [
        "Owner only allows Telegram Premium users to private chat.",
        "??????????????? Telegram Premium ????????????"
    ],
    "premium_ban": [
        "Owner bans Telegram Premium users from private chat.",
        "???????????? Telegram Premium ????????????"
    ],
    # endregion

    # region Silent
    "silent_curr_rule": [
        "Current silent status: %s",
        "??????????????????: ???%s"
    ],
    "silent_set": [
        f"Silent has been set to {bold('%s')}.",
        f"????????????????????????{bold('%s')}"
    ],
    # endregion

    # region Collect Logs
    "collect_logs_curr_rule": [
        "Current collect logs status: %s",
        "????????????????????????: ???%s"
    ],
    "collect_logs_note": [
        ("This feature will only collect user information and chat logs of non-verifiers "
         f"via @{log_collect_bot} , and is not provided to third parties (except @LivegramBot ).\n"
         "Information collected will be used for PMCaptcha improvements, "
         "toggling this feature does not affect the use of PMCaptcha."),
        (f"????????????????????? @{log_collect_bot} ??????????????????????????????????????????????????????????????????????????????"
         "???????????????????????????(@LivegramBot ??????)???\n???????????????????????? PMCaptcha ?????????????????????????????????????????? PMCaptcha ????????????")
    ],
    "collect_logs_set": [
        "Collect logs has been set to %s.",
        "???????????????????????? %s"
    ],
    # endregion

    # region Captcha Type
    "type_curr_rule": [
        "Current captcha type: %s",
        "?????????????????????: %s"
    ],
    "type_set": [
        f"Captcha type has been set to {bold('%s')}.",
        f"??????????????????????????? {bold('%s')}"
    ],
    "type_param_name": [
        "Type",
        "??????"
    ],
    "type_captcha_img": [
        "Image",
        "????????????"
    ],
    "type_captcha_math": [
        "Math",
        "??????"
    ],
    # endregion

    # region Image Captcha Type
    "img_captcha_type_func": [
        "funCaptcha",
        "funCaptcha",
    ],
    "img_captcha_type_github": [
        "GitHub",
        "GitHub",
    ],
    "img_captcha_type_rec": [
        "reCaptcha",
        "reCaptcha"
    ],
    "img_captcha_retry_curr_rule": [
        "Current max retry for image captcha: %s",
        "???????????????????????????????????????: %s"
    ],
    "img_captcha_retry_set": [
        "Max retry for image captcha has been set to %s.",
        "????????????????????????????????????????????? %s"
    ],
    # endregion
}


# noinspection DuplicatedCode
@dataclass
class SubCommand:
    msg: Message

    # Regex
    alias_rgx = r":alias: (.+)"
    param_rgx = r":param (opt)?\s?(\w+):\s?(.+)"

    def _extract_docs(self, subcmd_name: str, text: str) -> str:
        extras = []
        if result := re.search(self.param_rgx, text):
            is_optional = f"({italic(lang('cmd_param_optional'))} ) " if result[1] else ""
            extras.extend(
                (
                    f"{lang('cmd_param')}:",
                    f"{is_optional}{code(result[2].lstrip('_'))} - {result[3]}",
                )
            )

            text = re.sub(self.param_rgx, "", text)
        if result := re.search(self.alias_rgx, text):
            alias = result[1].replace(" ", "").split(",")
            alia_text = ", ".join(code(a) for a in alias)
            extras.append(f"{lang('cmd_alias')}: {alia_text}")
            text = re.sub(self.alias_rgx, "", text)
        len(extras) and extras.insert(0, "")
        subcmd_name = "" if cmd_name == subcmd_name else self._get_cmd_with_param(subcmd_name)
        return "\n".join([
                             code(f",{cmd_name} {subcmd_name}".strip()),
                             re.sub(r" {4,}", "", text).replace("{cmd_name}", cmd_name).strip()
                         ] + extras)

    def _get_cmd_with_param(self, subcmd_name: str) -> str:
        msg = subcmd_name
        if result := re.search(self.param_rgx, getattr(self, msg).__doc__):
            param = result[2].lstrip("_")
            msg += f" [{param}]" if result[1] else html.escape(f" <{param}>")
        return msg

    def _get_mapped_alias(self, alias_name: str, ret_type: str):
        # Get alias function
        for name, func in inspect.getmembers(self, inspect.iscoroutinefunction):
            if name.startswith("_"):
                continue
            if result := re.search(self.alias_rgx, func.__doc__):
                if alias_name in result[1].replace(" ", "").split(","):
                    return func if ret_type == "func" else name

    def __getitem__(self, cmd: str) -> Optional[Callable]:
        # Get subcommand function
        if func := getattr(self, cmd, None):
            return func
        # Check for alias
        if func := self._get_mapped_alias(cmd, "func"):
            return func
        return  # Not found

    async def pmcaptcha(self):
        """????????????????????????????????????"""
        if self.msg.chat.type != ChatType.PRIVATE:
            await self.msg.edit(lang('tip_run_in_pm'), parse_mode=ParseMode.HTML)
        else:
            await self.msg.edit(lang(f'verify_{"" if whitelist.check_id(self.msg.chat.id) else "un"}verified'))
        await asyncio.sleep(5)
        await self.msg.safe_delete()

    async def help(self, command: Optional[str] = None):
        """????????????????????????

        :param opt command: ????????????
        :alias: h
        """
        help_msg = [f"{code('PMCaptcha')} {lang('cmd_list')} (v{version}):", ""]
        footer = [
            italic(lang('cmd_detail')),
            "",
            f"{lang('priority')}: disable_pm > premium > whitelist > blacklist",
            f"???????????????????????? {code(',apt update')} ????????????????????????",
            "??????: cloudreflection.eu.org/donate"
        ]
        if command:  # Single command help
            func = getattr(self, command, self._get_mapped_alias(command, "func"))
            return await (
                self.msg.edit_text(self._extract_docs(func.__name__, func.__doc__), parse_mode=ParseMode.HTML)
                if func else self.msg.edit_text(f"{lang('cmd_not_found')}: {code(command)}", parse_mode=ParseMode.HTML))
        for name, func in inspect.getmembers(self, inspect.iscoroutinefunction):
            if name.startswith("_"):
                continue
            help_msg.append(
                (
                        code(f",{cmd_name} {self._get_cmd_with_param(name)}")
                        + f"\n> {re.search(r'(.+)', func.__doc__)[1].strip()}\n"
                )
            )

        if self.msg.chat.type != ChatType.PRIVATE:
            await self.msg.edit_text(lang('tip_run_in_pm'), parse_mode=ParseMode.HTML)
            await asyncio.sleep(5)
            return await self.msg.safe_delete()
        await self.msg.edit_text("\n".join(help_msg + footer), parse_mode=ParseMode.HTML)

    async def check(self, _id: int):
        """??????????????????????????????

        :param _id: ?????? ID
        """
        try:
            _id = _id and int(_id) or self.msg.chat.id
            verified = whitelist.check_id(_id)
            await self.msg.edit(lang(f"user_{'' if verified else 'un'}verified") % _id, parse_mode=ParseMode.HTML)
        except ValueError:
            await self.msg.edit(lang('invalid_user_id'), parse_mode=ParseMode.HTML)

    async def add(self, _id: Optional[int] = None):
        """??? ID ??????????????????????????????????????????????????? ID

        :param opt _id: ?????? ID
        """
        try:
            if not _id and self.msg.chat.type != ChatType.PRIVATE:
                return await self.msg.edit(lang('tip_run_in_pm'), parse_mode=ParseMode.HTML)
            _id = _id and int(_id) or self.msg.chat.id
            whitelist.add_id(_id)
            await bot.unarchive_chats(chat_ids=_id)
            await self.msg.edit(lang('add_whitelist_success') % _id, parse_mode=ParseMode.HTML)
        except ValueError:
            await self.msg.edit(lang('invalid_user_id'), parse_mode=ParseMode.HTML)

    async def delete(self, _id: Optional[int] = None):
        """?????? ID ???????????????????????????????????????????????? ID

        :param opt _id: ?????? ID
        :alias: del
        """
        try:
            if not _id and self.msg.chat.type != ChatType.PRIVATE:
                return await self.msg.edit(lang('tip_run_in_pm'), parse_mode=ParseMode.HTML)
            _id = _id and int(_id) or self.msg.chat.id
            text = lang('remove_verify_log_success' if whitelist.del_id(_id) else 'verify_log_not_found')
            await self.msg.edit(text % _id, parse_mode=ParseMode.HTML)
        except ValueError:
            await self.msg.edit(lang('invalid_user_id'), parse_mode=ParseMode.HTML)

    async def unstuck(self, _id: Optional[int] = None):
        """???????????????????????????????????????????????????????????????????????????

        :param _id: ?????? ID
        """
        try:
            if not _id and self.msg.chat.type != ChatType.PRIVATE:
                return await self.msg.edit(lang('tip_run_in_pm'), parse_mode=ParseMode.HTML)
            _id = _id and int(_id) or self.msg.chat.id
            if sqlite.get(f"pmcaptcha.challenge.{_id}"):
                del sqlite[f"pmcaptcha.challenge.{_id}"]
                return await self.msg.edit(lang('unstuck_success') % _id, parse_mode=ParseMode.HTML)
            await self.msg.edit(lang('not_stuck') % _id, parse_mode=ParseMode.HTML)
        except ValueError:
            await self.msg.edit(lang('invalid_user_id'), parse_mode=ParseMode.HTML)

    async def welcome(self, *message: str):
        """?????????????????????????????????????????????
        ?????? <code>,{cmd_name} welcome -clear</code> ?????????????????????

        :param message: ????????????
        :alias: wel
        """
        data = sqlite.get("pmcaptcha", {})
        if not message:
            return await self.msg.edit_text("\n".join((
                lang('welcome_curr_rule') + ":",
                code(data.get('welcome', lang('none'))),
                "",
                lang('tip_edit') % html.escape(f",{cmd_name} wel <{lang('vocab_msg')}>")
            )), parse_mode=ParseMode.HTML)
        message = " ".join(message)
        if message == "-clear":
            if data.get("welcome"):
                del data["welcome"]
                sqlite["pmcaptcha"] = data
            await self.msg.edit(lang('welcome_reset'), parse_mode=ParseMode.HTML)
            return
        data["welcome"] = message
        sqlite["pmcaptcha"] = data
        await self.msg.edit(lang('welcome_set'), parse_mode=ParseMode.HTML)

    async def whitelist(self, array: str):
        """???????????????????????????????????????????????????????????????
        ?????? <code>,{cmd_name} whitelist -clear</code> ???????????????

        :param array: ??????????????? (??????????????????)
        :alias: wl, whl
        """
        data = sqlite.get("pmcaptcha", {})
        if not array:
            return await self.msg.edit_text("\n".join((
                lang('whitelist_curr_rule') + ":",
                code(data.get('whitelist', lang('none'))),
                "",
                lang('tip_edit') % html.escape(f",{cmd_name} wl <{lang('vocab_array')}>")
            )), parse_mode=ParseMode.HTML)
        if array == "-clear":
            if data.get("whitelist"):
                del data["whitelist"]
                sqlite["pmcaptcha"] = data
            await self.msg.edit(lang('whitelist_reset'), parse_mode=ParseMode.HTML)
            return
        data["whitelist"] = array.replace(" ", "").split(",")
        sqlite["pmcaptcha"] = data
        await self.msg.edit(lang('whitelist_set'), parse_mode=ParseMode.HTML)

    async def blacklist(self, array: str):
        """??????????????????????????????????????? (??????????????????)
        ?????? <code>,{cmd_name} blacklist -clear</code> ???????????????

        :param array: ??????????????? (??????????????????)
        :alias: bl
        """
        data = sqlite.get("pmcaptcha", {})
        if not array:
            return await self.msg.edit_text("\n".join((
                lang('blacklist_curr_rule') + ":",
                code(data.get('blacklist', lang('none'))),
                "",
                lang('tip_edit') % html.escape(f",{cmd_name} bl <{lang('vocab_array')}>")
            )), parse_mode=ParseMode.HTML)
        if array == "-clear":
            if data.get("blacklist"):
                del data["blacklist"]
                sqlite["pmcaptcha"] = data
            await self.msg.edit(lang('blacklist_reset'), parse_mode=ParseMode.HTML)
            return
        data["blacklist"] = array.replace(" ", "").split(",")
        sqlite["pmcaptcha"] = data
        await self.msg.edit(lang('blacklist_set'), parse_mode=ParseMode.HTML)

    async def timeout(self, seconds: str):
        """??????????????????????????????????????? 30 ??? (<b>????????????????????????</b>)
        ?????? <code>,{cmd_name} wait off</code> ???????????????????????????

        :param seconds: ????????????????????????
        :alias: wait
        """
        data = sqlite.get("pmcaptcha", {})
        if not seconds:
            return await self.msg.edit_text("\n".join((
                lang('timeout_curr_rule') % int(data.get('timeout', 30)),
                "",
                lang('tip_edit') % html.escape(f",{cmd_name} wait <{lang('vocab_int')}>")
            )), parse_mode=ParseMode.HTML)
        if seconds == "off":
            if data.get("timeout"):
                data["timeout"] = 0
                sqlite["pmcaptcha"] = data
            await self.msg.edit(lang('timeout_off'), parse_mode=ParseMode.HTML)
            return
        try:
            data["timeout"] = int(seconds)
            sqlite["pmcaptcha"] = data
        except ValueError:
            return await self.msg.edit(lang('invalid_param'), parse_mode=ParseMode.HTML)
        await self.msg.edit(lang('timeout_set') % int(seconds), parse_mode=ParseMode.HTML)

    async def disable_pm(self, toggle: str):
        """?????? / ?????????????????????
        ???????????????????????????????????????(<i>???????????????</i>)??????
        ??????????????? <code>,{cmd_name} add</code> ????????????????????????

        :param toggle: ?????? (y / n)
        :alias: disablepm
        """
        data = sqlite.get("pmcaptcha", {})
        if not toggle:
            return await self.msg.edit_text("\n".join((
                lang('disable_pm_curr_rule') % lang('enabled' if data.get('disable') else 'disabled'),
                "",
                lang('tip_edit') % html.escape(f",{cmd_name} disablepm <{lang('vocab_bool')}>")
            )), parse_mode=ParseMode.HTML)
        toggle = toggle.lower()[0]
        if toggle not in ("y", "n", "t", "f", "1", "0"):
            return await self.msg.edit(lang('invalid_param'), parse_mode=ParseMode.HTML)
        data["disable"] = toggle in ("y", "t", "1")
        sqlite["pmcaptcha"] = data
        await self.msg.edit(lang('disable_pm_set') % lang("enabled" if data["disable"] else "disabled"),
                            parse_mode=ParseMode.HTML)

    async def stats(self, arg: str):
        """??????????????????
        ???????????? <code>,{cmd_name} stats -clear</code> ??????
        """
        data = sqlite.get("pmcaptcha", {})
        if not arg:
            data = (data.get('pass', 0) + data.get('banned', 0), data.get('pass', 0), data.get('banned', 0))
            return await self.msg.edit_text(f"{code('PMCaptcha')} {lang('stats_display') % data}",
                                            parse_mode=ParseMode.HTML)
        if arg == "-clear":
            data["pass"] = 0
            data["banned"] = 0
            sqlite["pmcaptcha"] = data
            await self.msg.edit(lang('stats_reset'), parse_mode=ParseMode.HTML)
            return

    async def action(self, action: str):
        """????????????????????????????????????????????? <code>archive</code>

        :param action: ???????????? (<code>ban</code> / <code>delete</code> / <code>archive</code> / <code>none</code>)
        :alias: act
        """
        data = sqlite.get("pmcaptcha", {})
        if not action:
            action = data.get("action", "archive")
            return await self.msg.edit_text("\n".join((
                lang('action_curr_rule') + ":",
                lang('action_set_none') if action == "none" else lang('action_set') % lang(f'action_{action}'),
                "",
                lang('tip_edit') % html.escape(f",{cmd_name} act <{lang('action_param_name')}>")
            )), parse_mode=ParseMode.HTML)
        if action not in ("ban", "delete", "archive", "none"):
            return await self.msg.edit(lang('invalid_param'), parse_mode=ParseMode.HTML)
        if action in ("ban", "delete", "archive"):
            await self.msg.edit(lang('action_set') % lang(f'action_{action}'), parse_mode=ParseMode.HTML)
        elif action == "none":
            await self.msg.edit(lang('action_set_none'), parse_mode=ParseMode.HTML)
        data["action"] = action
        sqlite["pmcaptcha"] = data

    async def report(self, toggle: str):
        """?????????????????????????????????????????????????????? <code>N</code>

        :param toggle: ?????? (y / n)
        """
        data = sqlite.get("pmcaptcha", {})
        if not toggle:
            return await self.msg.edit_text("\n".join((
                lang('report_curr_rule') % lang('enabled' if data.get('report') else 'disabled'),
                "",
                lang('tip_edit') % html.escape(f",{cmd_name} report <{lang('vocab_bool')}>")
            )), parse_mode=ParseMode.HTML)
        toggle = toggle.lower()[0]
        if toggle not in ("y", "n", "t", "f", "1", "0"):
            return await self.msg.edit(lang('invalid_param'), parse_mode=ParseMode.HTML)
        data["report"] = toggle in ("y", "t", "1")
        sqlite["pmcaptcha"] = data
        await self.msg.edit(lang('report_set') % lang("enabled" if data["report"] else "disabled"),
                            parse_mode=ParseMode.HTML)

    async def premium(self, action: str):
        """????????? <b>Premium</b> ??????????????????????????? <code>archive</code>

        :param action: ???????????? (<code>allow</code> / <code>ban</code> / <code>only</code> / <code>none</code>)
        :alias: vip, prem
        """
        data = sqlite.get("pmcaptcha", {})
        if not action:
            return await self.msg.edit_text("\n".join((
                lang('premium_curr_rule') + ":",
                lang(f'premium_set_{data.get("premium", "none")}'),
                "",
                lang('tip_edit') % html.escape(f",{cmd_name} prem <{lang('action_param_name')}>")
            )), parse_mode=ParseMode.HTML)
        if action not in ("allow", "ban", "only", "none"):
            return await self.msg.edit(lang('invalid_param'), parse_mode=ParseMode.HTML)
        if action == "none":
            del data["premium"]
        else:
            data["premium"] = action
        sqlite["pmcaptcha"] = data
        await self.msg.edit(lang(f'premium_set_{action}'), parse_mode=ParseMode.HTML)

    async def silent(self, toggle: Optional[str] = None):
        """?????????????????????????????? no
        ??????????????????????????????????????? (????????? log ??????)

        :param toggle: ?????? (yes / no)
        :alias: quiet
        """
        data = sqlite.get("pmcaptcha", {})
        if not toggle:
            return await self.msg.edit_text("\n".join((
                lang('silent_curr_rule') % lang('enabled' if data.get('silent', False) else 'disabled'),
                "",
                lang('tip_edit') % html.escape(f",{cmd_name} silent <{lang('vocab_bool')}>")
            )), parse_mode=ParseMode.HTML)
        toggle = toggle.lower()[0]
        if toggle not in ("y", "n", "t", "f", "1", "0"):
            return await self.msg.edit(lang('invalid_param'), parse_mode=ParseMode.HTML)
        data["silent"] = toggle in ("y", "t", "1")
        sqlite["pmcaptcha"] = data
        await self.msg.edit(lang('silent_set') % lang("enabled" if data["silent"] else "disabled"),
                            parse_mode=ParseMode.HTML)

    async def collect_logs(self, toggle: str):
        """??????????????????????????? <code>PMCaptcha</code> ?????????????????????????????????????????????
        ????????? N?????????????????????????????????????????????????????????????????????????????????

        :param toggle: ?????? (y / n)
        :alias: collect, log
        """
        data = sqlite.get("pmcaptcha", {})
        if not toggle:
            status = lang('enabled' if data.get('collect', False) else 'disabled')
            return await self.msg.edit_text("\n".join((
                lang('collect_logs_curr_rule') % status,
                lang("collect_logs_note"),
                "",
                lang('tip_edit') % html.escape(f",{cmd_name} log <{lang('vocab_bool')}>")
            )), parse_mode=ParseMode.HTML)
        toggle = toggle.lower()[0]
        if toggle not in ("y", "n", "t", "f", "1", "0"):
            return await self.msg.edit(lang('invalid_param'), parse_mode=ParseMode.HTML)
        data["collect"] = toggle in ("y", "t", "1")
        sqlite["pmcaptcha"] = data
        await self.msg.edit(lang('collect_logs_set') % lang("enabled" if data["collect"] else "disabled"))

    # Image Captcha

    async def change_type(self, _type: str):
        """????????????????????????????????? <code>math</code>
        ???????????????????????????????????????

        ???????????????????????????????????????????????????????????????

        :param _type: ??????????????? (<code>img</code> / <code>math</code>)
        :alias: type, typ
        """
        data = sqlite.get("pmcaptcha", {})
        if not _type:
            return await self.msg.edit_text("\n".join((
                lang('type_curr_rule') % lang(f'type_captcha_{data.get("type", "math")}'),
                "",
                lang('tip_edit') % html.escape(f",{cmd_name} typ <{lang('type_param_name')}>")
            )), parse_mode=ParseMode.HTML)
        if _type not in ("img", "math"):
            return await self.msg.edit(lang('invalid_param'), parse_mode=ParseMode.HTML)
        data["type"] = _type
        sqlite["pmcaptcha"] = data
        await self.msg.edit(lang('type_set') % lang(f'type_captcha_{_type}'), parse_mode=ParseMode.HTML)

    async def change_img_type(self, _type: str):
        """?????????????????????????????????????????? <code>func</code>
        ????????????????????????
        - <code>func</code> (<i>ArkLabs funCaptcha</i> )
        - <code>github</code> (<i>GitHub ????????????</i> )
        - <code>rec</code> (<i>Google reCAPTCHA</i> )
        ???????????? <code>reCAPTCHA</code> ?????????????????????<a href="https://t.me/c/1441461877/958395">????????????</a>???
        ???????????????????????????????????????????????? <code>func</code> ?????????????????????

        :param _type: ??????????????? (<code>func</code> / <code>github</code> / <code>rec</code>)
        :alias: img_type, img_typ
        """
        data = sqlite.get("pmcaptcha", {})
        if not _type:
            return await self.msg.edit_text("\n".join((
                lang('type_curr_rule') % lang(f'img_captcha_type_{data.get("img_type", "func")}'),
                "",
                lang('tip_edit') % html.escape(f",{cmd_name} img_typ <{lang('type_param_name')}>")
            )), parse_mode=ParseMode.HTML)
        if _type not in ("func", "github", "rec"):
            return await self.msg.edit(lang('invalid_param'), parse_mode=ParseMode.HTML)
        data["img_type"] = _type
        sqlite["pmcaptcha"] = data
        await self.msg.edit(
            lang('type_set') % lang(f'img_captcha_type_{_type}'),
            parse_mode=ParseMode.HTML,
        )

    async def img_retry_chance(self, number: str):
        """???????????????????????????????????????????????? <code>3</code>

        :param number: ????????????
        :alias: img_re
        """
        data = sqlite.get("pmcaptcha", {})
        if not number:
            return await self.msg.edit_text("\n".join((
                lang('img_captcha_retry_curr_rule') % data.get("img_max_retry", 3),
                "",
                lang('tip_edit') % html.escape(f",{cmd_name} img_re <{lang('vocab_int')}>")
            )), parse_mode=ParseMode.HTML)
        try:
            data["img_max_retry"] = int(number)
            sqlite["pmcaptcha"] = data
            await self.msg.edit(lang('img_captcha_retry_set') % number, parse_mode=ParseMode.HTML)
        except ValueError:
            return await self.msg.edit(lang('invalid_param'), parse_mode=ParseMode.HTML)


# region Captcha
async def punishment_worker(q: asyncio.Queue):
    data = None
    flood_text = "Flood Triggered: %is, command: %s, target: %s"
    while True:
        data = data or sqlite.get("pmcaptcha", {})
        target = None
        try:
            (target,) = await q.get()
            action = data.get("action", "archive")
            if action in ("ban", "delete", "archive"):
                for _ in range(3):
                    try:
                        await bot.block_user(user_id=target)
                        break
                    except FloodWait as e:
                        await log(flood_text % (e.value, "Block", target))
                        await asyncio.sleep(e.value)
                if action == "delete":
                    for _ in range(3):
                        try:
                            await bot.invoke(DeleteHistory(peer=await bot.resolve_peer(target), max_id=0))
                            break
                        except FloodWait as e:
                            await log(flood_text % (e.value, "Delete Message", target))
                            await asyncio.sleep(e.value)
                elif action == "archive":
                    for _ in range(3):
                        try:
                            await bot.archive_chats(chat_ids=target)
                            break
                        except FloodWait as e:
                            await log(flood_text % (e.value, "Archive", target))
                            await asyncio.sleep(e.value)
            data['banned'] = data.get('banned', 0) + 1
            sqlite['pmcaptcha'] = data
            chat_link = gen_link(str(target), f"tg://openmessage?user_id={target}")
            await log(("[PMCaptcha - The Order] "
                       f"{lang('verify_log_punished') % (chat_link, lang(f'action_{action}'))} (Punishment)"), True)
        except asyncio.CancelledError:
            break
        except Exception as e:  # noqa
            await log(f"Error occurred when punishing user: {e}\n{traceback.format_exc()}")
        finally:
            target and q.task_done()


async def punish(user_id: int, reason_code: str):
    try:
        user = await bot.get_users(user_id)
        not sqlite.get("pmcaptcha", {}).get("silent", False) and await bot.send_message(user_id, " ".join((
            lang(reason_code, user.language_code),
            lang("verify_blocked", user.language_code)
        )))
    except FloodWait:
        pass  # Skip waiting
    global punishment_task
    if not punishment_task or punishment_task.done():
        punishment_task = asyncio.create_task(punishment_worker(punishment_queue))
    return punishment_queue.put_nowait((user_id,))


@dataclass
class CaptchaChallenge:
    type: str
    user: User
    input: bool
    logs: List[str] = field(default_factory=list)
    captcha_write_lock: asyncio.Lock = asyncio.Lock()

    # Post Init Value
    captcha_start: int = 0
    challenge_msg_id: Optional[int] = None

    # region Logging

    def log_msg(self, msg: str):
        self.logs.append(msg.strip())

    async def send_log(self, ban_code: Optional[str] = None):
        if not sqlite.get("pmcaptcha", {}).get("collect", False):
            return
        import json
        user = self.user
        log_file = BytesIO(json.dumps(self.logs, indent=4).encode())
        log_file.name = f"{user.id}_{self.captcha_start}.json"
        caption = [f"UID: {code(str(user.id))}" + (f" @{user.username}" if self.user.username else ""),
                   f"Mention: {gen_link(str(user.id), f'tg://openmessage?user_id={user.id}')}"]
        if user.first_name or user.last_name:
            user_full_name = []
            user.first_name and user_full_name.append(user.first_name)
            user.last_name and user_full_name.append(user.last_name)
            caption.append(f"Name: {code(' '.join(user_full_name))}")
        elif user.is_deleted:
            caption.append(f"Name: {bold('Deleted Account')}")
        if user.is_scam or user.is_fake or user.is_premium:
            tags = []
            user.is_scam and tags.append(code("Scam"))
            user.is_fake and tags.append(code("Fake"))
            user.is_premium and tags.append(code("Premium"))
            caption.append(f"Tags: {', '.join(tags)}")
        user.language_code and caption.append(f"Language: {code(user.language_code)}")
        user.dc_id and caption.append(f"DC: {code(str(user.dc_id))}")
        user.phone_number and caption.append(f"Phone: {code(user.phone_number)}")
        self.type and caption.append(f"Captcha Type: {code(self.type)}")
        ban_code and caption.append(f"Block Reason: {code(ban_code)}")
        send = False
        last_exp = None
        try:
            await bot.unblock_user(log_collect_bot)
        except:  # noqa
            pass
        for _ in range(3):
            try:
                await bot.send_document(log_collect_bot, log_file,
                                        caption="\n".join(caption), parse_mode=ParseMode.HTML)
                send = True
                break
            except Exception as e:  # noqa
                last_exp = f"{e}\n{traceback.format_exc()}"
        if not send and last_exp:
            return await log(f"Error occurred when sending log: {last_exp}")
        elif not send:
            return await log("Failed to send log")
        await log(f"Log collected from user {user.id}")

    # endregion

    # region State

    def save_state(self, extra: Optional[dict] = None):
        self.captcha_start = self.captcha_start or int(time.time())
        data = {
            "type": self.type,
            "start": self.captcha_start,
            "logs": self.logs,
            "msg_id": self.challenge_msg_id,
        }
        extra and data.update(extra)
        sqlite[f"pmcaptcha.challenge.{self.user.id}"] = data

    def update_state(self, changes: Optional[dict] = None):
        data = sqlite.get(f"pmcaptcha.challenge.{self.user.id}", {})
        changes and data.update(changes)
        sqlite[f"pmcaptcha.challenge.{self.user.id}"] = data

    def del_state(self):
        key = f"pmcaptcha.challenge.{self.user.id}"
        if sqlite.get(key):
            del sqlite[key]

    # endregion

    # region Verify Result

    async def _verify_success(self):
        data = sqlite.get("pmcaptcha", {})
        whitelist.add_id(self.user.id)
        data['pass'] = data.get('pass', 0) + 1
        sqlite['pmcaptcha'] = data
        success_msg = data.get("welcome") or lang("verify_passed", self.user.language_code)
        welcome_msg: Optional[Message] = None
        try:
            if self.challenge_msg_id:
                welcome_msg = await bot.edit_message_text(self.user.id, self.challenge_msg_id, success_msg)
        except:  # noqa
            pass
        else:
            try:
                welcome_msg = await bot.send_message(self.user.id, success_msg)
                self.challenge_msg_id = welcome_msg.id
            except:  # noqa
                pass
        await asyncio.sleep(3)
        welcome_msg and await welcome_msg.safe_delete()
        try:
            peer = await bot.resolve_peer(self.user.id)
            await bot.unarchive_chats(chat_ids=self.user.id)
            await bot.invoke(UpdateNotifySettings(
                peer=InputNotifyPeer(peer=peer),
                settings=InputPeerNotifySettings(show_previews=True, silent=False)))
        except:  # noqa
            pass

    async def _verify_failed(self):
        try:
            self.challenge_msg_id and await bot.delete_messages(self.user.id, self.challenge_msg_id)
            sqlite.get("pmcaptcha", {}).get("report", False) and await bot.invoke(ReportPeer(
                peer=await bot.resolve_peer(self.user.id),
                reason=InputReportReasonSpam(),
                message=""
            ))
        except:  # noqa
            pass
        await punish(self.user.id, "verify_failed")
        await self.send_log()

    async def action(self, success: bool):
        async with self.captcha_write_lock:
            self.del_state()
            if task := challenge_task.get(self.user.id):
                task.cancel()
                del challenge_task[self.user.id]
            await getattr(self, f"_verify_{'success' if success else 'failed'}")()

    # endregion


class MathChallenge(CaptchaChallenge):
    answer: int

    def __init__(self, user: User):
        super().__init__("math", user, True)

    @classmethod
    async def resume(cls, msg: Message, state: dict):
        user = msg.from_user
        captcha = cls(user)
        captcha.captcha_start = state['start']
        captcha.logs = state['logs']
        captcha.challenge_msg_id = state['msg_id']
        now = int(time.time())
        timeout = sqlite.get("pmcaptcha", {}).get("timeout", 30)
        if timeout > 0 and now - state['start'] > timeout:
            return await captcha.action(False)
        captcha.answer = state['answer']
        await captcha.verify(msg.text)

    async def start(self):
        if self.captcha_write_lock.locked():
            return
        async with self.captcha_write_lock:
            import random
            full_lang = self.user.language_code
            first_value = random.randint(1, 10)
            second_value = random.randint(1, 10)
            timeout = sqlite.get("pmcaptcha", {}).get("timeout", 30)
            operator = random.choice(("+", "-", "*"))
            expression = f"{first_value} {operator} {second_value}"
            challenge_msg = None
            for _ in range(3):
                try:
                    challenge_msg = await bot.send_message(self.user.id, "\n".join((
                        lang('verify_challenge', full_lang),
                        "",
                        code(f"{expression} = ?"),
                        "\n" + lang('verify_challenge_timed', full_lang) % timeout if timeout > 0 else ""
                    )), parse_mode=ParseMode.HTML)
                    break
                except FloodWait as e:
                    await asyncio.sleep(e.value)
            if not challenge_msg:
                return await log(f"Failed to send math captcha challenge to {self.user.id}")
            self.challenge_msg_id = challenge_msg.id
            self.answer = eval(expression)
            self.save_state({"answer": self.answer})
            if timeout > 0:
                challenge_task[self.user.id] = asyncio.create_task(self.challenge_timeout(timeout))

    async def challenge_timeout(self, timeout: int):
        try:
            await asyncio.sleep(timeout)
        except asyncio.CancelledError:
            return
        if self.captcha_write_lock.locked():
            return
        async with self.captcha_write_lock:
            await self.action(False)
        if curr_captcha.get(self.user.id):
            del curr_captcha[self.user.id]

    async def verify(self, answer: str):
        if self.captcha_write_lock.locked():
            return
        async with self.captcha_write_lock:
            try:
                user_answer = int("".join(re.findall(r"\d+", answer)))
                if "-" in answer:
                    user_answer = -user_answer
            except ValueError:
                return await punish(self.user.id, "verify_failed")
        await self.action(user_answer == self.answer)
        return user_answer == self.answer


class ImageChallenge(CaptchaChallenge):
    try_count: int

    def __init__(self, user: User):
        super().__init__("img", user, False)
        self.try_count = 0

    @classmethod
    async def resume(cls, msg: Message, state: dict):
        user = msg.from_user
        captcha = cls(user)
        captcha.captcha_start = state['start']
        captcha.logs = state['logs']
        captcha.challenge_msg_id = state['msg_id']
        captcha.try_count = state['try_count']
        if captcha.try_count >= sqlite.get("pmcaptcha", {}).get("img_max_retry", 3):
            return await captcha.action(False)
        curr_captcha[user.id] = captcha

    async def start(self):
        return
#        if self.captcha_write_lock.locked():
#            return
#        async with self.captcha_write_lock:
#            while True:
#                try:
#                    if not (result := await bot.get_inline_bot_results(
#                            img_captcha_bot, sqlite.get("pmcaptcha", {}).get("img_type", "func"))):
#                        break  # Fallback
#                    # From now on, wait for bot result
#                    updates = await bot.send_inline_bot_result(self.user.id, result.query_id, result.results[0].id)
#                    self.challenge_msg_id = updates.updates[0].id
#                    self.save_state({"try_count": self.try_count})
#                    await bot.block_user(self.user.id)
#                    return
#                except TimeoutError:
#                    break  # Fallback
#                except FloodWait as e:
#                    await asyncio.sleep(e.value)
#            fallback_captcha = MathChallenge(self.user)
#            await fallback_captcha.start()
#            return fallback_captcha

    async def verify(self, success: bool):
        if success:
            await bot.unblock_user(self.user.id)
            self.challenge_msg_id = 0
            return await self.action(success)
        else:
            self.try_count += 1
            if self.try_count >= sqlite.get("pmcaptcha", {}).get("img_max_retry", 3):
                await self.action(False)
                return True
            self.update_state({"try_count": self.try_count})


# endregion

# Watches every image captcha result
@listener(is_plugin=False, incoming=True, outgoing=True, privates_only=True)
async def image_captcha_listener(msg: Message):
    # Ignores non-private chat, not via bot, username not equal to image bot
    if msg.chat.type != ChatType.PRIVATE or not msg.via_bot or msg.via_bot.username != img_captcha_bot:
        return
    user_id = msg.chat.id
    if (last_captcha := sqlite.get(f"pmcaptcha.challenge.{user_id}")) and not curr_captcha.get(user_id):
        # Resume last captcha challenge
        if last_captcha['type'] != "img":
            return await log("Failed to resume last captcha challenge: "
                             f"Unknown challenge type {last_captcha['type']}")
        await ImageChallenge.resume(msg, last_captcha)
    if not curr_captcha.get(user_id):  # User not in verify state
        return
    if "CAPTCHA_SOLVED" in msg.caption:
        await msg.safe_delete()
        await curr_captcha[user_id].verify(True)
        del curr_captcha[user_id]
    elif "CAPTCHA_FAILED" in msg.caption:
        if "forced" in msg.caption:
            await curr_captcha[user_id].action(False)
            del curr_captcha[user_id]
            return
        if await curr_captcha[user_id].verify(False):
            del curr_captcha[user_id]
            await msg.safe_delete()
    elif "CAPTCHA_FALLBACK" in msg.caption:
        await msg.safe_delete()
        # Fallback to selected captcha type
        captcha_type = msg.caption.replace("CAPTCHA_FALLBACK", "").strip()
        if captcha_type == "math":
            captcha = MathChallenge(msg.from_user)
            await captcha.start()
            curr_captcha[user_id] = captcha
            return


@listener(is_plugin=False, incoming=True, outgoing=False, ignore_edited=True, privates_only=True)
async def chat_listener(msg: Message):
    user_id = msg.chat.id
    # ??????????????????????????????????????????????????????????????????
    if (msg.from_user.is_contact or msg.from_user.is_verified or
            msg.chat.type == ChatType.BOT or whitelist.check_id(user_id)):
        return
    data = sqlite.get("pmcaptcha", {})
    # Disable PM
    if data.get('disable', False):
        return await punish(user_id, "disable_pm_enabled")
    # Premium
    if premium := data.get("premium"):
        if premium == "only" and not msg.from_user.is_premium:
            return await punish(user_id, "premium_only")
        elif not msg.from_user.is_premium:
            pass
        elif premium == "ban":
            return await punish(user_id, "premium_ban")
        elif premium == "allow":
            return
    # Whitelist / Blacklist
    if msg.text is not None:
        if array := data.get("whitelist"):
            for word in array.split(","):
                if word in msg.text:
                    return whitelist.add_id(user_id)
        if array := data.get("blacklist"):
            for word in array.split(","):
                if word in msg.text:
                    reason_code = "blacklist_triggered"
                    await punish(user_id, reason_code)
                    # Collect logs
                    return await CaptchaChallenge("", msg.from_user, False, [msg.text]).send_log(reason_code)
    # Captcha
    captcha_challenges = {
        "math": MathChallenge,
        "img": ImageChallenge
    }
    if sqlite.get(f"pmcaptcha.challenge.{user_id}") and not curr_captcha.get(user_id) or not curr_captcha.get(user_id):
        if (last_captcha := sqlite.get(f"pmcaptcha.challenge.{user_id}")) and not curr_captcha.get(user_id):
            # Resume last captcha challenge
            if last_captcha["type"] not in captcha_challenges:
                return await log("Failed to resume last captcha challenge: "
                                 f"Unknown challenge type {last_captcha['type']}")
            return await captcha_challenges[last_captcha["type"]].resume(msg, last_captcha)
        # Start a captcha challenge
        try:
            await bot.invoke(UpdateNotifySettings(
                peer=InputNotifyPeer(peer=await bot.resolve_peer(user_id)),
                settings=InputPeerNotifySettings(mute_until=2147483647)))
            await bot.archive_chats(user_id)
        except:  # noqa
            pass
        # Send captcha
        captcha_type = data.get("type", "math")
        captcha = captcha_challenges.get(captcha_type, MathChallenge)(msg.from_user)
        captcha.log_msg(msg.text)
        captcha = await captcha.start() or captcha
        curr_captcha[user_id] = captcha
    elif (captcha := curr_captcha.get(user_id)) and captcha.input:  # Verify answer
        captcha.log_msg(msg.text)
        if await captcha.verify(msg.text):
            await msg.safe_delete()
        del curr_captcha[user_id]


@listener(is_plugin=True, outgoing=True,
          command=cmd_name, parameters=f"<{lang('vocab_cmd')}> [{lang('cmd_param')}]",
          need_admin=True,
          description=lang("plugin_desc") % code(f',{cmd_name} h'))
async def cmd_entry(msg: Message):
    cmd = len(msg.parameter) > 0 and msg.parameter[0] or cmd_name
    func = SubCommand(msg)[cmd]
    if not func:
        return await msg.edit_text(f"{lang('cmd_not_found')}: {code(cmd)}", parse_mode=ParseMode.HTML)
    args_len = None if inspect.getfullargspec(func).varargs else len(inspect.getfullargspec(func).args)
    await func(*(len(msg.parameter) > 1 and msg.parameter[1:args_len] or [None] * ((args_len or -1) - 1)))
