import { api, type ClaimSummary } from "./api";
import { decisionLabel, money, STATE_LABELS, STATES, words } from "./format";
import { StateBadge } from "./StateBadge";
import { useLoad } from "./useLoad";

const stillWorking = (claims: ClaimSummary[]) =>
  claims.some((claim) => claim.state === "in_progress");

export function Queue() {
  const { data: claims, error } = useLoad(api.claims, stillWorking);
  if (error) return <p className="notice">Could not load the queue.</p>;
  if (!claims) return <p className="notice">Loading the queue.</p>;

  return (
    <>
      <h1>Claims queue</h1>
      <div className="counts">
        {STATES.map((state) => (
          <section className="panel count" key={state}>
            <span className="number">
              {claims.filter((claim) => claim.state === state).length}
            </span>
            <span>{STATE_LABELS[state]}</span>
          </section>
        ))}
      </div>
      <section className="panel">
        <table>
          <thead>
            <tr>
              <th>Claim</th>
              <th>Customer</th>
              <th className="wide">Type</th>
              <th className="amount">Claimed</th>
              <th>Status</th>
              <th className="wide">Decision</th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <tr key={claim.claim_id}>
                <td className="mono">
                  <a href={`#/claims/${claim.claim_id}`}>{claim.claim_id}</a>
                </td>
                <td>{claim.customer_name}</td>
                <td className="wide">{words(claim.claim_type)}</td>
                <td className="amount mono">{money(claim.amount_claimed)}</td>
                <td>
                  <StateBadge state={claim.state} />
                </td>
                <td className="wide">
                  {claim.decision ? decisionLabel(claim.decision) : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
