import {mkdir, cp, rm, readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const revision='b7505ed8cf49fea221c2bb0eae83239f066f32bb';
const files=[
 ['assets/plantnet.onnx',`https://huggingface.co/cpoisson/plantnet300k-mobilenetv3-small/resolve/${revision}/plantnet_mobilenetv3.onnx`,'6ffc56d953daec0c75c4cd0beefee0448ba28a2074d00933246a266b5a7df1c4'],
 ['vendor/ort.wasm.min.mjs','https://cdn.jsdelivr.net/npm/onnxruntime-web@1.20.1/dist/ort.wasm.min.mjs','f53ed4792e758e7232f779d479eb8931b97ff3ab2e3b9a33ee00d1251ffdaad6'],
 ['vendor/ort-wasm-simd-threaded.mjs','https://cdn.jsdelivr.net/npm/onnxruntime-web@1.20.1/dist/ort-wasm-simd-threaded.mjs','745eb7c0ce6f18a6aa521971b2877babc7ffb27eecb58ab3bc6e5ef4692672e8'],
 ['vendor/ort-wasm-simd-threaded.wasm','https://cdn.jsdelivr.net/npm/onnxruntime-web@1.20.1/dist/ort-wasm-simd-threaded.wasm','207d02be4591c156b0a98f024f3d58005b5b04c92274d759fb390338c63559ea']
];
await rm('dist',{recursive:true,force:true});await mkdir('dist/vendor',{recursive:true});
for(const path of ['index.html','style.css','src','samples','assets'])await cp(path,'dist/'+path,{recursive:true,filter:p=>!p.endsWith('.onnx')});
for(const [path,url,hash] of files){
 let bytes;try{bytes=await readFile(path);}catch{}
 if(!bytes||createHash('sha256').update(bytes).digest('hex')!==hash){execFileSync('curl',['--fail','--location','--retry','3','--max-time','180',url,'--output','dist/'+path],{stdio:'inherit'});bytes=await readFile('dist/'+path);}
 if(createHash('sha256').update(bytes).digest('hex')!==hash)throw new Error('Integrity mismatch for '+path);
 await writeFile('dist/'+path,bytes);
}
await writeFile('dist/.nojekyll','');
console.log('Built Leafnote with verified model and runtime assets.');
