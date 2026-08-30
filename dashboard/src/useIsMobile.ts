import { useEffect, useState } from "react";

const QUERY = "(max-width: 860px)";

/** True below the breakpoint where the sidebar switches from push-layout to
 *  an overlay drawer -- there isn't room to permanently reserve 236px on a
 *  phone screen. */
export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== "undefined" && window.matchMedia(QUERY).matches,
  );

  useEffect(() => {
    const mql = window.matchMedia(QUERY);
    const onChange = () => setIsMobile(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return isMobile;
}
