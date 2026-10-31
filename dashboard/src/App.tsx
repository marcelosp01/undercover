import { useEffect, useState } from "react";
import { ClaimPage } from "./ClaimPage";
import { Queue } from "./Queue";

function useRoute() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onChange = () => {
      setHash(window.location.hash);
    };
    window.addEventListener("hashchange", onChange);
    return () => {
      window.removeEventListener("hashchange", onChange);
    };
  }, []);
  return hash.replace(/^#/, "") || "/";
}

export function App() {
  const route = useRoute();
  const claimId = /^\/claims\/(.+)$/.exec(route)?.[1];

  return (
    <>
      <header>
        <a className="brand" href="#/">
          UnderCover
        </a>
        <span className="tagline">Travel insurance claims</span>
      </header>
      <main>
        {claimId ? <ClaimPage key={claimId} id={claimId} /> : <Queue />}
      </main>
    </>
  );
}
