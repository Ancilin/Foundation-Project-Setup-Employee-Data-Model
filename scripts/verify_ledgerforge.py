#!/usr/bin/env python3
"""LedgerForge self-check tool. Tells you whether YOUR results match the official numbers.

Usage (run from this folder):
  python verify_ledgerforge.py checks                      # run the integrity checks on the official data (see what 'correct' looks like)
  python verify_ledgerforge.py checks --data my_export/    # run them on CSVs exported from YOUR database (same file/column names as 03_Data/csv)
  python verify_ledgerforge.py payroll my_payroll.csv      # compare your payroll engine output (LF-07)
  python verify_ledgerforge.py trial-balance my_tb.csv     # compare your trial balance (LF-15)
  python verify_ledgerforge.py summary                     # print the official headline totals

my_payroll.csv needs columns: employee_id, run_id, gross_pay, total_deductions, net_pay   (more columns are fine)
my_tb.csv needs columns: account_code, debit, credit   (totals for the whole period)
"""
import sys, os, argparse
import pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); OFFICIAL=os.path.join(HERE,"..","03_Data","csv")
def rd(d,f,**k): return pd.read_csv(os.path.join(d,f+".csv"),**k)
def ok(flag,name,detail): print(("PASS  " if flag else "FAIL  ")+name+"  -  "+detail); return flag
def checks(d):
    je,jl,coa=rd(d,"journal_entries"),rd(d,"journal_lines"),rd(d,"chart_of_accounts")
    pr,pi,inv,emp=rd(d,"payroll_runs"),rd(d,"payroll_items"),rd(d,"invoices"),rd(d,"employees")
    r=[]
    diff=round(jl.debit.sum()-jl.credit.sum(),2); per=jl.groupby("entry_id")[["debit","credit"]].sum(); bad=int((per.debit.round(2)!=per.credit.round(2)).sum())
    r.append(ok(diff==0 and bad==0,"Every journal entry balances",f"debits-credits={diff}, unbalanced entries={bad}"))
    pj=jl.merge(je[["entry_id","source_type","source_id"]],on="entry_id"); pj=pj[(pj.source_type=="PAYROLL_RUN")&pj.account_code.between(5001,5005)]
    led=pj.groupby("source_id").debit.sum().round(2); run=pr.set_index("run_id").total_employer_cost.round(2)
    mx=float((run-led.reindex(run.index).fillna(0)).abs().max()); r.append(ok(mx<0.01,"Payroll equals ledger, every month",f"largest monthly difference={mx:.2f}"))
    ar=jl[jl.account_code==1100]; arb=round(ar.debit.sum()-ar.credit.sum(),2); op=round(inv[inv.status.isin(["SENT","OVERDUE","PARTIALLY_PAID"])].balance_due.sum(),2)  # DRAFT and CANCELLED invoices are not posted to the ledger
    r.append(ok(abs(arb-op)<0.01,"Receivables equal open invoices",f"ledger 1100={arb:,.2f}, open (sent/overdue/part-paid) invoices={op:,.2f}"))
    miss=int((~pi.employee_id.isin(emp.employee_id)).sum()); r.append(ok(miss==0,"Payroll employees exist",f"payroll rows with unknown employee={miss}"))
    x=pi.merge(emp[["employee_id","exit_date"]],on="employee_id"); x=x[x.exit_date.notna()]
    late=int((pd.to_datetime(x.period_start)>pd.to_datetime(x.exit_date)).sum()); r.append(ok(late==0,"Nobody is paid after leaving",f"payroll rows after exit_date={late}"))
    print(f"\n{sum(r)}/{len(r)} checks passed"); return all(r)
def payroll(csv,d):
    mine=pd.read_csv(csv); off=rd(d,"payroll_items")[["run_id","employee_id","gross_pay","total_deductions","net_pay"]]
    m=off.merge(mine,on=["run_id","employee_id"],how="left",suffixes=("","_mine")); found=m.net_pay_mine.notna().sum()
    print(f"Rows expected {len(off)}, rows found in your file {found}")
    bad=pd.Series(False,index=m.index)
    for c in ["gross_pay","total_deductions","net_pay"]:
        if c+"_mine" in m: bad|=(m[c]-m[c+"_mine"]).abs()>0.01
    bad|=m.net_pay_mine.isna(); good=int((~bad).sum()); print(f"Exact matches (within 1 paisa): {good}/{len(off)} = {100*good/len(off):.2f}%")
    if bad.any(): print("\nFirst mismatches (compare these rows by hand):"); print(m[bad].head(8).to_string(index=False))
    return not bad.any()
def tb(csv,d):
    jl=rd(d,"journal_lines"); off=jl.groupby("account_code")[["debit","credit"]].sum().round(2); mine=pd.read_csv(csv).groupby("account_code")[["debit","credit"]].sum().round(2)
    j=off.join(mine,rsuffix="_mine",how="outer").fillna(0); j["bad"]=((j.debit-j.debit_mine).abs()>0.01)|((j.credit-j.credit_mine).abs()>0.01)
    print(f"Accounts compared: {len(j)}, mismatched: {int(j.bad.sum())}"); 
    if j.bad.any(): print(j[j.bad].head(10))
    return not j.bad.any()
def summary(d):
    jl,coa,pr=rd(d,"journal_lines"),rd(d,"chart_of_accounts"),rd(d,"payroll_runs")
    m=jl.merge(coa[["account_code","account_type"]],on="account_code"); m["net"]=m.credit-m.debit; g=m.groupby("account_type").net.sum()
    print(f"Revenue  {g['INCOME']:,.2f}\nExpenses {-g['EXPENSE']:,.2f}\nProfit   {g['INCOME']+g['EXPENSE']:,.2f}\nPayroll runs {len(pr)}, employer cost {pr.total_employer_cost.sum():,.2f}")
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("cmd",choices=["checks","payroll","trial-balance","summary"]); ap.add_argument("file",nargs="?"); ap.add_argument("--data",default=OFFICIAL); a=ap.parse_args()
    res={"checks":lambda:checks(a.data),"summary":lambda:summary(a.data),"payroll":lambda:payroll(a.file,a.data),"trial-balance":lambda:tb(a.file,a.data)}[a.cmd]()
    sys.exit(0 if res in (True,None) else 1)
