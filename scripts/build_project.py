from pathlib import Path
import json, hashlib, shutil, zipfile, sqlite3, argparse
import pandas as pd

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,default=Path(__file__).resolve().parent/'source-data')
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'CommercePulse')
args=parser.parse_args()
ROOT=args.source.parent
OUT=args.output
for p in ['data','powerbi/CommercePulse.SemanticModel','powerbi/CommercePulse.Report/definition/pages','docs','sql','scripts','assets']:
    (OUT/p).mkdir(parents=True,exist_ok=True)
def write(path,text):
    p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
def js(path,obj): write(path,json.dumps(obj,indent=2,ensure_ascii=False))
def read(name): return pd.read_csv(args.source/name)
orders=read('olist_orders_dataset.csv');items=read('olist_order_items_dataset.csv')
cust=read('olist_customers_dataset.csv');products=read('olist_products_dataset.csv');sellers=read('olist_sellers_dataset.csv')
payments=read('olist_order_payments_dataset.csv');reviews=read('olist_order_reviews_dataset.csv')
translation=read('product_category_name_translation.csv')
assert orders.order_id.is_unique and cust.customer_id.is_unique
assert not items.duplicated(['order_id','order_item_id']).any()
assert products.product_id.is_unique and sellers.seller_id.is_unique
for c in ['order_purchase_timestamp','order_delivered_customer_date','order_estimated_delivery_date']:
    orders[c]=pd.to_datetime(orders[c],errors='coerce')
