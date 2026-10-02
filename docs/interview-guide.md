# Interview walkthrough

**Opening:** “I investigated how delivery performance relates to customer experience in a historical e-commerce marketplace. I built an order-and-item model because joining raw payments and reviews to items can multiply values.”

1. Explain the stakeholder: marketplace operations deciding where to investigate delays.
2. Show the overview and apply a year/state filter. Explain item value versus revenue and profit.
3. Show delivery diagnostics. Explain denominator eligibility and calendar-day lateness.
4. Show ratings by outcome. Say association, not causation. Name two confounders.
5. Show the seller queue and explain the minimum volume threshold and shared-order attribution.
6. Explain TREATAS: selected item groups identify orders, then the order metrics are recalculated once per order.
7. Conclude with an investigation or experiment proposal, not invented business impact.

Be prepared to explain COUNTROWS versus DISTINCTCOUNT, one-to-many relationships, filter context, missing values, review deduplication and non-additive KPIs. Re-run one SQL query and reconcile it with a visual. Describe the AI assistance used if asked; ownership means understanding and validating the work.

Resume wording after Desktop validation:
“Built a four-page Power BI case study of 99K e-commerce orders using SQL, Python and DAX; designed order/item relationships and documented delivery and review KPIs to prioritize operational investigation.”
