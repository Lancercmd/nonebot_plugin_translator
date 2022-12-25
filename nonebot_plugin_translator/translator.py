"""
Author       : Lancercmd
Date         : 2020-12-14 13:29:38
LastEditors  : Lancercmd
LastEditTime : 2022-06-21 13:30:40
Description  : None
GitHub       : https://github.com/Lancercmd
"""
from binascii import b2a_base64
from copy import deepcopy
from hashlib import sha1
from hmac import new
from random import randint
from sys import maxsize, version_info
from time import time

from aiohttp import request
from loguru import logger
from nonebot import get_driver
from nonebot.adapters import Event, Message, MessageTemplate
from nonebot.adapters.onebot.v11 import MessageEvent as OneBot_V11_MessageEvent
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg
from nonebot.permission import Permission
from nonebot.plugin import on_command, PluginMetadata
from nonebot.typing import T_State
from ujson import loads as loadJsonS

from ._permission import onFocus

config = get_driver().config

translate = on_command("翻译", aliases={"机翻"})


@translate.permission_updater
async def _(event: Event) -> Permission:
    return await onFocus(event)


async def getReqSign(params: dict) -> str:
    common = {
        "Action": "TextTranslate",
        "Region": f"{getattr(config, 'tencentcloud_common_region', 'ap-shanghai')}",
        "Timestamp": int(time()),
        "Nonce": randint(1, maxsize),
        "SecretId": f"{getattr(config, 'tencentcloud_common_secretid', '')}",
        "Version": "2018-03-21",
    }
    params.update(common)
    sign_str = "POSTtmt.tencentcloudapi.com/?"
    sign_str += "&".join("%s=%s" % (k, params[k]) for k in sorted(params))
    secret_key = getattr(config, "tencentcloud_common_secretkey", "")
    if version_info[0] > 2:
        sign_str = bytes(sign_str, "utf-8")
        secret_key = bytes(secret_key, "utf-8")
    hashed = new(secret_key, sign_str, sha1)
    signature = b2a_base64(hashed.digest())[:-1]
    if version_info[0] > 2:
        signature = signature.decode()
    return signature

target = "zh"

q_en = on_command("切换英文")
@q_en.handle()
async def _():
 global target
 target = "en"
 await q_en.finish("切换成功")

q_jp = on_command("切换日文")
@q_jp.handle()
async def _():
 global target
 target = "ja"
 await q_jp.finish("切换成功")

q_zh = on_command("切换中文")
@q_zh.handle()
async def _():
 global target
 target = "zh"
 await q_zh.finish("切换成功")

@translate.handle()
async def _(event: Event, state: T_State, args: Message = CommandArg()):
 _plain_text = args.extract_plain_text()

 if isinstance(event, OneBot_V11_MessageEvent):
        _source_text = _plain_text
        _source = "auto"
        _target = target
        try:
            endpoint = "https://tmt.tencentcloudapi.com"
            params = {
                "Source": _source,
                "SourceText": _source_text,
                "Target": _target,
                "ProjectId": 0,
            }
            params["Signature"] = await getReqSign(params)
            async with request("POST", endpoint, data=params) as resp:
                code = resp.status
                if code != 200:
                    message = "※ 网络异常，请稍后再试~"
                    if "header" in state:
                        message = "".join([state["header"], f"{message}"])
                    await translate.finish(message)
                data = loadJsonS(await resp.read())["Response"]
            if "Error" in data:
                message = "\n".join(
                    [
                        f"<{data['Error']['Code']}> {data['Error']['Message']}",
                        f"RequestId: {data['RequestId']}",
                    ]
                )
                if "header" in state:
                    message = "".join([state["header"], f"{message}"])
                await translate.finish(message)
            message = data["TargetText"]
            if "header" in state:
                message = "".join([state["header"], f"{message}"])
            await translate.finish(message)
        except ActionFailed as e:
            logger.warning(
                f"ActionFailed {e.info['retcode']} {e.info['msg'].lower()} {e.info['wording']}"
            )
 else:
        logger.warning("Not supported: translator")


__plugin_meta__ = PluginMetadata(
    name="多语种翻译插件",
    description="接口来自 腾讯机器翻译 TMT",
    usage="翻译 <ilang> <olang> <text>",
    extra={"author": "Lancercmd"},
)
