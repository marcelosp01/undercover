import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { decisionLabel, money, words } from "./format";
import {
  claim,
  customer,
  handlers,
  mockApi,
  policy,
  summary,
} from "./test-data";

beforeEach(() => {
  window.location.hash = "";
});

afterEach(() => {
  vi.useRealTimers();
  cleanup();
  vi.unstubAllGlobals();
});

it("formats money and words", () => {
  expect(money(1250)).toBe("$1,250.00");
  expect(words("trip_delay")).toBe("Trip delay");
  expect(
    decisionLabel({
      decision: "refer",
      payout: 0,
      explanation: "",
      policy_section: "",
      decided_at: "",
    }),
  ).toBe("Referred");
});

it("shows the queue with counts and states", async () => {
  mockApi({
    "GET /api/claims": [
      summary,
      { ...summary, claim_id: "CLM-1002", state: "awaiting_sign_off" },
      { ...summary, claim_id: "CLM-1003", state: "waiting" },
    ],
  });
  render(<App />);
  expect(await screen.findByText("CLM-1002")).toBeDefined();
  expect(screen.getAllByText("$1,250.00")).toHaveLength(3);
  expect(screen.getAllByText("Waiting for sign-off")).toHaveLength(2);
  const link = screen.getByRole("link", { name: "CLM-1001" });
  expect(link.getAttribute("href")).toBe("#/claims/CLM-1001");
});

it("shows a message when the queue cannot load", async () => {
  mockApi({});
  render(<App />);
  expect(await screen.findByText("Could not load the queue.")).toBeDefined();
});

it("shows a claim in full with its decision", async () => {
  window.location.hash = "#/claims/CLM-1001";
  mockApi({
    "GET /api/claims/CLM-1001": {
      ...claim,
      state: "decided",
      decision: {
        decision: "approve",
        payout: 420,
        explanation: "Covered in full.",
        policy_section: "Section 3, Trip Delay",
        decided_at: "2026-06-25",
      },
      sign_off: {
        handler_id: "HND-01",
        name: "Dana Whitfield",
        signed_off_at: "x",
      },
      payment: { amount: 420, paid_at: "x" },
    },
    "GET /api/policies/POL-2001": policy,
    "GET /api/customers/CUS-3001": customer,
  });
  render(<App />);
  expect(
    await screen.findByText("My flight home from Rome was canceled."),
  ).toBeDefined();
  expect(screen.getByText("Hotel Aurelia.")).toBeDefined();
  expect(screen.getByText("Covered in full.")).toBeDefined();
  expect(screen.getByText("Section 3, Trip Delay")).toBeDefined();
  expect(screen.getByText("Signed off by Dana Whitfield.")).toBeDefined();
  expect(await screen.findByText(/Bag arrived late/)).toBeDefined();
  expect(screen.getByText(/customer since 2023-04-11/)).toBeDefined();
});

it("shows a claim with no decision and no earlier claims", async () => {
  window.location.hash = "#/claims/CLM-1001";
  mockApi({
    "GET /api/claims/CLM-1001": claim,
    "GET /api/policies/POL-2001": { ...policy, add_ons: [] },
    "GET /api/customers/CUS-3001": { ...customer, previous_claims: [] },
  });
  render(<App />);
  expect(await screen.findByText("No decision yet.")).toBeDefined();
  expect(await screen.findByText("No earlier claims.")).toBeDefined();
});

it("shows a message when a claim cannot load", async () => {
  window.location.hash = "#/claims/CLM-0000";
  mockApi({});
  render(<App />);
  expect(
    await screen.findByText("Could not load claim CLM-0000."),
  ).toBeDefined();
});

const decision = {
  decision: "approve" as const,
  payout: 1250,
  explanation: "Covered.",
  policy_section: "Section 3",
  decided_at: "2026-06-25",
};

const details = {
  "GET /api/policies/POL-2001": policy,
  "GET /api/customers/CUS-3001": customer,
};

