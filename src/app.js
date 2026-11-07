import {SIZE, centerCrop, normalize, searchName, classNames} from './classifier.js';
import {getProfile} from './profiles.js';
const $ = id => document.getElementById(id);
let worker, request = 0, objectURL, profileAbort, allSpecies = [];
function status(message, error = false) { $('status').textContent = message; $('status').classList.toggle('error', error); }
function el(tag, text, className) {const node = document.createElement(tag); if(text) node.textContent = text; if(className) node.className=className; return node;}
function link(text, href) {const a=el('a',text); a.href=href; a.target='_blank'; a.rel='noopener noreferrer'; return a;}
async function profile(name) {
  profileAbort?.abort(); profileAbort = new AbortController();
  const {signal} = profileAbort;
  const section = $('profile');
  section.replaceChildren(el('h4', name), el('p','Finding a source-linked profile…'));
  const timer = setTimeout(() => profileAbort?.signal === signal && profileAbort.abort(), 12000);
  try {
    const info = await getProfile(name, signal);
    if(signal.aborted) return;
    section.replaceChildren(el('span','PLANT PROFILE','eyebrow'),el('h4',info.title),el('p',info.description || '', 'micro'),el('p',info.extract),link('Read the Wikipedia article', info.url),el('p','Wikipedia contributors · CC BY-SA. Check the article before using its information.', 'micro'));
  } catch {
    if (profileAbort.signal !== signal) return;
    section.replaceChildren(el('h4',name),el('p','A description is unavailable right now. Use the source links to explore this candidate.'));
  } finally {clearTimeout(timer);}
  if(profileAbort.signal !== signal) return;
  section.append(link('Explore botanical records','https://powo.science.kew.org/results?q='+encodeURIComponent(name)));
}
function render(matches) {
  $('empty').hidden = true; $('results').hidden = false; $('candidates').replaceChildren();
  for(const [index,match] of matches.entries()) {
    const button=el('button',null,'candidate'); button.type='button'; button.setAttribute('aria-pressed', String(index === 0));
    const text=el('span');text.append(el('strong',searchName(match.name)),el('small',match.name));
    button.append(text,el('span',(match.score*100).toFixed(1)+'%','score'));
    button.addEventListener('click',()=>{for(const b of $('candidates').children)b.setAttribute('aria-pressed',String(b===button));profile(searchName(match.name));});
    $('candidates').append(button);
  }
  $('uncertainty').textContent = matches[0].score < .5 || matches[0].score-matches[1].score < .2
    ? 'The model has no clear favourite. Try another close-up and compare all three suggestions.'
    : 'Even a high score can be wrong. Compare the candidate’s leaves and flowers with your plant.';
  profile(searchName(matches[0].name));
}
function ensureWorker() {
  if(worker) return worker;
  worker=new Worker(new URL('./model-worker.js',import.meta.url),{type:'module'});
  worker.onmessage=({data})=>{if(data.id!==request)return;if(data.status)status(data.status);if(data.error)status(data.error,true);if(data.matches){status('Three suggestions to explore. Select one to read its profile.');render(data.matches);}};
  worker.onerror=()=>{status('The model could not start in this browser. Try a recent Chrome, Edge, Firefox or Safari.',true);worker.terminate();worker=undefined;};
  return worker;
}
async function identify(file, source) {
  const id=++request; profileAbort?.abort();
  $('results').hidden=true;$('empty').hidden=false;
  if(!['image/jpeg','image/png','image/webp'].includes(file.type)){status('Choose a JPG, PNG or WebP image.',true);return;}
  if(file.size>15*1024*1024){status('This photo is too large. Choose one smaller than 15 MB.',true);return;}
  status('Opening your photo…');
  let bitmap;
  try {
    bitmap=await createImageBitmap(file);
    if(id!==request)return;
    if(bitmap.width*bitmap.height>40e6)throw new Error('Please resize the photo to under 40 megapixels.');
    const canvas=document.createElement('canvas');canvas.width=canvas.height=SIZE;
    const context=canvas.getContext('2d',{willReadFrequently:true});
    context.imageSmoothingEnabled=true;
    context.imageSmoothingQuality='high';
    context.fillStyle='#fff';context.fillRect(0,0,SIZE,SIZE);
    context.drawImage(bitmap,...centerCrop(bitmap.width,bitmap.height),0,0,SIZE,SIZE);
    const pixels=normalize(context.getImageData(0,0,SIZE,SIZE).data);
    if(objectURL)URL.revokeObjectURL(objectURL);objectURL=URL.createObjectURL(file);
    $('preview').src=objectURL;$('preview-wrap').hidden=false;$('dropzone').classList.add('compact');
    $('filename').textContent=file.name || 'Plant photo';
    $('photo-credit').replaceChildren();
    if(source)$('photo-credit').append(link('Photo by '+source.observer+' · CC0 · expected '+source.name+'',source.source));
    ensureWorker().postMessage({id,pixels},[pixels.buffer]);
  }catch(error){if(id===request)status(error.message || 'We could not open this image. Try a different photo.',true);}
  finally{bitmap?.close();}
}
$('photo').addEventListener('change',e=>{if(e.target.files[0])identify(e.target.files[0]);e.target.value='';});
for(const type of ['dragenter','dragover'])$('dropzone').addEventListener(type,e=>{e.preventDefault();$('dropzone').classList.add('dragging');});
for(const type of ['dragleave','drop'])$('dropzone').addEventListener(type,e=>{e.preventDefault();$('dropzone').classList.remove('dragging');});
$('dropzone').addEventListener('drop',e=>{if(e.dataTransfer.files[0])identify(e.dataTransfer.files[0]);});
fetch(new URL('../samples/index.json',import.meta.url)).then(r=>r.json()).then(samples=>{
 for(const sample of [...samples].reverse()){
  const button=el('button',null,'sample');button.type='button';const image=el('img');image.src=new URL('../samples/'+sample.slug+'.jpg',import.meta.url);image.alt=sample.common;image.loading='lazy';button.append(image,el('span',sample.common));
  button.addEventListener('click',async()=>{try{const response=await fetch(image.src);if(!response.ok)throw new Error();const blob=await response.blob();await identify(new File([blob],sample.common+'.jpg',{type:'image/jpeg'}),sample);}catch{status('The example photo could not load. Please try again.',true);}});$('samples').append(button);
 }
}).catch(()=>status('Example photos could not load. You can still choose your own photo.'));
function speciesList(){const q=$('species-search').value.toLowerCase().trim();const found=allSpecies.filter(name=>name.toLowerCase().includes(q));$('species-count').textContent=found.length+' matching species'+(found.length>80?' · showing the first 80':'');$('species-list').replaceChildren(...found.slice(0,80).map(name=>el('li',name)));}
fetch(new URL('../assets/species.json',import.meta.url)).then(r=>r.json()).then(data=>{allSpecies=classNames(data).sort();speciesList();}).catch(()=>{$('species-count').textContent='Species list unavailable. Please reload.';});
$('species-search').addEventListener('input',speciesList);
