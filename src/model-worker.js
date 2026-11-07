import * as ort from '../vendor/ort.wasm.min.mjs';
import {classNames, rank} from './classifier.js';
ort.env.wasm.numThreads = 1;
let ready;
async function load() {
  const [session, mapping] = await Promise.all([
    ort.InferenceSession.create(new URL('../assets/plantnet.onnx', import.meta.url).href, {executionProviders: ['wasm']}),
    fetch(new URL('../assets/species.json', import.meta.url)).then(r => {if (!r.ok) throw new Error('Species list could not load.'); return r.json();})
  ]);
  return {session, labels: classNames(mapping)};
}
self.onmessage = async ({data}) => {
  const {id, pixels} = data;
  try {
    self.postMessage({id, status: ready ? 'Looking at leaf shapes, colours and flowers…' : 'Loading the plant model. First use can take a little longer…'});
    if (!ready) ready = load().catch(error => {ready = undefined; throw error;});
    const {session, labels} = await ready;
    const output = await session.run({[session.inputNames[0]]: new ort.Tensor('float32', pixels, [1,3,224,224])});
    self.postMessage({id, matches: rank(output[session.outputNames[0]].data, labels)});
  } catch (error) {self.postMessage({id, error: 'The model could not run. Check your connection and try again. ' + error.message});}
};
