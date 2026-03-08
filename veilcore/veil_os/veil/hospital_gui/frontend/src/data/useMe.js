import { useEffect, useState } from "react";
import { apiFetch } from "./api";

export function useMe() {
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const data = await apiFetch("/api/auth/me");
        if (alive) setMe(data);
      } catch {
        if (alive) setMe(null);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  // Adjust if your roles differ:
  const canRestart = !!me && (me.role === "admin" || me.role === "operator");

  return { me, loading, canRestart };
}
