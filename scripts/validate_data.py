from pathlib import Path
import pandas as pd,json,sqlite3
p=Path('CommercePulse');o=pd.read_csv(p/'data/Orders.csv');i=pd.read_csv(p/'data/Items.csv');c=pd.read_csv(p/'data/Customers.csv');pr=pd.read_csv(p/'data/Products.csv')
con=sqlite3.connect(p/'data/commerce-pulse.sqlite');results=[]
for year,state in [(2017,'SP'),(2018,'RJ'),(2016,'BA')]:
 sub=o[o.OrderDate.str.startswith(str(year)) & o.CustomerID.isin(c.loc[c.State.eq(state),'CustomerID'])]
 expected=(len(sub),int(sub.IsLate.sum()),int(sub.DeliveryEligible.sum()))
 got=con.execute('SELECT COUNT(*),COALESCE(SUM(IsLate),0),COALESCE(SUM(DeliveryEligible),0) FROM Orders JOIN Customers USING(CustomerID) WHERE substr(OrderDate,1,4)=? AND State=?',(str(year),state)).fetchone()
 assert got==expected;results.append({'filter':f'{year}/{state}','orders':got[0],'late':got[1],'eligible':got[2]})
for category in ['Bed Bath Table','Health Beauty','Computers Accessories']:
 ids=pr.loc[pr.Category.eq(category),'ProductID'];sel=i[i.ProductID.isin(ids)];sub=o[o.OrderID.isin(sel.OrderID)]
 got=con.execute('SELECT COUNT(DISTINCT i.OrderID),SUM(i.ItemValue) FROM Items i JOIN Products p USING(ProductID) WHERE p.Category=?',(category,)).fetchone()
 assert got[0]==len(sub) and abs(got[1]-sel.ItemValue.sum())<.001
 results.append({'filter':category,'orders':len(sub),'item_value':round(float(sel.ItemValue.sum()),2)})
# Verify every authored visual references a real model field and stays on its page.
model=json.loads((p/'powerbi/CommercePulse.SemanticModel/model.bim').read_text())['model'];refs={t['name']:set(c['name'] for c in t['columns'])|set(m['name'] for m in t.get('measures',[])) for t in model['tables']}
count=0
for v in (p/'powerbi/CommercePulse.Report/definition').rglob('visual.json'):
 d=json.loads(v.read_text());pos=d['position'];assert pos['x']+pos['width']<=1440 and pos['y']+pos['height']<=900
 for role in d['visual']['query']['queryState'].values():
  for proj in role['projections']:
   f=next(iter(proj['field'].values()));assert f['Property'] in refs[f['Expression']['SourceRef']['Entity']]
 count+=1
(p/'docs/filter-validation.json').write_text(json.dumps({'python_sql_checks':results,'visual_field_and_bounds_checks':count,'native_dax_and_interactions':'Not executed; Power BI Desktop required'},indent=2))
print('Passed',len(results),'filter reconciliations and',count,'visual-reference checks')
