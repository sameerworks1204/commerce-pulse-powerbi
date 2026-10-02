# KPI contract

All slicers use purchase date, not delivery date. Customer state refers to the buyer; seller state refers to the seller. An empty selection result shows blank rates, not 0%.

| Metric | Definition |
|---|---|
| Orders | Distinct source order rows; all statuses and orders without items remain unless category/seller selections limit scope |
| Delivered Item Value | Sum item prices on delivered orders; BRL; excludes freight; not platform revenue |
| Average Order Value | Delivered item value divided by delivered order count; under category selections this is selected-item value per order containing those items |
| Eligible Deliveries | Delivered, actual and estimated delivery dates present, actual delivery not before purchase |
| Late Rate | Late eligible orders / eligible deliveries; actual calendar day later than promised calendar day |
| Average Delivery Days | Mean elapsed purchase-to-actual-delivery time across eligible orders; fractional days |
| Average Review | Mean latest answered review score per order; unreviewed excluded |
| Low Review Rate | Reviewed orders scored 1 or 2 / reviewed orders |
| Review Coverage | Reviewed orders / all scoped orders |
| Freight Share | Freight / (item value + freight); charged freight share, not logistics expense ratio |
| Distinct Buyers | Unique customer identity across selected orders, using customer_unique_id |
| Seller Priority | Late order count if at least 100 eligible deliveries; otherwise blank |

Orders and ratings across categories/sellers are non-additive. Multi-category and multi-seller orders appear in every involved group. Their total must be recalculated at order grain rather than summed from visible rows. A seller's late-order rate concerns involved orders; it does not identify which seller caused a delay.

An order without items has zero item value, but remains in Orders. Payment amounts are preserved for reconciliation and do not replace merchandise value. Orders outside the delivered status are excluded from delivered item value, but included in Item Value.

The final months have sparse purchases and may be incomplete; avoid interpreting them as a confirmed demand decline. Do not label ratings as NPS; no recommendation survey exists.
