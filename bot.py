import os
import time
import requests
from datetime import datetime

# ============================================================
# BTC WHALE MONITOR
# Monitoramento educativo de grandes movimentações de Bitcoin
# NÃO executa compras ou vendas.
# ============================================================

MIN_BTC = float(os.getenv("MIN_BTC", "100"))
CHECK_SECONDS = int(os.getenv("CHECK_SECONDS", "10"))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

MEMPOOL_API = "https://mempool.space/api/mempool/recent"
PRICE_API = "https://mempool.space/api/v1/prices"

seen = set()


def get_json(url):
    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "BTC-Whale-Monitor"}
    )
    response.raise_for_status()
    return response.json()


def get_btc_price():
    try:
        data = get_json(PRICE_API)
        return float(data["USD"])
    except Exception:
        return None


def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, data=data, timeout=20)
    except Exception as error:
        print("Erro no Telegram:", error)


def process_transaction(tx, btc_price):
    txid = tx.get("txid")

    if not txid:
        return

    if txid in seen:
        return

    seen.add(txid)

    # Valor da transação em satoshis
    value_sats = tx.get("value", 0)

    btc = value_sats / 100_000_000

    if btc < MIN_BTC:
        return

    usd = None

    if btc_price:
        usd = btc * btc_price

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    if usd:
        usd_text = f"${usd:,.0f}"
    else:
        usd_text = "N/D"

    message = f"""
🐋 GRANDE MOVIMENTAÇÃO BTC

🕐 Horário:
{now}

₿ Quantidade:
{btc:,.2f} BTC

💵 Valor aproximado:
{usd_text}

🔗 Transação:
https://mempool.space/tx/{txid}

⚠️ IMPORTANTE:
Uma grande transferência não significa necessariamente compra ou venda. Pode ser transferência entre carteiras, custódia, exchange ou outras operações.

Este bot é somente para monitoramento.
"""

    print(message)

    send_telegram(message)


def cleanup_seen():
    global seen

    # Mantém a memória do programa limitada
    if len(seen) > 10000:
        seen = set(list(seen)[-5000:])


def main():

    print("=" * 60)
    print("🐋 BTC WHALE MONITOR")
    print("=" * 60)

    print(f"Alerta mínimo: {MIN_BTC} BTC")
    print(f"Intervalo: {CHECK_SECONDS} segundos")
    print("Modo: MONITORAMENTO")
    print("")

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        print("✅ Telegram configurado")
    else:
        print("ℹ️ Telegram ainda não configurado")

    print("")
    print("Iniciando monitoramento...")
    print("=" * 60)

    while True:

        try:

            transactions = get_json(MEMPOOL_API)

            btc_price = get_btc_price()

            for tx in transactions:
                process_transaction(tx, btc_price)

            cleanup_seen()

            price_text = (
                f"${btc_price:,.2f}"
                if btc_price
                else "N/D"
            )

            print(
                datetime.now().strftime("%H:%M:%S"),
                "| BTC:",
                price_text,
                "| Transações analisadas:",
                len(transactions)
            )

        except KeyboardInterrupt:

            print("\nMonitor encerrado.")
            break

        except Exception as error:

            print(
                datetime.now().strftime("%H:%M:%S"),
                "| Erro temporário:",
                error
            )

        time.sleep(CHECK_SECONDS)


if __name__ == "__main__":
    main()
