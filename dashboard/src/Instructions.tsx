import { api } from "./api";
import { useLoad } from "./useLoad";

export function Instructions() {
  const { data, error } = useLoad(api.instructions);
  if (error) return <p className="notice">Could not load the instructions.</p>;
  if (!data) return <p className="notice">Loading the instructions.</p>;
  return (
    <>
      <h1>Agent instructions</h1>
      <p className="muted">
        This is what the agent reads before every claim. It is read only.
      </p>
      <section className="panel">
        <pre className="instructions">{data.text}</pre>
      </section>
    </>
  );
}
