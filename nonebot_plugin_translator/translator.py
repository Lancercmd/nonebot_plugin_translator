"""
Author       : Lancercmd
Date         : 2020-12-14 13:29:38
LastEditors  : Lancercmd
LastEditTime : 2022-12-26 18:15:46
Description  : None
GitHub       : https://github.com/Lancercmd
"""
from binascii import b2a_base64
from dataclasses import dataclass
from hashlib import sha1
from hmac import new
from pathlib import Path
from random import randint
from sys import maxsize, version_info
from time import time

from aiohttp import request
from nonebot import get_driver
from nonebot.adapters import Event, Message, MessageTemplate
from nonebot.adapters.onebot.v11 import MessageEvent as OneBot_V11_MessageEvent
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg
from nonebot.plugin import MatcherGroup, PluginMetadata
from nonebot.typing import T_State
from nonebot.utils import logger_wrapper
from ujson import dumps as dumpJsonS
from ujson import loads as loadJsonS

log = logger_wrapper(Path(__file__).stem.capitalize())

_config = get_driver().config


@dataclass
class Config:
    tencentcloud_common_region: str = (
        getattr(_config, "tencentcloud_common_region", "ap-shanghai") or "ap-shanghai"
    )
    tencentcloud_common_secretid: str = (
        getattr(_config, "tencentcloud_common_secretid", "") or ""
    )
    tencentcloud_common_secretkey: str = (
        getattr(_config, "tencentcloud_common_secretkey", "") or ""
    )


config = Config()


class Pool:
    def __init__(self):
        self._pool = set()
        self._kv = {}

    def add(self, user_id, lang):
        self._pool.add(user_id)
        self._kv.update({user_id: lang})

    def remove(self, user_id):
        self._pool.remove(user_id)

    def find(self, user_id):
        return user_id in self._pool

    def get(self, user_id):
        return self._kv.get(user_id)


session_pool = Pool()


async def getReqSign(action: str, params: dict) -> str:
    common = {
        "Action": action,
        "Region": config.tencentcloud_common_region,
        "Timestamp": int(time()),
        "Nonce": randint(1, maxsize),
        "SecretId": config.tencentcloud_common_secretid,
        "Version": "2018-03-21",
    }
    params.update(common)
    sign_str = "POSTtmt.tencentcloudapi.com/?"
    sign_str += "&".join("%s=%s" % (k, params[k]) for k in sorted(params))
    secret_key = config.tencentcloud_common_secretkey
    if version_info[0] > 2:
        sign_str = bytes(sign_str, "utf-8")
        secret_key = bytes(secret_key, "utf-8")
    hashed = new(secret_key, sign_str, sha1)
    signature = b2a_base64(hashed.digest())[:-1]
    if version_info[0] > 2:
        signature = signature.decode()
    return signature


async def requestTextTranslate(source: str, source_text: str, target: str):
    url = "https://tmt.tencentcloudapi.com"
    params = {
        "Source": source,
        "SourceText": source_text,
        "Target": target,
        "ProjectId": 0,
    }
    params["Signature"] = await getReqSign("TextTranslate", params)
    async with request("POST", url, data=params) as resp:
        code = resp.status
        if code != 200:
            return 1, "※ 网络异常，请稍后再试~"
        return 0, loadJsonS(await resp.read())["Response"]


async def requestLanguageDetect(text: str):
    url = "https://tmt.tencentcloudapi.com"
    params = {
        "Text": text,
        "ProjectId": 0,
    }
    params["Signature"] = await getReqSign("LanguageDetect", params)
    async with request("POST", url, data=params) as resp:
        code = resp.status
        if code != 200:
            return 1, "※ 网络异常，请稍后再试~"
        return 0, loadJsonS(await resp.read())["Response"]


async def iterAvaiLang(source: str = None, targets: bool = True) -> list:
    # fmt: off
    avl = [
        # "auto",
        "zh", "zh-TW", "en", "ja", "ko", "fr",
        "es", "it", "de", "tr", "ru", "pt",
        "vi", "id", "th", "ms", "ar", "hi"
    ]
    _avl = loadJsonS(dumpJsonS(avl))
    if targets:
        avl.remove("zh-TW")
    if not source:
        return avl
    avl = set(avl)
    if source != "en":
        avl -= {"ar", "hi"}
    if source not in ["zh", "zh-TW", "en"]:
        avl -= {"vi", "id", "th", "ms"}
    if source not in ["zh", "zh-TW", "en", "fr", "es", "it", "de", "tr", "ru", "pt"]:
        avl -= {"fr", "es", "it", "de", "tr", "ru", "pt"}
    if source not in ["zh", "zh-TW", "en", "ja", "ko"]:
        avl -= {"ja", "ko"}
    avl = [i for i in _avl if i in list(avl)]
    # fmt: on
    try:
        avl.remove(source)
    except ValueError:
        pass
    return avl


