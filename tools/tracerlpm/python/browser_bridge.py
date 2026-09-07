"""JSON boundary only. Scientific calculations live in the unchanged desktop modules."""
from pathlib import Path
from copy import deepcopy
from tempfile import TemporaryDirectory
import json
import platform
import re
import numpy
import scipy
from tracerlpm import service as s
from tracerlpm.engine import MODEL_NAMES, mixture_cdf


def _project(p):
    """Reject ambiguous JSON types instead of silently converting blank fields to zero."""
    if not isinstance(p, dict) or not isinstance(p.get('samples'), list):
        raise ValueError('Project must contain an observation list.')
    if isinstance(p.get('schema_version',1),bool) or p.get('schema_version', 1) != 1:
        raise ValueError('Unsupported project schema version.')
    for key in ('name','note'):
        if key in p and not isinstance(p[key],str):
            raise ValueError('Project '+key+' must be text.')
    if not isinstance(p.get('custom_histories',{}),dict):
        raise ValueError('Custom histories must be a collection of named records.')
    if not isinstance(p.get('custom_age',{}),dict):
        raise ValueError('Custom age distribution must contain ages and weights.')
    for key in ('ages','weights'):
        if not isinstance(p.get('custom_age',{}).get(key,[]),list):
            raise ValueError('Custom '+key+' must be a list.')
    def numeric_bool(value, label):
        if isinstance(value, bool):
            raise ValueError(label + ' must be numeric, not true or false.')
    for key in ('uz','fraction'):
        numeric_bool(p.get(key),key)
    for key in ('model','model2'):
        if key in p and not isinstance(p[key],dict):
            raise ValueError(key+' must contain model parameters.')
        if key in p and p[key].get('type') not in MODEL_NAMES:
            raise ValueError('Unknown model family in '+key+'.')
        for name in ('mean','shape','upper','lower'):
            numeric_bool(p.get(key,{}).get(name),key+'.'+name)
    if not isinstance(p.get('settings',{}),dict):
        raise ValueError('Settings must contain named model settings.')
    for key in ('age_min','age_max','shape_min','shape_max','a0','he4_rate','dic1','dic2','gas_uz','contaminant_decay'):
        numeric_bool(p.get('settings',{}).get(key),key)
    for k in ('binary',):
        if k in p and not isinstance(p[k], bool):
            raise ValueError(k + ' must be true or false.')
    for k in ('fit_shape', 'fit_fraction', 'fit_mean2'):
        if k in p.get('settings', {}) and not isinstance(p['settings'][k], bool):
            raise ValueError(k + ' must be true or false.')
    for row in p['samples']:
        if not isinstance(row, dict):
            raise ValueError('Each observation must be an object.')
        for key in ('name','tracer','qualifier','history'):
            if key in row and not isinstance(row[key],str):
                raise ValueError('Observation '+key+' must be text.')
        if 'use' in row and not isinstance(row['use'], bool):
            raise ValueError('Observation use must be true or false.')
        for key in ('date','value','sigma'):
            numeric_bool(row.get(key),'Observation '+key)
    for history in p.get('custom_histories',{}).values():
        if not isinstance(history,dict):
            raise ValueError('Every custom history must be a record.')
        for key in ('label','tracer','source','note'):
            if key in history and not isinstance(history[key],str):
                raise ValueError('History '+key+' must be text.')
        for key in ('years','values'):
            if not isinstance(history.get(key,[]),list):
                raise ValueError('History '+key+' must be a list.')
            for v in history.get(key,[]): numeric_bool(v,'History '+key)
    for key in ('ages','weights'):
        for v in p.get('custom_age',{}).get(key,[]): numeric_bool(v,'Custom '+key)
    return p


def _canonical(p, strict=False):
    p=deepcopy(_project(p))
    # UI editing preserves strings such as "1.". Convert complete numeric input
    # at the boundary, never while the researcher is typing a decimal/exponent.
    def convert(obj,key,label):
        if key not in obj: return
        try: obj[key]=s.finite(obj[key],label)
        except ValueError:
            if strict: raise
    for name in ('model','model2'):
        if name not in p or (strict and name=='model2' and not p.get('binary')): continue
        model=p[name]
        for key in ('mean','shape'):
            convert(model,key,name+'.'+key)
        if model.get('type')=='FPEM' or not strict:
            for key in ('upper','lower'): convert(model,key,name+'.'+key)
    if not strict:
        for key in ('uz','fraction'): convert(p,key,key)
        for key in ('age_min','age_max','shape_min','shape_max','a0','he4_rate','dic1','dic2','gas_uz','contaminant_decay'):
            convert(p.get('settings',{}),key,key)
        for row in p['samples']:
            for key in ('value','sigma'): convert(row,key,'Observation '+key)
            try: row['date']=s.parse_date(row['date'])
            except (ValueError,KeyError): pass
    return p


