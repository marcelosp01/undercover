import type { ClaimState, Decision } from "./api";

const dollars = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export const money = (amount: number) => dollars.format(amount);

export const STATE_LABELS: Record<ClaimState, string> = {
  waiting: "Waiting",
  in_progress: "In progress",
  awaiting_sign_off: "Waiting for sign-off",
  decided: "Decided",
};

export const STATES = Object.keys(STATE_LABELS) as ClaimState[];

const DECISION_LABELS: Record<Decision["decision"], string> = {
  approve: "Approved",
  decline: "Declined",
  refer: "Referred",
};

export const decisionLabel = (decision: Decision) =>
  DECISION_LABELS[decision.decision];

export function words(text: string) {
  const spaced = text.replaceAll("_", " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
