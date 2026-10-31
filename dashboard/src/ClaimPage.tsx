import { useCallback } from "react";
import { api, type Claim } from "./api";
import { decisionLabel, money, words } from "./format";
import { StateBadge } from "./StateBadge";
import { useLoad } from "./useLoad";

function Decision({ claim }: Readonly<{ claim: Claim }>) {
  const { decision, payment, sign_off: signOff } = claim;
  if (!decision) {
    return <p className="muted">No decision yet.</p>;
  }
  return (
    <>
      <p>
        <strong>{decisionLabel(decision)}</strong>
        {decision.decision === "approve" && (
          <>
            {" "}
            for <span className="mono">{money(decision.payout)}</span>
          </>
        )}
      </p>
      <p>{decision.explanation}</p>
      <p className="muted">{decision.policy_section}</p>
      {signOff && <p className="muted">Signed off by {signOff.name}.</p>}
      {payment && (
        <p className="muted">
          Paid <span className="mono">{money(payment.amount)}</span>.
        </p>
      )}
    </>
  );
}

function Details({ claim }: Readonly<{ claim: Claim }>) {
  const loadPolicy = useCallback(() => api.policy(claim.policy_id), [claim]);
  const loadCustomer = useCallback(
    () => api.customer(claim.customer_id),
    [claim],
  );
  const { data: policy } = useLoad(loadPolicy);
  const { data: customer } = useLoad(loadCustomer);

  return (
    <section className="panel">
      <h2>Policy and customer</h2>
      {policy && (
        <p>
          <span className="mono">{policy.policy_id}</span>, {words(policy.plan)}{" "}
          plan
          {policy.add_ons.length > 0 &&
            `, with ${policy.add_ons.map(words).join(", ").toLowerCase()}`}
          . Trip to {policy.trip.destination}, {policy.trip.departs_on} to{" "}
          {policy.trip.returns_on}, costing{" "}
          <span className="mono">{money(policy.trip.trip_cost)}</span>.
          Travelers: {policy.travelers.join(", ")}.
        </p>
      )}
      {customer && (
        <>
          <p>
            {customer.name}, customer since {customer.customer_since}.
          </p>
          {customer.previous_claims.length === 0 ? (
            <p className="muted">No earlier claims.</p>
          ) : (
            <ul>
              {customer.previous_claims.map((earlier) => (
                <li key={earlier.claim_id}>
                  <span className="mono">{earlier.claim_id}</span>{" "}
                  {earlier.incident_date}: {earlier.summary}.{" "}
                  {words(earlier.outcome)},{" "}
                  <span className="mono">{money(earlier.amount_paid)}</span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

export function ClaimPage({ id }: Readonly<{ id: string }>) {
  const load = useCallback(() => api.claim(id), [id]);
  const { data: claim, error } = useLoad(load);
  if (error) return <p className="notice">Could not load claim {id}.</p>;
  if (!claim) return <p className="notice">Loading claim {id}.</p>;

  return (
    <>
      <p>
        <a href="#/">Back to the queue</a>
      </p>
      <h1>
        <span className="mono">{claim.claim_id}</span>{" "}
        <StateBadge state={claim.state} />
      </h1>
      <section className="panel">
        <h2>{claim.summary}</h2>
        <p className="muted">
          {words(claim.claim_type)}. Incident on {claim.incident_date} in{" "}
          {claim.incident_location}. Submitted {claim.submitted_on}.
        </p>
        <p>{claim.story}</p>
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th className="wide">Category</th>
              <th className="amount">Amount</th>
            </tr>
          </thead>
          <tbody>
            {claim.items.map((item) => (
              <tr key={item.description}>
                <td>{item.description}</td>
                <td className="wide">{words(item.category)}</td>
                <td className="amount mono">{money(item.amount)}</td>
              </tr>
            ))}
            <tr>
              <th>Total claimed</th>
              <td className="wide" />
              <td className="amount mono">{money(claim.amount_claimed)}</td>
            </tr>
          </tbody>
        </table>
      </section>
      <section className="panel">
        <h2>Documents</h2>
        {claim.documents.map((document) => (
          <div key={document.name}>
            <h3>{document.name}</h3>
            <p>{document.content}</p>
          </div>
        ))}
      </section>
      <Details claim={claim} />
      <section className="panel">
        <h2>The agent&rsquo;s decision</h2>
        <Decision claim={claim} />
      </section>
    </>
  );
}
