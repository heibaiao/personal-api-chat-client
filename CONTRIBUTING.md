# 参与贡献

感谢你愿意改进这个项目。下面是最小但必要的约定。

## 提交 Issue

请附上：

- 复现步骤（点了哪里、输入了什么）
- 期望结果 vs 实际结果
- 截图（如果涉及界面）
- `debug.log` 的相关片段（**先确认里面没有你的 API Key**）
- Python 版本、Windows 版本、是源码运行还是发布包

## 提交 PR

1. Fork 并新建分支：`git checkout -b feat/your-feature`
2. 保持**单文件**结构（`deepseek_chat.py`），不要拆包，不要引入新的重量级依赖
3. 改完请自测：
   - `python -m py_compile deepseek_chat.py`
   - 源码运行一遍主要流程：切模型、发消息、流式渲染、导出、设置
4. **同步更新关于页**：`FEATURE_GROUPS` 里对应功能行必须一起改（这是本项目的既定规则）
5. 如有新功能，更新 `README.md` 与 `CHANGELOG.md`
6. 提交信息用现在时、简短描述：`add token usage bar` / `fix streaming duplication`

## 代码风格

- 4 空格缩进，行宽尽量 ≤ 100
- 中文注释，函数写 docstring
- UI 文案统一中文，图标/品牌名保留原文
- 异常处理不要裸 `except:`，至少 `except Exception:`

## 绝对不要提交

- `config.enc`、`chat_history.json`、`settings.json`、`debug.log`
- 任何真实 API Key、个人路径、聊天内容截图
- `dist/`、`build/`、`backup/`、`aaaaa/`（已在 `.gitignore` 中）

## 新增模型

在 `MODEL_REGISTRY` 追加一条：

```python
{
    "id": "my-model",            # 唯一 id，也用于 assets/logos/<id>.png
    "name": "My-Model",          # 展示名
    "version": "1.0",
    "vendor": "Vendor",          # 品牌，用于徽标配色
    "mark": "™",
    "base_url": "https://api.example.com/v1",
    "api_model": "my-model-1.0",
    "desc": "一句话说明",
    "thinking": False,           # 是否显示「深度思考」开关
},
```

并在 `MODEL_PRICING` 补 `(输入价, 输出价, "¥"|"$")`（每百万 tokens），
在 `BRAND_STYLE` 补品牌配色（可选）。

## 许可

提交 PR 即表示你同意以 [MIT License](LICENSE) 授权你的贡献。
