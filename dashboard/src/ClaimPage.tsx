import { useCallback, useState } from "react";
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

const working = (claim: Claim) => claim.state === "in_progress";

function Steps({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <section className="panel">
      <h2>What the agent did</h2>
      {claim.steps.length === 0 ? (
        <p className="muted">No steps yet.</p>
      ) : (
        <ol>
          {claim.steps.map((step) => (
            <li key={`${step.at}-${step.text}`}>
              <span className="mono muted">{step.at.slice(11, 19)}</span>{" "}
              {step.text}
            </li>
          ))}
        </ol>
      )}
      {claim.state === "in_progress" && <p className="muted">Working.</p>}
    </section>
  );
}

function RunAgent({
  claim,
  onDone,
}: Readonly<{ claim: Claim; onDone: () => void }>) {
  const [failed, setFailed] = useState(false);
  const run = () => {
    api
      .runAgent(claim.claim_id)
      .then(onDone)
      .catch(() => {
        setFailed(true);
      });
  };
  return (
    <section className="panel">
      <button onClick={run}>Run agent</button>
      {failed && <p className="muted">Could not start the agent.</p>}
    </section>
  );
}

function SignOff({
  claim,
  onDone,
}: Readonly<{ claim: Claim; onDone: () => void }>) {
  const load = useCallback(() => api.handlers(), []);
  const { data: handlers } = useLoad(load);
  const [chosen, setChosen] = useState("");
  const [failed, setFailed] = useState(false);
  const approvers = (handlers ?? []).filter(
    (handler) => handler.can_approve_over_limit,
  );
  const handlerId = chosen || approvers.at(0)?.handler_id;
  const payout = claim.decision?.payout ?? 0;

  const signOff = () => {
    if (!handlerId) return;
    api
      .signOff(claim.claim_id, handlerId)
      .then(() => api.pay(claim.claim_id, payout))
      .then(onDone)
      .catch(() => {
        setFailed(true);
      });
  };
  return (
    <section className="panel flagged">
      <h2>Sign-off needed</h2>
      <p>
        The payout of <span className="mono">{money(payout)}</span> is over the
        limit. A handler must sign off before it is paid.
      </p>
      <label>
        Handler{" "}
        <select
          value={handlerId ?? ""}
          onChange={(event) => {
            setChosen(event.target.value);
          }}
        >
          {approvers.map((handler) => (
            <option key={handler.handler_id} value={handler.handler_id}>
              {handler.name}
            </option>
          ))}
        </select>
      </label>{" "}
      <button onClick={signOff}>Sign off and pay</button>
      {failed && <p className="muted">Could not sign off.</p>}
    </section>
  );
}

export function ClaimPage({ id }: Readonly<{ id: string }>) {
  const load = useCallback(() => api.claim(id), [id]);
  const { data: claim, error, reload } = useLoad(load, working);
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
      {claim.state === "waiting" && <RunAgent claim={claim} onDone={reload} />}
      {claim.state === "awaiting_sign_off" && (
        <SignOff claim={claim} onDone={reload} />
      )}
      <Details claim={claim} />
      <section className="panel">
        <h2>The agent&rsquo;s decision</h2>
        <Decision claim={claim} />
      </section>
      <Steps claim={claim} />
    </>
  );
}
