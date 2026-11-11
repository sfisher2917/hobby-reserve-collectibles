# Deployment handoff

Live URL: https://hobby-reserve-collectibles.onrender.com
Repository: https://github.com/sfisher2917/hobby-reserve-collectibles
Render workspace: tea-dbq8lcgae00c73aa2ibg (Stephen’s workspace; user confirmed)
Render static site: srv-dbqbhtgm7kps73d2mf5g
Frontend code commit: 04bed1fa868a444b30092eb7380e1740da843279
Data branch: inventory-data

Seven automated tests passed locally and in GitHub Actions. Browser checks verified desktop/390px layout and search, numeric sorting, categories, featured filtering with synthetic QA products. QA fixtures were removed and were never pushed or deployed.

Pending: production eBay application keys and seller OAuth refresh token as GitHub encrypted repository secrets; first real inventory sync and comparison with seller account. No live item-level inventory has been verified. Site shows an honest connection-pending state and directs customers to eBay.

Cost: static service created; no paid compute, database, subscription, or custom domain added. Render account billing/spend controls unverified; dashboard requires sign-in. Render bandwidth overages apply if a payment method exists. Do not claim guaranteed zero future cost until verified.

Deployment: public Git URL integration did not trigger auto deploy after code push, so final frontend deployment was triggered manually. Configure Render’s Git provider for source auto deploy if desired. Inventory data branch updates are independent and never require frontend deployment.
