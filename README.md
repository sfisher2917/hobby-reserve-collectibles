# Hobby Reserve Collectibles

Premium black/gold storefront, eBay checkout and public CardScout catalog.

## Production eBay inventory

See [PRODUCTION-INVENTORY.md](PRODUCTION-INVENTORY.md) for credentials and data handling. The active architecture retrieves listings on website requests and details on item clicks. It has no saved catalog fallback. The old scheduled GitHub snapshot workflow and exporter CLI are retired.

- Public storefront: https://hobby-reserve-collectibles.onrender.com
- Production API: https://hobby-reserve-inventory-api.onrender.com
- API credentials belong only in the API service's protected Render environment.
- Seller authorization is required before real listings can be displayed. A healthy API is not evidence of a connected eBay account.
- All checkout remains on eBay; no payment processor is added.

## Development

`npm test` runs storefront/CardScout tests and Python integration tests. `npm run build` validates and copies public assets into dist. Render static hosting publishes public; the free API runs `python3 api/server.py` on the platform PORT.

CardScout is separate from the eBay seller integration. It retains its existing branding, researched retailer catalog, filters and visitor-local watchlists. No eBay inventory is stored in those watchlists.

Public-repository Render sources need explicit manual deployment. Verify terminal live status and HTTP behavior before claiming publication. See the data-handling document for historical snapshot retention limits.
