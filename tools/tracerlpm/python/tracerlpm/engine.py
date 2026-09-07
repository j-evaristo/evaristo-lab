"""Lumped-parameter transport, independent of Excel and the user interface.

Age is saturated-zone transit time in years. Histories use calendar decimal
years. Equations follow USGS TM 4-F3 (revised 2014); numerical integration
uses piecewise-linear input histories rather than the legacy XLL time steps.
"""
from functools import lru_cache
import math
import numpy as np
from scipy import stats

MODEL_NAMES = {'PFM': 'Piston flow', 'EMM': 'Exponential mixing',
               'EPM': 'Exponential piston flow', 'PEM': 'Partial exponential',
               'DM': 'Dispersion', 'FPEM': 'Full partial exponential',
               'GAM': 'Gamma (extension)', 'CUSTOM': 'User-defined ages'}
HALF_LIVES = {'3H':12.32, '14C':5730., '39Ar':269., '85Kr':10.756, '81Kr':229000.}
H3 = math.log(2)/12.32
GAS = {'CFC-11','CFC-12','CFC-113','SF6','85Kr','39Ar','81Kr'}
_gx, _gw = np.polynomial.legendre.leggauss(8)

def finite(value, label):
    try: value = float(value)
    except (ValueError, TypeError): raise ValueError(f'{label} must be a number.')
    if not math.isfinite(value): raise ValueError(f'{label} must be finite.')
    return value

class Distribution:
    def __init__(self, model, custom=None):
        self.kind = model['type']
        if self.kind not in MODEL_NAMES: raise ValueError('Unknown model: '+str(self.kind))
        self.mean = finite(model.get('mean', 25), 'Mean age')
        self.shape = finite(model.get('shape', 1), 'Shape parameter')
        self.rv = None
        self.ages = self.weights = None
        if self.kind == 'CUSTOM':
            custom = custom or {}
            self.ages = np.asarray(custom.get('ages', []), dtype=float)
            self.weights = np.asarray(custom.get('weights', []), dtype=float)
            if (len(self.ages)==0 or self.ages.shape!=self.weights.shape or
                self.ages.ndim!=1 or not np.all(np.isfinite(self.ages)) or
                not np.all(np.isfinite(self.weights)) or np.any(self.ages<0) or
                np.any(self.weights<0) or self.weights.sum()<=0):
                raise ValueError('Custom ages require finite, nonnegative age and weight columns with positive total weight.')
            order = np.argsort(self.ages)
            self.ages, self.weights = self.ages[order], self.weights[order]/self.weights.sum()
            self.mean = float(self.ages@self.weights)
            self.low, self.high = float(self.ages[0]), float(self.ages[-1])
            return
        if self.mean<0 or (self.mean==0 and self.kind!='PFM'): raise ValueError('Mean age must be positive (zero is allowed for piston flow).')
        t,r = self.mean,self.shape
        if self.kind == 'PFM':
            self.low = self.high = t
            self.ages,self.weights = np.array([t]),np.array([1.])
            return
        if self.kind in ('EPM','PEM') and r<0: raise ValueError('EPM and PEM ratios must be nonnegative.')
        if self.kind == 'EMM': self.rv = stats.expon(scale=t)
        elif self.kind == 'EPM': self.rv = stats.expon(loc=t*r/(1+r),scale=t/(1+r))
        elif self.kind == 'PEM':
            scale=t/(1+math.log1p(r))
            self.rv=stats.expon(loc=scale*math.log1p(r),scale=scale)
        elif self.kind == 'FPEM':
            upper=finite(model.get('upper',0),'Upper screen ratio')
            lower=finite(model.get('lower',5),'Lower screen ratio')
            if upper<0 or lower<0 or (lower!=0 and lower<=upper):
                raise ValueError('Full PEM requires 0 ≤ upper < lower; lower = 0 means an unbounded lower screen.')
            a=math.log1p(upper)
            if lower==0:
                scale=t/(a+1)
                self.rv=stats.expon(loc=a*scale,scale=scale)
            else:
                b=math.log1p(lower)
                # Conditional mean of a unit exponential between a and b.
                width=b-a
                unitmean=a+(width/2-width**2/12 if width<1e-4 else 1-width/math.expm1(width))
                scale=t/unitmean
                self.rv=stats.truncexpon(width,loc=a*scale,scale=scale)
        elif self.kind == 'DM':
            if not .00001<=r<=100: raise ValueError('Dispersion parameter must be between 0.00001 and 100.')
            self.rv=stats.invgauss(mu=2*r,scale=t/(2*r))
        elif self.kind == 'GAM':
            if not .05<=r<=1000: raise ValueError('Gamma shape must be between 0.05 and 1000.')
            self.rv=stats.gamma(a=r,scale=t/r)
        self.low=float(self.rv.support()[0])
        self.high=float(self.rv.ppf(1-1e-12))

    def cdf(self, ages):
        x=np.asarray(ages,dtype=float)
        if self.rv is not None: return self.rv.cdf(x)
        idx=np.searchsorted(self.ages,x,side='right')
        cumulative=np.concatenate(([0.],np.cumsum(self.weights)))
        return cumulative[idx]

    def pdf(self, ages):
        if self.rv is not None: return self.rv.pdf(ages)
        return np.zeros_like(np.asarray(ages,dtype=float))

    def quantile(self, p):
        if self.rv is not None: return float(self.rv.ppf(p))
        return float(self.ages[min(np.searchsorted(np.cumsum(self.weights),p),len(self.ages)-1)])

    def quadrature(self, history_ages=()):
        if self.rv is None: return self.ages,self.weights
        # Split at input-history knots and probability knots. Each interval's
        # weights are scaled to its exact CDF mass, preserving constant inputs.
        probabilities=np.unique(np.r_[np.geomspace(1e-12,.01,30),np.linspace(.01,.99,99),1-np.geomspace(1e-12,.01,30)])
        knots=np.r_[self.low,self.high,self.rv.ppf(probabilities),history_ages]
        knots=np.unique(knots[np.isfinite(knots)&(knots>=self.low)&(knots<=self.high)])
        left,right=knots[:-1],knots[1:]
        mass=np.maximum(0,self.cdf(right)-self.cdf(left))
        keep=(mass>1e-16)&(right>left)
        left,right,mass=left[keep],right[keep],mass[keep]
        nodes=(left[:,None]+right[:,None])/2+(right-left)[:,None]/2*_gx
        weights=self.pdf(nodes)*_gw
        sums=weights.sum(axis=1)
        valid=(sums>0)&np.isfinite(sums)
        nodes,weights,mass=nodes[valid],weights[valid],mass[valid]
        weights=weights/weights.sum(axis=1)[:,None]*mass[:,None]
        if abs(weights.sum()-1)>1e-7: raise ArithmeticError('Age integration did not conserve probability.')
        return nodes.ravel(),weights.ravel()

