# Deployment handoff

Repository: https://github.com/sfisher2917/hobby-reserve-collectibles
Render static service: srv-dbqbhtgm7kps73d2mf5g
Render workspace: tea-dbq8lcgae00c73aa2ibg (user confirmed)
Render URL: https://hobby-reserve-collectibles.onrender.com
Render build is marked live; public HTTP checks still return 404 with x-render-routing: no-server, including after a clean redeploy. Do not claim public storefront availability until HTTP 200 and page content are verified.
Private review Site: appgprj_6af4baac9ee88191bc69740043b8cdb1
Expected review URL: https://hobby-reserve-review.bentmacaron1.chatgpt.site (verify deployment result)

Seven automated tests passed locally and in GitHub Actions. Browser QA verified desktop and 390px layout, search, numeric sorting, overlapping categories, and featured filtering with synthetic fixtures. QA fixtures were removed before publication.

Pending eBay seller authorization: EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_REFRESH_TOKEN in GitHub repository encrypted secrets. A partial public snapshot of 48 listings is published. eBay reported 357 store listings; further pages returned a security check. Full seller-authorized inventory and automatic updates remain pending. Category counts: Football 15, Baseball 15, Pokémon 9, Basketball 5, Soccer 3, Other Collectibles 1. No synthetic products are published.

Cost controls verified in Render dashboard on 2026-11-11: Hobby plan, no card on file, $0 monthly pipeline spending limit, $0 current and projected charges. No paid service or subscription added.

Data branch inventory-data updates independently of static hosting. Render code auto-deploy has not been observed; use manual deploy until Git provider integration is confirmed.

Product detail dialog implemented and tested. Importer supports seller-provided CSV/JSON with an explicit expected-count and optional required-description check. Full 357-item data and descriptions remain unavailable. Never claim completed full import without count, image, and source validation.
