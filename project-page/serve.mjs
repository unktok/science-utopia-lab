import {createServer} from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import {resolve,extname,sep,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'dist');
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.pdf':'application/pdf','.mp4':'video/mp4'};
const server=createServer(async(req,res)=>{try{
  const path=resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
  if(path!==root&&!path.startsWith(root+sep)){res.writeHead(403).end();return;}
  const actual=(await stat(path)).isDirectory()?resolve(path,'index.html'):path;
  const bytes=await readFile(actual);res.writeHead(200,{'Content-Type':types[extname(actual)]??'application/octet-stream','Cache-Control':'no-store','Content-Length':bytes.length});res.end(bytes);
}catch{res.writeHead(404).end('Not found');}});
server.listen(4673,'127.0.0.1',()=>console.log('Local: http://127.0.0.1:4673'));
