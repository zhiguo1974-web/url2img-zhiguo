from __future__ import annotations

import asyncio
import os
import re
import threading
from pathlib import Path
from urllib.parse import urlparse

import tkinter as tk
from tkinter import messagebox

try:
    from pyppeteer import launch
except ImportError as exc:  # pragma: no cover - handled at runtime
    raise SystemExit(
        "pyppeteer 未安装。请先运行 'pip install -r requirements.txt' 再启动本程序。"
    ) from exc


class ScreenshotApp:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("网址截图工具")
        self.master.geometry("600x400")

        self.status_var = tk.StringVar()
        self.status_var.set("请输入网址，每行一个，然后点击“开始截图”。")

        self._build_widgets()

    def _build_widgets(self) -> None:
        instruction = tk.Label(
            self.master,
            text="在下面的输入框中输入多个网址，每行一个：",
            anchor="w",
        )
        instruction.pack(fill="x", padx=10, pady=(10, 0))

        self.url_text = tk.Text(self.master, height=15, wrap="none")
        self.url_text.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.capture_button = tk.Button(
            self.master,
            text="开始截图",
            command=self.start_capture,
            width=15,
        )
        self.capture_button.pack(pady=(0, 5))

        status_label = tk.Label(
            self.master,
            textvariable=self.status_var,
            anchor="w",
            justify="left",
            fg="#555555",
            wraplength=560,
        )
        status_label.pack(fill="x", padx=10, pady=(0, 10))

    def start_capture(self) -> None:
        raw_text = self.url_text.get("1.0", tk.END)
        urls = [line.strip() for line in raw_text.splitlines() if line.strip()]

        if not urls:
            messagebox.showwarning("提示", "请输入至少一个网址。")
            return

        self.capture_button.config(state=tk.DISABLED)
        self.status_var.set("正在处理，请稍候……")

        thread = threading.Thread(target=self._run_capture_thread, args=(urls,), daemon=True)
        thread.start()

    def _run_capture_thread(self, urls: list[str]) -> None:
        try:
            asyncio.run(self._capture_urls(urls))
        except Exception as exc:  # pragma: no cover - runtime error handling
            self._update_status(f"发生错误：{exc}")
            self.master.after(
                0,
                lambda: messagebox.showerror("错误", f"截图过程中发生错误：{exc}"),
            )
        else:
            self._update_status("截图完成！所有图片已保存在程序所在的目录中。")
            self.master.after(0, lambda: messagebox.showinfo("完成", "截图已全部完成！"))
        finally:
            self.master.after(0, lambda: self.capture_button.config(state=tk.NORMAL))

    async def _capture_urls(self, urls: list[str]) -> None:
        output_dir = Path(os.getcwd())
        browser = await launch(headless=True, args=["--no-sandbox"])

        try:
            page = await browser.newPage()
            await page.setViewport({"width": 1280, "height": 720})

            for index, original_url in enumerate(urls, start=1):
                url = self._normalize_url(original_url)
                filename = self._build_filename(original_url, index)
                output_path = output_dir / filename

                await self._update_status_async(f"正在处理：{url}")

                try:
                    await page.goto(url, waitUntil="networkidle2", timeout=60000)
                    await page.screenshot({"path": str(output_path), "fullPage": True})
                except Exception as exc:  # pragma: no cover - runtime error handling
                    await self._update_status_async(f"截图失败：{original_url} ({exc})")
                else:
                    await self._update_status_async(f"完成：{output_path.name}")
        finally:
            await browser.close()

    async def _update_status_async(self, message: str) -> None:
        self.master.after(0, lambda: self.status_var.set(message))
        await asyncio.sleep(0)

    def _update_status(self, message: str) -> None:
        self.master.after(0, lambda: self.status_var.set(message))

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse(url)
        if not parsed.scheme:
            return f"http://{url}"
        return url

    @staticmethod
    def _build_filename(url: str, index: int) -> str:
        parsed = urlparse(url)
        base = parsed.netloc or parsed.path or "screenshot"
        safe_base = re.sub(r"[^0-9A-Za-z_-]", "_", base) or "screenshot"
        return f"{index:03d}_{safe_base}.png"


def main() -> None:
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
