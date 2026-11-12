# Production inventory data handling

Hobby Reserve Inventory Sync retrieves active listings on request from the owner's Production eBay account, fixed to seller `hobbyreservecollectibles`. Checkout remains on eBay. It has no listing database, filesystem writes, persistent listing cache, scheduled export, analytics, or payload logs. Listing responses exist transiently during requests and in the visitor's current page memory. API responses use no-store headers. Credentials live separately in protected Render environment variables; access tokens exist in request memory only.

Catalog requests verify the public seller ID and paginate active listings. Item clicks retrieve current photos, descriptions, prices, condition, item specifics, availability, shipping and return terms. OutputSelector limits eBay responses to public product fields. Orders, transactions, buyers, bidders, customer accounts and private notes are not requested. Returned output is also allowlisted. Other sellers and inactive listings are rejected. Errors never publish saved inventory. Normal Render infrastructure/access logs may exist, but application logs contain no eBay response bodies or buyer information.

Required server environment: `EBAY_CLIENT_ID` (Production App ID), `EBAY_CLIENT_SECRET` (Production Cert ID), `EBAY_REFRESH_TOKEN` (seller-authorized Production OAuth refresh token). Optional `FEATURED_ITEM_IDS` is an owner-curated ID list. Use the base `https://api.ebay.com/oauth/api_scope` Trading scope; do not add order or buyer scopes. Never put credentials in public JavaScript or repository files. Sandbox credentials cannot enable Production.

The former scheduled snapshot workflow is retired. Current inventory files contain only empty connection status. Historical Git commits, hosted build archives, old private review copies and independently saved copies may still contain old listing snapshots. This change does not erase those histories. Historical cleanup must be verified separately before claiming all previously stored eBay data is removed. Developer exemption approval is not blanket compliance approval.

The free Render API may sleep when idle. The storefront allows cold-start time and links to eBay when unavailable. It never substitutes a saved catalog. Refreshes are limited to visible inventory. Product details recheck availability; checkout confirms price and availability on eBay.

## Owner authorization bootstrap

The owner opens `/oauth/connect` on the API service. eBay's Production RuName must have its accepted URL set to `https://hobby-reserve-inventory-api.onrender.com/oauth/callback`; `EBAY_REDIRECT_URI` contains that RuName, not the callback URL. The declined URL can remain eBay's default.

The connection flow requests only the base Trading scope, binds state to a Secure/HttpOnly/SameSite browser cookie, and rejects missing, expired or replayed state. The authorization code is exchanged on the server; the resulting user token must identify hobbyreservecollectibles. No buyer information is requested. After verification, the refresh credential enables the running process temporarily. A private, cookie-bound result page lets the owner copy it into Render's protected `EBAY_REFRESH_TOKEN` environment variable. The token is revealed only after a same-origin POST, and the result session expires after 15 minutes. The result page uses no-store, no-referrer, CSP and frame-denial headers. Application access logs remain disabled. Platform logs may retain ephemeral callback request URLs; no listing data is logged.

A successful browser consent alone does not prove the credential was saved durably. Verify a fresh Render deployment and a real seller inventory response before reporting completion.