it("shows steps and keeps polling while the agent works", async () => {
  vi.useFakeTimers();
  window.location.hash = "#/claims/CLM-1001";
  let calls = 0;
  mockApi({
    "GET /api/claims/CLM-1001": () => {
      calls += 1;
      return calls === 1
        ? {
            ...claim,
            state: "in_progress",
            steps: [
              { at: "2026-06-25T10:00:01+00:00", text: "Read the claim" },
            ],
          }
        : {
            ...claim,
            state: "decided",
            decision,
            steps: [
              { at: "2026-06-25T10:00:01+00:00", text: "Read the claim" },
            ],
          };
    },
    ...details,
  });
  render(<App />);
  await act(() => vi.advanceTimersByTimeAsync(0));
  expect(screen.getByText("Read the claim")).toBeDefined();
  expect(screen.getByText("Working.")).toBeDefined();
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(calls).toBe(2);
  expect(screen.queryByText("Working.")).toBeNull();
  await act(() => vi.advanceTimersByTimeAsync(6000));
  expect(calls).toBe(2);
});

it("runs the agent on a waiting claim", async () => {
  window.location.hash = "#/claims/CLM-1001";
  const fetchMock = mockApi({
    "GET /api/claims/CLM-1001": claim,
    "POST /api/claims/CLM-1001/run": { ...claim, state: "in_progress" },
    ...details,
  });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Run agent" }));
  await screen.findByText("No steps yet.");
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/claims/CLM-1001/run",
    expect.objectContaining({ method: "POST" }),
  );
});

it("says when the agent cannot start", async () => {
  window.location.hash = "#/claims/CLM-1001";
  mockApi({ "GET /api/claims/CLM-1001": claim, ...details });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Run agent" }));
  expect(await screen.findByText("Could not start the agent.")).toBeDefined();
});

it("signs off and pays a claim over the limit", async () => {
  window.location.hash = "#/claims/CLM-1001";
  const awaiting = { ...claim, state: "awaiting_sign_off", decision };
  const fetchMock = mockApi({
    "GET /api/claims/CLM-1001": awaiting,
    "GET /api/handlers": [
      ...handlers,
      {
        ...handlers[0],
        handler_id: "HND-09",
        name: "Not Allowed",
        can_approve_over_limit: false,
      },
    ],
    "POST /api/claims/CLM-1001/sign-off": awaiting,
    "POST /api/claims/CLM-1001/payment": awaiting,
    ...details,
  });
  render(<App />);
  expect(await screen.findByText("Sign-off needed")).toBeDefined();
  expect(
    await screen.findByRole("option", { name: "Dana Whitfield" }),
  ).toBeDefined();
  expect(screen.queryByRole("option", { name: "Not Allowed" })).toBeNull();
  fireEvent.change(screen.getByRole("combobox"), {
    target: { value: "HND-01" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  await act(() => Promise.resolve());
  const bodies = fetchMock.mock.calls.map(([path, init]) => [path, init?.body]);
  expect(bodies).toContainEqual([
    "/api/claims/CLM-1001/sign-off",
    JSON.stringify({ handler_id: "HND-01" }),
  ]);
  expect(bodies).toContainEqual([
    "/api/claims/CLM-1001/payment",
    JSON.stringify({ amount: 1250 }),
  ]);
});

it("says when the sign-off fails", async () => {
  window.location.hash = "#/claims/CLM-1001";
  mockApi({
    "GET /api/claims/CLM-1001": {
      ...claim,
      state: "awaiting_sign_off",
      decision,
    },
    "GET /api/handlers": handlers,
    ...details,
  });
  render(<App />);
  await screen.findByRole("option", { name: "Dana Whitfield" });
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  expect(await screen.findByText("Could not sign off.")).toBeDefined();
});

it("shows the instructions read only", async () => {
  window.location.hash = "#/instructions";
  mockApi({
    "GET /api/instructions": { text: "You are the UnderCover Agent." },
  });
  render(<App />);
  expect(
    await screen.findByText("You are the UnderCover Agent."),
  ).toBeDefined();
  expect(document.querySelector("input, textarea")).toBeNull();
});

it("shows a message when the instructions cannot load", async () => {
  window.location.hash = "#/instructions";
  mockApi({});
  render(<App />);
  expect(
    await screen.findByText("Could not load the instructions."),
  ).toBeDefined();
});
