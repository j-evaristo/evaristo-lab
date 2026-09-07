"""Project workflows, fitting, interpretation, and portable file formats."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime
import csv
import hashlib
import html
import json
import math
import numpy as np
from scipy.optimize import least_squares, brentq
from scipy.special import log_ndtr
from scipy.stats import chi2 as chi2_distribution
from . import __version__
from .engine import (MODEL_NAMES, HALF_LIVES, Distribution, predict, finite,
                     validate_history, mixture_cdf, sample_lag)

DATA=Path(__file__).parent/'data'
HISTORIES=json.loads((DATA/'histories.json').read_text(encoding='utf-8'))
TRACERS={
 '3H':{'label':'Tritium (3H)','unit':'TU','history_required':True},
 '3He(trit)':{'label':'Tritiogenic helium-3','unit':'TU','history_required':True},
 '3H0':{'label':'Initial tritium at water table','unit':'TU','history_required':True},
 '3H/3H0':{'label':'Tritium / initial tritium','unit':'ratio','history_required':True},
 'CFC-11':{'label':'CFC-11, equivalent air','unit':'pptv','history_required':True},
 'CFC-12':{'label':'CFC-12, equivalent air','unit':'pptv','history_required':True},
 'CFC-113':{'label':'CFC-113, equivalent air','unit':'pptv','history_required':True},
 'SF6':{'label':'SF6, equivalent air','unit':'pptv','history_required':True},
 '14C':{'label':'Carbon-14','unit':'pmC','history_required':False},
 '4He':{'label':'Radiogenic helium-4','unit':'cm³ STP/g','history_required':False},
 '39Ar':{'label':'Argon-39','unit':'% modern','history_required':False},
 '85Kr':{'label':'Krypton-85','unit':'dpm/cm³ Kr','history_required':True},
 '81Kr':{'label':'Krypton-81','unit':'% modern','history_required':False},
 'NO3-N':{'label':'Nitrate as N / loading scenario','unit':'mg N/L','history_required':True}}

def default_history(tracer):
    tracer='3H' if tracer in ('3He(trit)','3H0','3H/3H0') else tracer
    preferred={'3H':'stored_U','CFC-11':'stored_F','CFC-12':'stored_E','CFC-113':'stored_G','SF6':'stored_I','14C':'stored_O','39Ar':'stored_Z','81Kr':'stored_AA'}
    if tracer in preferred: return preferred[tracer]
    return next((k for k,v in HISTORIES.items() if v['tracer']==tracer),'')

def blank_project():
    return {'schema_version':1,'name':'Untitled groundwater model','samples':[],
      'model':{'type':'EPM','mean':25.,'shape':1.,'upper':0.,'lower':5.},
      'model2':{'type':'PFM','mean':200.,'shape':1.,'upper':0.,'lower':5.},
      'binary':False,'fraction':.7,'uz':0.,'settings':{
        'age_min':.1,'age_max':1000.,'fit_shape':False,'fit_fraction':False,'fit_mean2':False,
        'shape_min':.001,'shape_max':10.,'a0':100.,'he4_rate':1.5e-11,'dic1':1.,'dic2':1.,
        'gas_uz':0.,'history_before':'hold','history_after':'hold','history_interpolation':'linear',
        'contaminant_decay':0.},'custom_histories':{},'custom_age':{'ages':[],'weights':[]},
        'note':'All selected observations are modeled by one stationary water-age distribution.'}

def default_project():
    p=blank_project()
    p['name']='Demonstration — synthetic well'
    p['note']='Synthetic demonstration generated from an EPM (mean 25 years, ratio 1). Uncertainties are illustrative, not laboratory measurements. Replace with your data and recharge-area histories.'
    for tracer,sigma,offset in [('3H',.2,.25),('SF6',.15,-.3),('CFC-12',12.,.2),('CFC-11',6.,-.15)]:
        history=default_history(tracer)
        value=predict(p['model'],p['model2'],False,.7,tracer,2015.,HISTORIES[history],0,p['settings'])
        p['samples'].append({'name':'DEMO-01','date':2015.,'tracer':tracer,'value':round(value+sigma*offset,5),'sigma':sigma,'qualifier':'=','history':history,'use':True})
    return p

def example_project(index=0):
    """Original example observations; uncertainties are explicitly illustrative."""
    examples=json.loads((DATA/'usgs_examples.json').read_text(encoding='utf-8'))
    example=examples[int(index)]
    p=blank_project();m=example['model'];types=m['model'].split('-')
    p['name']=['USGS example 1 — Modesto PSW-1','USGS example 2 — groundwater mixing','USGS example 3 — Missouri River'][int(index)]
    p['note']=example['note']+' Original examples do not supply the uncertainties needed by this application. The loaded 5% (minimum 0.05) uncertainty values are illustrative weighting scales; replace them before statistical interpretation. Only selected observations share the fitted model.'
    p['model'].update({'type':types[1] if len(types)>1 else types[0],'mean':m['mean_age'],'shape':m.get('parameter',1)})
    p['uz']=m.get('uz',0);p['binary']=len(types)>1;p['fraction']=m.get('fraction',.7)
    p['model2'].update({'type':types[2] if len(types)>2 else 'PFM','mean':m.get('mean_age_2',200),'shape':m.get('parameter_2',1)})
    p['settings'].update({'history_interpolation':'step','dic1':m.get('dic_1',1),'dic2':m.get('dic_2',1),'gas_uz':m.get('gas_uz',0),'age_max':20000 if int(index)==1 else 1000,'fit_shape':int(index)<2})
    for tracer,h in example['histories'].items():
        h=deepcopy(h);h['tracer']='3H' if tracer in ('3He(trit)','3H0','3H/3H0') else tracer
        h['source']=example['source_file'];h['note']='Exact example input history; includes legacy reconstructed and projected values.'
        p['custom_histories']['example_'+tracer]=h
    for i,sample in enumerate(example['samples']):
        for tracer,value in sample['values'].items():
            if tracer not in TRACERS: continue
            include=(i==0 and tracer in ('3H','3He(trit)','SF6')) if int(index)==0 else (i==0 if int(index)==1 else True)
            p['samples'].append({'name':sample['id'],'date':parse_date(sample['date']),'tracer':tracer,'value':value,'sigma':max(abs(value)*.05,.05),'qualifier':'=','history':'example_'+tracer,'use':include})
    return p

def parse_date(value):
    try: return finite(value,'Sample date')
    except ValueError: pass
    for form in ('%Y-%m-%d','%Y-%m-%d %H:%M:%S','%m/%d/%Y'):
        try:
            date=datetime.strptime(str(value),form)
            start=datetime(date.year,1,1)
            return date.year+(date-start).total_seconds()/(datetime(date.year+1,1,1)-start).total_seconds()
        except ValueError: pass
    raise ValueError('Use a decimal year or an ISO date such as 2024-07-15.')

def history_for(p,row):
    key=row.get('history','')
    if not key: return None
    history=p.get('custom_histories',{}).get(key,HISTORIES.get(key))
    if history is None: raise ValueError(f'Input history "{key}" is unavailable. Choose or import a history.')
    tracer='3H' if row['tracer'] in ('3He(trit)','3H0','3H/3H0') else row['tracer']
    if history.get('tracer') and history['tracer']!=tracer:
        raise ValueError(f'{row["tracer"]} uses an incompatible {history.get("tracer")} input history.')
    return history

def validate_project(project):
    p=deepcopy(project)
    defaults=blank_project()
    for k,v in defaults.items(): p.setdefault(k,v)
    p['settings']={**defaults['settings'],**p['settings']}
    p['uz']=finite(p['uz'],'Water UZ time')
    p['fraction']=finite(p['fraction'],'First-component fraction')
    if p['uz']<0 or not 0<=p['fraction']<=1: raise ValueError('UZ time must be nonnegative and mixing fraction must lie between 0 and 1.')
    settings=p['settings']
    for key in ('age_min','age_max','shape_min','shape_max','a0','he4_rate','dic1','dic2','gas_uz','contaminant_decay'):
        settings[key]=finite(settings[key],key)
        if settings[key]<0: raise ValueError(key+' cannot be negative.')
    if settings['age_min']<=0 or settings['age_max']<=settings['age_min']:
        raise ValueError('Fitting bounds require 0 < minimum age < maximum age.')
    if settings['shape_min']<=0 or settings['shape_max']<=settings['shape_min']:
        raise ValueError('Shape fitting bounds require 0 < minimum < maximum.')
    if min(settings['dic1'],settings['dic2'])<=0: raise ValueError('Both DIC concentrations must be positive.')
    for key in ('history_before','history_after'):
        if settings[key] not in ('hold','zero','error'): raise ValueError('History boundary options are hold, zero, or error.')
    if settings['history_interpolation'] not in ('linear','step'): raise ValueError('History interpolation must be linear or step.')
    Distribution(p['model'],p['custom_age'])
    if p['binary']: Distribution(p['model2'],p['custom_age'])
    rows=[x for x in p['samples'] if x.get('use',True)]
    if not rows: raise ValueError('Include at least one observation to calculate or fit.')
    for row in rows:
        if row.get('tracer') not in TRACERS: raise ValueError('Choose a supported tracer for every included row.')
        row['date']=parse_date(row['date'])
        row['value']=finite(row['value'],'Observed concentration')
        row['sigma']=finite(row['sigma'],'Measurement uncertainty')
        if row['value']<0 or row['sigma']<=0: raise ValueError('Observations must be nonnegative; every included row needs positive 1σ uncertainty.')
        if row.get('qualifier','=') not in ('=','<'): raise ValueError('Observation qualifier must be = or < (detection limit).')
        history=history_for(p,row)
        if TRACERS[row['tracer']]['history_required'] and history is None: raise ValueError('Select an input history for '+row['tracer']+'.')
        if history is not None: validate_history(history)
    return p,rows

def predictions(p,rows):
    return np.array([predict(p['model'],p['model2'],p['binary'],p['fraction'],r['tracer'],r['date'],history_for(p,r),p['uz'],p['settings'],p['custom_age']) for r in rows])

def residual_vector(predicted,rows):
    residual=[]
    for pred,row in zip(predicted,rows):
        z=(float(pred)-row['value'])/row['sigma']
        residual.append(math.sqrt(max(0.,-2*float(log_ndtr(-z)))) if row.get('qualifier')=='<' else z)
    return np.array(residual)

def _fit(p,rows,quick=False):
    p=deepcopy(p)
    if p['model']['type']=='CUSTOM': raise ValueError('Custom age weights are fixed. Use Calculate to evaluate them; choose a parameterized model to fit.')
    s=p['settings']
    names=[('model','mean')]
    lower=[math.log(s['age_min'])]; upper=[math.log(s['age_max'])]
    if s['fit_shape'] and p['model']['type'] in ('EPM','PEM','DM','GAM'):
        names.append(('model','shape'))
        shape_min=max(s['shape_min'],.05 if p['model']['type']=='GAM' else .00001)
        shape_max=min(s['shape_max'],100 if p['model']['type']=='DM' else 1000)
        if shape_min>=shape_max: raise ValueError('Shape bounds do not overlap the selected model domain.')
        lower.append(math.log(shape_min)); upper.append(math.log(shape_max))
    if p['binary'] and s['fit_mean2']:
        if p['model2']['type']=='CUSTOM': raise ValueError('Custom component ages cannot be optimized.')
        names.append(('model2','mean'));lower.append(math.log(s['age_min']));upper.append(math.log(s['age_max']))
    if p['binary'] and s['fit_fraction']:
        names.append(('','fraction'));lower.append(0.);upper.append(1.)
    groups={}
    for row in rows: groups.setdefault((row.get('name',''),row['date']),set()).add(row['tracer'])
    if any(len(g&{'3H','3He(trit)','3H0','3H/3H0'})>2 for g in groups.values()):
        raise ValueError('Do not fit 3H, 3He, derived 3H0 and their ratio as independent measurements. Include measured 3H and tritiogenic 3He, and exclude their derived quantities.')
    def encode(): return np.array([math.log(max(p[a][b],1e-12)) if a else p[b] for a,b in names])
    def assign(x):
        for value,(a,b) in zip(x,names):
            if a: p[a][b]=float(math.exp(value))
            else: p[b]=float(value)
    def fun(x):
        assign(x)
        return residual_vector(predictions(p,rows),rows)
    initial=np.clip(encode(),lower,upper)
    young_grid=(np.linspace(s['age_min'],min(180,s['age_max']),50 if quick else 110)
                if s['age_min']<180 else np.array([]))
    grid=np.unique(np.r_[np.geomspace(s['age_min'],s['age_max'],40 if quick else 90),young_grid])
    scan=[]
    for age in grid:
        x=initial.copy();x[0]=math.log(age)
        r=fun(x);scan.append(float(r@r))
    # Every scan minimum is a seed, with a cap for pathological input histories.
    candidates=[i for i in range(len(grid)) if (i==0 or scan[i]<=scan[i-1]) and (i==len(grid)-1 or scan[i]<=scan[i+1])]
    candidates=sorted(candidates,key=lambda i:scan[i])[:(4 if quick else 9)]
    seeds=[initial]
    for i in candidates:
        x=initial.copy();x[0]=math.log(grid[i]);seeds.append(x)
    if len(names)>1:
        rng=np.random.default_rng(1729)
        seeds.extend(rng.uniform(lower,upper,size=(3 if quick else 8,len(names))))
    solutions=[]
    for x in seeds:
        fit=least_squares(fun,np.clip(x,lower,upper),bounds=(lower,upper),max_nfev=100 if quick else 240,ftol=2e-8,xtol=2e-8,gtol=2e-8,diff_step=1e-4)
        solutions.append((float(fit.fun@fit.fun),fit.x.copy(),bool(fit.success)))
    solutions.sort(key=lambda x:x[0]); best=solutions[0]
    assign(best[1])
    bound_hits=[('.'.join(x) if x[0] else x[1]) for i,x in enumerate(names) if min(best[1][i]-lower[i],upper[i]-best[1][i])<.005*(upper[i]-lower[i])]
    # A one-dimensional scan, holding all other parameters at their optimum.
    # This is deliberately NOT labeled a confidence interval or profiled likelihood.
    optimum=best[1].copy();scores=[]
    for age in grid:
        x=optimum.copy();x[0]=math.log(age);r=fun(x);scores.append(float(r@r))
    assign(optimum)
    minima=[{'objective':score,'mean':math.exp(x[0])} for score,x,ok in solutions if score<=best[0]+4]
    return p,len(names),{'ages':grid.tolist(),'scores':scores,'note':'Conditional age scan: all other parameters held fixed. Not a confidence interval.'},bound_hits,minima,best[2]

def run(project,fit=False,compare=False):
    p,rows=validate_project(project)
    profile={'ages':[],'scores':[]};hits=[];minima=[];converged=True;n_parameters=0
    if fit or compare: p,n_parameters,profile,hits,minima,converged=_fit(p,rows)
    modeled=predictions(p,rows)
    residuals=residual_vector(modeled,rows)
    score=float(residuals@residuals)
    first=Distribution(p['model'],p['custom_age'])
    second=Distribution(p['model2'],p['custom_age']) if p['binary'] else first
    fraction=p['fraction'] if p['binary'] else 1.
    mean=fraction*first.mean+(1-fraction)*second.mean
    cdf=lambda x:mixture_cdf(x,p['model'],p['model2'],p['binary'],p['fraction'],p['custom_age'])
    high=max(first.high,second.high)
    def quantile(prob):
        if not p['binary']: return first.quantile(prob)
        lo,hi=0.,max(high,1.)
        for _ in range(70):
            mid=(lo+hi)/2
            if float(cdf(mid))>=prob: hi=mid
            else: lo=mid
        return hi
    median=quantile(.5);q05=quantile(.05);q95=quantile(.95)
    xmax=max(quantile(.99),1.)
    x=np.unique(np.r_[np.linspace(0,xmax,700),first.low,second.low,first.mean,second.mean])
    density=fraction*first.pdf(x)+(1-fraction)*second.pdf(x)
    atoms=[]
    for weight,dist in [(fraction,first),(1-fraction,second)]:
        if weight and dist.rv is None: atoms.extend([{'age':float(a),'weight':float(w*weight)} for a,w in zip(dist.ages,dist.weights)])
    reference_date=max(r['date'] for r in rows)
    # Strict inequalities matter for PFM and custom point masses. The CDF
    # includes mass at its argument; its left limit excludes that boundary.
    young=float(cdf(np.nextafter(10-p['uz'],-np.inf)))
    pre1950=1-float(cdf(reference_date-1950-p['uz']))
    result_rows=[{'name':r.get('name','Sample'),'date':r['date'],'tracer':r['tracer'],'observed':r['value'],
        'predicted':float(pred),'sigma':r['sigma'],'residual':float((pred-r['value'])/r['sigma']),
        'qualifier':r.get('qualifier','='),'history':r.get('history',''),'unit':TRACERS[r['tracer']]['unit']} for r,pred in zip(rows,modeled)]
    censored=any(r.get('qualifier')=='<' for r in rows)
    derived=any(r['tracer'] in ('3H0','3H/3H0') for r in rows)
    dof=len(rows)-n_parameters
    pvalue=float(chi2_distribution.sf(score,dof)) if (fit or compare) and dof>0 and not censored and not derived else None
    result={'model':p['model'],'model2':p['model2'],'binary':p['binary'],'fraction':p['fraction'],
        'mean':mean,'total_mean':mean+p['uz'],'median':median,'q05':q05,'q95':q95,
        'young_fraction':young,'pre1950_fraction':pre1950,'reference_date':reference_date,
        'chi2':score,'dof':dof,'pvalue':pvalue,'n_parameters':n_parameters,'rows':result_rows,
        'age':{'x':x.tolist(),'pdf':np.nan_to_num(density,posinf=0).tolist(),'cdf':cdf(x).tolist(),'atoms':atoms},
        'fit_profile':profile,'comparison':[],'warnings':[],'interpretations':[],
        'metadata':{'application_version':__version__,'created':datetime.now().isoformat(timespec='seconds'),
          'fitted':bool(fit or compare),'objective':'Censored Gaussian deviance + squared standardized residuals' if censored else 'Sum of squared standardized residuals',
          'interpolation':p['settings']['history_interpolation'],'half_lives':HALF_LIVES,'bound_hits':hits,'converged':converged},'project':p}
    if compare:
        for kind in ('PFM','EMM','EPM','PEM','DM'):
            candidate=deepcopy(p);candidate['binary']=False;candidate['model']['type']=kind
            if kind=='DM': candidate['model']['shape']=.3
            candidate['settings']['fit_shape']=kind in ('EPM','PEM','DM')
            cp,count,_,_,_,_= _fit(candidate,rows,quick=True)
            rr=residual_vector(predictions(cp,rows),rows);cs=float(rr@rr)
            result['comparison'].append({'model':kind,'mean':cp['model']['mean'],'shape':cp['model']['shape'],'chi2':cs,'n_parameters':count,'aic':cs+2*count})
        result['comparison'].sort(key=lambda r:r['aic'])
    _interpret(p,rows,result,hits,minima,censored,derived)
    return result

def _interpret(p,rows,result,hits,minima,censored,derived):
    notes=result['interpretations']; warnings=result['warnings'];s=p['settings']
    def add(title,text): notes.append({'title':title,'text':text})
    add('Conditional water-age distribution',f'The selected model estimates a saturated-zone mean of {result["mean"]:.3g} years, median {result["median"]:.3g} years, and 5th–95th percentile range {result["q05"]:.3g}–{result["q95"]:.3g} years. Adding the water UZ delay gives a total mean of {result["total_mean"]:.3g} years. These estimates depend on the chosen histories, tracer corrections, and flow model.')
    add('Response to recent recharge',f'{result["young_fraction"]:.1%} of modeled water has total travel time below 10 years. This fraction can respond to recent recharge loading. It does not establish contaminant presence or concentration. At the reference sampling date {result["reference_date"]:.3f}, {result["pre1950_fraction"]:.1%} recharged before 1950.')
    add('Source-reduction scenario',f'If a conservative, spatially uniform recharge source stopped instantly while flow stayed stationary, the predicted discharge concentration would fall by 50% after approximately {result["median"]+p["uz"]:.3g} years. A persistent old-water tail can prolong response. Real cleanup times also depend on source extent, reactions and changing pumping.')
    if result['metadata']['fitted']:
        add('Fit and information content',f'Objective = {result["chi2"]:.4g} using {len(rows)} included observations and {result["n_parameters"]} fitted parameters; residual degrees of freedom = {result["dof"]}. '+('There are no residual degrees of freedom to assess fit.' if result['dof']<=0 else 'Goodness-of-fit calculations assume the stated uncertainties are independent Gaussian errors; they do not prove a unique model.'))
    else: add('Forward calculation','Parameters were supplied, not fitted. Residuals show compatibility at those settings; no fit probability or parameter uncertainty is inferred.')
    if not result['metadata']['converged']: warnings.append('The best optimizer run reached its stopping limit. Inspect the age scan and try different bounds or starting parameters.')
    if hits: warnings.append('Fitted parameter near a search bound: '+', '.join(hits)+'. The chosen bounds may control the result.')
    if len(minima)>1 and max(x['mean'] for x in minima)>1.5*max(.001,min(x['mean'] for x in minima)):
        add('Alternative age solutions',f'The multi-start search found nearby objective values at first-component means from {min(x["mean"] for x in minima):.3g} to {max(x["mean"] for x in minima):.3g} years. Multiple age solutions may be compatible. This range is not a confidence interval.')
    if p['model']['type'] in ('EPM','PEM') or result['comparison']:
        add('EPM and PEM can be equivalent','EPM and one-sided PEM are the same shifted-exponential family after reparameterization: EPM ratio = ln(1 + PEM ratio). A tie is not independent confirmation of an aquifer geometry. Use screen position and hydrogeology to choose the physical interpretation.')
    if p['binary']:
        add('Binary mixing',f'The first component contributes {p["fraction"]:.1%} of water; the second contributes {1-p["fraction"]:.1%}. Component 1 is not assumed to be the younger water. Ages and mixing fractions can trade off, especially if only modern tracers constrain a small young fraction. Carbon-14 concentrations use DIC mass weights.')
    if derived: warnings.append('Derived initial tritium or 3H/3H0 may share measurement errors with other tritium-family observations. Chi-square probability is suppressed; covariance is not modeled.')
    if censored:
        add('Nondetects are upper limits','Rows marked < use a censored Gaussian likelihood, not a zero concentration. Low or undetected modern tracers can reflect old water, dilution or tracer loss. A standard chi-square probability is not reported for this mixed objective.')
    names={r.get('name','') for r in rows}
    if len(names)>1: warnings.append('Multiple sample IDs are being fitted to one common stationary age distribution. Run separate projects for unrelated wells.')
    if len({r['date'] for r in rows})>1: add('Time-series assumption','The same age distribution is applied to every selected sampling date. Systematic time-related residuals may warrant changing recharge/pumping assumptions or a nonstationary model.')
    if 'synthetic' in p.get('note','').lower() or 'demonstration' in p['name'].lower(): warnings.append('Synthetic demonstration: its uncertainties are illustrative. Enter actual measurements and laboratory uncertainty before field interpretation.')
    elif 'illustrative' in p.get('note','').lower(): warnings.append('This project uses illustrative uncertainties. Replace them with justified measurement uncertainties before statistical field interpretation.')
    traced=set()
    for row in rows:
        history=history_for(p,row)
        if history is None:
            if row['tracer']=='14C': warnings.append('Carbon-14 uses a constant 100 pmC input scaled by A0; no atmospheric calibration history selected.')
            continue
        key=row.get('history','')
        coverage_key=(key,row['date'],sample_lag(row['tracer'],p['uz'],s))
        if coverage_key in traced: continue
        traced.add(coverage_key)
        end=history.get('supported_end_year')
        if end is not None and row['date']>end:
            cutoff=row['date']-sample_lag(row['tracer'],p['uz'],s)-end
            fraction=float(mixture_cdf(np.nextafter(cutoff,-np.inf),p['model'],p['model2'],p['binary'],p['fraction'],p['custom_age']))
            if fraction>1e-5: warnings.append(f'{history["label"]}: at sample date {row["date"]:g}, {fraction:.1%} of modeled water samples input dates after its {end:g} legacy continuation boundary. Import an appropriate updated history.')
        if row['tracer'] in ('CFC-11','CFC-12','CFC-113','SF6') and key.startswith('stored_'):
            warnings.append(f'{history["label"]}: legacy gas curves include projections after January 2014 (USGS version notes). Stored date coverage is not observation coverage.')
        earliest=history['years'][0]
        old=1-float(mixture_cdf(row['date']-sample_lag(row['tracer'],p['uz'],s)-earliest,p['model'],p['model2'],p['binary'],p['fraction'],p['custom_age']))
        if old>.001: warnings.append(f'{history["label"]}: at sample date {row["date"]:g}, {old:.1%} of the age distribution reaches before the first input year ({earliest:g}); boundary rule = {s["history_before"]}.')
    tracers={r['tracer'] for r in rows}
    if tracers&{'CFC-11','CFC-12','CFC-113','SF6'}:
        add('Gas preparation and alternative explanations','CFC and SF6 observations must already be corrected to equivalent atmospheric pptv using recharge temperature, pressure/elevation, salinity and excess air. Raw dissolved concentrations cannot be entered in these fields. Dissolved-gas and redox measurements can help distinguish recharge corrections, contamination, degradation and gas loss.')
    if '14C' in tracers: add('Carbon-14 is also a geochemical signal',f'A0 scaling is {s["a0"]:g}% of the selected input history. Low activity may reflect residence time, dead-carbon dilution, or mixing. Check laboratory normalization and geochemical corrections. The bundled long-term record is legacy IntCal13, not a current calibration release.')
    if '4He' in tracers: add('Helium rate controls the age estimate',f'Radiogenic helium-4 is modeled with a fixed accumulation rate of {s["he4_rate"]:.3g} cm³ STP/g/year. The product of this rate and mean age controls concentration; helium-4 alone cannot identify the age-distribution shape. Atmospheric components, external helium and variable release require independent evaluation.')
    for row in result['rows']:
        if row['qualifier']=='<' or abs(row['residual'])<2: continue
        direction='above' if row['observed']>row['predicted'] else 'below'
        text=f'{row["name"]}: measured {row["tracer"]} is {abs(row["residual"]):.2f} stated standard deviations {direction} the model.'
        if row['tracer']=='SF6' and direction=='above': text+=' Plausible alternatives include excess-air correction, local/geogenic SF6, or more recent water than the model represents.'
        elif row['tracer'].startswith('CFC'):
            text+=(' Check contamination/local sources, recharge correction and age mixing.' if direction=='above' else ' Check degradation/sorption, gas loss, recharge correction and age mixing.')
        elif row['tracer']=='3He(trit)' and direction=='below': text+=' Check helium loss, tritiogenic-helium correction, UZ assumptions and age mixing.'
        else: text+=' Recheck the input history, uncertainty, tracer correction and model structure before assigning a cause.'
        add('Tracer mismatch: '+row['tracer'],text)
    if result['comparison']:
        top=result['comparison'][0]
        alternatives=[r for r in result['comparison'] if r['aic']<=top['aic']+2]
        add('Comparison of candidate models','Models were fitted to the same included observations. Ranking uses objective + 2 × parameter count (AIC up to a common constant). Models within 2 units: '+', '.join(f'{x["model"]} ({x["mean"]:.3g} yr)' for x in alternatives)+'. This comparison covers tested single-component families and does not validate hydrogeologic geometry; unequal shape bounds can affect equivalent EPM/PEM fits.')
    warnings[:]=list(dict.fromkeys(warnings))

def forecast(project,result,start,end):
    p=deepcopy(result.get('project',project))
    start=finite(start,'Forecast start');end=finite(end,'Forecast end')
    if end<=start: raise ValueError('Forecast end must be later than its start.')
    years=np.linspace(start,end,161)
    series=[];seen=set()
    for row in p['samples']:
        if not row.get('use',True) or (row['tracer'],row.get('history')) in seen: continue
        seen.add((row['tracer'],row.get('history')))
        history=history_for(p,row)
        values=[predict(p['model'],p['model2'],p['binary'],p['fraction'],row['tracer'],t,history,p['uz'],p['settings'],p['custom_age']) for t in years]
        baseline=values[0]
        if baseline>1e-20:
            series.append({'label':row['tracer']+' / starting value','values':(np.array(values)/baseline*100).tolist(),'concentrations':values,'unit':TRACERS[row['tracer']]['unit'],'start_concentration':baseline})
    elapsed=years-start-p['uz']
    remaining=1-mixture_cdf(np.maximum(elapsed,0),p['model'],p['model2'],p['binary'],p['fraction'],p['custom_age'])
    remaining=np.where(elapsed<0,1,remaining)
    series.append({'label':'Uniform conservative source stops at start','values':(100*remaining).tolist(),'unit':'% of initial steady concentration'})
    return {'years':years.tolist(),'series':series,'y_label':'Percent of starting / initial steady concentration',
        'note':'Tracer curves are normalized to their first forecast concentration and use the selected input history and boundary rules. Absolute concentrations are retained in forecast data. The source-stop curve is a separate conservative, uniform-loading scenario: 100 × [1 − age CDF], including water UZ delay. Legacy future history rows are assumptions, not verified future observations.'}

def load_history_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as handle:
        reader=csv.DictReader(handle);rows=list(reader)
    if not rows or not {'year','value'}<=set(rows[0]): raise ValueError('History CSV headers: year,value; optional tracer,label,source.')
    points=sorted((parse_date(r['year']),finite(r['value'],'History value')) for r in rows)
    history={'id':'custom_'+Path(path).stem,'label':rows[0].get('label') or Path(path).stem,
        'tracer':rows[0].get('tracer',''),'years':[x[0] for x in points],'values':[x[1] for x in points],
        'source':rows[0].get('source') or Path(path).name,'note':'User-supplied history; verify location, units, date interval and observational versus projected values.'}
    validate_history(history)
    return history

def load_age_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    if not rows or not {'age','weight'}<=set(rows[0]): raise ValueError('Age CSV needs age,weight headers. Ages are discrete transit times, weights are relative water fractions.')
    data={'ages':[float(r['age']) for r in rows],'weights':[float(r['weight']) for r in rows]}
    dist=Distribution({'type':'CUSTOM','mean':1},data)
    return {'ages':dist.ages.tolist(),'weights':dist.weights.tolist()}

def import_samples_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    if not rows or not {'date','tracer','value','sigma'}<=set(rows[0]): raise ValueError('Observation CSV headers: name,date,tracer,value,sigma,qualifier,history,use. date,tracer,value,sigma are required.')
    out=[]
    for r in rows:
        tracer=r['tracer'].strip()
        if tracer not in TRACERS: raise ValueError('Unknown tracer: '+tracer)
        value=finite(r['value'],'Value');sigma=finite(r['sigma'],'Uncertainty')
        qualifier=(r.get('qualifier') or '=').strip()
        if value<0 or sigma<=0: raise ValueError('Observations must be nonnegative and uncertainties positive.')
        if qualifier not in ('=','<'): raise ValueError('Observation qualifier must be = or < (detection limit).')
        out.append({'name':r.get('name') or 'Sample','date':parse_date(r['date']),'tracer':tracer,
            'value':value,'sigma':sigma,
            'qualifier':qualifier,'history':r.get('history') or default_history(tracer),
            'use':r.get('use','true').strip().lower() not in ('false','0','no')})
    return out

def save_project(path,project):
    data=deepcopy(project);data['schema_version']=1
    # Embed selected built-in records so a project remains reproducible if the
    # application later ships updated histories. No network paths are fetched.
    data.setdefault('custom_histories',{})
    for row in data.get('samples',[]):
        key=row.get('history')
        if key in HISTORIES and key not in data['custom_histories']: data['custom_histories'][key]=HISTORIES[key]
    Path(path).write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')

def load_project(path):
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data,dict) or data.get('schema_version',1)!=1 or not isinstance(data.get('samples'),list): raise ValueError('This is not a supported TracerLPM Desktop project.')
    defaults=blank_project();defaults.update(data)
    defaults['settings']={**blank_project()['settings'],**data.get('settings',{})}
    return defaults

def export_results(path,project,result,kind='csv'):
    if kind=='csv':
        keys=['name','date','tracer','observed','predicted','sigma','residual','qualifier','history','unit']
        with open(path,'w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(result['rows'])
        return
    esc=lambda x:html.escape(str(x))
    p=result.get('project',project)
    cards=''.join(f'<h2>{esc(n["title"])}</h2><p>{esc(n["text"])}</p>' for n in result['interpretations'])
    warnings=''.join('<li>'+esc(w)+'</li>' for w in result['warnings'])
    headers=['Sample','Date','Tracer','Observed','Modeled','1σ','Residual (σ)','Qualifier']
    rows=''.join('<tr>'+''.join('<td>'+esc(r[k])+'</td>' for k in ('name','date','tracer','observed','predicted','sigma','residual','qualifier'))+'</tr>' for r in result['rows'])
    sources=[]
    for r in p['samples']:
        if not r.get('use',True): continue
        h=history_for(p,r)
        if h:
            checksum=hashlib.sha256(json.dumps([h['years'],h['values']],separators=(',',':')).encode()).hexdigest()
            sources.append(f'{h["label"]}: {h.get("source","")}. {h.get("note","")} Data SHA-256: {checksum}')
    sourcehtml=''.join('<li>'+esc(x)+'</li>' for x in dict.fromkeys(sources))
    settings=esc(json.dumps({k:p[k] for k in ('model','model2','binary','fraction','uz','settings')},indent=2))
    page=f'<!doctype html><html lang="en"><meta charset="utf-8"><title>{esc(p["name"])}</title><style>body{{font:16px/1.65 Segoe UI,sans-serif;max-width:1080px;margin:48px auto;color:#193245;padding:0 24px}}h1,h2{{color:#006d77}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #ddd;padding:8px;text-align:left}}pre{{white-space:pre-wrap;background:#f3f6f8;padding:18px}}.note{{background:#fff4d5;padding:18px}}@media print{{body{{margin:0}}}}</style><h1>TracerLPM Desktop — {esc(p["name"])}</h1><p>Independent implementation • Version {__version__} • {esc(result["metadata"]["created"])}</p><p>{esc(p.get("note",""))}</p><div class="note"><ul>{warnings}</ul></div>{cards}<h2>Observations and predictions</h2><table><tr>'+''.join('<th>'+h+'</th>' for h in headers)+f'</tr>{rows}</table><h2>Model settings</h2><pre>{settings}</pre><h2>Input provenance</h2><ul>{sourcehtml}</ul><h2>Scientific basis</h2><p><a href="https://pubs.usgs.gov/tm/4-f3/">USGS Techniques and Methods 4-F3</a>; <a href="https://www.usgs.gov/software/tracerlpm">TracerLPM software and version history</a>. This application is not an official USGS product. Save the JSON project alongside this report to preserve inputs and excluded observations.</p></html>'
    Path(path).write_text(page,encoding='utf-8')
