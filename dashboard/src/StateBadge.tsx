import type { ClaimState } from "./api";
import { STATE_LABELS } from "./format";

export function StateBadge({ state }: Readonly<{ state: ClaimState }>) {
  return <span className={`badge ${state}`}>{STATE_LABELS[state]}</span>;
}