workers = MatcherGroup(type="message", block=True)
worker1 = workers.on_command("翻译", aliases={"机翻"})
worker2 = workers.on_command("翻译+", aliases={"机翻+", "翻译锁定", "机翻锁定"})


@worker1.handle()
async def _(event: OneBot_V11_MessageEvent, state: T_State, args: Message = CommandArg()):
    avl = await iterAvaiLang(targets=False)
    state["avl"] = " | ".join(avl)
    state["valid"] = loadJsonS(dumpJsonS(avl))
    _plain_text = args.extract_plain_text()
    if _plain_text:
        for language in avl:
            if _plain_text.startswith(language):
                state["Source"] = language
                break
            elif _plain_text.startswith("jp"):
                state["Source"] = "ja"
                break
        if "Source" in state:
            input = _plain_text.split(" ", 2)
            avl = await iterAvaiLang(state["Source"])
            if len(avl) == 1:
                state["Target"] = avl[0]
                if len(input) == 3:
                    state["SourceText"] = input[2]
                else:
                    state["SourceText"] = input[1]
            elif len(input) == 3:
                state["Target"] = input[1]
                state["SourceText"] = input[2]
            elif len(input) == 2:
                for language in avl:
                    if input[0] in avl:
                        state["Target"] = input[1]
                    else:
                        state["SourceText"] = input[1]
        else:
            state["SourceText"] = _plain_text
    message = f"请选择输入语种，可选值如下~\n{state['avl']}"
    if "header" in state:
        message = "".join([state["header"], f"{message}"])
    state["prompt"] = message


@worker1.got("Source", prompt=MessageTemplate("{prompt}"))
async def _(event: OneBot_V11_MessageEvent, state: T_State):
    _source = str(state["Source"])
    try:
        avl: list = loadJsonS(dumpJsonS(state["valid"]))
        if _source.lower() == "jp":
            _source = "ja"
        elif not _source in state["valid"]:
            message = f"不支持的输入语种 {_source}"
            if "header" in state:
                message = "".join([state["header"], f"{message}"])
            await worker1.finish(message)
        avl = await iterAvaiLang(_source)
        if len(avl) == 1:
            state["Target"] = avl[0]
        else:
            state["avl"] = " | ".join(avl)
            state["valid"] = loadJsonS(dumpJsonS(avl))
        message = f"请选择目标语种，可选值如下~\n{state['avl']}"
        if "header" in state:
            message = "".join([state["header"], f"{message}"])
        state["prompt"] = message
    except ActionFailed as e:
        log(
            "WARNING",
            f"ActionFailed {e.info['retcode']} {e.info['msg'].lower()} {e.info['wording']}",
        )


@worker1.got("Target", prompt=MessageTemplate("{prompt}"))
async def _(event: OneBot_V11_MessageEvent, state: T_State):
    _target = str(state["Target"])
    try:
        if _target.lower() == "jp":
            _target = "ja"
        elif not _target in state["valid"]:
            message = f"不支持的目标语种 {_target}"
            if "header" in state:
                message = "".join([state["header"], f"{message}"])
            await worker1.finish(message)
        message = "请输入要翻译的内容~"
        if "header" in state:
            message = "".join([state["header"], f"{message}"])
        state["prompt"] = message
    except ActionFailed as e:
        log(
            "WARNING",
            f"ActionFailed {e.info['retcode']} {e.info['msg'].lower()} {e.info['wording']}",
        )


@worker1.got("SourceText", prompt=MessageTemplate("{prompt}"))
async def _(event: OneBot_V11_MessageEvent, state: T_State):
    _source = state["Source"]
    _target = state["Target"]
    _source_text = str(state["SourceText"])
    try:
        resp = await requestTextTranslate(_source, _source_text, _target)
        if resp[0]:
            message = resp[1]
        else:
            data = resp[1]
            if "Error" in data:
                message = "\n".join(
                    [
                        f"<{data['Error']['Code']}> {data['Error']['Message']}",
                        f"RequestId: {data['RequestId']}",
                    ]
                )
            else:
                message = data["TargetText"]
        if "header" in state:
            message = "".join([state["header"], f"{message}"])
        await worker1.finish(message)
    except ActionFailed as e:
        log(
            "WARNING",
            f"ActionFailed {e.info['retcode']} {e.info['msg'].lower()} {e.info['wording']}",
        )