def validate_history(history):
    years=np.asarray(history.get('years',[]),dtype=float)
    values=np.asarray(history.get('values',[]),dtype=float)
    if (years.ndim!=1 or len(years)<2 or years.shape!=values.shape or
        not np.all(np.isfinite(years)) or not np.all(np.isfinite(values)) or
        np.any(np.diff(years)<=0) or np.any(values<0)):
        raise ValueError('History requires at least two increasing, unique years and finite nonnegative concentrations.')
    return years,values

def sample_lag(tracer, uz, settings):
    return float(settings.get('gas_uz',0)) if tracer in GAS else float(uz)

def component_prediction(distribution,tracer,date,history,uz,settings):
    date=finite(date,'Sample date')
    uz=finite(uz,'Unsaturated-zone travel time')
    if uz<0: raise ValueError('Unsaturated-zone travel time cannot be negative.')
    for key, default in [('gas_uz',0),('he4_rate',1.5e-11),('a0',100),('contaminant_decay',0)]:
        if finite(settings.get(key,default),key)<0: raise ValueError(key+' cannot be negative.')
    lag=sample_lag(tracer,uz,settings)
    if tracer=='4He': return distribution.mean*float(settings.get('he4_rate',1.5e-11))
    if history is None:
        if tracer=='14C': history={'years':[-10000000,3000],'values':[100,100]}
        elif tracer in ('39Ar','81Kr'): history={'years':[-10000000,3000],'values':[100,100]}
        else: raise ValueError(f'Choose an input history for {tracer}.')
    years,values=validate_history(history)
    ages,weights=distribution.quadrature(date-lag-years)
    recharge=date-lag-ages
    before=settings.get('history_before','hold')
    after=settings.get('history_after','hold')
    if after=='error' and np.any((recharge>years[-1])&(weights>1e-9)):
        raise ValueError(f'{tracer}: the input history ends before required recharge dates. Import a longer history or explicitly hold its last value.')
    if before=='error' and np.any((recharge<years[0])&(weights>1e-9)):
        raise ValueError(f'{tracer}: the age distribution reaches before the history begins.')
    if settings.get('history_interpolation','linear')=='step':
        cin=values[np.clip(np.searchsorted(years,recharge,side='right')-1,0,len(values)-1)].copy()
        if before=='zero': cin[recharge<years[0]]=0
        if after=='zero': cin[recharge>years[-1]]=0
    else:
        cin=np.interp(recharge,years,values,left=0 if before=='zero' else values[0],right=0 if after=='zero' else values[-1])
    if tracer in ('3H','3He(trit)','3H0','3H/3H0'):
        initial=cin*np.exp(-H3*lag)
        h=float(weights@(initial*np.exp(-H3*ages)))
        h0=float(weights@initial)
        if tracer=='3H': return h
        if tracer=='3He(trit)': return h0-h
        if tracer=='3H0': return h0
        if h0<=1e-30: raise ValueError('3H/3H0 is undefined when initial tritium is zero.')
        return h/h0
    decay=math.log(2)/HALF_LIVES[tracer] if tracer in HALF_LIVES else 0.
    if tracer=='NO3-N': decay=float(settings.get('contaminant_decay',0))
    if tracer=='14C': cin=cin*float(settings.get('a0',100))/100
    return float(weights@(cin*np.exp(-decay*(ages+lag))))

