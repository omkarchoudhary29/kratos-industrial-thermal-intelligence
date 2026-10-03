#!/usr/bin/env python3
import asyncio
import json
import urllib.request
import websockets
import subprocess
import time

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

async def main():
    cmd = [CHROME_PATH, "--remote-debugging-port=9232", "--headless=new", "--disable-gpu", "--window-size=1920,1080", "about:blank"]
    p = subprocess.Popen(cmd)
    time.sleep(2)
    req = urllib.request.urlopen("http://127.0.0.1:9232/json/list")
    data = json.loads(req.read().decode())
    ws_url = data[0]["webSocketDebuggerUrl"]

    ws = await websockets.connect(ws_url)
    mid = 1
    async def send(method, params=None):
        nonlocal mid
        payload = {"id": mid, "method": method, "params": params or {}}
        mid += 1
        await ws.send(json.dumps(payload))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == mid - 1:
                return r.get("result", {})

    await send("Console.enable")
    await send("Page.navigate", {"url": "http://127.0.0.1:5174"})
    await asyncio.sleep(4)

    # Check root HTML
    body_res = await send("Runtime.evaluate", {
        "expression": "document.body.innerHTML",
        "returnByValue": True
    })
    print("BODY HTML (first 500 chars):", body_res.get("result", {}).get("value", "")[:500])

    # Check if there is an error in console or root
    err_res = await send("Runtime.evaluate", {
        "expression": "window.__vite_plugin_react_preamble_installed__ ? 'VITE PREAMBLE OK' : 'NO PREAMBLE'",
        "returnByValue": True
    })
    print("PREAMBLE:", err_res.get("result", {}).get("value"))

    # Check root element
    root_res = await send("Runtime.evaluate", {
        "expression": "document.getElementById('root') ? document.getElementById('root').innerHTML : 'NO ROOT'",
        "returnByValue": True
    })
    print("ROOT INNER (first 500 chars):", root_res.get("result", {}).get("value", "")[:500])

    await ws.close()
    p.terminate()

if __name__ == "__main__":
    asyncio.run(main())
