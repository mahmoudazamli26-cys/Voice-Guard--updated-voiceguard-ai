"""CLI integration with a tiny RANDOM model and synthetic tones, never research data."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
import soundfile as sf
from transformers import Wav2Vec2Config, Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor


def test_research_clis_on_synthetic_software_fixtures(tmp_path):
    base=tmp_path/'random-model'
    config=Wav2Vec2Config(hidden_size=8,num_hidden_layers=1,num_attention_heads=2,intermediate_size=16,
        conv_dim=(8,8,8),conv_stride=(5,2,2),conv_kernel=(10,3,3),num_conv_pos_embedding_groups=2,
        num_conv_pos_embeddings=16,classifier_proj_size=8,num_labels=2,id2label={0:'real',1:'fake'},
        label2id={'real':0,'fake':1},mask_time_prob=0.0)
    Wav2Vec2ForSequenceClassification(config).save_pretrained(base,safe_serialization=True)
    Wav2Vec2FeatureExtractor(sampling_rate=16000,return_attention_mask=True).save_pretrained(base)
    manifest=tmp_path/'TEST_ONLY.csv'
    with manifest.open('w',newline='') as file:
        writer=csv.writer(file);writer.writerow(['path','label','speaker','language','split','consent'])
        for i,(split,label) in enumerate((s,l) for s in ['train','validation','test'] for l in ['real','fake']):
            # Arbitrary labels are used only to exercise the CLI plumbing, not measure detection.
            path=tmp_path/f'tone{i}.wav'
            audio=np.sin(np.arange(8000)*2*np.pi*(200+i*40)/16000)*0.1
            sf.write(path,audio,16000)
            writer.writerow([path.name,label,f'fixture{i}','ar',split,'true'])
    env={**os.environ,'VG_MODEL_ID':str(base),'VG_MODEL_REVISION':'local','VG_CALIBRATION':'',
         'VG_SECOND_MODEL':'','VG_SECOND_REVISION':'','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    root=Path(__file__).resolve().parents[1]
    def run(*args):
        result=subprocess.run([sys.executable,*map(str,args)],cwd=root,env=env,capture_output=True,text=True,timeout=120)
        assert result.returncode==0,result.stdout+'\n'+result.stderr
    output=tmp_path/'evaluation.json'
    run('evaluate.py',manifest,'--output',output)
    assert json.loads(output.read_text())['metrics']['count']==2
    assert output.with_suffix('.png').is_file()
    robustness=tmp_path/'robustness.json'
    run('robustness.py',manifest,'--output',robustness)
    summary=json.loads(robustness.read_text())
    assert len(summary['conditions'])==5
    assert summary['loudspeaker_status'].startswith('not run')
    trained=tmp_path/'trained'
    run('train_arabic.py',manifest,'--output',trained,'--epochs','1','--batch-size','2')
    assert (trained/'model.safetensors').is_file()
    assert len(json.loads((trained/'training.json').read_text())['history'])==1