def _plot_cdf(result):
    # Add exact jump positions for every custom/PFM atom; the scientific result
    # arrays remain unchanged. Connecting a coarse grid would smear point mass.
    age=result['age'];p=result['project']
    atoms=sorted({a['age'] for a in age['atoms']})
    x=numpy.unique(numpy.r_[age['x'],atoms])
    cdf=lambda values:mixture_cdf(values,p['model'],p['model2'],p['binary'],p['fraction'],p['custom_age'])
    y=cdf(x)
    plot=[]
    for value,fraction in zip(x,y):
        if value in atoms:
            plot.append({'x':float(value),'cdf':float(cdf(numpy.nextafter(value,-numpy.inf)))*100})
        plot.append({'x':float(value),'cdf':float(fraction)*100})
    age['plot_cdf']=plot
    return result


def dispatch(request):
    for key in ('fit','compare','blank'):
        if key in request and not isinstance(request[key],bool):
            raise ValueError(key+' must be true or false.')
    op = request.get('op')
    if op == 'bootstrap':
        return {'models': MODEL_NAMES, 'tracers': s.TRACERS,
                'defaults': {k:s.default_history(k) for k in s.TRACERS},
                'histories': {k:{**{a:h.get(a) for a in ('label','tracer','source','note','supported_end_year')},
                                 'first_year':h['years'][0], 'last_year':h['years'][-1], 'count':len(h['years'])}
                              for k,h in s.HISTORIES.items()},
                'runtime': {'python':platform.python_version(), 'numpy':numpy.__version__, 'scipy':scipy.__version__,
                            'edition':'Browser', 'pyodide':'314.0.6'}}
    if op == 'new':
        return s.blank_project() if request.get('blank') else s.default_project()
    if op == 'example':
        if isinstance(request.get('index',0),bool) or request.get('index',0) not in (0,1,2):
            raise ValueError('Example index must be 0, 1 or 2.')
        return s.example_project(request.get('index', 0))
    if op == 'run':
        return _plot_cdf(s.run(_canonical(request['project'],strict=True), fit=bool(request.get('fit')), compare=bool(request.get('compare'))))
    if op == 'forecast':
        result=request['result']
        return s.forecast(result['project'], result, request['start'], request['end'])
    if op == 'history':
        key=request['key']
        return request.get('project',{}).get('custom_histories',{}).get(key, s.HISTORIES.get(key))
    with TemporaryDirectory() as temp:
        name = re.sub(r'[^\w. -]', '_', str(request.get('filename', 'input.csv')))
        name = name.strip('. ')[:180] or 'input.csv'
        path=Path(temp)/name
        if op in ('load','import_samples','import_history','import_age'):
            path.write_text(request['text'], encoding='utf-8')
            if op == 'load': return _project(s.load_project(path))
            if op == 'import_samples': return s.import_samples_csv(path)
            if op == 'import_history': return s.load_history_csv(path)
            if op == 'import_age': return s.load_age_csv(path)
        if op == 'save':
            s.save_project(path,_canonical(request['project']))
            return {'text':path.read_text(encoding='utf-8'), 'mime':'application/json', 'extension':'json'}
        if op == 'export':
            result=request['result']; kind=request.get('kind','csv')
            if kind not in ('html','csv'): raise ValueError('Choose HTML report or CSV results.')
            s.export_results(path,result['project'],result,kind)
            text=path.read_text(encoding='utf-8-sig')
            if kind=='html':
                text=text.replace('TracerLPM Desktop —','TracerLPM Browser —',1)
                text=text.replace('<h2>Scientific basis</h2>', '<h2>Browser calculation environment</h2><p>Pyodide 314.0.6 · Python '+platform.python_version()+' · NumPy '+numpy.__version__+' · SciPy '+scipy.__version__+'. The scientific engine and interpretation rules are shared with the desktop edition.</p><h2>Scientific basis</h2>',1)
                text=text.replace('</html>', '<footer><p>A fitted age is a model result, not a unique water history.<br>Jaivime Evaristo, PhD · <a href="mailto:evaristo@alumni.upenn.edu">evaristo@alumni.upenn.edu</a></p></footer></html>')
            return {'text':text,'mime':'text/html' if kind=='html' else 'text/csv','extension':kind}
    raise ValueError('Unknown operation: '+str(op))


def handle_json(text):
    return json.dumps(dispatch(json.loads(text)),allow_nan=False,separators=(',',':'))