@worker2.handle()
async def _(event: OneBot_V11_MessageEvent, state: T_State, args: Message = CommandArg()):
    user_id = event.get_user_id()
    try:
        if not session_pool.find(user_id):
            avl = await iterAvaiLang()
            lang = "en"
            _plain_text = args.extract_plain_text()
            if _plain_text:
                lang = _plain_text.split(" ", 1)[0]
                lang = lang.lower()
                if lang == "jp":
                    lang = "ja"
            if lang in avl:
                session_pool.add(user_id, lang)
                message = "\n".join(
                    [
                        f"了解~切换为翻译锁定模式——当前目标语种为 {lang}",
                        "",
                        "使用“+lang”来切换目标语言，如 +ja",
                        "使用“翻译-”或“--”来切出翻译锁定模式",
                        "",
                        "请输入要翻译的内容~",
                    ]
                )
                if "header" in state:
                    message = "".join([state["header"], f"{message}"])
                await worker2.send(message)
            else:
                message = "\n".join(
                    [
                        f"不支持的目标语种 {lang}",
                        "",
                        "可用的目标语种有：",
                        " | ".join(avl),
                    ]
                )
                if "header" in state:
                    message = "".join([state["header"], f"{message}"])
                await worker2.finish(message)
        else:
            message = "\n".join([
                "已恢复到翻译锁定模式的会话~",
                "",
                "超时会自动切出会话，请注意~",
            ])
            if "header" in state:
                message = "".join([state["header"], f"{message}"])
            await worker2.send(message)
    except ActionFailed as e:
        log(
            "WARNING",
            f"ActionFailed {e.info['retcode']} {e.info['msg'].lower()} {e.info['wording']}",
        )


@worker2.got("SourceText")
async def _(event: OneBot_V11_MessageEvent, state: T_State):
    user_id = event.get_user_id()
    try:
        if session_pool.find(user_id):
            _source_text = str(state["SourceText"])
            if _source_text.startswith(("翻译-", "--")):
                session_pool.remove(user_id)
                message = "已切出翻译锁定模式~"
                if "header" in state:
                    message = "".join([state["header"], f"{message}"])
                await worker2.finish(message)
            elif _source_text.startswith("+"):
                _source_text = _source_text[1:]
                avl = await iterAvaiLang()
                if _source_text in avl:
                    session_pool.add(user_id, _source_text)
                    message = "\n".join([f"已切换为目标语种 {_source_text}", "取决于输入语种，目标语种可能变化"])
                else:
                    message = "\n".join(
                        [
                            f"不支持的目标语种 {_source_text}",
                            "",
                            "可用的目标语种有：",
                            " | ".join(avl),
                        ]
                    )
                if "header" in state:
                    message = "".join([state["header"], f"{message}"])
                await worker2.reject(message)
            else:
                resp = await requestLanguageDetect(_source_text)
                if resp[0]:
                    message = resp[1]
                    if "header" in state:
                        message = "".join([state["header"], f"{message}"])
                    await worker2.reject(message)
                else:
                    data = resp[1]
                    if "Error" in data:
                        message = "\n".join(
                            [
                                f"<{data['Error']['Code']}> {data['Error']['Message']}",
                                f"RequestId: {data['RequestId']}",
                            ]
                        )
                        if "header" in state:
                            message = "".join([state["header"], f"{message}"])
                        await worker2.reject(message)
                    else:
                        _source = data["Lang"]
                avl = await iterAvaiLang(_source)
                _target = session_pool.get(user_id)
                treated = False
                if _target not in avl:
                    _target = avl[0]
                    treated = True
                resp = await requestTextTranslate(_source, _source_text, _target)
                if resp[0]:
                    message = resp[1]
                else:
                    data = resp[1]
                    if "Error" in data:
                        message = "\n".join(
                            [
                                f"<{data['Error']['Code']}> {data['Error']['Message']}",
                                f"RequestId: {data['RequestId']}",
                            ]
                        )
                    else:
                        message = data["TargetText"]
                if treated:
                    message = "\n".join([f"目标语种修正为 {_target}", message])
                if "header" in state:
                    message = "".join([state["header"], f"{message}"])
                await worker2.reject(message)
    except ActionFailed as e:
        log(
            "WARNING",
            f"ActionFailed {e.info['retcode']} {e.info['msg'].lower()} {e.info['wording']}",
        )


@worker1.handle()
@worker2.handle()
async def _(event: Event) -> None:
    # fmt: off
    supported = \
        isinstance(event, OneBot_V11_MessageEvent)
    # fmt: on
    if not supported:
        log("WARNING", "Not supported: translator")


__plugin_meta__ = PluginMetadata(
    name="多语种翻译插件",
    description="接口来自 腾讯机器翻译 TMT",
    usage="翻译 <ilang> <olang> <text>",
    extra={"author": "Lancercmd"},
)
