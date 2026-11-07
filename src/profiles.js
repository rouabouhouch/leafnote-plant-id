export async function getProfile(name, signal) {
  const cached = await fetch(new URL('../assets/profiles.json', import.meta.url), {signal}).then(r => r.json()).catch(() => ({}));
  if (signal.aborted) throw new DOMException('Aborted', 'AbortError');
  if (cached[name]) return cached[name];
  const response = await fetch('https://en.wikipedia.org/api/rest_v1/page/summary/' + encodeURIComponent(name.replaceAll(' ', '_')), {signal});
  if (!response.ok) throw new Error('No profile available');
  const data = await response.json();
  if (!data.extract || data.type === 'disambiguation') throw new Error('No clear profile available');
  const url = data.content_urls?.desktop?.page;
  if (!url?.startsWith('https://en.wikipedia.org/wiki/')) throw new Error('Invalid profile source');
  return {title:data.title, description:data.description, extract:data.extract, url};
}
