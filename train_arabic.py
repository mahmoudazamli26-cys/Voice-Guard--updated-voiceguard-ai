"""Optional Arabic fine-tuning. Requires consented, speaker-disjoint training data."""
import argparse
import json
import random
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from voiceguard.config import Settings
from voiceguard.data import read_manifest, load_audio
from voiceguard.engine import Detector


class AudioDataset(Dataset):
    def __init__(self, rows, settings, fake_index, train):
        self.rows,self.settings,self.fake_index,self.train=rows,settings,fake_index,train

    def __len__(self):return len(self.rows)

    def __getitem__(self,index):
        row=self.rows[index];audio=load_audio(row,self.settings);width=self.settings.sample_rate*5
        start=random.randint(0,max(0,len(audio)-width)) if self.train else 0
        return audio[start:start+width], self.fake_index if row['label']=='fake' else 1-self.fake_index


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--output',default='models/arabic')
    p.add_argument('--epochs',type=int,default=3);p.add_argument('--batch-size',type=int,default=2)
    p.add_argument('--learning-rate',type=float,default=1e-5);p.add_argument('--seed',type=int,default=42)
    args=p.parse_args()
    if args.epochs<1 or args.batch_size<1 or not 0<args.learning_rate<=0.01:p.error('Invalid training hyperparameters')
    output=Path(args.output)
    if output.exists() and any(output.iterdir()):p.error('Use a new empty output directory; existing models are preserved')
    rows=read_manifest(args.manifest);splits={key:[r for r in rows if r['split']==key and r['language']=='ar'] for key in ['train','validation']}
    if any({r['label'] for r in subset}!={'real','fake'} for subset in splits.values()):p.error('Arabic train and validation splits each need both classes')
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    settings=Settings.from_env();detector=Detector(settings.model_id,settings.revision)
    if detector.sample_rate!=settings.sample_rate:p.error('This training workflow requires a 16 kHz model')
    model=detector.model;model.freeze_feature_encoder()
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model.to(device)
    def collate(batch):
        inputs=detector.extractor([item[0] for item in batch],sampling_rate=16000,padding=True,return_tensors='pt')
        return {k:v.to(device) for k,v in inputs.items()},torch.tensor([item[1] for item in batch],device=device)
    loaders={key:DataLoader(AudioDataset(value,settings,detector.fake_index,key=='train'),batch_size=args.batch_size,
        shuffle=key=='train',collate_fn=collate,num_workers=0) for key,value in splits.items()}
    optimizer=torch.optim.AdamW([x for x in model.parameters() if x.requires_grad],lr=args.learning_rate)
    output.mkdir(parents=True,exist_ok=True);history=[];best=float('inf')
    for epoch in range(args.epochs):
        losses={}
        for split,loader in loaders.items():
            model.train(split=='train');total=0;count=0
            with torch.set_grad_enabled(split=='train'):
                for inputs,labels in loader:
                    loss=model(**inputs,labels=labels).loss
                    if not torch.isfinite(loss):raise RuntimeError('Non-finite training loss')
                    if split=='train':
                        optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.0);optimizer.step()
                    total+=float(loss.detach())*len(labels);count+=len(labels)
            losses[split]=total/count
        history.append({'epoch':epoch+1,**losses});print(json.dumps(history[-1]))
        if losses['validation']<best:
            best=losses['validation'];model.save_pretrained(output,safe_serialization=True);detector.extractor.save_pretrained(output)
        (output/'training.json').write_text(json.dumps({'seed':args.seed,'base_model':settings.model_id,'revision':settings.revision,
            'train_count':len(splits['train']),'validation_count':len(splits['validation']),
            'selection':'lowest validation loss; 5-second random training crops, first 5-second validation crops',
            'history':history,'note':'Test split was not used. Evaluate full recordings before/after with evaluate.py.'},indent=2))


if __name__=='__main__':main()
