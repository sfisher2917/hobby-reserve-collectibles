# Hobby Reserve Collectibles

Premium black and metallic gold storefront using the original Hobby Reserve logo. Quality Cards. Trusted Service.

## Status

Render reports the deployment live at https://hobby-reserve-collectibles.onrender.com, but public HTTP checks return 404 with x-render-routing: no-server. Public availability is NOT verified. A private review copy is deployed separately. A manually retrieved public snapshot contains 48 of the 357 listings reported by the eBay store on November 11, 2026. Further pages returned an eBay security check, so this is a partial catalog. Categories were reviewed from listing titles. Photos, listed prices, and purchase links came from the public store page. Full item descriptions remain on eBay. The snapshot is labeled and hidden after 24 hours; automatic inventory updates still require seller authorization. No synthetic products are presented as stock. All checkout stays on eBay.

## Seller authorization (one-time)

1. Use an approved production application in the eBay Developers Program. Obtain seller consent for the production Trading API OAuth scope `https://api.ebay.com/oauth/api_scope`. Obtain a refresh token using the official authorization-code flow. Developer program enrollment/key approval may be required by eBay. Do not paste keys into chat or commit them.
2. In this repository's Settings → Secrets and variables → Actions, save secrets `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, and `EBAY_REFRESH_TOKEN`.
3. Set repository variable `EBAY_SELLER_ID` to the exact seller username if different from `hobbyreservecollectibles`. The exporter verifies the authorized seller before publishing any data.
4. Optionally set `FEATURED_ITEM_IDS` to comma-separated eBay item IDs. Only selected active items receive the Featured badge. Nothing is promoted as featured without this selection.
5. Run Actions → Refresh eBay inventory → Run workflow. Verify a successful export and compare its count and sample items with eBay. Production live API testing remains pending until credentials are configured.

## Inventory design

- Read-only Trading API: `GetUser`, paginated `GetMyeBaySelling.ActiveList`, and `GetItem` for descriptions and full photos. Does not create listings, change prices, access payments, or place orders.
- Full snapshots replace prior inventory, removing sold/ended/removed items after the next successful sync. This is periodic polling, not instantaneous webhooks.
- Sync runs at minutes 7 and 37 each hour. GitHub schedules can be delayed. Browser refreshes the data every five minutes and hides snapshots older than 90 minutes; ended listings are hidden locally as well. Availability is always confirmed on eBay.
- Public inventory is stored on `inventory-data`, read from raw.githubusercontent.com; main hosts code and static assets. Data pushes do not redeploy the static host. Descriptions are plain text, never executed HTML. Credentials exist only in GitHub encrypted secrets and runner process memory.
- Description/photo details are cached for up to 24 hours. Prices and active status refresh every run. Initial sync calls GetItem for every active item; check your eBay application's call quota if inventory grows. Exports stop at the API's 25,000-item cap.
- Category rules use eBay category names and listing titles; sealed products and memorabilia can also belong to a sport/TCG. Review ambiguous items and adjust `classify()` as needed.
- GitHub public repositories use standard hosted runners. Keep the repo public to avoid private-runner minute billing; do not enable larger runners. GitHub may disable scheduled workflows after extended repository inactivity; inspect Actions if freshness stops.

## Free hosting

Deploy the `public` directory as a Render Static Site, branch `main`, build command `node scripts/build.mjs`, Render currently uses the public repository URL; code changes require a manual deploy through the Render connector/dashboard until its GitHub provider connection is configured. Inventory updates do not require deployment. No paid web service, database, payment processor, domain, or subscription is needed. The included Render subdomain is sufficient. Render workspace bandwidth/build allowances and billing settings still apply: verify the account has no payment method if strict zero spend is required, and set the build pipeline spend limit to $0. Render bandwidth overages can be billed when a payment method exists. Account billing verified: Hobby workspace, no card on file, $0 monthly build spending limit, $0 current/projected charges. Keep these controls in place. A free service is not a guarantee of unlimited traffic.

## Local checks

`npm test` checks search, overlapping categories, numeric sorting, featured filtering, expired products, URL safety, category mapping, paginated exports, removal of old inventory, and seller identity validation using synthetic fixtures. `npm run build` validates static deployment assets. No npm or Python dependencies are needed.

Official references:
- https://developer.ebay.com/Devzone/XML/docs/Reference/eBay/GetMyeBaySelling.html
- https://developer.ebay.com/Devzone/XML/docs/Reference/eBay/GetItem.html
- https://developer.ebay.com/api-docs/static/oauth-authorization-code-grant.html
- https://render.com/docs/static-sites

Instagram: https://www.instagram.com/hobbyreservecollectibles/
eBay: https://www.ebay.com/str/hobbyreservecollectibles
