# Universal Register - 通用 AI 平台注册器

从 [codex_register](https://github.com/nicoxia/codex_register) 提取核心逻辑，适配所有 AI 平台注册。

## 核心能力

| 模块 | 来源 | 功能 |
|------|------|------|
| TLS 指纹伪装 | codex_register | `curl_cffi` 伪装 Chrome 120，绕 Cloudflare |
| Sentinel 攻克 | codex_register | OpenAI 反爬 Token 自动获取 |
| OAuth2 PKCE | codex_register | 拦截重定向，提取 access_token + refresh_token |
| 临时邮箱 | codex_register | mail.tm API 自动创建 + 轮询验证码 |
| 通用适配器 | 新增 | JSON 配置即可适配任意平台 |

## 快速开始

```bash
cd universal-register
source .venv/bin/activate

# OpenAI 注册（单次）
python main.py --platform openai --once

# OpenAI 注册（循环）
python main.py --platform openai --loop

# 通用平台注册
python main.py --platform generic --config configs/siliconflow.json --once

# 使用代理
python main.py --platform openai --proxy http://127.0.0.1:7890 --once
```

## 自定义平台配置

复制 `configs/siliconflow.json`，修改以下字段：

```json
{
    "name": "your_platform",
    "register_url": "https://example.com/api/register",
    "form_fields": {
        "email": "{email}",
        "password": "{password}",
        "username": "{username}"
    },
    "method": "POST",
    "content_type": "json",
    "otp_keywords": ["verification", "code"],
    "api_key_url": "https://example.com/api/keys",
    "verify_url": "https://example.com/api/login"
}
```

`{email}`, `{password}`, `{username}` 会自动替换为随机生成的值。

## 输出

```
output/
├── openai/
│   ├── openai_user_at_domain.json    # 每个账号的详细信息
│   └── accounts.txt                  # 汇总: platform----email----password----apikey
└── siliconflow/
    ├── siliconflow_user_at_domain.json
    └── accounts.txt
```

## 项目结构

```
universal-register/
├── main.py                  # 入口
├── core/
│   ├── tls_client.py        # TLS 指纹伪装客户端
│   └── mail_tm.py           # mail.tm 临时邮箱
├── platforms/
│   ├── __init__.py          # BasePlatform 基类
│   ├── openai.py            # OpenAI 专用（Sentinel + PKCE）
│   └── generic.py           # 通用适配器（JSON 配置）
├── configs/
│   ├── siliconflow.json     # 硅基流动配置
│   └── groq.json            # Groq 配置
└── .venv/                   # Python venv（curl_cffi）
```

## 依赖

- Python 3.8+
- `curl_cffi` (TLS 指纹伪装)
- mail.tm (免费临时邮箱，无需注册)
