import assert from 'node:assert/strict';
import test from 'node:test';
import worker,{runTimer} from './worker.mjs';
const env={OAI_SITES_AUTHORIZATION:'test-platform-token',TIMER_API_KEY:'test-machine-token'};
const runId='12345678-1234-1234-1234-123456789abc';
const counters={catalog:68,resolved:68,quarantined:0,ottoSkusMissing:0,ottoReadbackMismatches:0,deliveryMappingsMissingAfter:0,activeSkus:68,marketplaceRows:68,unresolvedLedgerAfter:0,mode:'LIVE_FULL',orderMirror:'ON'};
test('Timer sendet genau einen authentifizierten POST und loggt nur erlaubte Felder',async()=>{
 const logs=[];let calls=0;
 const result=await runTimer(env,async(url,init)=>{calls++;assert.equal(url,'https://mrcolombo-otto-sync.d0minik88.chatgpt.site/api/sync');assert.equal(init.method,'POST');assert.equal(init.redirect,'manual');assert.equal(init.headers['x-sync-key'],env.TIMER_API_KEY);return Response.json({status:'SUCCEEDED',runId,counters:{...counters,ottoQuantityPlan:'private-secret'}});},(s)=>logs.push(s));
 assert.equal(result.status,'SUCCEEDED');assert.equal(calls,1);assert.doesNotMatch(logs.join(),/private|test-platform|test-machine/);
});
test('jede fehlende oder falsche Prüfziffer sowie Dry-Run und HTTP500 bleiben Fehler',async()=>{
 for(const key of Object.keys(counters)){
  await assert.rejects(runTimer(env,async()=>Response.json({status:'SUCCEEDED',runId,counters:{...counters,[key]:null}}),()=>{}),/NOT_VERIFIED/);
 }
 await assert.rejects(runTimer(env,async()=>Response.json({status:'SUCCEEDED',runId,counters},{status:500}),()=>{}),/NOT_VERIFIED/);
 await assert.rejects(runTimer(env,async()=>Response.json({status:'SKIPPED',runId,counters}),()=>{}),/NOT_VERIFIED/);
});
test('Transportfehler und ungültige Antworten werden nie wiederholt oder roh geloggt',async()=>{
 let calls=0;
 await assert.rejects(runTimer(env,async()=>{calls++;throw Error('private-secret');}),/OUTCOME_UNCONFIRMED/);assert.equal(calls,1);
 await assert.rejects(runTimer(env,async()=>new Response('<html>private</html>')),/RESPONSE_INVALID/);
 await assert.rejects(runTimer({},()=>assert.fail()),/CREDENTIALS_MISSING/);
 assert.equal((await worker.fetch()).status,404);
});
test('JSON-null, ungültige Lauf-ID, Redirect und übergroßer Body bleiben Fehler',async()=>{
 for(const body of [null,{status:'SUCCEEDED',counters},{status:'SUCCEEDED',counters,runId:'private-secret'}]) await assert.rejects(runTimer(env,async()=>Response.json(body),()=>{}),/NOT_VERIFIED/);
 await assert.rejects(runTimer(env,async()=>new Response(null,{status:302,headers:{location:'https://example.test'}}),()=>{}),/RESPONSE_INVALID/);
 await assert.rejects(runTimer(env,async()=>new Response('x'.repeat(65537)),()=>{}),/RESPONSE_INVALID/);
});
test('scheduled meldet keine Wiederholung und hält den echten Abgleich bis zum Abschluss offen',async()=>{
 const originalFetch=globalThis.fetch;const originalLog=console.log;let noRetry=0;let task;
 globalThis.fetch=async()=>Response.json({status:'SUCCEEDED',counters,runId});console.log=()=>{};
 try {worker.scheduled({noRetry(){noRetry++;}},env,{waitUntil(p){task=p;}});assert.equal(noRetry,1);assert.equal((await task).runId,runId);}
 finally {globalThis.fetch=originalFetch;console.log=originalLog;}
});