def predict(model,model2,binary,fraction,tracer,date,history,uz,settings,custom=None):
    fraction=finite(fraction,'Mixing fraction')
    if not 0<=fraction<=1: raise ValueError('Mixing fraction must be between zero and one.')
    if binary and tracer=='14C':
        if finite(settings.get('dic1',1),'DIC 1')<=0 or finite(settings.get('dic2',1),'DIC 2')<=0:
            raise ValueError('DIC concentrations must be positive.')
    first=Distribution(model,custom)
    if binary:
        second=Distribution(model2,custom)
        if tracer=='3H/3H0':
            numerator=predict(model,model2,True,fraction,'3H',date,history,uz,settings,custom)
            denominator=predict(model,model2,True,fraction,'3H0',date,history,uz,settings,custom)
            if denominator<=1e-30: raise ValueError('Mixed 3H/3H0 is undefined when initial tritium is zero.')
            return numerator/denominator
        c1=component_prediction(first,tracer,date,history,uz,settings)
        c2=component_prediction(second,tracer,date,history,uz,settings)
        if tracer=='14C':
            d1,d2=float(settings.get('dic1',1)),float(settings.get('dic2',1))
            return (fraction*d1*c1+(1-fraction)*d2*c2)/(fraction*d1+(1-fraction)*d2)
        return fraction*c1+(1-fraction)*c2
    return component_prediction(first,tracer,date,history,uz,settings)

def mixture_cdf(x,model,model2,binary,fraction,custom=None):
    first=Distribution(model,custom).cdf(x)
    if not binary: return first
    return fraction*first+(1-fraction)*Distribution(model2,custom).cdf(x)

def helium_rate(uranium_ppm,thorium_ppm,porosity,bulk_density):
    uranium_ppm=finite(uranium_ppm,'Uranium')
    thorium_ppm=finite(thorium_ppm,'Thorium')
    porosity=finite(porosity,'Porosity')
    bulk_density=finite(bulk_density,'Bulk density')
    if uranium_ppm<0 or thorium_ppm<0 or bulk_density<=0: raise ValueError('U/Th must be nonnegative and bulk density positive.')
    if not 0<porosity<=1: raise ValueError('Porosity must be between 0 and 1.')
    return bulk_density/porosity*(1.19e-13*uranium_ppm+2.88e-14*thorium_ppm)
