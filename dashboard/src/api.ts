export type ClaimState =
  "waiting" | "in_progress" | "awaiting_sign_off" | "decided";

export interface Decision {
  decision: "approve" | "decline" | "refer";
  payout: number;
  explanation: string;
  policy_section: string;
  decided_at: string;
}

export interface Step {
  at: string;
  text: string;
}

export interface ClaimSummary {
  claim_id: string;
  customer_id: string;
  customer_name: string;
  claim_type: string;
  summary: string;
  submitted_on: string;
  amount_claimed: number;
  state: ClaimState;
  decision: Decision | null;
}

export interface Claim {
  claim_id: string;
  policy_id: string;
  customer_id: string;
  claim_type: string;
  submitted_on: string;
  incident_date: string;
  incident_location: string;
  summary: string;
  story: string;
  items: { description: string; category: string; amount: number }[];
  amount_claimed: number;
  documents: { name: string; type: string; content: string }[];
  state: ClaimState;
  decision: Decision | null;
  sign_off: { handler_id: string; name: string; signed_off_at: string } | null;
  payment: { amount: number; paid_at: string } | null;
  steps: Step[];
}

export interface Policy {
  policy_id: string;
  plan: string;
  add_ons: string[];
  purchased_on: string;
  trip: {
    destination: string;
    departs_on: string;
    returns_on: string;
    trip_cost: number;
  };
  travelers: string[];
}

export interface Customer {
  customer_id: string;
  name: string;
  customer_since: string;
  previous_claims: {
    claim_id: string;
    incident_date: string;
    summary: string;
    outcome: string;
    amount_paid: number;
  }[];
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
  can_approve_over_limit: boolean;
}

async function send<T>(method: string, path: string, body?: object) {
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok)
    throw new Error(`${method} ${path}: ${String(response.status)}`);
  return (await response.json()) as T;
}

export const api = {
  claims: () => send<ClaimSummary[]>("GET", "/api/claims"),
  claim: (id: string) => send<Claim>("GET", `/api/claims/${id}`),
  policy: (id: string) => send<Policy>("GET", `/api/policies/${id}`),
  customer: (id: string) => send<Customer>("GET", `/api/customers/${id}`),
  handlers: () => send<Handler[]>("GET", "/api/handlers"),
  instructions: () => send<{ text: string }>("GET", "/api/instructions"),
  runAgent: (id: string) => send<Claim>("POST", `/api/claims/${id}/run`),
  signOff: (id: string, handlerId: string) =>
    send<Claim>("POST", `/api/claims/${id}/sign-off`, {
      handler_id: handlerId,
    }),
  pay: (id: string, amount: number) =>
    send<Claim>("POST", `/api/claims/${id}/payment`, { amount }),
};
