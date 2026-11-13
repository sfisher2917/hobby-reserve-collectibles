# CardScout source review — November 13, 2026

30 public offers: 29 available products and one explicitly labeled orderable preorder. All 28 previous public offers were checked on their exact seller product pages; no currently sold-out offer was retained. Previously excluded research records remain excluded from LISTINGS. No changes to eBay inventory, API credentials, buyer information or visitor-local watchlists.

## Published changes

- Dave & Adam’s 2026 Topps Museum Collection Baseball Hobby: $679.95 (was $749.95).
- Dave & Adam’s Pokémon Delta Reign six-pack bundle: $49.95 (was $54.95).
- Added Dave & Adam’s 2026 Topps Midnight Football Hobby at $699.95, November 13 release, seven cards and three autographs on average. Existing exact-format local product photo retained.
- Topps Basketball Mega is released (retailer date November 12), $89.95, 12 packs / 15 cards; removed preorder warning.
- MTG Star Trek Play ($124.95) and Collector ($549.95) now available, not presells. Publisher global release November 13; retailer lists November 6, disclosed in notes. Exact formats: 30 x 14 cards and 12 x 15 cards respectively. Play box seller suggested reference $209.70 is labeled seller suggested, not MSRP.
- Added English OP-18 display preorder at Gamers Guild AZ, $214.99. Exact page has an enabled Add to cart button and InStock Offer schema. Publisher and retailer agree November 20 release. 24 packs / 12 cards per pack. New local image comes from that retailer's pictured English display. Collection/index prices conflicted ($223.99/$227.99); used exact product page $214.99, not an aggregator or lowest-price claim.
- Corrected excluded Stadium Club Football Mega research release to December 22 (manufacturer page), not December 10. Kept excluded because current orderability was not established.
- Public catalog assembly rejects unavailable statuses and invalid asking prices before UI filters.

## Evidence

Each retained offer's `url` points to its exact seller product page. Dave & Adam’s pages displayed exact prices and an Add to Cart offer for the same product in Recently Viewed; none displayed an unavailable message. Panini Prizm WNBA direct product Offer schema states InStock, USD 349.95. Direct executor fetches of Dave & Adam’s returned 403, so used the supported web retrieval channel; no restriction bypass attempted.

Official research sources:
- https://www-next.topps.com/release-calendar (November 13 Midnight; November 18 Chrome Football; November 25 Stadium Club Basketball)
- https://www.topps.com/products/2026-topps-stadium-club-football-mega-box
- https://www.paniniamerica.net/cards/trading-cards.html
- https://www.paniniamerica.net/2026-panini-prizm-wnba-trading-card-box-hobby
- https://www.pokemon.com/us/news/pokemon-tcg-mega-evolution-delta-reign-product-showcase
- https://disneylorcana.com/en/product/hyperia-city/
- https://magic.wizards.com/en/news/feature/where-to-play-star-trek
- https://en.onepiece-cardgame.com/products/op18.html

Exact changed offer sources:
- https://www.dacardworld.com/sports-cards/2026-topps-museum-collection-baseball-hobby-box
- https://www.dacardworld.com/gaming/pokemon-mega-evolution-delta-reign-6-pack-booster-bundle
- https://www.dacardworld.com/sports-cards/2026-topps-midnight-football-hobby-box
- https://www.dacardworld.com/sports-cards/2026-27-topps-basketball-mega-box
- https://www.dacardworld.com/gaming/magic-the-gathering-star-trek-play-booster-box
- https://www.dacardworld.com/gaming/magic-the-gathering-star-trek-collector-booster-box
- https://www.gamersguildusa.com/products/one-piece-tcg-op-18-the-dominance-of-god-display-box-english

## Gaps

No newly verified available soccer replacement was established. Announced-only products, unavailable older boxes and unverified manufacturer preorders remain outside the public catalog. No missing chase valuation, retail/MSRP or zero-autograph placeholder added. Prices exclude tax and shipping unless stated.

Validation: existing JavaScript/Python tests and static build. Live publication verified separately after deployment.
