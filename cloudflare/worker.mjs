const ENDPOINT = "https://mrcolombo-otto-sync.d0minik88.chatgpt.site/api/sync";
const EXPECTED = {
  catalog:68, resolved:68, quarantined:0, ottoSkusMissing:0,
  ottoReadbackMismatches:0, deliveryMappingsMissingAfter:0,
  activeSkus:68, marketplaceRows:68, unresolvedLedgerAfter:0,
  mode:"LIVE_FULL", orderMirror:"ON",
};

export async function runTimer(env, send = fetch, log = console.log) {
  if (!env.OAI_SITES_AUTHORIZATION?.trim() || !env.TIMER_API_KEY?.trim()) {
    throw new Error("TIMER_CREDENTIALS_MISSING");
  }
  let response;
  try {
    response = await send(ENDPOINT, {
      method:"POST", redirect:"manual", signal:AbortSignal.timeout(240_000),
      headers:{
        "OAI-Sites-Authorization":`Bearer ${env.OAI_SITES_AUTHORIZATION}`,
        "x-sync-key":env.TIMER_API_KEY,
        "content-type":"application/json",
      }, body:"{}",
    });
  } catch {
    throw new Error("TIMER_TRANSPORT_OUTCOME_UNCONFIRMED");
  }
  let body;
  try {
    if (!response.body) throw new Error();
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let text = ""; let bytes = 0;
    try {
      while (true) {
        const {done,value} = await reader.read();
        if (done) break;
        bytes += value.byteLength;
        if (bytes > 65_536) { await reader.cancel(); throw new Error(); }
        text += decoder.decode(value,{stream:true});
      }
      text += decoder.decode();
    } finally { reader.releaseLock(); }
    body = JSON.parse(text);
  } catch { throw new Error("TIMER_RESPONSE_INVALID"); }
  // No raw errors, SKU diagnostics, payloads, headers or secrets in timer logs.
  const counters = body?.counters;
  const valid = counters && typeof counters === "object" &&
    Object.entries(EXPECTED).every(([key,value]) => counters[key] === value);
  const runId = typeof body?.runId === "string" && /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(body.runId)
    ? body.runId : null;
  if (!response.ok || body?.status !== "SUCCEEDED" || !valid || !runId) {
    log(JSON.stringify({status:"FAILED", httpStatus:response.status, runId}));
    throw new Error("TIMER_SYNC_NOT_VERIFIED");
  }
  log(JSON.stringify({status:"SUCCEEDED",runId,catalog:68,resolved:68}));
  return {status:"SUCCEEDED",runId};
}

export default {
  fetch() { return new Response("Not found", {status:404}); },
  scheduled(controller, env, ctx) {
    // Only a new scheduled event may re-plan; never replay an ambiguous POST.
    if (typeof controller.noRetry === "function") controller.noRetry();
    ctx.waitUntil(runTimer(env));
  },
};
