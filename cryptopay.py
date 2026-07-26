import httpx

from config import CRYPTO_PAY_API, CRYPTO_PAY_TOKEN

HEADERS = {
    "Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN
}


class CryptoPayError(Exception):
    pass


async def _request(method: str, payload: dict | None = None):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{CRYPTO_PAY_API}/{method}",
            headers=HEADERS,
            json=payload or {}
        )

    if response.status_code != 200:
        raise CryptoPayError(
            f"HTTP {response.status_code}\n{response.text}"
        )

    try:
        data = response.json()
    except Exception:
        raise CryptoPayError("Crypto Pay returned invalid JSON.")

    if not data.get("ok"):
        raise CryptoPayError(str(data))

    return data["result"]


async def create_invoice(user_id: int, amount: float):
    result = await _request(
        "createInvoice",
        {
            "asset": "USDT",
            "amount": amount,
            "description": "Bit Ref 4U subscription",
            "payload": str(user_id)
        }
    )

    return result


async def get_invoice(invoice_id: int):
    result = await _request(
        "getInvoices",
        {
            "invoice_ids": str(invoice_id)
        }
    )

    items = result.get("items", [])

    if not items:
        return None

    return items[0]


async def is_invoice_paid(invoice_id: int):
    invoice = await get_invoice(invoice_id)

    if invoice is None:
        return False

    return invoice.get("status") == "paid"