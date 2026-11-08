"""Reproducible Flowers-102 CPU pilot. Keeps official train/val/test splits."""
import argparse, hashlib, json, random, re, time
from html.parser import HTMLParser
from pathlib import Path
import numpy as np
from scipy.io import loadmat
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader, TensorDataset
from torchvision import models, transforms
from PIL import Image

class Flowers(Dataset):
    def __init__(self,root,ids,labels,transform):self.root=root;self.ids=ids;self.labels=labels;self.transform=transform
    def __len__(self):return len(self.ids)
    def __getitem__(self,i):
        image_id=int(self.ids[i])
        with Image.open(self.root/'jpg'/f'image_{image_id:05d}.jpg') as image:return self.transform(image.convert('RGB')),int(self.labels[image_id-1])

@torch.inference_mode()
def evaluate(model,loader):
    model.eval();correct=torch.zeros(102);counts=torch.zeros(102);top3=0;conf=torch.zeros(102,102,dtype=torch.int64)
    for x,y in loader:
        pred=model(x).topk(3,dim=1).indices
        hit=pred[:,0]==y;correct+=torch.bincount(y[hit],minlength=102);counts+=torch.bincount(y,minlength=102);top3+=pred.eq(y[:,None]).any(1).sum().item()
        conf+=torch.bincount(y*102+pred[:,0],minlength=102*102).reshape(102,102)
    return dict(top1=(correct.sum()/counts.sum()).item(),top3=top3/counts.sum().item(),macro_recall=(correct/counts.clamp_min(1)).mean().item(),support=counts.tolist(),correct=correct.tolist(),confusion=conf.tolist())

@torch.inference_mode()
def cache(model,loader):
    model.eval();xs=[];ys=[]
    for x,y in loader:xs.append(model.avgpool(model.features(x)).flatten(1));ys.append(y)
    return TensorDataset(torch.cat(xs),torch.cat(ys))

