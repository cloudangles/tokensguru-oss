let optimizersPromise = null;

async function request(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error("Could not reach the tokensguru server. Is `tokensguru docs` still running?");
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    throw new Error((data && data.error) || `The server answered with status ${response.status}.`);
  }
  return data;
}

export function getOptimizers() {
  if (!optimizersPromise) {
    optimizersPromise = request("/api/optimizers").catch((error) => {
      optimizersPromise = null;
      throw error;
    });
  }
  return optimizersPromise;
}

export function runOptimizer(payload) {
  return request("/api/optimize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getBenchmark(optimizerId) {
  return request(`/api/benchmark?optimizer=${encodeURIComponent(optimizerId)}`);
}

let guardrailsPromise = null;

export function getGuardrails() {
  if (!guardrailsPromise) {
    guardrailsPromise = request("/api/guardrails").catch((error) => {
      guardrailsPromise = null;
      throw error;
    });
  }
  return guardrailsPromise;
}

export function runCheck(payload) {
  return request("/api/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getGuardrailBenchmark(guardrailId) {
  return request(`/api/guardrail-benchmark?guardrail=${encodeURIComponent(guardrailId)}`);
}