reviews['review_answer_timestamp']=pd.to_datetime(reviews.review_answer_timestamp,errors='coerce')
# Latest answered review per order; deterministic tie-breaker on review ID.
review=reviews.sort_values(['order_id','review_answer_timestamp','review_id']).drop_duplicates('order_id',keep='last')[['order_id','review_score']]
totals=items.groupby('order_id',as_index=False).agg(ItemValue=('price','sum'),FreightValue=('freight_value','sum'),ItemCount=('order_item_id','count'))
paid=payments.groupby('order_id',as_index=False).agg(PaymentValue=('payment_value','sum'))
fact=orders.merge(totals,on='order_id',how='left',validate='one_to_one').merge(paid,on='order_id',how='left',validate='one_to_one').merge(review,on='order_id',how='left',validate='one_to_one')
fact[['ItemValue','FreightValue','ItemCount','PaymentValue']]=fact[['ItemValue','FreightValue','ItemCount','PaymentValue']].fillna(0)
fact['OrderDate']=fact.order_purchase_timestamp.dt.normalize()
elapsed=(fact.order_delivered_customer_date-fact.order_purchase_timestamp).dt.total_seconds()/86400
eligible=(fact.order_status.eq('delivered') & fact.order_delivered_customer_date.notna() & fact.order_estimated_delivery_date.notna() & elapsed.ge(0))
fact['DeliveryEligible']=eligible.astype(int)
late=eligible & (fact.order_delivered_customer_date.dt.normalize()>fact.order_estimated_delivery_date.dt.normalize())
fact['IsLate']=late.astype(int)
fact['DeliveryDays']=elapsed.where(eligible)
fact['DelayDays']=(fact.order_delivered_customer_date.dt.normalize()-fact.order_estimated_delivery_date.dt.normalize()).dt.days.clip(lower=0).where(eligible)
fact['DeliveryOutcome']='Not eligible';fact.loc[eligible,'DeliveryOutcome']='On time';fact.loc[late,'DeliveryOutcome']='Late'
fact['ReviewBand']=fact.review_score.map({1:'1–2 | Low',2:'1–2 | Low',3:'3 | Neutral',4:'4–5 | High',5:'4–5 | High'}).fillna('Unreviewed')
fact['DelayBand']='Not eligible';fact.loc[eligible,'DelayBand']='0 | On time'
fact.loc[late & fact.DelayDays.le(3),'DelayBand']='1 | 1–3 days';fact.loc[late & fact.DelayDays.between(4,7),'DelayBand']='2 | 4–7 days';fact.loc[late & fact.DelayDays.gt(7),'DelayBand']='3 | 8+ days'
fact=fact.rename(columns={'order_id':'OrderID','customer_id':'CustomerID','order_status':'OrderStatus','review_score':'ReviewScore'})
fact=fact[['OrderID','CustomerID','OrderDate','OrderStatus','ItemValue','FreightValue','ItemCount','PaymentValue','DeliveryEligible','IsLate','DeliveryDays','DelayDays','DeliveryOutcome','ReviewScore','ReviewBand','DelayBand']]
dimcust=cust.rename(columns={'customer_id':'CustomerID','customer_unique_id':'CustomerUniqueID','customer_state':'State','customer_city':'City'})[['CustomerID','CustomerUniqueID','State','City']]
dimprod=products.merge(translation,on='product_category_name',how='left',validate='many_to_one')
dimprod['Category']=dimprod.product_category_name_english.fillna(dimprod.product_category_name).fillna('unknown').str.replace('_',' ').str.title()
dimprod=dimprod.rename(columns={'product_id':'ProductID'})[['ProductID','Category']]
dimseller=sellers.rename(columns={'seller_id':'SellerID','seller_state':'SellerState','seller_city':'SellerCity'})[['SellerID','SellerState','SellerCity']]
dimitem=items.rename(columns={'order_id':'OrderID','order_item_id':'ItemNumber','product_id':'ProductID','seller_id':'SellerID','price':'ItemValue','freight_value':'FreightValue'})[['OrderID','ItemNumber','ProductID','SellerID','ItemValue','FreightValue']]
dates=pd.DataFrame({'Date':pd.date_range(fact.OrderDate.min(),fact.OrderDate.max())})
dates['Year']=dates.Date.dt.year;dates['Month']=dates.Date.dt.strftime('%b');dates['MonthNumber']=dates.Date.dt.month;dates['YearMonth']=dates.Date.dt.strftime('%Y-%m')
tables={'Orders':fact,'Items':dimitem,'Customers':dimcust,'Products':dimprod,'Sellers':dimseller,'Calendar':dates}
for name,df in tables.items(): df.to_csv(OUT/'data'/f'{name}.csv',index=False,date_format='%Y-%m-%d')
assert len(fact)==len(orders)
assert abs(fact.ItemValue.sum()-items.price.sum())<.001
assert abs(fact.PaymentValue.sum()-payments.payment_value.sum())<.001
assert fact.IsLate.sum()<=fact.DeliveryEligible.sum()
for child,key,parent in [('Items','OrderID','Orders'),('Items','ProductID','Products'),('Items','SellerID','Sellers'),('Orders','CustomerID','Customers')]:
    assert tables[child][key].isin(tables[parent][key]).all()
eligible_df=fact[fact.DeliveryEligible.eq(1)]
insights={
 'orders':len(fact),'orders_with_items':int(fact.ItemCount.gt(0).sum()),'item_value_brl':round(float(dimitem.ItemValue.sum()),2),
 'delivered_item_value_brl':round(float(fact.loc[fact.OrderStatus.eq('delivered'),'ItemValue'].sum()),2),
 'eligible_deliveries':len(eligible_df),'late_deliveries':int(fact.IsLate.sum()),'late_rate':float(eligible_df.IsLate.mean()),
 'mean_delivery_days':float(eligible_df.DeliveryDays.mean()),'mean_review_score':float(fact.ReviewScore.mean()),
 'late_mean_review':float(eligible_df.loc[eligible_df.IsLate.eq(1),'ReviewScore'].mean()),
 'on_time_mean_review':float(eligible_df.loc[eligible_df.IsLate.eq(0),'ReviewScore'].mean()),
 'orders_without_items':int(fact.ItemCount.eq(0).sum()),'reviews_removed_by_order_deduplication':len(reviews)-len(review),
 'date_min':str(fact.OrderDate.min().date()),'date_max':str(fact.OrderDate.max().date())}
