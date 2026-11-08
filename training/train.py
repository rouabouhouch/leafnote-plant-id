"""Fine-tune all MobileNetV3 Large layers; select on validation, never test."""
import argparse, json, random
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms

class Plants(Dataset):
    def __init__(self, manifest, root, split, transform):
        self.rows=[json.loads(s) for s in open(manifest) if json.loads(s)['learn_tag']==split]
        if not self.rows: raise ValueError('Empty split: '+split)
        self.root=Path(root);self.transform=transform
    def __len__(self): return len(self.rows)
    def __getitem__(self,i):
        r=self.rows[i]
        with Image.open(self.root/r['path']) as image:
            return self.transform(image.convert('RGB')),r['label']

@torch.inference_mode()
def evaluate(model, loader, device, classes):
    model.eval(); hits1=hits3=total=0
    correct=torch.zeros(classes);counts=torch.zeros(classes)
    for x,y in loader:
        logits=model(x.to(device));pred=logits.topk(min(3,classes),dim=1).indices.cpu()
        hit=pred[:,0].eq(y);hits1+=hit.sum().item();hits3+=pred.eq(y[:,None]).any(1).sum().item();total+=len(y)
        counts+=torch.bincount(y,minlength=classes)
        correct+=torch.bincount(y[hit],minlength=classes)
    recall=correct/counts.clamp_min(1)
    return {'top1':hits1/total,'top3':hits3/total,'macro_recall':recall[counts>0].mean().item(),'images':total,'class_support':counts.tolist(),'class_recall':recall.tolist()}

def main(a):
    random.seed(a.seed);np.random.seed(a.seed);torch.manual_seed(a.seed)
    if not torch.cuda.is_available(): raise RuntimeError('A CUDA GPU is required for this full-dataset training job.')
    device='cuda';out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    labels=json.load(open(Path(a.manifest).parent/'labels.json'))
    weights=models.MobileNet_V3_Large_Weights.IMAGENET1K_V2
    train_transform=transforms.Compose([transforms.RandomResizedCrop(224,scale=(.65,1.0)),transforms.RandomHorizontalFlip(),transforms.ColorJitter(.15,.15,.15,.05),transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])])
    loaders={split:DataLoader(Plants(a.manifest,a.images,split,train_transform if split=='train' else weights.transforms()),batch_size=a.batch,shuffle=split=='train',num_workers=a.workers,pin_memory=True) for split in ['train','val','test']}
    model=models.mobilenet_v3_large(weights=weights)
    model.classifier[-1]=torch.nn.Linear(model.classifier[-1].in_features,len(labels));model.to(device)
    optimizer=torch.optim.AdamW([{'params':model.features.parameters(),'lr':a.lr/10},{'params':model.classifier.parameters(),'lr':a.lr}],weight_decay=.01)
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=a.epochs)
    loss_fn=torch.nn.CrossEntropyLoss(label_smoothing=.1)
    scaler=torch.amp.GradScaler('cuda');start=0;best=-1
    if a.resume:
        state=torch.load(a.resume,map_location=device,weights_only=False)
        if state['labels']!=labels:raise ValueError('Checkpoint label mapping differs')
        model.load_state_dict(state['model']);optimizer.load_state_dict(state['optimizer']);scheduler.load_state_dict(state['scheduler']);scaler.load_state_dict(state['scaler']);start=state['epoch']+1;best=state['best']
    (out/'config.json').write_text(json.dumps(vars(a),indent=2))
    for epoch in range(start,a.epochs):
        model.train();loss_sum=seen=0
        for x,y in loaders['train']:
            x=x.to(device);y=y.to(device);optimizer.zero_grad(set_to_none=True)
            with torch.autocast('cuda'):loss=loss_fn(model(x),y)
            scaler.scale(loss).backward();scaler.step(optimizer);scaler.update()
            loss_sum+=loss.item()*len(y);seen+=len(y)
        scheduler.step();metrics=evaluate(model,loaders['val'],device,len(labels))
        improved=metrics['macro_recall']>best
        best=max(best,metrics['macro_recall'])
        state={'model':model.state_dict(),'optimizer':optimizer.state_dict(),'scheduler':scheduler.state_dict(),'scaler':scaler.state_dict(),'labels':labels,'epoch':epoch,'best':best}
        torch.save(state,out/'last.pt')
        if improved:torch.save(state,out/'best.pt')
        with (out/'history.jsonl').open('a') as f:f.write(json.dumps({'epoch':epoch,'loss':loss_sum/seen,'validation':metrics})+'\n')
        print(epoch,loss_sum/seen,metrics['top1'],metrics['macro_recall'],flush=True)
    model.load_state_dict(torch.load(out/'best.pt',map_location=device,weights_only=False)['model'])
    metrics=evaluate(model,loaders['test'],device,len(labels))
    metrics['sunflower']={labels[i]:{'recall':metrics['class_recall'][i],'support':metrics['class_support'][i]} for i,n in enumerate(labels) if n.startswith('Helianthus annuus')}
    (out/'test-metrics.json').write_text(json.dumps(metrics,indent=2))
    (out/'labels.json').write_text(json.dumps(labels,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--images',required=True);p.add_argument('--output',required=True);p.add_argument('--epochs',type=int,default=15);p.add_argument('--batch',type=int,default=64);p.add_argument('--workers',type=int,default=4);p.add_argument('--lr',type=float,default=.001);p.add_argument('--seed',type=int,default=42);p.add_argument('--resume');main(p.parse_args())
