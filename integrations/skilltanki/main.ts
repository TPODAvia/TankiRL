import '@/ui/theme.css';
import {installAssetResolver} from '@/config/assets';
installAssetResolver();
const {tanki:t} = await import('@/lib/tanki');
const {createCommand} = await import('@/model/TankCommand');
const {Vector3} = await import('@/engine/math/Vector3');
const canvas=document.querySelector('#app') as HTMLCanvasElement;
t.uiRootService.mount(document.querySelector('#ui') as HTMLElement);
t.engineService.create(canvas);
await t.assetCatalogService.load();
t.touchInputService.attachKeyboard();
let stats:any, source:any=null, stepped=false, paused=false, stopped=false, frames=0, stage=4;
let held=new Set<string>();
let leaseUntil=0;
setInterval(()=>{if(leaseUntil && performance.now()>leaseUntil){release();leaseUntil=0;}},50);
function lease(ms:number){leaseUntil=performance.now()+Math.max(100,Math.min(2000,ms));}
window.addEventListener('keydown',e=>{held.add(e.code); if(e.code==='KeyP'){e.preventDefault();toggle();}});
window.addEventListener('keyup',e=>held.delete(e.code));
window.addEventListener('blur',()=>release());
function release(){for(const code of held) window.dispatchEvent(new KeyboardEvent('keyup',{code}));held.clear();t.touchInputService.releaseAll();}
function toggle(){paused=!paused;release();document.querySelector('#pause')!.textContent=paused?'Resume AI (P)':'Pause AI (P)';}
document.querySelector('#pause')!.addEventListener('click',toggle);
document.querySelector('#stop')!.addEventListener('click',()=>{stopped=true;paused=true;release();});
// Preserve the actual upstream shot listener; count only emitted shots.
const listenerFor=t.combatService.listenerFor;
t.combatService.listenerFor=(team,getShooter,turret)=>{const l=listenerFor(team,getShooter,turret);return {...l,onShot:(r)=>{if(getShooter()?.id===t.battleStateService.local.id)stats.shots++;l.onShot(r);}};};
function aimAlignment(){
 const s=t.battleStateService;if(stage!==2||!s.hasLocal)return null;
 const g=s.local.gameTank,origin=new Vector3(),direction=new Vector3();g.getMuzzleWorldPosition(origin);g.getShotDirection(direction);
 let best=0;for(const a of s.actors()){if(a.isLocal||!a.alive)continue;const p=a.gameTank.tank.getBody().state.position;
 const dx=p.x-origin.x,dy=p.y-origin.y;const distance=Math.hypot(dx,dy);if(distance>1500||distance<1)continue;
 const dot=(dx*direction.x+dy*direction.y)/(distance*Math.hypot(direction.x,direction.y));best=Math.max(best,Math.max(0,dot));}return best;
}
function telemetry(){const s=t.battleStateService;return {...stats,aim_alignment:aimAlignment(),time_ms:s.timeMs,phase:s.phase,paused,stopped,keys:[...held],actors:s.actors().map(a=>{const k=a.gameTank.tank,b=k.getBody().state;return {id:a.id,local:a.isLocal,alive:a.alive,health:k.health,max_health:k.maxHealth,position:{x:b.position.x,y:b.position.y,z:b.position.z},orientation:{...b.orientation},turret:k.turretController.getDirection()};})};}
function random(seed:number){let v=seed>>>0;return ()=>{v+=0x6D2B79F5;let z=v;z=Math.imul(z^(z>>>15),z|1);z^=z+Math.imul(z^(z>>>7),z|61);return ((z^(z>>>14))>>>0)/4294967296;};}
async function reset(c:any={}){
 release(); leaseUntil=0;t.battleSessionService.dispose();Math.random=random(c.seed??1);
 if((c.enemies??1)<0||(c.enemies??1)>11)throw Error('enemies must be 0..11');
 paused=false;stopped=false;stepped=c.stepped??false;stage=c.stage??4;
 stats={damage_dealt:0,damage_received:0,kills:0,deaths:0,shots:0,hits:0};
 const config={mode:'dm',mapId:c.map??'arena_old_summer',playerName:'TankiRL',loadout:{hull:c.hull??'Hunter',turret:c.turret??'Smoky',modification:'M0'},team:'red',bots:c.stage===1?0:(c.enemies??1),botDifficulty:c.difficulty??'easy',seed:c.seed??1};
 await t.battleSessionService.start(config as any);
 const state=t.battleStateService;
 t.battleEventService.on('death',e=>{if(e.victimId===state.local.id)stats.deaths++;if(e.killerId===state.local.id && e.victimId!==state.local.id)stats.kills++;});
 for(const a of state.actors()){
  const k=a.gameTank.tank, damage=k.takeDamage.bind(k), update=a.gameTank.updateWeapon.bind(a.gameTank);
  k.takeDamage=(amount)=>{const before=k.health;const out=damage(amount);const actual=Math.max(0,before-k.health);if(a.isLocal)stats.damage_received+=actual;
   if(source?.isLocal&&!a.isLocal&&actual>0){stats.damage_dealt+=actual;stats.hits++;}return out;};
  a.gameTank.updateWeapon=(...args)=>{source=a;try{return update(...args);}finally{source=null;}};
  if(!a.isLocal&&(c.stage===2||c.stage===3))await t.controlRegistryService.replace(a,{kind:'bot',start:async(sink)=>{sink.push(createCommand());},tick:()=>{},stop:()=>{}});
 }
 // Curriculum target fixture: two real tanks at a valid map spawn, facing each other.
 // Only setup/tests use positions; they never enter policy observations.
 if(c.stage===2||c.stage===3||c.fixture){
  const p=state.mapStage.spawnPoints[0];if(!p)throw Error('Map has no target fixture spawn');
  state.actors().forEach((a,i)=>{a.gameTank.spawnAtPoint({...p,position:p.position.clone().add({x:0,y:i*600,z:0} as any),rotationZ:i?Math.PI:0});if(i>0||c.fixture)a.gameTank.tank.getBody().movable=false;});
 }
 if((stage===2||stage===3)&&!c.fixture)state.local.gameTank.tank.turretController.setDirectionImmediate((Math.random()-.5)*1.6);
 if(stepped)t.battleLoopService.stop();
 t.hudService.show();canvas.focus();return telemetry();
}
function advance(ticks:number){if(!stepped)throw Error('advance requires stepped mode');if(paused||stopped)return telemetry();for(let i=0;i<ticks;i++)(t.battleLoopService as any).onFrame(0.033);return telemetry();}
let last=performance.now();t.engineService.app.on('frameend',()=>{frames++;let now=performance.now();if(now-last>1000){document.querySelector('#status')!.textContent=`${Math.round(frames*1000/(now-last))} render FPS | local only`;frames=0;last=now;}});
function capture(){return new Promise<string>((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Renderer did not produce a frame')),5000);t.engineService.app.once('frameend',()=>{clearTimeout(timer);resolve(canvas.toDataURL('image/png'));});});}
(window as any).tankirl={reset,advance,telemetry,release,capture,lease,pause:toggle,catalog:()=>({maps:t.assetCatalogService.maps.map(x=>x.id),hulls:t.assetCatalogService.hulls,turrets:t.assetCatalogService.turrets}),ready:true};
const params=new URLSearchParams(location.search);
if(!params.has('bridge')) await reset({map:params.get('map')??undefined,enemies:Number(params.get('enemies')??1),hull:params.get('hull')??undefined,turret:params.get('turret')??undefined,difficulty:params.get('difficulty')??'easy',seed:Number(params.get('seed')??1)});
