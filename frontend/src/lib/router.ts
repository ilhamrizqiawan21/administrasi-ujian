import { useEffect, useState } from "react";

export function useHashRoute(): [string, (path: string) => void] {
  const readHash = () => {
    const raw = window.location.hash.replace(/^#/, "");
    return raw.startsWith("/") ? raw : "/";
  };

  const [route, setRoute] = useState<string>(readHash);

  useEffect(() => {
    const onHashChange = () => setRoute(readHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  function navigate(path: string) {
    const target = path.startsWith("/") ? path : `/${path}`;
    window.location.hash = `#${target}`;
    setRoute(target);
  }

  return [route, navigate];
}
