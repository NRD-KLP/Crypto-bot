import httpx


URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin,ethereum"
    "&vs_currencies=usd"
    "&include_24hr_change=true"
)


async def get_market_data():
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(URL)
        response.raise_for_status()

        data = response.json()

        return {
            "btc_price": data["bitcoin"]["usd"],
            "btc_change": round(data["bitcoin"]["usd_24h_change"], 2),
            "eth_price": data["ethereum"]["usd"],
            "eth_change": round(data["ethereum"]["usd_24h_change"], 2),
        }
