import {defineConfig} from 'vite';
import {resolve, extname, sep} from 'node:path';
import {createReadStream, statSync} from 'node:fs';
const root=resolve(import.meta.dirname,'../..');
const assets=resolve(root,'third_party/skilltanki/assets');
export default defineConfig({
 root:resolve(root,'integrations/skilltanki'), cacheDir:resolve(root,'runtime/vite'),
 resolve:{alias:{'@':resolve(root,'third_party/skilltanki/apps/mobile/src')}},
 server:{hmr:false,watch:null,host:'127.0.0.1',port:5173,strictPort:true,fs:{allow:[root]}},
 plugins:[{name:'local-assets',configureServer(server){server.middlewares.use((req,res,next)=>{
  if(req.url?.startsWith('/api/')||req.url?.startsWith('/ws/')) {res.statusCode=403;res.end('Offline only');return;}
  if(!req.url?.startsWith('/assets/')) return next();
  const file=resolve(assets,decodeURIComponent(req.url.split('?')[0].slice(8)));
  if(!file.startsWith(assets+sep)) {res.statusCode=403;res.end();return;}
  try {const s=statSync(file);if(!s.isFile())throw Error();
   res.setHeader('Content-Type',({'.json':'application/json','.png':'image/png','.jpg':'image/jpeg','.xml':'application/xml','.mp3':'audio/mpeg'})[extname(file)]||'application/octet-stream');
   res.setHeader('Content-Length',s.size); createReadStream(file).pipe(res);
  }catch{res.statusCode=404;res.end('Missing local asset');}
 });}}]
});
