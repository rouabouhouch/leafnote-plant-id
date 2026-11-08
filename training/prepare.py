"""Create a licensed, observation-disjoint manifest from official PlantCLEF metadata."""
import argparse, csv, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path

ALLOWED = {'cc0', 'cc-by', 'cc-by-sa'}

def prepare(source, output):
    rows, names, groups, images = [], {}, {}, set()
    with open(source, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        required = {'image_name','species_id','species','obs_id','license','author','references','learn_tag','image_backup_url','dataset'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Unexpected PlantCLEF metadata schema')
        for row in reader:
            if row['license'].lower() not in ALLOWED:
                continue
            split = row['learn_tag'].lower()
            if split not in {'train', 'val', 'test'}:
                continue
            group = row['dataset'] + ':' + row['obs_id']
            if not row['obs_id']:
                raise ValueError('Missing observation ID')
            if group in groups and groups[group] != split:
                raise ValueError('Observation leakage across splits: ' + group)
            groups[group] = split
            if row['image_name'] in images:
                raise ValueError('Duplicate image in metadata')
            images.add(row['image_name'])
            names[row['species_id']] = row['species']
            rows.append({k:row[k] for k in required})
    train_ids = {r['species_id'] for r in rows if r['learn_tag']=='train'}
    names = {k:v for k,v in names.items() if k in train_ids}
    if not any(v.startswith('Helianthus annuus') for v in names.values()):
        raise ValueError('Sunflower coverage not verified. Refusing to prepare this dataset.')
    keys = sorted(names)
    indexes = {key:i for i,key in enumerate(keys)}
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    with (output/'manifest.jsonl').open('w') as f:
        for row in rows:
            if row['species_id'] not in indexes: continue
            row['label'] = indexes[row['species_id']]
            row['path'] = f"{row['learn_tag']}/{row['species_id']}/{row['image_name']}"
            counts[row['learn_tag']] += 1
            f.write(json.dumps(row, ensure_ascii=False)+'\n')
    (output/'labels.json').write_text(json.dumps([names[k] for k in keys],ensure_ascii=False,indent=2))
    digest = hashlib.sha256()
    with open(source,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): digest.update(chunk)
    report = {'species':len(keys),'images':dict(counts),'metadata_sha256':digest.hexdigest(),'licenses':sorted(ALLOWED),'sunflower_verified':True}
    (output/'dataset-report.json').write_text(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('metadata');p.add_argument('output');a=p.parse_args()
    print(json.dumps(prepare(a.metadata,a.output),indent=2))
