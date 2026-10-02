# Required Desktop acceptance check

**Not yet executed:** this environment cannot run Power BI Desktop. Schema and Python checks do not replace native rendering or DAX validation.

- [ ] Open the PBIP, set DataFolder if necessary, Refresh without errors.
- [ ] Apply the supplied theme. Confirm all visuals render and no text is clipped at Fit to page and 100%.
- [ ] Clear every slicer on overview. Orders must equal 99,441; Delivered Item Value must equal R$ 13,221,498.11.
- [ ] Delivery page: eligible 96,470, late 6,534, late rate rounds to 6.8%.
- [ ] Select a year and state. Confirm KPI and charts change together; clear selections and recover baseline.
- [ ] Select a category. Compare its item value against SQL on Items joined to Products; order count must be distinct involved orders.
- [ ] Choose a seller row. Check order measures scope to distinct involved orders and do not multiply with item count.
- [ ] Click a state bar. Verify cross-filter/highlight behavior is useful; change Edit interactions to Filter if necessary. Check empty contexts.
- [ ] Confirm chronological month order and Month sorting by MonthNumber.
- [ ] Confirm review averages exclude missing reviews and review coverage remains separate.
- [ ] Sort the seller table by Seller Priority descending. Review qualifying sellers and sample sizes.
- [ ] Ensure independent page slicers are clear when comparing page totals.
- [ ] Export actual screenshots and record a 60–90 second interactive demo before publishing.

If a Desktop version rejects a visual or model definition, capture the exact error and fix it before publishing. The report uses standard built-in visuals; it requires no paid custom visuals.