js('docs/validation-results.json',insights)
by_state=eligible_df.merge(dimcust,on='CustomerID').groupby('State').agg(Eligible=('OrderID','count'),Late=('IsLate','sum'))
by_state['LateRate']=by_state.Late/by_state.Eligible;by_state.sort_values('Late',ascending=False).to_csv(OUT/'docs/state-diagnostics.csv')

# Order metrics include all orders unless an item-side dimension is being filtered.
scope='IF(ISCROSSFILTERED(Products) || ISCROSSFILTERED(Sellers) || ISFILTERED(Items), CALCULATE({expr}, KEEPFILTERS(TREATAS(VALUES(Items[OrderID]), Orders[OrderID]))), {expr})'
def scoped(expr): return scope.replace('{expr}',expr)
measures={
 'Orders':(scoped('COUNTROWS(Orders)'),'#,0'),
 'Delivered Orders':(scoped('CALCULATE(COUNTROWS(Orders), Orders[OrderStatus] = "delivered")'),'#,0'),
 'Item Value':('SUM(Items[ItemValue])','"R$ "#,0.00'),
 'Delivered Item Value':('CALCULATE([Item Value], Orders[OrderStatus] = "delivered")','"R$ "#,0.00'),
 'Freight Value':('SUM(Items[FreightValue])','"R$ "#,0.00'),
 'Average Order Value':('DIVIDE([Delivered Item Value], [Delivered Orders])','"R$ "#,0.00'),
 'Eligible Deliveries':(scoped('CALCULATE(COUNTROWS(Orders), Orders[DeliveryEligible] = 1)'),'#,0'),
 'Late Deliveries':(scoped('CALCULATE(COUNTROWS(Orders), Orders[IsLate] = 1)'),'#,0'),
 'Late Rate':('DIVIDE([Late Deliveries], [Eligible Deliveries])','0.0%'),
 'On Time Rate':('IF([Eligible Deliveries] > 0, 1 - [Late Rate])','0.0%'),
 'Average Delivery Days':(scoped('AVERAGE(Orders[DeliveryDays])'),'0.0'),
 'Average Review':(scoped('AVERAGE(Orders[ReviewScore])'),'0.00'),
 'Reviewed Orders':(scoped('COUNT(Orders[ReviewScore])'),'#,0'),
 'Low Review Orders':(scoped('CALCULATE(COUNTROWS(Orders), Orders[ReviewScore] >= 1, Orders[ReviewScore] <= 2)'),'#,0'),
 'Low Review Rate':('DIVIDE([Low Review Orders], [Reviewed Orders])','0.0%'),
 'Review Coverage':('DIVIDE([Reviewed Orders], [Orders])','0.0%'),
 'Freight Share':('DIVIDE([Freight Value], [Item Value] + [Freight Value])','0.0%'),
 'Distinct Buyers':(scoped('DISTINCTCOUNT(Customers[CustomerUniqueID])'),'#,0'),
 'Seller Priority':('IF([Eligible Deliveries] >= 100, [Late Deliveries])','#,0'),
}
# Buyer identity lives on Orders too, avoiding reverse relationship dependence.
fact['CustomerUniqueID']=fact.CustomerID.map(dimcust.set_index('CustomerID').CustomerUniqueID)
fact.to_csv(OUT/'data/Orders.csv',index=False,date_format='%Y-%m-%d')
measures['Distinct Buyers']=(scoped('DISTINCTCOUNT(Orders[CustomerUniqueID])'),'#,0')
modeltables=[]
for name,df in tables.items():
    cols=[];types=[]
    for c in df.columns:
        t='dateTime' if pd.api.types.is_datetime64_any_dtype(df[c]) else 'int64' if pd.api.types.is_integer_dtype(df[c]) else 'double' if pd.api.types.is_float_dtype(df[c]) else 'string'
        col={'name':c,'dataType':t,'sourceColumn':c,'summarizeBy':'none'}
        if c=='Month':col['sortByColumn']='MonthNumber'
        if t=='dateTime':col['formatString']='yyyy-MM-dd'
        if c in ['OrderID','CustomerID','CustomerUniqueID','ProductID','SellerID','ItemNumber','MonthNumber']:col['isHidden']=True
        cols.append(col);types.append('{"'+c+'", '+({'dateTime':'type date','int64':'Int64.Type','double':'type number','string':'type text'}[t])+'}')
    m='let\n Source = Csv.Document(File.Contents(DataFolder & "\\'+name+'.csv"), [Delimiter=",", Columns='+str(len(cols))+', Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n Typed = Table.TransformColumnTypes(Headers, {'+', '.join(types)+'}, "en-US")\nin Typed'
    table={'name':name,'columns':cols,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':m.splitlines()}}]}
    if name=='Orders':table['measures']=[{'name':n,'expression':e,'formatString':f,'displayFolder':'Portfolio KPIs'} for n,(e,f) in measures.items()]
    modeltables.append(table)
rels=[]
for ft,fc,tt,tc in [('Orders','CustomerID','Customers','CustomerID'),('Orders','OrderDate','Calendar','Date'),('Items','OrderID','Orders','OrderID'),('Items','ProductID','Products','ProductID'),('Items','SellerID','Sellers','SellerID')]:
    rels.append({'name':ft+'_'+tt,'fromTable':ft,'fromColumn':fc,'toTable':tt,'toColumn':tc,'crossFilteringBehavior':'oneDirection'})
js('powerbi/CommercePulse.SemanticModel/model.bim',{'name':'CommercePulse','compatibilityLevel':1600,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','tables':modeltables,'relationships':rels,'expressions':[{'name':'DataFolder','kind':'m','expression':'"C:\\CommercePulse\\data" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'}]}})
js('powerbi/CommercePulse.SemanticModel/definition.pbism',{'version':'1.0','settings':{}})
js('powerbi/CommercePulse.pbip',{'version':'1.0','artifacts':[{'report':{'path':'CommercePulse.Report'}}],'settings':{'enableAutoRecovery':True}})
js('powerbi/CommercePulse.Report/definition.pbir',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../CommercePulse.SemanticModel'}}})
BASE='https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'
js('powerbi/CommercePulse.Report/definition/version.json',{'$schema':BASE+'versionMetadata/1.0.0/schema.json','version':'2.0.0'})
js('powerbi/CommercePulse.Report/definition/report.json',{'$schema':BASE+'report/2.0.0/schema.json','themeCollection':{}})
def literal(v): return {'expr':{'Literal':{'Value':str(v).lower() if isinstance(v,bool) else str(v) if isinstance(v,(float,int)) else "'"+v.replace("'","''")+"'"}}}
def color(v):return {'solid':{'color':literal(v)}}
def field(t,c,measure=False):return {('Measure' if measure else 'Column'):{'Expression':{'SourceRef':{'Entity':t}},'Property':c}}
def visual(page,n,kind,x,y,w,h,roles,title):
    q={role:{'projections':[{'field':field(t,c,m),'queryRef':t+'.'+c,'nativeQueryRef':c} for t,c,m in fs]} for role,fs in roles.items()}
    v={'visualType':kind,'query':{'queryState':q},'visualContainerObjects':{
     'title':[{'properties':{'show':literal(True),'text':literal(title),'fontSize':literal(12),'fontColor':color('#172B4D')}}],
     'background':[{'properties':{'show':literal(True),'color':color('#FFFFFF'),'transparency':literal(0)}}],
     'border':[{'properties':{'show':literal(True),'color':color('#E2E8F0'),'radius':literal(8)}}]}}
    if kind=='slicer':v['objects']={'data':[{'properties':{'mode':literal('Dropdown')}}]}
    if kind=='card':v['objects']={'labels':[{'properties':{'color':color('#0F766E'),'fontSize':literal(26)}}]}
    obj={'$schema':BASE+'visualContainer/2.7.0/schema.json','name':n,'position':{'x':x,'y':y,'width':w,'height':h,'z':y,'tabOrder':y+x},'visual':v}
    js(f'powerbi/CommercePulse.Report/definition/pages/{page}/visuals/{n}/visual.json',obj)
def metric(n):return ('Orders',n,True)
def col(t,n):return (t,n,False)
pages=[('overview','01 | Executive overview'),('delivery','02 | Delivery diagnostics'),('experience','03 | Customer experience'),('sellers','04 | Seller performance')]
for page,title in pages:
    js(f'powerbi/CommercePulse.Report/definition/pages/{page}/page.json',{'$schema':BASE+'page/2.0.0/schema.json','name':page,'displayName':title,'displayOption':'FitToPage','width':1440,'height':900,'objects':{'background':[{'properties':{'color':color('#F1F5F9'),'transparency':literal(0)}}]}})
    # Native slicers on every page; deliberate independent page contexts.
    for i,(t,c,label) in enumerate([('Calendar','Year','Purchase year'),('Customers','State','Customer state'),('Products','Category','Product category'),('Orders','OrderStatus','Order status')]):
        visual(page,'filter'+str(i),'slicer',24+i*354,24,336,76,{'Values':[col(t,c)]},label)
    cards={'overview':['Delivered Item Value','Orders','On Time Rate','Average Review'], 'delivery':['Eligible Deliveries','Late Deliveries','Late Rate','Average Delivery Days'], 'experience':['Reviewed Orders','Average Review','Low Review Rate','Review Coverage'], 'sellers':['Delivered Item Value','Delivered Orders','Late Rate','Freight Share']}[page]
    for i,m in enumerate(cards):visual(page,'kpi'+str(i),'card',24+i*354,120,336,124,{'Values':[metric(m)]},m)
    if page=='overview':
        charts=[('trend','lineChart',24,264,864,286,{'Category':[col('Calendar','YearMonth')],'Y':[metric('Delivered Item Value')]},'Delivered item value by purchase month • BRL'),('states','barChart',912,264,504,286,{'Category':[col('Customers','State')],'Y':[metric('Late Deliveries')]},'Late deliveries by customer state'),('categories','barChart',24,574,864,286,{'Category':[col('Products','Category')],'Y':[metric('Delivered Item Value')]},'Category sales • delivered items'),('status','donutChart',912,574,504,286,{'Category':[col('Orders','OrderStatus')],'Y':[metric('Orders')]},'Order status mix')]
    elif page=='delivery':
        charts=[('trend','lineChart',24,264,864,286,{'Category':[col('Calendar','YearMonth')],'Y':[metric('Late Rate')]},'Late rate by purchase month'),('bands','barChart',912,264,504,286,{'Category':[col('Orders','DelayBand')],'Y':[metric('Orders')]},'Delay severity • includes ineligible orders'),('states','tableEx',24,574,864,286,{'Values':[col('Customers','State'),metric('Eligible Deliveries'),metric('Late Deliveries'),metric('Late Rate'),metric('Average Delivery Days')]},'State diagnostic • compare volume and rate'),('reviews','barChart',912,574,504,286,{'Category':[col('Orders','DeliveryOutcome')],'Y':[metric('Average Review')]},'Ratings by delivery outcome • association')]
    elif page=='experience':
        charts=[('ratings','columnChart',24,264,684,286,{'Category':[col('Orders','ReviewBand')],'Y':[metric('Orders')]},'Review bands • missing reviews shown'),('outcomes','columnChart',732,264,684,286,{'Category':[col('Orders','DeliveryOutcome')],'Y':[metric('Low Review Rate')]},'Low review rate by delivery outcome'),('category','tableEx',24,574,864,286,{'Values':[col('Products','Category'),metric('Orders'),metric('Average Review'),metric('Low Review Rate'),metric('Late Rate')]},'Category experience • order-based, non-additive'),('monthly','lineChart',912,574,504,286,{'Category':[col('Calendar','YearMonth')],'Y':[metric('Average Review')]},'Review score over time')]
    else:
        # Seller IDs visible in report even though hidden in field list.
        charts=[('seller','tableEx',24,264,1392,360,{'Values':[col('Sellers','SellerID'),col('Sellers','SellerState'),metric('Delivered Item Value'),metric('Eligible Deliveries'),metric('Late Deliveries'),metric('Late Rate'),metric('Average Review'),metric('Seller Priority')]},'Seller queue • priority = late orders where eligible deliveries ≥100'),('state','barChart',24,648,684,212,{'Category':[col('Sellers','SellerState')],'Y':[metric('Delivered Item Value')]},'Seller-state delivered item value'),('risk','barChart',732,648,684,212,{'Category':[col('Sellers','SellerState')],'Y':[metric('Late Rate')]},'Seller-state late rate • inspect volume before acting')]
    for n,k,x,y,w,h,r,t in charts:visual(page,n,k,x,y,w,h,r,t)
js('powerbi/CommercePulse.Report/definition/pages/pages.json',{'$schema':BASE+'pagesMetadata/1.0.0/schema.json','pageOrder':[p for p,t in pages],'activePageName':'overview'})
js('assets/CommercePulse-theme.json',{'name':'Commerce Pulse','dataColors':['#0F766E','#2563EB','#F59E0B','#E11D48','#64748B','#7C3AED'],'background':'#F1F5F9','foreground':'#172B4D','tableAccent':'#0F766E'})

# Reproducible SQL uses normalized tables, never a raw multi-fact join.
db=sqlite3.connect(OUT/'data/commerce-pulse.sqlite')
for n,df in tables.items():df.to_sql(n,db,index=False,if_exists='replace')
sql='''-- SQLite; one row per order before joining to any item analysis.
-- Calendar-day lateness, only eligible delivered orders.
SELECT c.State, COUNT(*) AS eligible_orders, SUM(o.IsLate) AS late_orders,
       ROUND(100.0 * SUM(o.IsLate) / COUNT(*), 2) AS late_pct,
       ROUND(AVG(o.DeliveryDays), 2) AS mean_delivery_days
FROM Orders o JOIN Customers c ON c.CustomerID = o.CustomerID
WHERE o.DeliveryEligible = 1
GROUP BY c.State ORDER BY late_orders DESC;

-- Experience association; not proof that delay caused poor ratings.
SELECT DeliveryOutcome, COUNT(*) AS orders, COUNT(ReviewScore) AS reviewed,
       ROUND(AVG(ReviewScore),2) AS mean_review,
       ROUND(100.0 * SUM(CASE WHEN ReviewScore <= 2 THEN 1 ELSE 0 END)
         / NULLIF(COUNT(ReviewScore),0),2) AS low_review_pct
FROM Orders GROUP BY DeliveryOutcome;

-- Seller attribution: a multi-seller order belongs to each involved seller.
WITH seller_orders AS (SELECT DISTINCT SellerID, OrderID FROM Items)
SELECT s.SellerID, COUNT(*) AS eligible_orders, SUM(o.IsLate) AS late_orders,
       ROUND(100.0 * SUM(o.IsLate) / COUNT(*),2) AS late_pct
FROM seller_orders s JOIN Orders o ON s.OrderID=o.OrderID
WHERE o.DeliveryEligible=1
GROUP BY s.SellerID HAVING COUNT(*) >= 100 ORDER BY late_orders DESC;
'''
write('sql/analysis.sql',sql)
clean_sql='\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('--'))
for q in clean_sql.split(';'):
    if q.strip():db.execute(q).fetchall()
db.close()
write('powerbi/measures.dax','\n\n'.join(n+' =\n'+e for n,(e,f) in measures.items()))
write('.gitignore','powerbi/**/.pbi/\n*.pbix\n__pycache__/\ndata/*.sqlite\n')
write('requirements.txt','pandas>=2.2,<3\n')
shutil.copy2(__file__,OUT/'scripts/build_project.py')
print(json.dumps(insights,indent=2))
