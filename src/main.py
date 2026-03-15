import asyncio

import click

from src.config import load_config
from src.scraper_bookmarks import collect_bookmarks
from src.scraper_details import fetch_details


@click.group()
def cli():
    """X.com ブックマークスクレイピングツール"""
    pass


@cli.command("collect-bookmarks")
@click.option("--config", "config_path", default="./config.yaml", help="設定ファイルのパス")
def collect_bookmarks_cmd(config_path: str):
    """Phase 1: ブックマークページから URL を収集して Spreadsheet に書き込む"""
    config = load_config(config_path)
    asyncio.run(collect_bookmarks(config))


@cli.command("fetch-details")
@click.option("--config", "config_path", default="./config.yaml", help="設定ファイルのパス")
def fetch_details_cmd(config_path: str):
    """Phase 3: 各ポストの投稿日時と画像を取得して Spreadsheet を更新する"""
    config = load_config(config_path)
    asyncio.run(fetch_details(config))


if __name__ == "__main__":
    cli()
