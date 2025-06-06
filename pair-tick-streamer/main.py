import datetime
import asyncio, json, os, websockets
import time
from redis_writer import write_to_redis, cleanup_old_data
import logging

PAIR = os.getenv("PAIR", "BTC-USDT")
WS_SYMBOL = PAIR.lower().replace("-", "")
WS_URL = f"wss://stream.binance.com:9443/ws/{WS_SYMBOL}@kline_1s"
REDIS_KEY = f"{PAIR}:live"
INTERVAL = 1.0

# Configuration du logging (au début du fichier)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


async def listen():
    logging.info("[%s] Connecting to: %s", PAIR, WS_URL)
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
                        logging.info(
                            f"Kline timestamp: {kline['t']}, Local time: "
                            f"{round(datetime.datetime.now().timestamp()) * 1000}"
                        )
                        write_to_redis(REDIS_KEY, row)
                        cleanup_old_data(REDIS_KEY)

                        next_tick = max(next_tick, time.time())
                        sleep_time = next_tick - time.time()

                        if sleep_time > 0:
                            await asyncio.sleep(sleep_time)

                        next_tick += INTERVAL

                    except websockets.ConnectionClosed as e:
                        logging.warning(
                            f"[{PAIR}] Connection closed: {e.code} - {e.reason}"
                        )
                        break  # Exit inner loop to reconnect

                    except Exception as e:
                        logging.error(f"[{PAIR}] WebSocket error: {e}")
                        await asyncio.sleep(5)
                        next_tick = time.time() + INTERVAL

        except Exception as e:
            logging.error(f"[{PAIR}] Failed to connect: {e}")
            await asyncio.sleep(10)  # Wait before retrying


if __name__ == "__main__":
    asyncio.run(listen())
