"""Evaluate a labeled manifest; optionally calibrate on validation ONLY."""
import argparse
import hashlib
import json
from pathlib import Path
from voiceguard.config import Settings
from voiceguard.data import read_manifest, load_audio
from voiceguard.engine import Engine
from voiceguard.metrics import metrics, calibrate, decision_metrics


def write_plots(result, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1,2,figsize=(9,4))
    roc=result['metrics']['roc']
    axes[0].plot(roc['fpr'],roc['tpr']);axes[0].plot([0,1],[0,1],'--',color='gray')
    axes[0].set(xlabel='False positive rate',ylabel='True positive rate',title='ROC (fake = positive)')
    cm=result['metrics']['confusion_matrix_real_fake']
    axes[1].imshow(cm,cmap='Blues')
    for y in range(2):
        for x in range(2):axes[1].text(x,y,str(cm[y][x]),ha='center',va='center')
    axes[1].set(xticks=[0,1],yticks=[0,1],xticklabels=['real','fake'],yticklabels=['real','fake'],
                xlabel='Predicted at diagnostic 0.5',ylabel='True class',title='Confusion matrix')
    fig.tight_layout();fig.savefig(output.with_suffix('.png'),dpi=160);plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest');parser.add_argument('--split',choices=['validation','test'],default='test')
    parser.add_argument('--language',help='Optional language subset, e.g. ar')
    parser.add_argument('--output',default='reports/evaluation.json')
    parser.add_argument('--calibrate',metavar='PATH',help='Write calibration; validation split only')
    parser.add_argument('--max-error',type=float,default=0.05)
    args=parser.parse_args()
    if args.calibrate and args.split!='validation':parser.error('Never calibrate on the held-out test split')
    rows=read_manifest(args.manifest)
    rows=[r for r in rows if r['split']==args.split and (not args.language or r['language']==args.language)]
    if {r['label'] for r in rows}!={'real','fake'}:parser.error('Selected subset must contain real AND fake examples')
    engine=Engine(Settings.from_env());predictions=[]
    for row in rows:
        score=engine.analyze(load_audio(row,engine.settings))['_raw_fake_score']
        predictions.append({'id':row['id'],'language':row['language'],'label':int(row['label']=='fake'),'score':score})
    labels=[r['label'] for r in predictions];scores=[r['score'] for r in predictions]
    result={'split':args.split,'identity':engine.identity(),'metrics':metrics(labels,scores),
            'per_language':{},'samples':predictions,
            'note':'0.5 metrics are diagnostic. Production decisions require validation-only abstention calibration.'}
    for language in sorted({r['language'] for r in predictions}):
        subset=[r for r in predictions if r['language']==language]
        result['per_language'][language]=(metrics([r['label'] for r in subset],[r['score'] for r in subset])
            if {r['label'] for r in subset}=={0,1} else {'status':'both classes required','count':len(subset)})
    if args.calibrate:
        calibration=calibrate(labels,scores,args.max_error)
        calibration.update(identity=engine.identity(),split='validation',
            dataset_sha256=hashlib.sha256(''.join(sorted(r['id'] for r in rows)).encode()).hexdigest())
        path=Path(args.calibrate);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(calibration,indent=2))
        result['calibration']=calibration
    if engine.calibration:result['abstention_metrics']=decision_metrics(labels,scores,engine.calibration)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2,allow_nan=False));write_plots(result,path)
    print(json.dumps({key:value for key,value in result['metrics'].items() if key!='roc'},indent=2))


if __name__=='__main__':main()
