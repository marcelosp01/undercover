import { vi } from "vitest";
import type { Claim, ClaimSummary, Customer, Handler, Policy } from "./api";

export const summary: ClaimSummary = {
  claim_id: "CLM-1001",
  customer_id: "CUS-3001",
  customer_name: "Maya Patel",
  claim_type: "trip_delay",
  summary: "Flight canceled",
  submitted_on: "2026-06-24",
  amount_claimed: 1250,
  state: "waiting",
  decision: null,
};

export const claim: Claim = {
  claim_id: "CLM-1001",
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  claim_type: "trip_delay",
  submitted_on: "2026-06-24",
  incident_date: "2026-06-18",
  incident_location: "Rome, Italy",
  summary: "Flight canceled",
  story: "My flight home from Rome was canceled.",
  items: [
    { description: "Airport hotel", category: "accommodation", amount: 1250 },
  ],
  amount_claimed: 1250,
  documents: [
    { name: "Hotel receipt", type: "receipt", content: "Hotel Aurelia." },
  ],
  state: "waiting",
  decision: null,
  sign_off: null,
  payment: null,
  steps: [],
};

export const policy: Policy = {
  policy_id: "POL-2001",
  plan: "premium",
  add_ons: ["electronics_plus"],
  purchased_on: "2026-04-22",
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
};

export const customer: Customer = {
  customer_id: "CUS-3001",
  name: "Maya Patel",
  customer_since: "2023-04-11",
  previous_claims: [
    {
      claim_id: "CLM-0412",
      incident_date: "2024-08-09",
      summary: "Bag arrived late",
      outcome: "approved",
      amount_paid: 140,
    },
  ],
};

export const handlers: Handler[] = [
  {
    handler_id: "HND-01",
    name: "Dana Whitfield",
    role: "Senior Claims Handler",
    can_approve_over_limit: true,
  },
];

/** Answer fetches from a table of "METHOD /path" to JSON, and record the calls. */
export function mockApi(routes: Record<string, unknown>) {
  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${path}`;
    if (!(key in routes))
      return Promise.resolve(new Response("{}", { status: 404 }));
    const reply = routes[key];
    const body =
      typeof reply === "function" ? (reply as () => unknown)() : reply;
    return Promise.resolve(Response.json(body));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
