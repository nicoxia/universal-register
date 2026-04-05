#!/usr/bin/env python3
"""
Universal Register - 通用 AI 平台注册器
从 codex_register 提取核心逻辑，适配所有平台

用法:
    # 注册 OpenAI
    python main.py --platform openai --once
    python main.py --platform openai --loop

    # 注册通用平台（配置 JSON）
    python main.py --platform generic --config siliconflow.json

    # 使用代理
    python main.py --platform openai --proxy http://127.0.0.1:7890
"""
import argparse
import json
import random
import time
from pathlib import Path
from datetime import datetime

# 平台适配器
from platforms.openai import OpenAIPlatform
from platforms.generic import GenericPlatform

OUTPUT_DIR = Path(__file__).parent / "output"


def load_platform_config(config_path: str) -> dict:
    """从 JSON 配置文件加载平台参数"""
    with open(config_path, "r") as f:
        return json.load(f)


def create_platform(name: str, proxy: str = None, config_path: str = None):
    """根据名称创建平台实例"""
    out = OUTPUT_DIR / name
    out.mkdir(parents=True, exist_ok=True)

    if name == "openai":
        return OpenAIPlatform(proxy=proxy, out_dir=out)

    elif config_path:
        cfg = load_platform_config(config_path)
        cfg["proxy"] = proxy
        cfg["out_dir"] = out
        return GenericPlatform(**cfg)

    else:
        print(f"[!] 未知平台: {name}，请提供 --config")
        return None


def main():
    parser = argparse.ArgumentParser(description="Universal AI Platform Register")
    parser.add_argument("--platform", default="openai", help="平台名称 (openai / generic)")
    parser.add_argument("--config", default=None, help="通用平台 JSON 配置文件路径")
    parser.add_argument("--proxy", default=None, help="代理地址 http://host:port")
    parser.add_argument("--once", action="store_true", help="只注册一次")
    parser.add_argument("--loop", action="store_true", help="循环注册（默认）")
    parser.add_argument("--count", type=int, default=999, help="循环注册次数上限")
    args = parser.parse_args()

    platform = create_platform(args.platform, args.proxy, args.config)
    if not platform:
        return

    count = 0
    print(f"\n{'='*50}")
    print(f"🚀 Universal Register - {platform.platform_name}")
    print(f"{'='*50}")

    while count < args.count:
        count += 1
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] >>> 第 {count} 次注册 <<<")

        result = platform.run()

        if result:
            print(f"  [✅] 注册成功!")
            api_key = result.get("api_key", result.get("access_token", ""))
            if api_key:
                print(f"  [🔑] API Key: {api_key[:30]}...")
        else:
            print(f"  [❌] 注册失败")

        if args.once:
            break

        wait = random.randint(5, 15)
        print(f"  [*] 冷却 {wait} 秒...")
        time.sleep(wait)


if __name__ == "__main__":
    main()
