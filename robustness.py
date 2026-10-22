"""Paired compression/noise/resampling checks; optional real loudspeaker recordings."""
import argparse
import io
import json
import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from voiceguard.config import Settings
from voiceguard.data import read_manifest, load_audio
from voiceguard.audio import decode_audio
from voiceguard.engine import Engine
from voiceguard.metrics import metrics


def perturb(audio, rate, seed):
    rng=np.random.default_rng(seed)
    rms=max(float(np.sqrt(np.mean(audio**2))),1e-8)
    result={'original':audio,'resampled_8khz':resample_poly(resample_poly(audio,1,2),2,1)[:len(audio)]}
    for snr in [20,10]:
        noise=rng.normal(size=audio.shape);noise=noise/np.sqrt(np.mean(noise**2))*rms/(10**(snr/20))
        result[f'noise_{snr}db']=np.clip(audio+noise,-1,1).astype(np.float32)
    buffer=io.BytesIO();sf.write(buffer,audio,rate,format='WAV')
    encoded=subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-protocol_whitelist','pipe',
        '-i','pipe:0','-f','mp3','-b:a','32k','pipe:1'],input=buffer.getvalue(),capture_output=True,check=True,timeout=20)
    result['mp3_32kbps']=decode_audio(encoded.stdout,rate,len(audio)/rate+1)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest')
    p.add_argument('--split',choices=['validation','test'],default='test')
    p.add_argument('--language');p.add_argument('--rerecorded',help='Manifest with matching pair_id values')
    p.add_argument('--output',default='reports/robustness.json');args=p.parse_args()
    all_rows=read_manifest(args.manifest)
    rows=[r for r in all_rows if r['split']==args.split and (not args.language or r['language']==args.language)]
    if {r['label'] for r in rows}!={'real','fake'}:p.error('Selected subset needs both classes')
    rerecorded={}
    if args.rerecorded:
        for r in read_manifest(args.rerecorded):
            if r['split']!=args.split:continue
            if not r.get('pair_id') or r['pair_id'] in rerecorded:p.error('Re-recordings need unique pair_id values')
            rerecorded[r['pair_id']]=r
    engine=Engine(Settings.from_env());conditions={};pairs=[]
    for row in rows:
        scores={}
        for condition,audio in perturb(load_audio(row,engine.settings),engine.settings.sample_rate,int(row['id'][:8],16)).items():
            scores[condition]=engine.analyze(audio)['_raw_fake_score']
        if rerecorded:
            match=rerecorded.get(row.get('pair_id'))
            if not match or any(match[k]!=row[k] for k in ['label','speaker','language']):p.error('Missing or mismatched re-recording pair')
            scores['loudspeaker_rerecorded']=engine.analyze(load_audio(match,engine.settings))['_raw_fake_score']
        label=int(row['label']=='fake');pairs.append({'id':row['id'],'label':label,'scores':scores})
        for condition,score in scores.items():conditions.setdefault(condition,[]).append((label,score,score-scores['original']))
    summary={condition:{'metrics':metrics([v[0] for v in values],[v[1] for v in values]),
        'mean_absolute_score_change':float(np.mean([abs(v[2]) for v in values])),
        'mean_signed_score_change':float(np.mean([v[2] for v in values]))} for condition,values in conditions.items()}
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'identity':engine.identity(),'split':args.split,'conditions':summary,'pairs':pairs,
        'loudspeaker_status':'tested' if rerecorded else 'not run: physical re-recordings not provided'},indent=2,allow_nan=False))
    print('condition | accuracy | EER | mean absolute score change')
    for name,value in summary.items():print(f"{name} | {value['metrics']['accuracy']:.3f} | {value['metrics']['eer_interpolated']:.3f} | {value['mean_absolute_score_change']:.3f}")


if __name__=='__main__':main()
