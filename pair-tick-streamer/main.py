import asyncio, json, os, websockets
import time
from redis_writer import write_to_redis, cleanup_old_data

PAIR = os.getenv("PAIR", "BTC-USDT")
WS_SYMBOL = PAIR.lower().replace("-", "")
WS_URL = f"wss://stream.binance.com:9443/ws/{WS_SYMBOL}@kline_1s"
REDIS_KEY = f"{PAIR}:live"
INTERVAL = 1.0


async def listen():
    print(f"[{PAIR}] Connecting to: {WS_URL}")
    while True:  # Retry loop
        try:
            async with websockets.connect(
                WS_URL, ping_interval=180, ping_timeout=600
            ) as ws:
                next_tick = time.time() + INTERVAL
                while True:
                    try:
                        msg = await ws.recv()
                        payload = json.loads(msg)
                        kline = payload["k"]

                        row = {
                            "timestamp": kline["t"],
                            "price": float(kline["c"]),
                            "volume": float(kline["v"]),
                            "open": float(kline["o"]),
                            "high": float(kline["h"]),
                            "low": float(kline["l"]),
                            "close": float(kline["c"]),
                        }

                        write_to_redis(REDIS_KEY, row)
                        cleanup_old_data(REDIS_KEY)

                        next_tick = max(next_tick, time.time())
                        sleep_time = next_tick - time.time()

                        if sleep_time > 0:
                            await asyncio.sleep(sleep_time)

                        next_tick += INTERVAL

                    except websockets.ConnectionClosed as e:
                        print(f"[{PAIR}] Connection closed: {e.code} - {e.reason}")
                        break  # Exit inner loop to reconnect

                    except Exception as e:
                        print(f"[{PAIR}] WebSocket error: {e}")
                        await asyncio.sleep(5)
                        next_tick = time.time() + INTERVAL

        except Exception as e:
            print(f"[{PAIR}] Failed to connect: {e}")
            await asyncio.sleep(10)  # Wait before retrying


if __name__ == "__main__":
    asyncio.run(listen())
