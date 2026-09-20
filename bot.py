import os
import time
import requests
from datetime import datetime

# ============================================================
# BTC WHALE MONITOR V2
# Monitoramento educativo de grandes movimentações BTC
# NÃO executa compras ou vendas.
# ============================================================

MIN_BTC = float(os.getenv("MIN_BTC", "100"))
CHECK_SECONDS = int(os.getenv("CHECK_SECONDS", "10"))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

BASE_URL = "https://mempool.space/api"

seen = set()


def get_json(url):
    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "BTC-Whale-Monitor-V2"}
    )
    response.raise_for_status()
    return response.json()


def get_btc_price():
    try:
        data = get_json(
            "https://mempool.space/api/v1/prices"
        )
        return float(data["USD"])
    except Exception:
        return None


def send_telegram(message):

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:
        requests.post(
            url,
            data=data,
            timeout=20
        )
    except Exception as error:
        print("Erro Telegram:", error)


def btc_from_sats(sats):
    return sats / 100_000_000


def analyze_transaction(txid, btc_price):

    try:

        tx = get_json(
            f"{BASE_URL}/tx/{txid}"
        )

        vin = tx.get("vin", [])
        vout = tx.get("vout", [])

        input_value = sum(
            item.get("prevout", {}).get("value", 0)
            for item in vin
        )

        output_value = sum(
            item.get("value", 0)
            for item in vout
        )

        input_btc = btc_from_sats(input_value)
        output_btc = btc_from_sats(output_value)

        # Maior saída individual
        outputs = [
            btc_from_sats(item.get("value", 0))
            for item in vout
        ]

        largest_output = (
            max(outputs)
            if outputs
            else 0
        )

        # Número de entradas e saídas
        input_count = len(vin)
        output_count = len(vout)

        # Classificação estrutural.
        # Isto NÃO determina intenção de compra ou venda.
        if input_count > output_count * 2:
            classification = "CONSOLIDACAO DE UTXOs"

        elif output_count > input_count * 2:
            classification = "DISTRIBUICAO PARA VARIAS SAIDAS"

        else:
            classification = "GRANDE TRANSFERENCIA"

        usd = (
            output_btc * btc_price
            if btc_price
            else None
        )

        if usd:
            usd_text = f"${usd:,.0f}"
        else:
            usd_text = "N/D"

        confirmed = tx.get("status", {}).get(
            "confirmed",
            False
        )

        status = (
            "CONFIRMADA"
            if confirmed
            else "PENDENTE"
        )

        now = datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        message = (
            "🐋 GRANDE MOVIMENTAÇÃO BTC\n\n"
            f"🕐 {now}\n\n"
            f"₿ Valor movimentado: "
            f"{output_btc:,.2f} BTC\n"
            f"💵 Valor aproximado: {usd_text}\n\n"
            f"📥 Entradas: {input_count}\n"
            f"📤 Saídas: {output_count}\n"
            f"💰 Maior saída: "
            f"{largest_output:,.2f} BTC\n\n"
            f"🔎 Classificação estrutural:\n"
            f"{classification}\n\n"
            f"⛓️ Status: {status}\n\n"
            f"🔗 https://mempool.space/tx/{txid}\n\n"
            "⚠️ Uma transferência grande não prova "
            "compra ou venda. A classificação acima "
            "descreve somente a estrutura da transação."
        )

        print("\n" + "=" * 65)
        print(message)
        print("=" * 65)

        send_telegram(message)

    except Exception as error:

        print(
            "Erro analisando transação",
            txid,
            ":",
            error
        )


def main():

    print("=" * 65)
    print("🐋 BTC WHALE MONITOR V2")
    print("=" * 65)

    print(
        f"Alerta mínimo: {MIN_BTC} BTC"
    )

    print(
        f"Intervalo: {CHECK_SECONDS} segundos"
    )

    print(
        "Modo: MONITORAMENTO"
    )

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        print("Telegram: CONFIGURADO")
    else:
        print("Telegram: NÃO CONFIGURADO")

    print("=" * 65)

    while True:

        try:

            recent = get_json(
                f"{BASE_URL}/mempool/recent"
            )

            btc_price = get_btc_price()

            price_text = (
                f"${btc_price:,.2f}"
                if btc_price
                else "N/D"
            )

            print(
                datetime.now().strftime(
                    "%H:%M:%S"
                ),
                "| BTC:",
                price_text,
                "| Transações:",
                len(recent)
            )

            for tx in recent:

                txid = tx.get("txid")

                if not txid:
                    continue

                if txid in seen:
                    continue

                seen.add(txid)

                btc = btc_from_sats(
                    tx.get("value", 0)
                )

                if btc >= MIN_BTC:

                    analyze_transaction(
                        txid,
                        btc_price
                    )

            # Evita crescimento infinito da memória
            if len(seen) > 5000:
                seen.clear()

        except Exception as error:

            print(
                datetime.now().strftime(
                    "%H:%M:%S"
                ),
                "| Erro:",
                error
            )

        time.sleep(CHECK_SECONDS)


if __name__ == "__main__":
    main()
