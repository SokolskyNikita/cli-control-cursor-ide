#!/usr/bin/env python3
import websockets
import asyncio
import json
import random
import aiohttp
import argparse
from typing import List, Dict
from pathlib import Path


class ShortcutError(Exception):
    pass


# Electron modifiers as constants
class Mod:
    CMD = "Command"
    COMMAND = "Command"
    CTRL = "Control"
    CONTROL = "Control"
    CMD_OR_CTRL = "CommandOrControl"
    ALT = "Alt"
    OPTION = "Option"
    ALT_GR = "AltGr"
    SHIFT = "Shift"
    SUPER = "Super"
    META = "meta"


async def get_websocket_uri():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:9222/json/list") as response:
                if response.status != 200:
                    raise ShortcutError("Cursor debug port not accessible")
                data = await response.json()
                if not data:
                    raise ShortcutError("No Cursor windows found")
                if len(data) > 1:
                    raise ShortcutError(
                        "Multiple Cursor windows found - please close extra windows"
                    )
                return data[0]["webSocketDebuggerUrl"]
        except aiohttp.ClientError as e:
            raise ShortcutError(f"Failed to connect to debug port: {e}")


class Input:
    @staticmethod
    def _create_key_event(
        event_type: str, key: str, modifiers: List[str] = None
    ) -> Dict:
        mods = modifiers if modifiers else []
        return {"type": event_type, "key": key, "modifiers": mods}

    @staticmethod
    def shortcut(mods: List[str], key: str) -> List[Dict]:
        return [Input._create_key_event("keyDown", key, mods)]

    @staticmethod
    def key(key: str) -> List[Dict]:
        return Input.shortcut([], key)

    @staticmethod
    def text(text: str) -> List[Dict]:
        return [{"type": "char", "text": char, "key": char} for char in text]


class CursorWebSocket:
    def __init__(self):
        self.ws = None
        self.message_id = random.randint(1, 1000000)
        self.runtime_enabled = False
        self.js_function = (
            Path(__file__).parent.joinpath("electron_commands.js").read_text()
        )

    async def __aenter__(self):
        uri = await get_websocket_uri()
        self.ws = await websockets.connect(uri, close_timeout=10)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.ws:
            await self.ws.close()

    async def ensure_runtime_enabled(self):
        if not self.runtime_enabled:
            await self.ws.send(
                json.dumps({"id": self.message_id, "method": "Runtime.enable"})
            )
            self.runtime_enabled = True
            self.message_id += 1

    async def send_input(self, input_data: dict) -> bool:
        try:
            await self.ensure_runtime_enabled()

            if not isinstance(input_data, dict) or "type" not in input_data:
                raise ShortcutError("Invalid input data structure")

            await self.ws.send(
                json.dumps(
                    {
                        "id": self.message_id,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": f"({self.js_function})({json.dumps(input_data)})",
                            "returnByValue": True,
                        },
                    }
                )
            )

            # Keep reading responses until we get sent_keydown_event
            while True:
                response = json.loads(
                    await asyncio.wait_for(self.ws.recv(), timeout=5.0)
                )
                if "error" in response:
                    raise ShortcutError(f"Electron error: {response['error']}")
                if "sent_keydown_event" in str(response):
                    self.message_id += 1
                    return True

        except Exception as e:
            raise ShortcutError(f"Failed to send input: {e}")


async def send_inputs(inputs: List[Dict]) -> None:
    try:
        async with CursorWebSocket() as cursor:
            for input_data in inputs:
                events = input_data if isinstance(input_data, list) else [input_data]
                for event in events:
                    try:
                        if not await cursor.send_input(event):
                            print(f"Failed to send input: {event}")
                            return
                        await asyncio.sleep(0.05)
                    except ShortcutError as e:
                        print(f"Error sending input {event}: {e}")
                        return
            print("Success")
    except Exception as e:
        print(f"Error: {e}")


async def send_message(text: str, web_mode: bool = False) -> None:
    inputs = [
        Input.shortcut([Mod.META, Mod.SHIFT], "P"),  # Unfocus chat if open
        Input.shortcut([Mod.META, Mod.SHIFT], "Y"),  # Open Composer
        Input.shortcut([Mod.META, Mod.SHIFT], "Y"),  # to be safe
        Input.text(text),  # Send the main text
    ]

    if web_mode:
        inputs.append(Input.text(" @Web"))  # Add web tag
        inputs.append(Input.shortcut([], "Enter"))  # Confirm web command

    inputs.append(Input.shortcut([], "Enter"))  # Final enter to send

    await send_inputs(inputs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send message to Cursor")
    parser.add_argument("message", help="The message to send")
    parser.add_argument("--web", action="store_true", help="Add @Web command")

    args = parser.parse_args()
    asyncio.run(send_message(args.message, args.web))