def main(a):
    torch.set_num_threads(4);random.seed(42);np.random.seed(42);torch.manual_seed(42)
    root=Path(a.data);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    labels=loadmat(root/'imagelabels.mat')['labels'].reshape(-1)-1
    splits=loadmat(root/'setid.mat');ids={k:splits[v].reshape(-1) for k,v in [('train','trnid'),('val','valid'),('test','tstid')]}
    assert not(set(ids['train'])&set(ids['val']) or set(ids['train'])&set(ids['test']) or set(ids['val'])&set(ids['test']))
    names={}
    class Categories(HTMLParser):
        def handle_starttag(self,t,attrs):
            d=dict(attrs);m=re.search(r'thumbim_(\d+)\.jpg',d.get('src',''))
            if t=='img' and m:names[int(labels[int(m[1])-1])]=d['alt']
    Categories().feed((root/'categories.html').read_text());assert len(names)==102
    (out/'labels.json').write_text(json.dumps([names[i] for i in range(102)],indent=2))
    # Check exact image duplicates across the official splits before training.
    hashes={}; removed={}
    # Prefer held-out test, then validation: remove duplicate bytes from earlier-use splits.
    for split in ['test','val','train']:
        keep=[];removed[split]=0
        for i in ids[split]:
            h=hashlib.sha256((root/'jpg'/f'image_{int(i):05d}.jpg').read_bytes()).hexdigest()
            if h in hashes:removed[split]+=1;continue
            hashes[h]=split;keep.append(i)
        ids[split]=np.array(keep)
    assert len(set(labels[ids['train']-1]))==102
    (out/'splits.json').write_text(json.dumps({'removed_exact_duplicates':removed,'ids':{k:[int(i) for i in v] for k,v in ids.items()}},indent=2))
    print('Exact duplicate removals',removed,flush=True)
    weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1;tf=weights.transforms()
    loaders={k:DataLoader(Flowers(root,v,labels,tf),batch_size=16,num_workers=0) for k,v in ids.items()}
    model=models.mobilenet_v3_small(weights=weights);model.classifier[-1]=nn.Linear(model.classifier[-1].in_features,102)
    before={k:v.clone() for k,v in model.features[-3:].state_dict().items()}
    print('Caching train and validation features',flush=True)
    train_cache=cache(model,loaders['train']);val_cache=cache(model,loaders['val'])
    baseline=evaluate(model.classifier,DataLoader(val_cache,batch_size=16));print('Random-head validation',baseline['top1'],flush=True)
    opt=torch.optim.AdamW(model.classifier.parameters(),lr=.001,weight_decay=.01);loss_fn=nn.CrossEntropyLoss(label_smoothing=.05)
    best=-1;history=[];started=time.time()
    for epoch in range(30):
        model.classifier.train()
        for x,y in DataLoader(train_cache,batch_size=16,shuffle=True):
            opt.zero_grad();loss=loss_fn(model.classifier(x),y);loss.backward();opt.step()
        metrics=evaluate(model.classifier,DataLoader(val_cache,batch_size=16))
        history.append({'phase':'head','epoch':epoch,'val_top1':metrics['top1']})
        if metrics['top1']>best:best=metrics['top1'];torch.save(model.state_dict(),out/'best.pt')
        if epoch%5==4:print('Head epoch',epoch+1,'val_top1',metrics['top1'],flush=True)
    head_best=best;model.load_state_dict(torch.load(out/'best.pt',weights_only=True))
    for p in model.features.parameters():p.requires_grad=False
    for p in model.features[-3:].parameters():p.requires_grad=True
    opt=torch.optim.AdamW([{'params':model.features[-3:].parameters(),'lr':.0001},{'params':model.classifier.parameters(),'lr':.0003}],weight_decay=.01)
    aug=transforms.Compose([transforms.RandomResizedCrop(224,scale=(.75,1)),transforms.RandomHorizontalFlip(),transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])])
    train=DataLoader(Flowers(root,ids['train'],labels,aug),batch_size=8,shuffle=True,num_workers=0)
    for epoch in range(a.epochs):
        model.train();model.features.eval() # Keep pretrained batch-normalization statistics stable with tiny batches.
        loss_sum=0
        for step,(x,y) in enumerate(train):
            opt.zero_grad();loss=loss_fn(model(x),y);loss.backward();opt.step();loss_sum+=loss.item()
            if (step+1)%32==0:print('Fine-tune epoch',epoch+1,'batch',step+1,'of',len(train),flush=True)
        metrics=evaluate(model,loaders['val']);history.append({'phase':'fine-tune','epoch':epoch,'loss':loss_sum/len(train),'val_top1':metrics['top1']})
        changed=sum((v-before[k]).abs().sum().item() for k,v in model.features[-3:].state_dict().items() if v.is_floating_point())
        torch.save({'model':model.state_dict(),'optimizer':opt.state_dict(),'epoch':epoch,'history':history},out/'last.pt')
        if metrics['top1']>best:best=metrics['top1'];torch.save(model.state_dict(),out/'best.pt')
        (out/'progress.json').write_text(json.dumps(history,indent=2))
        print('Fine-tune validation',epoch+1,metrics['top1'],'feature_delta',changed,flush=True)
    model.load_state_dict(torch.load(out/'best.pt',weights_only=True));print('Evaluating held-out test set',flush=True)
    final=evaluate(model,loaders['test']);final['labels']=[names[i] for i in range(102)]
    final.update(seed=42,batch_size=8,train_images=len(ids['train']),val_images=len(ids['val']),test_images=len(ids['test']),best_val_top1=best,head_best_val_top1=head_best,elapsed_seconds=time.time()-started,backbone_update_l1=changed,history=history,torch_version=torch.__version__)
    for name in ['sunflower','english marigold']:
        i=next(i for i,n in names.items() if n==name);final[name]={'class_index':i,'correct':final['correct'][i],'support':final['support'][i],'recall':final['correct'][i]/final['support'][i]}
    (out/'results.json').write_text(json.dumps(final,indent=2));print(json.dumps({k:v for k,v in final.items() if k not in ['history','confusion','labels','support','correct']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--output',required=True);p.add_argument('--epochs',type=int,default=5);main(p.parse_args())
