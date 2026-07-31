import httpx


COINGECKO_API = (
    "https://api.coingecko.com/api/v3"
)


async def get_price(coin_id):

    url = (
        f"{COINGECKO_API}/simple/price"
    )

    params = {
        "ids": coin_id,
        "vs_currencies": "usd"
    }


    async with httpx.AsyncClient() as client:

        response = await client.get(
            url,
            params=params
        )

        data = response.json()


    return data.get(
        coin_id,
        {}
    ).get(
        "usd",
        0
    )



async def get_full_market():

    btc = await get_price(
        "bitcoin"
    )

    eth = await get_price(
        "ethereum"
    )

    ton = await get_price(
        "the-open-network"
    )


    return {

        "btc_price": btc,

        "eth_price": eth,

        "ton_price": ton

    }
