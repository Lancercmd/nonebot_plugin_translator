<!--
 * @Author       : Lancercmd
 * @Date         : 2020-12-15 10:21:55
 * @LastEditors  : Lancercmd
 * @LastEditTime : 2020-12-15 13:52:20
 * @Description  : None
 * @GitHub       : https://github.com/Lancercmd
-->
# nonebot_plugin_translator

- 基于 [nonebot / nonebot2](https://github.com/nonebot/nonebot2)

## 功能

- 多语种翻译插件

> 接口来自 [腾讯 AI 开放平台](https://ai.qq.com/product/nlptrans.shtml)

## 准备工作

- 在 [腾讯 AI 开放平台](https://ai.qq.com/console/) 新建应用，并从能力库接入 [机器翻译](https://ai.qq.com/console/capability/detail/7) 能力

## 开始使用

建议使用 poetry

- 通过 poetry 添加到 nonebot2 项目的 pyproject.toml

``` {.sourceCode .bash}
poetry add nonebot-plugin-translator
```

- 也可以通过 pip 从 [PyPI](https://pypi.org/project/nonebot-plugin-translator/) 安装

``` {.sourceCode .bash}
pip install nonebot-plugin-translator
```

- 在 nonebot2 项目中设置 `nonebot.load_plugin()`
> 当使用 [nb-cli](https://github.com/nonebot/nb-cli) 添加本插件时，该条会被自动添加

``` {.sourceCode .python}
nonebot.load_plugin('nonebot_plugin_translator')
```

- 参照下文在 nonebot2 项目的环境文件 `.env.*` 中添加配置项

## 配置项

- [腾讯 AI 开放平台](https://ai.qq.com/console/) 应用鉴权信息（必须）：

  `tencent_app_id: int` 应用 APPID

  `tencent_app_key: str` 应用 APPKEY

``` {.sourceCode .bash}
  tencent_app_id = 0123456789
  tencent_app_key = ""
```

- 这样，就能够在 bot 所在群聊或私聊发送 `翻译` 或 `机翻` 使用了

## 特别感谢

- [Mrs4s / go-cqhttp](https://github.com/Mrs4s/go-cqhttp)
- [nonebot / nonebot2](https://github.com/nonebot/nonebot2)

## 优化建议

如有优化建议请积极提交 Issues 或 Pull requests