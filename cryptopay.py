import httpx

from config import (
    CRYPTO_PAY_TOKEN,
    CRYPTO_PAY_API,
)



HEADERS = {
    "Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN
}



async def create_invoice(
        user_id: int,
        amount: float,
        currency: str = "USDT"
):

    url = (
        f"{CRYPTO_PAY_API}/createInvoice"
    )


    payload = {
        "asset": currency,
        "amount": str(amount),

        "description": (
            f"Bit Ref 4U Premium "
            f"30 days | User {user_id}"
        )
    }


    async with httpx.AsyncClient() as client:

        response = await client.post(
            url,
            headers=HEADERS,
            json=payload
        )


        data = response.json()


    if not data.get("ok"):

        raise Exception(
            data
        )


    result = data["result"]


    return {
        "invoice_id": result["invoice_id"],

        "pay_url": (
            result.get(
                "bot_invoice_url"
            )
            or
            result.get(
                "mini_app_invoice_url"
            )
        )
    }



async def get_invoice(
        invoice_id: int
):

    url = (
        f"{CRYPTO_PAY_API}/getInvoices"
    )


    params = {
        "invoice_ids": invoice_id
    }


    async with httpx.AsyncClient() as client:

        response = await client.get(
            url,
            headers=HEADERS,
            params=params
        )


        data = response.json()


    if not data.get("ok"):

        raise Exception(
            data
        )


    invoices = data["result"]["items"]


    if not invoices:

        return None


    return invoices[0]



async def is_invoice_paid(
        invoice_id: int
):

    invoice = await get_invoice(
        invoice_id
    )


    if not invoice:

        return False


    return (
        invoice["status"]
        ==
        "paid"
    )
