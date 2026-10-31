import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { decisionLabel, money, words } from "./format";
import { claim, customer, mockApi, policy, summary } from "./test-data";

beforeEach(() => {
  window.location.hash = "";
});

afterEach(() => {
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
